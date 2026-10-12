import unittest

from market_engine import detect_odds_movements, normalize_implied_probabilities


class MarketEngineTests(unittest.TestCase):
    def test_no_vig_probabilities_sum_to_one_and_report_margin(self):
        result = normalize_implied_probabilities({"home": 2.0, "draw": 3.5, "away": 4.0})
        self.assertAlmostEqual(sum(result["fair_probabilities"].values()), 1.0)
        self.assertGreater(result["overround"], 0)
        self.assertAlmostEqual(result["raw_probabilities"]["home"], 0.5)

    def test_invalid_odds_are_ignored(self):
        result = normalize_implied_probabilities({"home": 2.0, "bad": 1, "none": None})
        self.assertEqual(set(result["fair_probabilities"]), {"home"})

    def test_detects_large_price_move_from_distinct_observations(self):
        rows = [
            {"fixture_key": "f1", "market": "1X2", "option_name": "Home", "bookmaker": "Bet365",
             "stage": "Inplay", "line": "", "odd": 2.2, "observed_at": "2026-10-12T10:00:00+00:00",
             "home": "A", "away": "B"},
            {"fixture_key": "f1", "market": "1X2", "option_name": "Home", "bookmaker": "Bet365",
             "stage": "Inplay", "line": "", "odd": 1.8, "observed_at": "2026-10-12T10:05:00+00:00",
             "home": "A", "away": "B"},
        ]
        moves = detect_odds_movements(rows)
        self.assertEqual(len(moves), 1)
        self.assertAlmostEqual(moves[0]["change"], -0.4)
        self.assertEqual(moves[0]["direction"], "Oran düştü")

    def test_does_not_compare_different_stages(self):
        rows = [
            {"fixture_key": "f1", "market": "1X2", "option_name": "Home", "bookmaker": "Bet365",
             "stage": "Opening", "odd": 2.0, "observed_at": "2026-10-12T10:00:00+00:00"},
            {"fixture_key": "f1", "market": "1X2", "option_name": "Home", "bookmaker": "Bet365",
             "stage": "Closing", "odd": 2.02, "observed_at": "2026-10-12T10:05:00+00:00"},
        ]
        self.assertEqual(detect_odds_movements(rows), [])


if __name__ == "__main__":
    unittest.main()
