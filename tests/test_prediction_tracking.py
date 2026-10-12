import os
import tempfile
import unittest

from db_store import connect_history_db
from prediction_tracking import settle_fixture_predictions, record_pre_match_predictions


class PredictionTrackingTests(unittest.TestCase):
    def test_settles_only_targets_with_final_data(self):
        with tempfile.TemporaryDirectory() as directory:
            conn = connect_history_db(sqlite_path=os.path.join(directory, "history.sqlite3"))
            try:
                conn.execute("""INSERT INTO fixtures
                    (fixture_key, source, match_date, league, home, away, status,
                     home_goals, away_goals, finished, last_seen, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("f1", "test", "2026-10-12T18:00:00+00:00", "Test League", "Alpha", "Beta",
                     "FT", 2, 1, 1, "2026-10-12T20:00:00+00:00",
                     '{"corners":{"home":5,"away":3},"cards":{"home":{"yellow":2,"red":0},"away":{"yellow":3,"red":0}}}'))
                for i, target in enumerate(("team_poisson_v1:home_win", "team_poisson_v1:over_2_5_goals",
                                            "team_poisson_v1:over_9_5_corners", "team_poisson_v1:over_4_5_cards"), start=1):
                    conn.execute("""INSERT INTO predictions
                        (fixture_key, created_at, target, probability, evaluated_result)
                        VALUES (?, ?, ?, ?, NULL)""", ("f1", "2026-10-12T17:00:00+00:00", target, 0.5))
                conn.commit()
                settled = settle_fixture_predictions(conn)
                self.assertEqual(settled, 4)
                rows = conn.execute("SELECT target, evaluated_result FROM predictions ORDER BY id").fetchall()
                self.assertEqual(rows[0]["evaluated_result"], 1)
                self.assertEqual(rows[1]["evaluated_result"], 1)
                self.assertEqual(rows[2]["evaluated_result"], 0)
                self.assertEqual(rows[3]["evaluated_result"], 1)
            finally:
                conn.close()

    def test_pre_match_predictions_skip_when_history_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            conn = connect_history_db(sqlite_path=os.path.join(directory, "history.sqlite3"))
            try:
                conn.execute("""INSERT INTO fixtures
                    (fixture_key, source, match_date, league, home, away, status, finished, last_seen, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("upcoming", "test", "2026-10-13T18:00:00+00:00", "Test League", "Alpha", "Beta",
                     "NS", 0, "2026-10-12T20:00:00+00:00", "{}"))
                conn.commit()
                self.assertEqual(record_pre_match_predictions(conn), 0)
                self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM predictions").fetchone()["n"], 0)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
