import os
import tempfile
import unittest

from db_store import connect_history_db


class DatabaseStoreTests(unittest.TestCase):
    def test_sqlite_schema_is_created_and_usable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "history.sqlite3")
            conn = connect_history_db(sqlite_path=path)
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            self.assertTrue({"fixtures", "snapshots", "odds_history", "predictions", "league_inventory", "alerts_sent", "alerts_pending", "paper_bets", "provider_health", "collector_runs"}.issubset(tables))
            conn.execute(
                "INSERT INTO fixtures (fixture_key, source, home, away, last_seen) VALUES (?, ?, ?, ?, ?)",
                ("test|1", "test", "Home", "Away", "2026-10-12T00:00:00+00:00")
            )
            conn.commit()
            row = conn.execute("SELECT home, away FROM fixtures WHERE fixture_key=?", ("test|1",)).fetchone()
            self.assertEqual(row["home"], "Home")
            conn.close()


if __name__ == "__main__":
    unittest.main()
