import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("tennis_bot.py")
SPEC = importlib.util.spec_from_file_location("tennis_bot", MODULE_PATH)
bot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bot)


class TennisBotTests(unittest.TestCase):
    def test_opencode_snapshot_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "agent-run.json"
            matches = [{
                "player1": "Player One",
                "player2": "Player Two",
                "home_odds": 1.55,
                "away_odds": 2.4,
            }]
            bot.save_agent_snapshot(
                path,
                "2026-07-30",
                1.5,
                1.6,
                57.0,
                matches,
                "verified prompt",
            )

            snapshot = bot.load_agent_snapshot(path)

        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["date"], "2026-07-30")
        self.assertEqual(snapshot["matches"], matches)
        self.assertEqual(snapshot["analysis_prompt"], "verified prompt")

    def test_validation_summary_overrides_rejected_narrative_picks(self):
        report = "## TOP PICKS\nA speculative candidate."
        result = bot.add_validation_summary(report, 1, [])

        self.assertIn("Python accepted 0 bet(s)", result)
        self.assertIn("Final betting decision: NO BETS", result)
        self.assertIn("must not be treated as recommendations", result)

    def test_log_bets_deduplicates_same_player_and_date(self):
        recommendation = {
            "player": "Darderi, Luciano",
            "grade": "Value Pick",
            "odds": 1.6,
        }
        match = {
            "player1": "Svrcina, Dalibor",
            "player2": "Darderi, Luciano",
            "tournament": "ATP Test",
        }
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "bets-log.csv"
            with patch.object(bot, "LOG_FILE", log_path):
                first_stake = bot.log_bets(
                    "2026-07-30",
                    [recommendation],
                    [match],
                    100.0,
                )
                second_stake = bot.log_bets(
                    "2026-07-30",
                    [recommendation],
                    [match],
                    98.0,
                )
            rows = log_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(first_stake, 2.0)
        self.assertEqual(second_stake, 0.0)
        self.assertEqual(len(rows), 2)

    def test_tennis_abstract_elo_is_parsed_and_compacted(self):
        html = """
        <table><tr><td>navigation</td></tr></table>
        <table>
          <tr><th>Elo Rank</th><th>Player</th><th>Age</th><th>Elo</th>
              <th>x</th><th>hRank</th><th>hElo</th><th>cRank</th>
              <th>cElo</th><th>gRank</th><th>gElo</th><th>x</th>
              <th>Peak</th><th>Peak Month</th><th>x</th><th>ATP Rank</th></tr>
          <tr><td>31</td><td>Luciano Darderi</td><td>24.4</td><td>1843.4</td>
              <td></td><td>42</td><td>1760.2</td><td>24</td>
              <td>1843.6</td><td>55</td><td>1701.1</td><td></td>
              <td>1880.5</td><td>2026-05</td><td></td><td>23</td></tr>
        </table>
        """
        profiles = bot.parse_tennis_abstract_elo(html)
        line = bot.compact_profile_line("Darderi, Luciano", profiles)

        self.assertIn("official rank=23", line)
        self.assertIn("Elo=1843.4 (Elo rank #31)", line)
        self.assertIn("clay Elo=1843.6", line)

    def test_tennis_abstract_reader_fallback(self):
        row = (
            "31\tLuciano Darderi\t24.4\t1843.4\t\t85\t1682.7\t19\t"
            "1843.6\t92\t1625.8\t\t1858.1\t2026-05\t\t23\t0.30"
        )
        matches = [{
            "player1": "Darderi, Luciano",
            "player2": "Unknown Player",
        }]
        with (
            patch.object(bot, "fetch", side_effect=[None, None]),
            patch.object(bot, "fetch_reader", side_effect=[row, None]),
        ):
            profiles = bot.fetch_tennis_abstract_profiles(matches)

        line = bot.compact_profile_line("Darderi, Luciano", profiles)
        self.assertIn("official rank=23", line)
        self.assertIn("hard Elo=1682.7", line)

    @patch.object(bot.requests, "get")
    def test_reader_uses_api_headers_instead_of_blocked_browser_headers(self, get):
        response = get.return_value
        response.raise_for_status.return_value = None
        response.text = "leaderboard"

        result = bot.fetch_reader(
            "https://tennisabstract.com/reports/atp_elo_ratings.html"
        )

        self.assertEqual(result, "leaderboard")
        headers = get.call_args.kwargs["headers"]
        self.assertEqual(headers["Accept"], "text/plain")
        self.assertEqual(headers["User-Agent"], "tennis-betting-bot/1.0")
        self.assertNotEqual(headers, bot.REQUEST_HEADERS)

    def test_completion_limit_fits_groq_tpm_budget(self):
        self.assertLessEqual(bot.MAX_COMPLETION_TOKENS, 2048)

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

    def test_structured_picks_are_parsed(self):
        report = """## MACHINE READABLE PICKS
```json
[
  {
    "player": "Luciano Darderi",
    "opponent": "Dalibor Svrcina",
    "score": 7.5,
    "assessed_probability": 0.72
  }
]
```"""
        self.assertEqual(
            bot.parse_recommendations(report),
            [{
                "player": "Luciano Darderi",
                "opponent": "Dalibor Svrcina",
                "score": 7.5,
                "assessed_probability": 0.72,
            }],
        )

    def test_validation_rejects_groq_negative_ev_error(self):
        candidates = [{
            "player": "Maiko Uchijima",
            "score": 8.5,
            "assessed_probability": 0.65,
        }]
        matches = [{
            "player1": "Maiko Uchijima",
            "player2": "Laquisa Khan",
            "home_odds": 1.5,
            "away_odds": 2.5,
            "player1_profile": {"elo": 1600},
            "player2_profile": {"elo": 1600},
        }]
        self.assertEqual(bot.validate_recommendations(candidates, matches), [])

    def test_validation_uses_verified_odds_and_computes_grade(self):
        candidates = [{
            "player": "Darderi, Luciano",
            "score": 7.5,
            "assessed_probability": 0.70,
        }]
        matches = [{
            "player1": "Svrcina, Dalibor",
            "player2": "Darderi, Luciano",
            "home_odds": 2.5,
            "away_odds": 1.6,
            "player1_profile": {"elo": 1600},
            "player2_profile": {"elo": 1800},
        }]
        validated = bot.validate_recommendations(candidates, matches)
        self.assertEqual(len(validated), 1)
        self.assertEqual(validated[0]["grade"], "Top Pick")
        self.assertGreater(validated[0]["ev"], 0.05)
        self.assertEqual(validated[0]["odds"], 1.6)

    def test_tennis_baseline_blends_devigged_market_and_elo(self):
        match = {
            "player1": "Stronger", "player2": "Weaker",
            "home_odds": 1.6, "away_odds": 2.5,
            "player1_profile": {"elo": 1800},
            "player2_profile": {"elo": 1600},
        }

        baseline = bot.calculate_tennis_baseline(match, "Stronger")

        self.assertAlmostEqual(baseline["market_probability"], 0.6097561)
        self.assertAlmostEqual(baseline["elo_probability"], 0.7597469)
        self.assertAlmostEqual(
            baseline["assessed_probability"],
            0.55 * 0.7597469 + 0.45 * 0.6097561,
            places=6,
        )

    def test_statistical_scan_rejects_large_elo_market_disagreement(self):
        match = {
            "player1": "Market Favourite", "player2": "Elo Favourite",
            "home_odds": 1.5, "away_odds": 2.5,
            "player1_profile": {"elo": 1400},
            "player2_profile": {"elo": 2000},
        }

        candidates = bot.build_statistical_candidates([match], 1.5, 3.0)

        self.assertEqual(candidates, [])

    def test_validation_rejects_players_own_out_of_range_odds(self):
        match = {
            "player1": "Longshot", "player2": "Favourite",
            "home_odds": 3.2, "away_odds": 1.4,
            "player1_profile": {"elo": 1700},
            "player2_profile": {"elo": 1700},
        }
        candidate = {"player": "Longshot", "score": 8, "assessed_probability": 0.5}

        result = bot.validate_recommendations([candidate], [match], 1.5, 3.0)

        self.assertEqual(result, [])

    def test_opencode_context_adjustment_is_bounded(self):
        match = {
            "player1": "Stronger", "player2": "Weaker",
            "home_odds": 1.6, "away_odds": 2.5,
            "player1_profile": {"elo": 1800},
            "player2_profile": {"elo": 1600},
        }
        baseline = bot.calculate_tennis_baseline(match, "Stronger")
        accepted = {
            "player": "Stronger", "score": 9,
            "assessed_probability": baseline["assessed_probability"] + 0.04,
        }
        rejected = {
            "player": "Stronger", "score": 9,
            "assessed_probability": baseline["assessed_probability"] + 0.06,
        }

        self.assertEqual(
            len(bot.validate_recommendations(
                [accepted], [match], 1.5, 3.0, allow_context_adjustment=True
            )),
            1,
        )
        self.assertEqual(
            bot.validate_recommendations(
                [rejected], [match], 1.5, 3.0, allow_context_adjustment=True
            ),
            [],
        )

    def test_portfolio_caps_exposure_and_one_player_per_match(self):
        shared_match = {"player1": "A", "player2": "B"}
        recommendations = [
            {"player": "A", "grade": "Top Pick", "ev": .20, "score": 9, "match": shared_match},
            {"player": "B", "grade": "Top Pick", "ev": .19, "score": 9, "match": shared_match},
            {"player": "C", "grade": "Top Pick", "ev": .18, "score": 9,
             "match": {"player1": "C", "player2": "D"}},
            {"player": "E", "grade": "Top Pick", "ev": .17, "score": 9,
             "match": {"player1": "E", "player2": "F"}},
        ]

        selected = bot.select_portfolio(recommendations)

        self.assertEqual([item["player"] for item in selected], ["A", "C"])

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

        result = bot.call_ai("test prompt", ["secret-key"])

        self.assertEqual(result, "## TOP PICKS\nNo picks.")
        _, kwargs = post.call_args
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            "Bearer secret-key",
        )
        self.assertEqual(kwargs["json"]["model"], "llama-3.3-70b-versatile")
        self.assertEqual(kwargs["json"]["max_tokens"], 2048)

    @patch.object(bot.requests, "post")
    def test_call_ai_rotates_key_after_rate_limit(self, post):
        limited = unittest.mock.Mock(status_code=429)
        fallback = unittest.mock.Mock(status_code=200)
        fallback.raise_for_status.return_value = None
        fallback.json.return_value = {
            "choices": [{"message": {"content": "fallback report"}}]
        }
        post.side_effect = [limited, fallback]

        result = bot.call_ai("test prompt", ["first-key", "second-key"])

        self.assertEqual(result, "fallback report")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(
            post.call_args_list[1].kwargs["json"]["model"],
            "llama-3.3-70b-versatile",
        )
        self.assertEqual(
            post.call_args_list[0].kwargs["headers"]["Authorization"],
            "Bearer first-key",
        )
        self.assertEqual(
            post.call_args_list[1].kwargs["headers"]["Authorization"],
            "Bearer second-key",
        )


if __name__ == "__main__":
    unittest.main()
