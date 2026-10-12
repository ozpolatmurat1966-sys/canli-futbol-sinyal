import unittest

from model_engine import calibrate_probability, evaluate_calibration
from player_props import extract_player_prop_rows


class ModelEngineTests(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for i in range(100):
            p = (i % 10 + 1) / 10
            # Outcomes deliberately correlated with predicted probability.
            y = int((i % 10) >= 5)
            self.rows.append({
                "target": "next10_goal", "probability": p,
                "evaluated_result": y, "created_at": f"2026-10-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00"
            })

    def test_calibration_waits_for_minimum_history(self):
        calibrated, n = calibrate_probability(self.rows[:20], "next10_goal", 0.65, min_samples=50)
        self.assertIsNone(calibrated)
        self.assertEqual(n, 20)

    def test_calibration_returns_smoothed_probability(self):
        calibrated, n = calibrate_probability(self.rows, "next10_goal", 0.65, min_samples=50)
        self.assertIsNotNone(calibrated)
        self.assertGreater(calibrated, 0)
        self.assertLess(calibrated, 1)
        self.assertEqual(n, 30)

    def test_holdout_evaluation_is_chronological_and_guarded(self):
        result = evaluate_calibration(self.rows, "next10_goal", min_samples=50)
        self.assertTrue(result["ready"])
        self.assertGreater(result["test_samples"], 0)
        self.assertIn("brier_raw", result)
        small = evaluate_calibration(self.rows[:10], "next10_goal", min_samples=50)
        self.assertFalse(small["ready"])


class PlayerPropTests(unittest.TestCase):
    def test_extracts_only_explicit_player_markets(self):
        payload = {"bookmakers": [{
            "name": "TestBook",
            "odds": {"player_shots": [{
                "market": "Player Shots",
                "player": {"name": "Player One"},
                "selection": "Over 1.5",
                "odd": 2.2,
                "line": 1.5,
                "stage": "opening"
            }]}
        }]}
        rows = extract_player_prop_rows(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Oyuncu"], "Player One")
        self.assertEqual(rows[0]["Oran"], 2.2)

    def test_does_not_infer_player_prop_without_player_market(self):
        payload = {"market": "Match Winner", "selection": "Home", "odd": 1.8}
        self.assertEqual(extract_player_prop_rows(payload), [])


if __name__ == "__main__":
    unittest.main()
