"""SQLite/PostgreSQL-compatible history storage for the Streamlit app and collector worker."""
import os
import sqlite3


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS fixtures (
        fixture_key TEXT PRIMARY KEY, source TEXT, match_date TEXT, league TEXT,
        home TEXT, away TEXT, status TEXT, minute INTEGER, home_goals INTEGER,
        away_goals INTEGER, finished INTEGER DEFAULT 0, last_seen TEXT, raw_json TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fixture_key TEXT NOT NULL, observed_at TEXT NOT NULL,
        minute INTEGER, status TEXT, home_goals INTEGER, away_goals INTEGER,
        corners_home REAL, corners_away REAL, stats_json TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS odds_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fixture_key TEXT NOT NULL, observed_at TEXT NOT NULL,
        market TEXT, option_name TEXT, bookmaker TEXT, odd REAL, stage TEXT, line TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fixture_key TEXT NOT NULL, created_at TEXT NOT NULL,
        target TEXT NOT NULL, probability REAL NOT NULL, baseline_minute INTEGER,
        baseline_home_goals INTEGER, baseline_away_goals INTEGER, baseline_corners REAL,
        evaluated_result INTEGER, evaluated_at TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_fixture_time ON snapshots(fixture_key, observed_at)",
    "CREATE INDEX IF NOT EXISTS idx_odds_fixture_time ON odds_history(fixture_key, observed_at)",
    "CREATE INDEX IF NOT EXISTS idx_predictions_fixture_time ON predictions(fixture_key, created_at)",
    """CREATE TABLE IF NOT EXISTS league_inventory (
        provider TEXT NOT NULL, provider_league_id TEXT NOT NULL, name TEXT, country TEXT,
        last_fixture_utc TEXT, is_popular INTEGER DEFAULT 0, observed_at TEXT,
        UNIQUE(provider, provider_league_id)
    )""",
    """CREATE TABLE IF NOT EXISTS provider_health (
        provider TEXT PRIMARY KEY, ok INTEGER NOT NULL DEFAULT 0, detail TEXT, checked_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS collector_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_at TEXT NOT NULL, status TEXT NOT NULL, detail TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_collector_runs_time ON collector_runs(run_at)",
    """CREATE TABLE IF NOT EXISTS alerts_sent (
        alert_key TEXT PRIMARY KEY, fixture_key TEXT, sent_at TEXT, message TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS alerts_pending (
        alert_key TEXT PRIMARY KEY, fixture_key TEXT, created_at TEXT, message TEXT,
        attempts INTEGER DEFAULT 0, last_error TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS paper_bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fixture_key TEXT, market TEXT, selection TEXT,
        odds REAL, model_probability REAL, stake REAL, placed_at TEXT,
        settled_result INTEGER, settled_at TEXT, status TEXT DEFAULT 'open'
    )""",
]


class PostgresCompat:
    """Small adapter for the SQLite-style execute/row-key API used in app.py."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=()):
        sql = sql.strip()
        if sql.upper().startswith("PRAGMA "):
            return None
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
        sql = sql.replace("?", "%s")
        return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def connect_history_db(database_url=None, sqlite_path=None):
    database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
    if database_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL ayarlı ancak psycopg kurulu değil; requirements.txt bağımlılıklarını yükle.") from exc
        conn = PostgresCompat(psycopg.connect(database_url, row_factory=dict_row, connect_timeout=10))
        try:
            for statement in SCHEMA:
                conn.execute(statement)
            conn.commit()
        except Exception:
            conn.close()
            raise
        return conn
    path = sqlite_path or os.getenv("FOOTBALL_HISTORY_DB_PATH", "football_history.sqlite3")
    conn = sqlite3.connect(path, timeout=8)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    for statement in SCHEMA:
        conn.execute(statement)
    conn.commit()
    return conn
