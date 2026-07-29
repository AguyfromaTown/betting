import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("tennis_bot.py")
SPEC = importlib.util.spec_from_file_location("tennis_bot", MODULE_PATH)
bot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bot)


class TennisBotTests(unittest.TestCase):
    def test_completion_limit_fits_groq_tpm_budget(self):
        self.assertLessEqual(bot.MAX_COMPLETION_TOKENS, 4096)

    def test_parser_accepts_named_odds_and_complex_names(self):
        report = """## TOP PICKS
1. **Carlos Alcaraz vs Jannik Sinner**
   - Odds: Carlos Alcaraz 1.55

## VALUE PICKS
1. **Félix Auger-Aliassime vs Alex de Minaur**
   - Odds: Félix Auger-Aliassime 1.60

## PICKS TO AVOID
"""
        picks = bot.parse_recommendations(report)
        self.assertEqual(
            [(p["player"], p["odds"], p["grade"]) for p in picks],
            [
                ("Carlos Alcaraz", 1.55, "Top Pick"),
                ("Félix Auger-Aliassime", 1.60, "Value Pick"),
            ],
        )

    def test_extract_moneyline_odds(self):
        payload = {
            "bookmakers": {
                "Bet365": [
                    {
                        "name": "ML",
                        "odds": [{"home": "1.55", "away": "2.50"}],
                    }
                ]
            }
        }
        self.assertEqual(
            bot.extract_moneyline_odds(payload),
            (1.55, 2.5, "Bet365"),
        )

    @patch.object(bot, "fetch_odds_json")
    def test_odds_api_uses_batches_of_ten(self, fetch_odds_json):
        events = [
            {
                "id": event_id,
                "date": "2026-07-30T12:00:00Z",
                "home": f"Home {event_id}",
                "away": f"Away {event_id}",
                "league": {"name": "ATP Test"},
            }
            for event_id in range(11)
        ]
        odds = [
            {
                **event,
                "bookmakers": {
                    "Bet365": [
                        {
                            "name": "ML",
                            "odds": [{"home": "1.55", "away": "2.50"}],
                        }
                    ]
                },
            }
            for event in events
        ]
        fetch_odds_json.side_effect = [
            (events, 0),
            (odds[:10], 0),
            (odds[10:], 0),
        ]

        matches = bot.fetch_matches_from_odds_api(
            "2026-07-30",
            ["secret-key"],
        )

        self.assertEqual(len(matches), 11)
        self.assertEqual(fetch_odds_json.call_count, 3)
        bulk_calls = fetch_odds_json.call_args_list[1:]
        self.assertTrue(
            all(call.args[0].endswith("/odds/multi") for call in bulk_calls)
        )
        self.assertEqual(
            bulk_calls[0].args[1]["eventIds"],
            "0,1,2,3,4,5,6,7,8,9",
        )

    @patch.object(bot.requests, "get")
    def test_odds_api_rotates_key_after_429(self, get):
        exhausted = unittest.mock.Mock(status_code=429)
        working = unittest.mock.Mock(status_code=200)
        working.raise_for_status.return_value = None
        working.json.return_value = [{"id": 1}]
        get.side_effect = [exhausted, working]

        payload, key_index = bot.fetch_odds_json(
            "https://api.odds-api.io/v3/events",
            {"sport": "tennis"},
            ["first-key", "second-key"],
            0,
        )

        self.assertEqual(payload, [{"id": 1}])
        self.assertEqual(key_index, 1)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[0].kwargs["params"]["apiKey"], "first-key")
        self.assertEqual(get.call_args_list[1].kwargs["params"]["apiKey"], "second-key")

    @patch.object(bot.requests, "post")
    def test_call_ai_uses_groq_contract(self, post):
        response = post.return_value
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "## TOP PICKS\nNo picks."}}]
        }

        result = bot.call_ai("test prompt", "secret-key")

        self.assertEqual(result, "## TOP PICKS\nNo picks.")
        _, kwargs = post.call_args
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            "Bearer secret-key",
        )
        self.assertEqual(kwargs["json"]["model"], "llama-3.3-70b-versatile")
        self.assertEqual(kwargs["json"]["max_tokens"], 4096)


if __name__ == "__main__":
    unittest.main()
