import unittest
from unittest.mock import patch

from backtest_engine import evaluate_paper_bets
from decision_engine import assess_market
from advanced_features import fetch_leagues


class DecisionEngineTests(unittest.TestCase):
    def test_missing_model_probability_is_always_pass(self):
        result = assess_market(None, 2.2, sample_count=1000,
                               data_age_seconds=10, data_complete=True)
        self.assertEqual(result["decision"], "PAS GEÇ")
        self.assertIn("model olasılığı yok", result["reason"])

    def test_insufficient_sample_is_pass(self):
        result = assess_market(0.60, 2.0, sample_count=199,
                               data_age_seconds=10, data_complete=True)
        self.assertEqual(result["decision"], "PAS GEÇ")

    def test_value_candidate_requires_all_gates(self):
        result = assess_market(0.65, 2.0, sample_count=250,
                               data_age_seconds=30, data_complete=True)
        self.assertEqual(result["decision"], "ADAY — garanti değil")
        stale = assess_market(0.65, 2.0, sample_count=250,
                              data_age_seconds=500, data_complete=True)
        self.assertEqual(stale["decision"], "PAS GEÇ")


class BacktestTests(unittest.TestCase):
    def test_roi_and_drawdown_are_calculated_from_settled_bets(self):
        rows = [
            {"odds": 2.0, "stake": 10, "settled_result": 1, "model_probability": 0.8},
            {"odds": 3.0, "stake": 10, "settled_result": 0, "model_probability": 0.2},
        ]
        result = evaluate_paper_bets(rows)
        self.assertTrue(result["ready"])
        self.assertEqual(result["bets"], 2)
        self.assertEqual(result["profit"], 0)
        self.assertEqual(result["roi"], 0)
        self.assertEqual(result["max_drawdown"], 10)
        self.assertEqual(result["brier_samples"], 2)
        self.assertAlmostEqual(result["brier_score"], 0.04)

    def test_no_settled_bets_means_no_roi(self):
        result = evaluate_paper_bets([{"odds": 2.0, "stake": 10, "settled_result": None}])
        self.assertFalse(result["ready"])


class LeagueInventoryTests(unittest.TestCase):
    @patch("advanced_features.requests.get")
    def test_fetch_leagues_parses_provider_inventory(self, mock_get):
        class Response:
            status_code = 200
            text = ""
            def json(self):
                return {
                    "success": 1,
                    "data": [{"id": 10, "name": "Example League",
                              "country": {"name": "Example Country"},
                              "last_fixture_utc": "2026-10-12T10:00:00Z",
                              "is_popular": True}],
                    "pagination": {"has_more": False},
                }
        mock_get.return_value = Response()
        rows, error = fetch_leagues("test-key")
        self.assertIsNone(error)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["provider_league_id"], "10")
        self.assertEqual(rows[0]["country"], "Example Country")
        mock_get.assert_called_once()

    def test_missing_api_key_does_not_make_request(self):
        rows, error = fetch_leagues("")
        self.assertEqual(rows, [])
        self.assertIn("tanımlı değil", error)


if __name__ == "__main__":
    unittest.main()
