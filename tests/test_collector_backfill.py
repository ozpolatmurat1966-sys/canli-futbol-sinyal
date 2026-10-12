import json
import os
import tempfile
import unittest
from unittest.mock import patch

from background_collector import collect_historical_batch
from db_store import connect_history_db


class HistoricalBackfillTests(unittest.TestCase):
    def test_backfill_paginates_and_persists_cursor(self):
        with tempfile.TemporaryDirectory() as directory:
            conn = connect_history_db(sqlite_path=os.path.join(directory, "history.sqlite3"))
            try:
                conn.execute("""INSERT INTO league_inventory
                    (provider, provider_league_id, name, country, is_popular, observed_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    ("5DollarFootballAPI", "39", "Test League", "Test", 1, "2026-10-12T00:00:00+00:00"))
                conn.commit()
                with patch("background_collector.request_payload", return_value={
                    "success": 1, "data": [], "pagination": {"has_more": True}
                }) as request:
                    result = collect_historical_batch(conn)
                request.assert_called_once_with(
                    "/leagues/39/fixtures", {"status": "finished", "page": 1, "per_page": 100}
                )
                self.assertEqual(result["page"], 1)
                self.assertTrue(result["has_more"])
                state = conn.execute(
                    "SELECT state_value FROM collector_state WHERE state_key=?",
                    ("finished_fixture_backfill",)
                ).fetchone()
                self.assertEqual(json.loads(state["state_value"]), {"league_index": 0, "page": 2})
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
