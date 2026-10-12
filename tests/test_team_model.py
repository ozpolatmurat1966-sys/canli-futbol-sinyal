import unittest

from team_model import estimate_fixture_markets


def sample_history(count=25):
    rows = []
    for i in range(count):
        rows.append({
            "fixture_key": f"hist-{i}", "finished": 1,
            "match_date": f"2026-09-{(i % 28) + 1:02d}T18:00:00+00:00",
            "league": "Test League", "home": "Alpha" if i % 2 == 0 else "Gamma",
            "away": "Beta" if i % 2 == 0 else "Alpha",
            "home_goals": i % 3, "away_goals": (i + 1) % 2, "raw_json": "{}",
        })
    return rows


class TeamModelTests(unittest.TestCase):
    def test_model_requires_history_and_team_samples(self):
        result = estimate_fixture_markets(sample_history(10), "Alpha", "Beta", "Test League")
        self.assertFalse(result["ready"])
        self.assertIn("tamamlanmış maç", result["reason"])

    def test_model_returns_bounded_probabilities_when_ready(self):
        rows = sample_history(40)
        for i in range(12):
            rows.append({
                "fixture_key": f"alpha-beta-{i}", "finished": 1,
                "match_date": f"2026-08-{(i % 28) + 1:02d}T18:00:00+00:00",
                "league": "Test League", "home": "Alpha" if i % 2 == 0 else "Beta",
                "away": "Beta" if i % 2 == 0 else "Alpha",
                "home_goals": i % 4, "away_goals": (i + 1) % 3, "raw_json": "{}",
            })
        result = estimate_fixture_markets(rows, "Alpha", "Beta", "Test League")
        self.assertTrue(result["ready"], result["reason"])
        self.assertGreater(result["expected_goals_home"], 0)
        self.assertGreater(result["expected_goals_away"], 0)
        self.assertAlmostEqual(sum(m["probability"] for m in result["markets"][:3]), 1.0, places=4)
        self.assertTrue(all(0 <= m["probability"] <= 1 for m in result["markets"]))


if __name__ == "__main__":
    unittest.main()
