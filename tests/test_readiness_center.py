import os
import tempfile
import unittest
from unittest.mock import patch

from db_store import connect_history_db
from readiness_center import inspect_database, save_provider_checks, smoke_test_5dollar
from background_collector import istanbul_day_window


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class ReadinessCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp.name, "test.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def connect(self):
        return connect_history_db(sqlite_path=self.db_path)

    @patch("readiness_center.SESSION.get")
    def test_provider_smoke_test_checks_leagues_and_live_fixtures(self, mock_get):
        mock_get.return_value = FakeResponse(200, {"success": 1, "data": [{"id": 1}]})
        checks = smoke_test_5dollar("test-key")
        self.assertEqual(len(checks), 2)
        self.assertTrue(all(item["ok"] for item in checks))
        self.assertEqual(mock_get.call_count, 2)

    @patch("readiness_center.SESSION.get")
    def test_provider_smoke_test_reports_http_error(self, mock_get):
        mock_get.return_value = FakeResponse(401, {}, "unauthorized")
        checks = smoke_test_5dollar("bad-key")
        self.assertTrue(all(not item["ok"] for item in checks))
        self.assertIn("401", checks[0]["detail"])

    def test_provider_checks_are_persisted(self):
        save_provider_checks(self.connect, [{"provider": "test", "ok": True, "detail": "HTTP 200"}])
        conn = self.connect()
        try:
            row = conn.execute("SELECT provider, ok, detail FROM provider_health WHERE provider='test'").fetchone()
            self.assertEqual(row["provider"], "test")
            self.assertEqual(row["ok"], 1)
            self.assertEqual(row["detail"], "HTTP 200")
        finally:
            conn.close()

    def test_cross_source_score_conflicts_are_flagged(self):
        conn = self.connect()
        try:
            for source, home, away, hg, ag in (
                ("FeedA", "Alpha FC", "Beta FC", 1, 0),
                ("FeedB", "Alpha", "Beta", 2, 0),
            ):
                conn.execute("""INSERT INTO fixtures
                    (fixture_key, source, match_date, league, home, away, status,
                     home_goals, away_goals, finished, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (source + "|1", source, "2026-10-12T18:00:00Z", "Test League",
                     home, away, "FT", hg, ag, 1, "2026-10-12T20:00:00+00:00"))
            conn.commit()
        finally:
            conn.close()
        result = inspect_database(self.connect)
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertIn("1-0", result["conflicts"][0]["Farklı skorlar"])
        self.assertIn("2-0", result["conflicts"][0]["Farklı skorlar"])

    def test_istanbul_day_window_is_24_hours(self):
        from datetime import datetime, timezone
        start, end = istanbul_day_window(datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(end - start, 86400)


if __name__ == "__main__":
    unittest.main()
