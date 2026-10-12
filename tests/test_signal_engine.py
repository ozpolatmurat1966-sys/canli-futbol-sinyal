import unittest

from signal_engine import build_trend_rows, format_telegram_message, summarize_odds_movements


class SignalEngineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {"home": "Home FC", "away": "Away FC", "league": "Test League"}
        self.snapshots = [
            {"observed_at": "2026-10-12T10:00:00+00:00", "home_goals": 0, "away_goals": 0, "corners_home": 1, "corners_away": 1},
            {"observed_at": "2026-10-12T10:05:00+00:00", "home_goals": 1, "away_goals": 0, "corners_home": 3, "corners_away": 1},
            {"observed_at": "2026-10-12T10:10:00+00:00", "home_goals": 1, "away_goals": 1, "corners_home": 4, "corners_away": 2},
            {"observed_at": "2026-10-12T10:15:00+00:00", "home_goals": 2, "away_goals": 1, "corners_home": 5, "corners_away": 2},
        ]

    def test_build_trend_rows_reports_observed_changes(self):
        rows = build_trend_rows(self.fixture, self.snapshots)
        self.assertTrue(rows)
        five = next(row for row in rows if row["Pencere"].startswith("Son 5"))
        self.assertEqual(five["Gol değişimi"], 1)
        self.assertEqual(five["Korner değişimi"], 1)
        self.assertEqual(five["Maç"], "Home FC - Away FC")

    def test_missing_corners_are_not_invented(self):
        snapshots = [
            {"observed_at": "2026-10-12T10:00:00+00:00", "home_goals": 0, "away_goals": 0},
            {"observed_at": "2026-10-12T10:05:00+00:00", "home_goals": 0, "away_goals": 0},
        ]
        rows = build_trend_rows(self.fixture, snapshots)
        self.assertTrue(rows)
        self.assertIsNone(rows[0]["Korner değişimi"])
        self.assertEqual(rows[0]["Korner önce/sonra"], "Veri yok")

    def test_telegram_message_is_bounded_and_disclaims_advice(self):
        message = format_telegram_message([f"signal {i}" for i in range(30)])
        self.assertIn("kazanma garantisi değildir", message)
        self.assertIn("signal 0", message)
        self.assertNotIn("signal 25", message)

    def test_movement_helper_accepts_rows(self):
        rows = summarize_odds_movements(rows=[{"latest_odd": 2.1, "previous_odd": 1.9}])
        self.assertEqual(rows[0]["latest_odd"], 2.1)


if __name__ == "__main__":
    unittest.main()
