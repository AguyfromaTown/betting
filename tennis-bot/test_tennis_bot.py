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
