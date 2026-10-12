"""Independent polling worker. Run as a separate background service, not inside Streamlit."""
import argparse
import hashlib
import json
import logging
import os
import signal
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from db_store import connect_history_db
from player_props import extract_player_prop_rows

API_BASE = "https://api.5dollarfootballapi.com/v1"
API_KEY = os.getenv("FIVE_DOLLAR_FOOTBALL_API_KEY", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
POLL_SECONDS = max(60, int(os.getenv("COLLECTOR_POLL_SECONDS", "90")))
STATS_EVERY = max(1, int(os.getenv("COLLECTOR_STATS_EVERY", "3")))
ODDS_EVERY = max(1, int(os.getenv("COLLECTOR_ODDS_EVERY", "5")))
MAX_FIXTURES = max(1, int(os.getenv("COLLECTOR_MAX_FIXTURES", "30")))
DATE_FIXTURES_EVERY = max(1, int(os.getenv("COLLECTOR_DATE_FIXTURES_EVERY", "12")))
STOP = False

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("football-collector")

# Retry idempotent requests on transient provider errors and honor Retry-After.
SESSION = requests.Session()
_RETRY = Retry(total=3, connect=3, read=2, status=3, backoff_factor=0.6,
               status_forcelist=(429, 500, 502, 503, 504),
               allowed_methods=frozenset({"GET"}), respect_retry_after_header=True)
_ADAPTER = HTTPAdapter(max_retries=_RETRY)
SESSION.mount("https://", _ADAPTER)
SESSION.mount("http://", _ADAPTER)


def stop_worker(*_):
    global STOP
    STOP = True


signal.signal(signal.SIGINT, stop_worker)
signal.signal(signal.SIGTERM, stop_worker)


def request_payload(path, params=None):
    response = SESSION.get(
        f"{API_BASE}{path}", params=params,
        headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"},
        timeout=20,
    )
    remaining = response.headers.get("X-RateLimit-Remaining") or response.headers.get("RateLimit-Remaining")
    if remaining is not None:
        log.info("Provider quota remaining=%s endpoint=%s", remaining, path)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} for {path}: {response.text[:160]}")
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("success") == 0:
        raise RuntimeError(str((payload.get("error") or {}).get("message") if isinstance(payload, dict) else "Unexpected JSON response"))
    return payload


def request_json(path, params=None):
    payload = request_payload(path, params)
    return payload.get("data") or payload.get("response") or []


def normalize_fixture(item):
    if not isinstance(item, dict):
        return None
    teams = item.get("teams") or {}
    home_obj, away_obj = teams.get("home") or {}, teams.get("away") or {}
    home = home_obj.get("name") if isinstance(home_obj, dict) else home_obj
    away = away_obj.get("name") if isinstance(away_obj, dict) else away_obj
    if not home or not away:
        return None
    goals = item.get("goals") or item.get("score") or {}
    status_obj = item.get("status")
    if isinstance(status_obj, dict):
        raw_status = str(status_obj.get("long") or status_obj.get("name") or status_obj.get("short") or item.get("state") or item.get("status_name") or item.get("status_code") or "unknown").strip()
        status_minute = status_obj.get("elapsed")
    else:
        raw_status = str(status_obj or item.get("state") or item.get("status_name") or item.get("status_code") or "unknown").strip()
        status_minute = None
    status_lower = raw_status.lower().replace("-", "_").replace(" ", "_")
    minute = item.get("minute", item.get("elapsed", status_minute))
    try:
        minute = int(minute) if minute is not None else None
    except (TypeError, ValueError):
        minute = None
    if status_lower in ("half", "ht", "half_time", "halftime", "break", "interval"):
        short = "HT"
    elif status_lower in ("finished", "full", "full_time", "ft", "after_extra_time", "after_penalties", "completed"):
        short = "FT"
    elif status_lower in ("scheduled", "not_started", "ns", "upcoming", "fixture", "pre_match"):
        short = "NS"
    elif status_lower in ("postponed", "pst"):
        short = "PST"
    elif status_lower in ("cancelled", "canceled", "canc"):
        short = "CANC"
    elif status_lower in ("unknown", "") and minute is None:
        short = "NS"
    else:
        short = "LIVE"
    league = item.get("league") or {}
    if not isinstance(league, dict):
        league = {"name": str(league)}
    country = item.get("country") or {}
    country_name = country.get("name", "") if isinstance(country, dict) else str(country or "")
    return {
        "fixture": {"id": item.get("id"), "date": item.get("kickoff_utc") or item.get("date") or item.get("starting_at") or item.get("kickoff"),
                    "status": {"long": raw_status, "short": short, "elapsed": minute}},
        "league": {"id": league.get("id"), "name": league.get("name", "Lig bilinmiyor"),
                   "country": country_name, "round": item.get("round")},
        "teams": {"home": {"id": home_obj.get("id") if isinstance(home_obj, dict) else None, "name": home},
                  "away": {"id": away_obj.get("id") if isinstance(away_obj, dict) else None, "name": away}},
        "goals": {"home": goals.get("home"), "away": goals.get("away")},
        "corners": item.get("corners") or {},
        "cards": item.get("cards") or {},
        "_source": "5DollarFootballAPI", "source": "5DollarFootballAPI",
        "_raw_5dollar": item,
    }


def extract_corners(stats, fixture):
    values = {"home": None, "away": None}
    direct = (fixture or {}).get("corners") or {}
    if isinstance(direct, dict):
        values.update({k: direct.get(k) for k in ("home", "away") if direct.get(k) is not None})
    def walk(node, side=None):
        if isinstance(node, list):
            for item in node:
                walk(item, side)
        elif isinstance(node, dict):
            label = " ".join(str(node.get(k) or "") for k in ("type", "name", "statistic", "label")).lower()
            team = node.get("team") or node.get("side") or side
            if "corner" in label or "korner" in label:
                key = None
                if isinstance(team, dict):
                    team = team.get("name") or team.get("side")
                text_team = str(team or "").lower()
                if text_team in ("home", "home team", "ev sahibi"):
                    key = "home"
                elif text_team in ("away", "away team", "deplasman"):
                    key = "away"
                value = node.get("value", node.get("total"))
                if key and value is not None:
                    values[key] = value
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, key if key in ("home", "away") else team)
    walk(stats)
    return values


def fixture_key(match):
    fixture = match.get("fixture") or {}
    fid = fixture.get("id")
    teams = match.get("teams") or {}
    home = (teams.get("home") or {}).get("name") or "home"
    away = (teams.get("away") or {}).get("name") or "away"
    identity = str(fid) if fid is not None else f'{fixture.get("date")}|{home}|{away}'
    return f'5DollarFootballAPI|{identity}'


def save_snapshot(conn, match, stats=None):
    fixture = match.get("fixture") or {}
    teams = match.get("teams") or {}
    league = match.get("league") or {}
    status = (fixture.get("status") or {})
    status_short = str(status.get("short") or status.get("long") or "unknown")
    minute = status.get("elapsed")
    goals = match.get("goals") or {}
    corners = extract_corners(stats, match)
    now = datetime.now(timezone.utc).isoformat()
    key = fixture_key(match)
    home = (teams.get("home") or {}).get("name") or "Ev sahibi"
    away = (teams.get("away") or {}).get("name") or "Deplasman"
    finished = int(status_short.upper() in ("FT", "AET", "PEN", "FINISHED", "FULL_TIME"))
    conn.execute("""INSERT INTO fixtures
        (fixture_key, source, match_date, league, home, away, status, minute, home_goals, away_goals, finished, last_seen, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fixture_key) DO UPDATE SET
        match_date=excluded.match_date, league=excluded.league, home=excluded.home, away=excluded.away,
        status=excluded.status, minute=excluded.minute, home_goals=excluded.home_goals,
        away_goals=excluded.away_goals, finished=excluded.finished, last_seen=excluded.last_seen, raw_json=excluded.raw_json""",
        (key, "5DollarFootballAPI", str(fixture.get("date") or ""), str(league.get("name") or "Lig bilinmiyor"),
         str(home), str(away), status_short, minute, goals.get("home"), goals.get("away"), finished, now,
         json.dumps(match.get("_raw_5dollar") or match, ensure_ascii=False, default=str)))
    last = conn.execute("SELECT * FROM snapshots WHERE fixture_key=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
    changed = (not last or last["minute"] != minute or last["status"] != status_short
               or last["home_goals"] != goals.get("home") or last["away_goals"] != goals.get("away")
               or (corners["home"] is not None and str(last["corners_home"]) != str(corners["home"]))
               or (corners["away"] is not None and str(last["corners_away"]) != str(corners["away"])) or stats is not None)
    if changed or not last:
        conn.execute("""INSERT INTO snapshots
            (fixture_key, observed_at, minute, status, home_goals, away_goals, corners_home, corners_away, stats_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, now, minute, status_short, goals.get("home"), goals.get("away"),
             corners["home"], corners["away"], json.dumps(stats, ensure_ascii=False, default=str) if stats is not None else None))
    conn.commit()
    change_lines = []
    if last:
        old_home, old_away = last["home_goals"], last["away_goals"]
        new_home, new_away = goals.get("home"), goals.get("away")
        if None not in (old_home, old_away, new_home, new_away) and (old_home != new_home or old_away != new_away):
            change_lines.append(f"Skor değişti: {home} {new_home} - {new_away} {away} (önce {old_home}-{old_away})")
        old_corners = (last["corners_home"], last["corners_away"])
        new_corners = (corners["home"], corners["away"])
        if all(v is not None for v in old_corners + new_corners) and old_corners != new_corners:
            change_lines.append(f"Korner değişti: {home} {new_corners[0]} - {new_corners[1]} {away}")
    return key, change_lines


def retry_pending_telegram_alerts(conn):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    pending = conn.execute("SELECT * FROM alerts_pending ORDER BY created_at LIMIT 50").fetchall()
    for row in pending:
        try:
            response = SESSION.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": row["message"], "disable_web_page_preview": True},
                timeout=12,
            )
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            if response.ok and payload.get("ok"):
                conn.execute("INSERT INTO alerts_sent (alert_key, fixture_key, sent_at, message) VALUES (?, ?, ?, ?) ON CONFLICT(alert_key) DO NOTHING",
                             (row["alert_key"], row["fixture_key"], datetime.now(timezone.utc).isoformat(), row["message"]))
                conn.execute("DELETE FROM alerts_pending WHERE alert_key=?", (row["alert_key"],))
                conn.commit()
                log.info("Telegram alert sent for fixture %s", row["fixture_key"])
            else:
                error = f"HTTP {response.status_code}"
                conn.execute("UPDATE alerts_pending SET attempts=attempts+1, last_error=? WHERE alert_key=?",
                             (error, row["alert_key"]))
                conn.commit()
                log.warning("Telegram alert remains queued: %s", error)
        except (requests.RequestException, ValueError) as exc:
            conn.execute("UPDATE alerts_pending SET attempts=attempts+1, last_error=? WHERE alert_key=?",
                         (str(exc)[:180], row["alert_key"]))
            conn.commit()
            log.warning("Telegram alert remains queued: %s", str(exc)[:160])


def send_telegram_alert(conn, fixture_key_value, match, change_lines):
    if not os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or not os.getenv("TELEGRAM_CHAT_ID", "").strip():
        return
    teams = match.get("teams") or {}
    home = (teams.get("home") or {}).get("name") or "Ev sahibi"
    away = (teams.get("away") or {}).get("name") or "Deplasman"
    league = (match.get("league") or {}).get("name") or "Lig bilinmiyor"
    status = match.get("fixture", {}).get("status") or {}
    minute = status.get("elapsed")
    for change in change_lines:
        message = f"⚽ {league}\n{home} - {away}\nDakika: {minute if minute is not None else '—'}\n{change}\n\nYalnızca veri değişimi bildirimi; bahis tavsiyesi değildir."
        alert_key = hashlib.sha256(f"{fixture_key_value}|{change}".encode("utf-8")).hexdigest()
        sent = conn.execute("SELECT alert_key FROM alerts_sent WHERE alert_key=?", (alert_key,)).fetchone()
        if sent:
            continue
        conn.execute("""INSERT INTO alerts_pending
            (alert_key, fixture_key, created_at, message, attempts, last_error)
            VALUES (?, ?, ?, ?, 0, NULL) ON CONFLICT(alert_key) DO NOTHING""",
            (alert_key, fixture_key_value, datetime.now(timezone.utc).isoformat(), message))
    conn.commit()
    retry_pending_telegram_alerts(conn)


def collect_leagues_if_stale(conn):
    """Refresh the provider league inventory no more than once per day."""
    latest = conn.execute("SELECT MAX(observed_at) AS observed_at FROM league_inventory").fetchone()["observed_at"]
    if latest:
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(latest).astimezone(timezone.utc)).total_seconds()
            if age < 86400:
                return
        except (TypeError, ValueError):
            pass
    saved = 0
    for page in range(1, 11):
        response = SESSION.get(f"{API_BASE}/leagues", params={"page": page, "per_page": 100},
                               headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}, timeout=20)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code} for /leagues: {response.text[:160]}")
        payload = response.json()
        if payload.get("success") == 0:
            raise RuntimeError(str((payload.get("error") or {}).get("message") or "League inventory request failed"))
        items = payload.get("data") or []
        observed = datetime.now(timezone.utc).isoformat()
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or item.get("id") is None:
                continue
            country = item.get("country") or {}
            country_name = country.get("name") if isinstance(country, dict) else str(country)
            conn.execute("""INSERT INTO league_inventory
                (provider, provider_league_id, name, country, last_fixture_utc, is_popular, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, provider_league_id) DO UPDATE SET
                name=excluded.name, country=excluded.country, last_fixture_utc=excluded.last_fixture_utc,
                is_popular=excluded.is_popular, observed_at=excluded.observed_at""",
                ("5DollarFootballAPI", str(item["id"]), str(item.get("name") or item.get("short_name") or "Lig adı yok"),
                 str(country_name or "Ülke belirtilmemiş"), str(item.get("last_fixture_utc") or ""),
                 int(bool(item.get("is_popular", False))), observed))
            saved += 1
        conn.commit()
        if not (payload.get("pagination") or {}).get("has_more", False):
            break
    log.info("League inventory refreshed: %s records", saved)


def save_odds(conn, key, payload):
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for prop in extract_player_prop_rows(payload):
        conn.execute("""INSERT INTO odds_history
            (fixture_key, observed_at, market, option_name, bookmaker, odd, stage, line)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, now, prop["Pazar"], f'{prop["Oyuncu"]}: {prop["Seçenek"]}',
             prop["Şirket"], prop["Oran"], prop["Aşama"], prop["Çizgi"]))
        count += 1
    # Also preserve recognizable top-level market prices from the provider payload.
    market_names = {
        "1x2": "Maç Sonucu (1X2)", "goal_line": "Gol Alt/Üst",
        "goal_line_half": "İlk Yarı Gol Alt/Üst", "corner_line": "Korner Alt/Üst",
        "corner_line_half": "İlk Yarı Korner Alt/Üst", "card_line": "Kart Alt/Üst",
        "card_line_half": "İlk Yarı Kart Alt/Üst", "btts": "Karşılıklı Gol",
        "asian_handicap": "Asya Handikap", "corner_asian": "Asya Korner Handikap",
        "card_asian": "Asya Kart Handikap", "player_shots": "Oyuncu Şutları",
        "player_goals": "Oyuncu Golü", "player_assists": "Oyuncu Asisti",
        "player_cards": "Oyuncu Kartı", "player_fouls": "Oyuncu Faulleri",
    }
    containers = {"data", "response", "bookmakers", "odds", "fixtures", "events", "markets"}
    def walk(node, market="Pazar", bookmaker="Bet365", stage="Mevcut", line=""):
        nonlocal count
        if isinstance(node, list):
            for item in node:
                walk(item, market, bookmaker, stage, line)
            return
        if not isinstance(node, dict):
            return
        market = str(node.get("market_name") or node.get("market") or node.get("marketName") or market)
        if isinstance(node.get("name"), str) and "odds" in node:
            bookmaker = node.get("name")
        bookmaker = str(node.get("bookmaker") or node.get("bookmaker_name") or bookmaker)
        stage = str(node.get("stage") or stage)
        line = str(node.get("line") or node.get("handicap") or line)
        # Common structured markets expose prices under outcome keys rather than an "odd" field.
        outcomes = ("home", "draw", "away", "over", "under", "yes", "no")
        for outcome in outcomes:
            try:
                price = float(node.get(outcome))
            except (TypeError, ValueError):
                continue
            if price > 1 and not any(term in market.lower() for term in ("player", "oyuncu")):
                conn.execute("""INSERT INTO odds_history
                    (fixture_key, observed_at, market, option_name, bookmaker, odd, stage, line)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (key, now, market, outcome.title(), bookmaker, price, stage, line))
                count += 1
        if any(k in node for k in ("odd", "price", "decimal_odds", "decimalOdds")):
            for price_key in ("odd", "price", "decimal_odds", "decimalOdds"):
                try:
                    price = float(node.get(price_key))
                except (TypeError, ValueError):
                    continue
                if price > 1 and not any(term in market.lower() for term in ("player", "oyuncu")):
                    selection = str(node.get("selection") or node.get("outcome") or node.get("label") or node.get("value") or price_key)
                    conn.execute("""INSERT INTO odds_history
                        (fixture_key, observed_at, market, option_name, bookmaker, odd, stage, line)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (key, now, market, selection, bookmaker, price, stage, line))
                    count += 1
                    break
        for child_key, value in node.items():
            if not isinstance(value, (dict, list)):
                continue
            child = str(child_key).lower()
            if child in containers:
                child_market = market
            elif child in ("opening", "closing", "inplay", "live"):
                child_market, child_stage = market, child.title()
                walk(value, child_market, bookmaker, child_stage, line)
                continue
            else:
                child_market = market_names.get(child, child.replace("_", " ").title())
            walk(value, child_market, bookmaker, stage, line)
    walk(payload)
    conn.commit()
    return count


def istanbul_day_window(now=None):
    """Return Unix timestamps covering the current Istanbul calendar day."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now.astimezone(ZoneInfo("Europe/Istanbul"))
    start_local = datetime.combine(local_now.date(), datetime.min.time(), tzinfo=ZoneInfo("Europe/Istanbul"))
    end_local = start_local + timedelta(days=1)
    return int(start_local.astimezone(timezone.utc).timestamp()), int(end_local.astimezone(timezone.utc).timestamp())


def collect_today_fixtures(conn):
    """Occasionally persist today's scheduled/live/completed fixtures for form and backtest datasets."""
    start_time, end_time = istanbul_day_window()
    items = request_json("/fixtures", {"start_time": start_time, "end_time": end_time, "per_page": 100})
    saved = 0
    for item in items:
        match = normalize_fixture(item)
        if not match:
            continue
        save_snapshot(conn, match, (item.get("statistics") or item.get("stats")) if isinstance(item, dict) else None)
        saved += 1
    log.info("Today's Istanbul-day fixtures observed: %s", saved)


def collect_historical_batch(conn):
    """Backfill one page of finished fixtures per hour, respecting the provider's free-tier limits."""
    leagues = conn.execute("""SELECT provider_league_id, name FROM league_inventory
        WHERE is_popular=1 ORDER BY name, provider_league_id""").fetchall()
    if not leagues:
        leagues = conn.execute("""SELECT provider_league_id, name FROM league_inventory
            ORDER BY is_popular DESC, name, provider_league_id LIMIT 5""").fetchall()
    if not leagues:
        log.info("Historical backfill skipped: no league inventory available yet")
        return {"saved": 0, "reason": "no_leagues"}

    state_row = conn.execute(
        "SELECT state_value FROM collector_state WHERE state_key=?",
        ("finished_fixture_backfill",)
    ).fetchone()
    try:
        cursor = json.loads(state_row["state_value"]) if state_row and state_row["state_value"] else {}
    except (TypeError, ValueError):
        cursor = {}
    try:
        league_index = int(cursor.get("league_index", 0)) % len(leagues)
        page = max(1, int(cursor.get("page", 1)))
    except (TypeError, ValueError):
        league_index, page = 0, 1

    league = leagues[league_index]
    league_id = str(league["provider_league_id"])
    payload = request_payload(
        f"/leagues/{league_id}/fixtures",
        {"status": "finished", "page": page, "per_page": 100},
    )
    items = payload.get("data") or payload.get("response") or []
    if isinstance(items, dict):
        items = items.get("fixtures") or items.get("data") or []
    if not isinstance(items, list):
        items = []
    saved = 0
    for item in items:
        match = normalize_fixture(item)
        if not match:
            continue
        raw = item.get("statistics") or item.get("stats")
        save_snapshot(conn, match, raw)
        saved += 1

    pagination = payload.get("pagination") or {}
    has_more = bool(pagination.get("has_more", False))
    if has_more:
        next_cursor = {"league_index": league_index, "page": page + 1}
    else:
        next_cursor = {"league_index": (league_index + 1) % len(leagues), "page": 1}
    conn.execute("""INSERT INTO collector_state (state_key, state_value, updated_at)
        VALUES (?, ?, ?) ON CONFLICT(state_key) DO UPDATE SET
        state_value=excluded.state_value, updated_at=excluded.updated_at""",
        ("finished_fixture_backfill", json.dumps(next_cursor), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    log.info("Historical fixtures page saved: league=%s (%s), page=%s, rows=%s, has_more=%s",
             league["name"], league_id, page, saved, has_more)
    return {"saved": saved, "league_id": league_id, "league": league["name"],
            "page": page, "has_more": has_more, "next_cursor": next_cursor}


def run_once(conn, cycle):
    retry_pending_telegram_alerts(conn)
    collect_leagues_if_stale(conn)
    if cycle % DATE_FIXTURES_EVERY == 0:
        try:
            collect_today_fixtures(conn)
        except Exception as exc:
            log.warning("Daily fixture collection failed: %s", str(exc)[:180])
        try:
            collect_historical_batch(conn)
        except Exception as exc:
            log.warning("Historical backfill failed: %s", str(exc)[:180])
    # A single bulk request for live fixtures plus stats/events limits free-tier request use.
    items = request_json("/fixtures", {"status": "live", "per_page": 50, "include": "stats,events"})
    matches = [normalized for item in items if (normalized := normalize_fixture(item))]
    log.info("Live fixtures received: %s", len(matches))
    for match in matches[:MAX_FIXTURES]:
        fixture_id = (match.get("fixture") or {}).get("id")
        raw = match.get("_raw_5dollar") or {}
        stats = raw.get("statistics") or raw.get("stats")
        key, changes = save_snapshot(conn, match, stats)
        if changes:
            send_telegram_alert(conn, key, match, changes)
        if fixture_id is None:
            continue
        if cycle % ODDS_EVERY == 0:
            try:
                odds = request_json(f"/fixtures/{fixture_id}/odds")
                count = save_odds(conn, key, odds)
                log.info("Saved %s odds rows for fixture %s", count, fixture_id)
            except Exception as exc:
                log.warning("Odds unavailable for fixture %s: %s", fixture_id, str(exc)[:180])


def record_collector_run(conn, status, detail):
    try:
        conn.execute("INSERT INTO collector_runs (run_at, status, detail) VALUES (?, ?, ?)",
                     (datetime.now(timezone.utc).isoformat(), str(status), str(detail)[:500]))
        conn.commit()
    except Exception as exc:
        log.warning("Could not persist collector heartbeat: %s", str(exc)[:160])


def main():
    parser = argparse.ArgumentParser(description="Independent football history collector")
    parser.add_argument("--once", action="store_true", help="Run a single collection cycle and exit")
    args = parser.parse_args()
    if not API_KEY:
        raise SystemExit("FIVE_DOLLAR_FOOTBALL_API_KEY environment variable is required.")
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL is required for a persistent independent worker; configure PostgreSQL.")
    conn = connect_history_db(DATABASE_URL)
    cycle = int(time.time() // 300) if args.once else 0
    log.info("Collector started: poll=%ss stats_every=%s odds_every=%s date_fixtures_every=%s max_fixtures=%s",
             POLL_SECONDS, STATS_EVERY, ODDS_EVERY, DATE_FIXTURES_EVERY, MAX_FIXTURES)
    while not STOP:
        if not args.once:
            cycle += 1
        started = time.monotonic()
        try:
            run_once(conn, cycle)
            record_collector_run(conn, "success", f"Tur tamamlandı; cycle={cycle}")
        except Exception as exc:
            record_collector_run(conn, "error", f"{type(exc).__name__}: {str(exc)[:420]}")
            log.exception("Collection cycle failed: %s", str(exc)[:220])
            if args.once:
                conn.close()
                raise
            try:
                conn.close()
            except Exception:
                pass
            time.sleep(3)
            conn = connect_history_db(DATABASE_URL)
        if args.once:
            break
        elapsed = time.monotonic() - started
        time.sleep(max(1, POLL_SECONDS - elapsed))
    conn.close()
    log.info("Collector stopped.")


if __name__ == "__main__":
    main()
