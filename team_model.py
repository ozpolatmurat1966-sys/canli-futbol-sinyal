"""Experimental, transparent football-market baselines from stored finished results."""
import json
import math
import re
import unicodedata
from collections import defaultdict


def _get(row, key, default=None):
    try:
        return row.get(key, default)
    except AttributeError:
        try:
            return row[key] if key in row.keys() else default
        except Exception:
            return default


def _norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", value)


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else None
    except (TypeError, ValueError):
        return None


def _pair(obj):
    if not isinstance(obj, dict):
        return None, None
    return _number(obj.get("home")), _number(obj.get("away"))


def _team_cards(value):
    if isinstance(value, dict):
        yellow, red = _number(value.get("yellow")), _number(value.get("red"))
        if yellow is None and red is None:
            return None
        return (yellow or 0.0) + (red or 0.0)
    return _number(value)


def _features(row):
    try:
        raw = json.loads(_get(row, "raw_json") or "{}")
    except (TypeError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    goals = raw.get("goals") or raw.get("score") or {}
    home_goals = _number(_get(row, "home_goals"))
    away_goals = _number(_get(row, "away_goals"))
    if home_goals is None and isinstance(goals, dict):
        home_goals = _number(goals.get("home"))
    if away_goals is None and isinstance(goals, dict):
        away_goals = _number(goals.get("away"))
    corner_home, corner_away = _pair(raw.get("corners") or {})
    cards = raw.get("cards") or {}
    if isinstance(cards, dict):
        card_home, card_away = _team_cards(cards.get("home")), _team_cards(cards.get("away"))
    else:
        card_home, card_away = None, None
    return {
        "date": str(_get(row, "match_date") or ""),
        "league": str(_get(row, "league") or ""),
        "home": str(_get(row, "home") or ""),
        "away": str(_get(row, "away") or ""),
        "home_goals": home_goals, "away_goals": away_goals,
        "corners_home": corner_home, "corners_away": corner_away,
        "cards_home": card_home, "cards_away": card_away,
    }


def _poisson(lam, max_k=18):
    lam = max(0.01, min(float(lam), 12.0))
    values = [math.exp(-lam)]
    for k in range(1, max_k + 1):
        values.append(values[-1] * lam / k)
    total = sum(values)
    return [value / total for value in values]


def _over_probability(lam, line):
    probs = _poisson(lam)
    return max(0.0, min(1.0, 1.0 - sum(probs[:int(math.floor(line)) + 1])))


def _smooth(values, prior, strength=5.0):
    return (sum(values) + prior * strength) / (len(values) + strength)


def estimate_fixture_markets(history_rows, home, away, league,
                              min_team_matches=6, min_league_matches=20, max_team_matches=10):
    """Estimate pre-match probabilities only when recent same-league history is adequate.

    This is a simple Poisson baseline, not a trained/validated betting model. Corners/cards
    use a Poisson approximation and are emitted only when their own historical samples exist.
    """
    home_key, away_key, league_key = _norm(home), _norm(away), _norm(league)
    if not home_key or not away_key or not league_key:
        return {"ready": False, "reason": "Takım veya lig kimliği eksik.", "markets": [], "samples": {}}
    candidates, seen = [], set()
    for row in history_rows or []:
        if not _get(row, "finished", 0):
            continue
        item = _features(row)
        if item["home_goals"] is None or item["away_goals"] is None:
            continue
        if _norm(item["league"]) != league_key or not item["home"] or not item["away"]:
            continue
        identity = (item["date"][:10], _norm(item["home"]), _norm(item["away"]))
        if identity in seen:
            continue
        seen.add(identity)
        candidates.append(item)
    candidates.sort(key=lambda item: item["date"], reverse=True)
    if len(candidates) < min_league_matches:
        return {"ready": False, "reason": f"Aynı ligde {len(candidates)}/{min_league_matches} tamamlanmış maç var.",
                "markets": [], "samples": {"league": len(candidates), "home_team": 0, "away_team": 0}}

    team_rows = defaultdict(list)
    for item in candidates:
        team_rows[_norm(item["home"])].append({
            "date": item["date"], "gf": item["home_goals"], "ga": item["away_goals"],
            "corners": item["corners_home"], "cards": item["cards_home"],
        })
        team_rows[_norm(item["away"])].append({
            "date": item["date"], "gf": item["away_goals"], "ga": item["home_goals"],
            "corners": item["corners_away"], "cards": item["cards_away"],
        })
    home_rows = sorted(team_rows[home_key], key=lambda item: item["date"], reverse=True)[:max_team_matches]
    away_rows = sorted(team_rows[away_key], key=lambda item: item["date"], reverse=True)[:max_team_matches]
    samples = {"league": len(candidates), "home_team": len(home_rows), "away_team": len(away_rows)}
    if len(home_rows) < min_team_matches or len(away_rows) < min_team_matches:
        return {"ready": False,
                "reason": f"Takım geçmişi yetersiz: ev sahibi {len(home_rows)}/{min_team_matches}, deplasman {len(away_rows)}/{min_team_matches}.",
                "markets": [], "samples": samples}

    league_home = sum(item["home_goals"] for item in candidates) / len(candidates)
    league_away = sum(item["away_goals"] for item in candidates) / len(candidates)
    league_team = (league_home + league_away) / 2.0
    if league_team <= 0:
        return {"ready": False, "reason": "Lig gol ortalaması hesaplanamıyor.", "markets": [], "samples": samples}
    home_attack = _smooth([r["gf"] for r in home_rows], league_team) / league_team
    home_defence = _smooth([r["ga"] for r in home_rows], league_team) / league_team
    away_attack = _smooth([r["gf"] for r in away_rows], league_team) / league_team
    away_defence = _smooth([r["ga"] for r in away_rows], league_team) / league_team
    lambda_home = max(0.05, min(5.0, league_home * home_attack * away_defence))
    lambda_away = max(0.05, min(5.0, league_away * away_attack * home_defence))
    hp, ap = _poisson(lambda_home), _poisson(lambda_away)
    p_home = p_draw = p_away = 0.0
    total_goals = [0.0] * (len(hp) + len(ap) - 1)
    for h, ph in enumerate(hp):
        for a, pa in enumerate(ap):
            joint = ph * pa
            total_goals[h + a] += joint
            if h > a:
                p_home += joint
            elif h == a:
                p_draw += joint
            else:
                p_away += joint
    total_sum = sum(total_goals)
    total_goals = [p / total_sum for p in total_goals]
    p_btts = max(0.0, min(1.0, 1.0 - hp[0] - ap[0] + hp[0] * ap[0]))
    markets = [
        {"market": "Ev sahibi kazanır", "target": "home_win", "probability": p_home},
        {"market": "Beraberlik", "target": "draw", "probability": p_draw},
        {"market": "Deplasman kazanır", "target": "away_win", "probability": p_away},
        {"market": "2,5 gol üst", "target": "over_2_5_goals", "probability": sum(total_goals[3:])},
        {"market": "1,5 gol üst", "target": "over_1_5_goals", "probability": sum(total_goals[2:])},
        {"market": "3,5 gol üst", "target": "over_3_5_goals", "probability": sum(total_goals[4:])},
        {"market": "Karşılıklı gol: Evet", "target": "btts_yes", "probability": p_btts},
    ]
    home_corner_values = [r["corners"] for r in home_rows if r["corners"] is not None]
    away_corner_values = [r["corners"] for r in away_rows if r["corners"] is not None]
    league_corner_matches = [m for m in candidates if m["corners_home"] is not None and m["corners_away"] is not None]
    if len(home_corner_values) >= min_team_matches and len(away_corner_values) >= min_team_matches and len(league_corner_matches) >= min_league_matches:
        league_corner_team = sum(m["corners_home"] + m["corners_away"] for m in league_corner_matches) / (2 * len(league_corner_matches))
        home_corners = _smooth(home_corner_values, league_corner_team)
        away_corners = _smooth(away_corner_values, league_corner_team)
        lambda_corners = home_corners + away_corners
        for line in (8.5, 9.5, 10.5):
            markets.append({"market": f"{line:.1f} korner üst", "target": f"over_{str(line).replace('.', '_')}_corners",
                            "probability": _over_probability(lambda_corners, line), "expected_total": lambda_corners,
                            "stat_samples": len(league_corner_matches)})
    home_card_values = [r["cards"] for r in home_rows if r["cards"] is not None]
    away_card_values = [r["cards"] for r in away_rows if r["cards"] is not None]
    league_card_matches = [m for m in candidates if m["cards_home"] is not None and m["cards_away"] is not None]
    if len(home_card_values) >= min_team_matches and len(away_card_values) >= min_team_matches and len(league_card_matches) >= min_league_matches:
        league_card_team = sum(m["cards_home"] + m["cards_away"] for m in league_card_matches) / (2 * len(league_card_matches))
        home_cards = _smooth(home_card_values, league_card_team)
        away_cards = _smooth(away_card_values, league_card_team)
        lambda_cards = home_cards + away_cards
        for line in (3.5, 4.5, 5.5):
            markets.append({"market": f"{line:.1f} kart üst", "target": f"over_{str(line).replace('.', '_')}_cards",
                            "probability": _over_probability(lambda_cards, line), "expected_total": lambda_cards,
                            "stat_samples": len(league_card_matches)})
    return {
        "ready": True, "reason": "Deneysel Poisson tabanı; henüz doğrulanmış bahis modeli değildir.",
        "samples": samples, "expected_goals_home": lambda_home, "expected_goals_away": lambda_away,
        "markets": markets,
    }
