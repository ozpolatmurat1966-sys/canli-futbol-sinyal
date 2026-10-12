"""Record and evaluate experimental pre-match model probabilities against final results."""
import json
import re
from datetime import datetime, timezone

from team_model import estimate_fixture_markets


MODEL_PREFIX = "team_poisson_v1:"


def _parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def record_pre_match_predictions(conn, now=None):
    """Save each pre-match model target once, only with sufficient same-league history."""
    now = now or datetime.now(timezone.utc)
    history = [dict(row) for row in conn.execute("""SELECT fixture_key, match_date, league, home, away,
        home_goals, away_goals, finished, status, raw_json FROM fixtures
        WHERE finished=1 AND home_goals IS NOT NULL AND away_goals IS NOT NULL
        ORDER BY match_date DESC LIMIT 5000""").fetchall()]
    upcoming = conn.execute("""SELECT fixture_key, match_date, league, home, away, status, finished
        FROM fixtures WHERE finished=0 AND UPPER(status) IN ('NS','SCHEDULED','NOT_STARTED','FIXTURE')
        AND home IS NOT NULL AND away IS NOT NULL ORDER BY match_date LIMIT 100""").fetchall()
    saved = 0
    created_at = now.astimezone(timezone.utc).isoformat()
    for match in upcoming:
        kickoff = _parse_dt(match["match_date"])
        if kickoff is None or kickoff <= now.astimezone(timezone.utc):
            continue
        result = estimate_fixture_markets(history, match["home"], match["away"], match["league"])
        if not result.get("ready"):
            continue
        for market in result["markets"]:
            target = MODEL_PREFIX + str(market["target"])
            exists = conn.execute("SELECT 1 FROM predictions WHERE fixture_key=? AND target=? LIMIT 1",
                                  (match["fixture_key"], target)).fetchone()
            if exists:
                continue
            conn.execute("""INSERT INTO predictions
                (fixture_key, created_at, target, probability, baseline_minute,
                 baseline_home_goals, baseline_away_goals, baseline_corners, evaluated_result, evaluated_at)
                VALUES (?, ?, ?, ?, 0, NULL, NULL, NULL, NULL, NULL)""",
                (match["fixture_key"], created_at, target, float(market["probability"])))
            saved += 1
    conn.commit()
    return saved


def _number(value):
    try:
        number = float(value)
        return number if number >= 0 else None
    except (TypeError, ValueError):
        return None


def _cards_total(raw):
    cards = (raw or {}).get("cards") or {}
    if not isinstance(cards, dict) or not isinstance(cards.get("home"), dict) or not isinstance(cards.get("away"), dict):
        return None
    total = 0.0
    found = False
    for side in ("home", "away"):
        for kind in ("yellow", "red"):
            value = _number(cards[side].get(kind))
            if value is not None:
                total += value
                found = True
    return total if found else None


def _target_result(target, home_goals, away_goals, raw):
    if home_goals is None or away_goals is None:
        return None
    if target == "home_win":
        return int(home_goals > away_goals)
    if target == "draw":
        return int(home_goals == away_goals)
    if target == "away_win":
        return int(home_goals < away_goals)
    if target == "btts_yes":
        return int(home_goals > 0 and away_goals > 0)
    goal_match = re.fullmatch(r"over_(\d+)_(\d+)_goals", target)
    if goal_match:
        line = float(f"{goal_match.group(1)}.{goal_match.group(2)}")
        return int(home_goals + away_goals > line)
    stat_match = re.fullmatch(r"over_(\d+)_(\d+)_(corners|cards)", target)
    if stat_match:
        line = float(f"{stat_match.group(1)}.{stat_match.group(2)}")
        if stat_match.group(3) == "corners":
            corners = (raw or {}).get("corners") or {}
            if not isinstance(corners, dict):
                return None
            home, away = _number(corners.get("home")), _number(corners.get("away"))
            if home is None or away is None:
                return None
            return int(home + away > line)
        total_cards = _cards_total(raw)
        return None if total_cards is None else int(total_cards > line)
    return None


def settle_fixture_predictions(conn):
    """Settle only targets with sufficient final data; missing stats remain unevaluated."""
    rows = conn.execute("""SELECT p.id, p.target, f.home_goals, f.away_goals, f.raw_json
        FROM predictions p JOIN fixtures f ON f.fixture_key=p.fixture_key
        WHERE p.target LIKE ? AND p.evaluated_result IS NULL AND f.finished=1""",
        (MODEL_PREFIX + "%",)).fetchall()
    settled = 0
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except (TypeError, ValueError):
            raw = {}
        target = str(row["target"]).removeprefix(MODEL_PREFIX)
        result = _target_result(target, _number(row["home_goals"]), _number(row["away_goals"]), raw)
        if result is None:
            continue
        conn.execute("UPDATE predictions SET evaluated_result=?, evaluated_at=? WHERE id=? AND evaluated_result IS NULL",
                     (result, now, row["id"]))
        settled += 1
    conn.commit()
    return settled
