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
    def test_atomic_text_write_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.txt"; target.write_text("old", encoding="utf-8")
            bot.atomic_write_text(target, "new")
            self.assertEqual(target.read_text(encoding="utf-8"), "new")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_diagnostic_summary_has_no_mutating_actions(self):
        with patch.object(bot, "fetch_matches_from_odds_api", return_value=[]):
            result = bot.run_diagnostic("2026-08-01", 1.5, 1.6, ["key"])
        self.assertFalse(result["would_write"])
        self.assertFalse(result["would_settle"])
        self.assertFalse(result["would_call_ai"])
        self.assertFalse(result["would_stake"])

    def test_fixture_provider_failure_is_distinct_from_empty_schedule(self):
        with patch.object(bot, "fetch_odds_json", return_value=(None, 0)):
            bot.fetch_matches_from_odds_api("2026-08-01", ["key"])
            self.assertEqual(bot.LAST_FIXTURE_STATUS, "provider_failure")
        with patch.object(bot, "fetch_odds_json", return_value=([], 0)):
            bot.fetch_matches_from_odds_api("2026-08-01", ["key"])
            self.assertEqual(bot.LAST_FIXTURE_STATUS, "valid_empty_schedule")

    def test_diagnostic_mode_does_not_save_discovered_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            aliases = Path(directory) / "aliases.csv"
            with patch.object(bot, "PLAYER_ALIASES_FILE", aliases), patch.object(bot, "DIAGNOSTIC_MODE", True):
                bot.save_player_alias("Provider Name", "Canonical Name", .99)
            self.assertFalse(aliases.exists())

    def test_counterfactual_policy_decision_is_versioned_and_deduplicated(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.csv"
            row = {"DATE": "2026-08-01", "EVENT_ID": "7", "MATCH": "A vs B", "PLAYER1": "A", "PLAYER2": "B", "PICK": "A"}
            with patch.object(bot, "POLICY_FILE", policy):
                bot.record_policy_decision(datetime.now(timezone.utc), row, None, {"player_odds": 1.6, "assessed_probability": .7, "ev": .12}, "cancelled", "bookmaker_conflict")
                bot.record_policy_decision(datetime.now(timezone.utc), row, None, None, "cancelled", "duplicate")
            with policy.open(encoding="utf-8") as handle: rows = list(__import__("csv").DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["MODEL_VERSION"], bot.MODEL_VERSION)

    def test_emergency_kill_switch_detects_calibration_drift(self):
        stable = [{"DATE": "2026-01-01", "RESULT": "W", "MODEL_PROBABILITY": ".9", "CLV": ".02"}] * 30
        degraded = [{"DATE": "2026-02-01", "RESULT": "L", "MODEL_PROBABILITY": ".9", "CLV": "-.05"}] * 30
        self.assertTrue(bot.tennis_kill_switch(stable + degraded)["active"])

    def test_workload_measures_rest_matches_and_sets(self):
        history = [
            {"tourney_date": "20260731", "winner_name": "Player One", "loser_name": "Other", "score": "6-4 6-4", "tourney_name": "Event A"},
            {"tourney_date": "20260729", "winner_name": "Other", "loser_name": "Player One", "score": "6-4 4-6 6-3", "tourney_name": "Event A"},
            {"tourney_date": "20260727", "winner_name": "Player One", "loser_name": "Other", "score": "7-6 6-7 6-4", "tourney_name": "Event B"},
        ]
        workload = bot.calculate_workload(history, "Player One", "2026-08-01", "Event C")
        self.assertEqual((workload["rest_days"], workload["matches_7"], workload["sets_7"]), (1, 3, 8))
        self.assertGreater(workload["penalty"], 0)

    def test_tennis_context_and_match_format(self):
        self.assertEqual(bot.tennis_context_uncertainty({"tournament": "ITF Madrid", "level": "ITF"})[0], .02)
        self.assertEqual(bot.inferred_best_of({"tournament": "Wimbledon", "level": "ATP"}), 5)
        self.assertEqual(bot.inferred_best_of({"tournament": "Wimbledon", "level": "WTA"}), 3)

    def test_tennis_quality_detects_bookmaker_conflict(self):
        match = {"player1": "A", "player2": "B", "bookmaker_count": 3, "home_dispersion": .20,
                 "surface": "hard", "player1_profile": {}, "player2_profile": {}}
        quality = bot.tennis_data_quality(match, {"form_sample": 8, "serve_return_sample": 8}, "A")
        self.assertIn("bookmaker_conflict", quality["reasons"])

    def test_tennis_price_history_snapshot(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / "pending.csv"
            with patch.object(bot, "PENDING_FILE", pending):
                bot.append_price_snapshot(datetime(2026, 8, 1, tzinfo=timezone.utc), {"DATE": "2026-08-01", "MATCH": "A vs B", "PICK": "A"},
                                          {"player1": "A", "player2": "B", "bookmaker_count": 3, "home_dispersion": .04}, {"player_odds": 1.55})
            text = (Path(directory) / "price-history.csv").read_text(encoding="utf-8")
        self.assertIn("TIMESTAMP,DATE,MATCH,PICK,ODDS", text)
        self.assertIn("1.550", text)

    def test_tournament_correlation_cap(self):
        recs = [{"player": f"P{i}", "grade": "Value Pick", "ev": .10 - i * .01, "score": 8,
                 "match": {"player1": f"P{i}", "player2": f"O{i}", "tournament": "ATP Test"}} for i in range(3)]
        self.assertEqual(len(bot.select_portfolio(recs, max_exposure=.2, max_bets=4)), 2)

    def test_calibration_requires_mature_probability_bucket(self):
        rows = [{"MODEL_PROBABILITY": ".60", "RESULT": "W"} for _ in range(99)]
        self.assertEqual(bot.calibrate_probability(.60, rows), (.60, 99))
        rows.append({"MODEL_PROBABILITY": ".60", "RESULT": "W"})
        probability, sample = bot.calibrate_probability(.60, rows)
        self.assertEqual(sample, 100)
        self.assertGreater(probability, .60)

    def test_segment_suspension_needs_roi_and_clv_confirmation(self):
        rows = [{"SURFACE": "hard", "TOUR": "ATP", "RESULT": "L",
                 "OPENING_ODDS": "1.60", "CLV": "-0.03"} for _ in range(30)]
        health = bot.segment_health({"surface": "hard", "level": "ATP"}, rows)
        self.assertTrue(health["suspended"])
        rows[0]["CLV"] = "1.00"
        self.assertFalse(bot.segment_health({"surface": "hard", "level": "ATP"}, rows)["suspended"])

    def test_retirement_and_walkover_are_void(self):
        self.assertEqual(bot.tennis_void_reason({"status": "cancelled"}), "cancelled")
        self.assertEqual(bot.tennis_void_reason({"result": "Player retired"}), "walkover_or_retirement")
        self.assertIsNone(bot.tennis_void_reason({"status": "settled", "result": "2-0"}))

    def test_walk_forward_weights_stay_shadow_without_enough_history(self):
        rows = [{"DATE": f"2026-01-{(index % 28) + 1:02d}", "RESULT": "W",
                 "ELO_PROBABILITY": ".60", "MARKET_PROBABILITY": ".55",
                 "MODEL_PROBABILITY": ".58"} for index in range(199)]
        self.assertIsNone(bot.learned_component_weights(rows))

    def test_stage_pending_does_not_log_or_deduct(self):
        rec = {"player": "Player One", "grade": "Value Pick", "odds": 1.55,
               "assessed_probability": .70, "ev": .085,
               "match": {"player1": "Player One", "player2": "Player Two", "tournament": "ATP Test",
                         "surface": "hard", "start_time": "2026-08-01T13:00:00Z", "event_id": "7"}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); pending = root / "pending-bets.csv"
            with patch.object(bot, "PENDING_FILE", pending):
                staged = bot.stage_pending_bets("2026-08-01", [rec], 1.5, 1.6)
            with pending.open(encoding="utf-8") as handle:
                rows = list(__import__("csv").DictReader(handle))
        self.assertEqual(staged, 1)
        self.assertEqual(rows[0]["STATUS"], "pending_revalidation")

    def test_match_time_state_controls_authorization_window(self):
        from datetime import datetime, timezone
        now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(bot.match_time_state("2026-08-01T14:00:00Z", now), "waiting")
        self.assertEqual(bot.match_time_state("2026-08-01T13:00:00Z", now), "ready")
        self.assertEqual(bot.match_time_state("2026-08-01T11:00:00Z", now), "passed")

    def test_validation_summary_overrides_rejected_narrative_picks(self):
        report = "## TOP PICKS\nA speculative candidate."
        result = bot.add_validation_summary(report, 1, [])

        self.assertIn("Python accepted 0 candidate(s) for staging", result)
        self.assertIn("Final betting decision: NO BETS", result)
        self.assertIn("must not be treated as recommendations", result)

    def test_settlement_credits_full_winning_return(self):
        event = {
            "id": 7, "date": "2026-08-01T12:00:00Z", "status": "settled",
            "home": "Player One", "away": "Player Two",
            "scores": {"home": 2, "away": 0},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path, bankroll_path = root / "bets-log.csv", root / "bankroll.txt"
            log_path.write_text(
                "DATE,MATCH,BET,ODDS,STAKE,RESULT,RETURN,STARTING BALANCE\n"
                "2026-08-01,Player One vs Player Two (ATP),Player One to win,2.00,3.00,,,100.00\n",
                encoding="utf-8",
            )
            bankroll_path.write_text("97.00", encoding="utf-8")
            with (
                patch.object(bot, "LOG_FILE", log_path),
                patch.object(bot, "BANKROLL_FILE", bankroll_path),
                patch.object(bot, "fetch_odds_json", side_effect=[([event], 0), ([], 0)]),
                patch.object(bot, "update_audit_result"),
            ):
                settled = bot.settle_pending_bets(["key"])

            with log_path.open(encoding="utf-8") as handle:
                rows = list(__import__("csv").DictReader(handle))
            self.assertEqual(settled, 1)
            self.assertEqual(rows[0]["RESULT"], "W")
            self.assertEqual(rows[0]["RETURN"], "6.00")
            self.assertEqual(bankroll_path.read_text(), "103.00")

    def test_log_bets_deduplicates_same_player_and_date(self):
        recommendation = {
            "player": "Darderi, Luciano",
            "grade": "Value Pick",
            "odds": 1.6,
            "assessed_probability": 0.70,
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

    def test_player_identity_alias_resolves_to_canonical_profile(self):
        profiles = {bot.normalize_player_name("Alexander Zverev"): {"name": "Alexander Zverev", "elo": 1900}}
        with tempfile.TemporaryDirectory() as directory:
            aliases_file = Path(directory) / "player-aliases.csv"
            aliases_file.write_text("PROVIDER_NAME,CANONICAL_NAME,SOURCE,CONFIDENCE\nA. Zverev,Alexander Zverev,manual,1.0\n", encoding="utf-8")
            with patch.object(bot, "PLAYER_ALIASES_FILE", aliases_file):
                aliases = bot.load_player_aliases()
                resolved = bot.resolve_profile_key("A. Zverev", profiles, aliases)

        self.assertEqual(resolved, bot.normalize_player_name("Alexander Zverev"))

    def test_player_normalization_preserves_diacritic_identity(self):
        self.assertEqual(bot.normalize_player_name("Félix Auger-Aliassime"), bot.normalize_player_name("Felix Auger Aliassime"))

    def test_recent_form_is_opponent_adjusted_and_requires_sample(self):
        history = [{
            "tourney_date": f"20260{month}0{day}", "surface": "Clay",
            "winner_name": "Test Player", "loser_name": f"Opponent {day}",
            "winner_rank": "50", "loser_rank": "10", "score": "6-4 6-4",
        } for month, day in ((5,1),(5,2),(5,3),(5,4),(5,5),(5,6),(5,7),(5,8))]

        form = bot.calculate_recent_form(history, "Test Player", "clay", "2026-06-01")

        self.assertEqual(form["sample"], 8)
        self.assertGreater(form["probability"], 0.5)
        self.assertIsNone(bot.calculate_recent_form(history[:7], "Test Player", "clay", "2026-06-01"))

    def test_serve_return_profile_requires_points_and_calculates_rates(self):
        history = []
        for day in range(1, 9):
            history.append({
                "tourney_date": f"202605{day:02d}", "surface": "Clay", "score": "6-4 6-4",
                "winner_name": "Server", "loser_name": f"Opponent {day}",
                "w_ace": "8", "w_df": "3", "w_svpt": "100", "w_1stIn": "62", "w_1stWon": "46", "w_2ndWon": "20", "w_bpSaved": "4", "w_bpFaced": "5",
                "l_ace": "2", "l_df": "4", "l_svpt": "90", "l_1stIn": "55", "l_1stWon": "32", "l_2ndWon": "14", "l_bpSaved": "3", "l_bpFaced": "7",
            })

        profile = bot.calculate_serve_return_profile(history, "Server", "clay", "2026-06-01")

        self.assertEqual(profile["sample"], 8)
        self.assertAlmostEqual(profile["service_points_won"], 0.66)
        self.assertGreater(profile["return_points_won"], 0.45)
        self.assertGreater(profile["hold_probability"], 0.7)

    def test_serve_return_matchup_is_symmetric_and_bounded(self):
        strong = {"sample": 20, "service_points_won": 0.68, "return_points_won": 0.42}
        weak = {"sample": 18, "service_points_won": 0.60, "return_points_won": 0.35}

        forward = bot.calculate_serve_return_matchup(strong, weak)
        reverse = bot.calculate_serve_return_matchup(weak, strong)

        self.assertGreater(forward["probability"], 0.5)
        self.assertAlmostEqual(forward["probability"] + reverse["probability"], 1.0)
        self.assertEqual(forward["sample"], 18)

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

    def test_moneyline_market_uses_best_prices_and_median_consensus(self):
        payload = {"bookmakers": {
            "A": [{"name": "ML", "odds": [{"home": "1.50", "away": "2.60"}]}],
            "B": [{"name": "ML", "odds": [{"home": "1.60", "away": "2.40"}]}],
            "C": [{"name": "ML", "odds": [{"home": "1.55", "away": "2.50"}]}],
        }}

        market = bot.extract_moneyline_market(payload)

        self.assertEqual(market["best_home"], 1.6)
        self.assertEqual(market["best_away"], 2.6)
        self.assertEqual(market["consensus_home"], 1.55)
        self.assertEqual(market["consensus_away"], 2.5)

    def test_surface_elo_is_used_when_surface_is_known(self):
        match = {
            "player1": "Clay Player", "player2": "Opponent",
            "home_odds": 1.8, "away_odds": 2.2, "surface": "clay",
            "player1_profile": {"elo": 1600, "clay_elo": 1800},
            "player2_profile": {"elo": 1700, "clay_elo": 1600},
        }

        baseline = bot.calculate_tennis_baseline(match, "Clay Player")

        self.assertEqual(baseline["elo_type"], "clay_elo")
        self.assertGreater(baseline["elo_probability"], 0.7)

    def test_recent_form_has_bounded_weight_in_probability(self):
        match = {
            "player1": "Player", "player2": "Opponent",
            "home_odds": 2.0, "away_odds": 2.0,
            "player1_profile": {"elo": 1700}, "player2_profile": {"elo": 1700},
            "player1_recent_form": {"sample": 12, "probability": 0.65},
        }

        baseline = bot.calculate_tennis_baseline(match, "Player")

        self.assertAlmostEqual(baseline["assessed_probability"], 0.5225)
        self.assertEqual(baseline["form_sample"], 12)

    def test_full_model_uses_serve_return_at_fifteen_percent(self):
        match = {
            "player1": "Player", "player2": "Opponent", "home_odds": 2.0, "away_odds": 2.0,
            "player1_profile": {"elo": 1700}, "player2_profile": {"elo": 1700},
            "player1_recent_form": {"sample": 12, "probability": 0.60},
            "player1_serve_return": {"sample": 20, "service_points_won": 0.67, "return_points_won": 0.40},
            "player2_serve_return": {"sample": 20, "service_points_won": 0.61, "return_points_won": 0.35},
        }

        baseline = bot.calculate_tennis_baseline(match, "Player")
        expected = 0.40 * 0.5 + 0.30 * 0.5 + 0.15 * 0.60 + 0.15 * baseline["serve_return_probability"]

        self.assertAlmostEqual(baseline["assessed_probability"], expected)
        self.assertIn("serve_return=.15", baseline["component_weights"])

    def test_evidence_quality_rewards_surface_profiles_and_bookmakers(self):
        match = {
            "surface": "clay",
            "player1_profile": {"elo": 1700},
            "player2_profile": {"elo": 1650},
            "bookmaker_count": 4,
        }
        baseline = {
            "elo_type": "clay_elo",
            "market_overround": 1.05,
            "elo_market_gap": 0.08,
        }

        score, grade = bot.evidence_quality(match, baseline)

        self.assertEqual(score, 10)
        self.assertEqual(grade, "A")

    def test_backtest_summary_segments_settled_predictions(self):
        rows = [
            {"DATE": "2026-07-01", "OPENING_ODDS": "1.60", "MODEL_PROBABILITY": "0.65", "EV": "0.04", "RESULT": "W", "CLV": "0.02", "TOUR": "ATP", "SURFACE": "clay", "QUALITY_GRADE": "A"},
            {"DATE": "2026-07-02", "OPENING_ODDS": "1.70", "MODEL_PROBABILITY": "0.62", "EV": "0.03", "RESULT": "L", "CLV": "-0.01", "TOUR": "ATP", "SURFACE": "clay", "QUALITY_GRADE": "B"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "backtest-summary.md"
            with patch.object(bot, "BACKTEST_FILE", output):
                bot.generate_backtest_summary(rows)
            report = output.read_text(encoding="utf-8")

        self.assertIn("## Odds bands", report)
        self.assertIn("1.50–1.75 | 2 | 50.0%", report)
        self.assertIn("## Surface", report)
        self.assertIn("## Monthly performance", report)

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

    def test_dashboard_uses_automated_data_sources_and_wl_results(self):
        dashboard = MODULE_PATH.parent.parent.joinpath("docs", "index.html").read_text(
            encoding="utf-8"
        )
        lowered = dashboard.lower()

        self.assertIn("predictions-log.csv", dashboard)
        self.assertIn("performance-summary.md", dashboard)
        self.assertIn("bankroll.txt", dashboard)
        self.assertIn('["w","win","won"]', dashboard)
        self.assertIn('id="audit-body"', dashboard)
        self.assertIn('id="backtest-body"', dashboard)
        self.assertIn("workload_penalty", dashboard)
        self.assertIn("market_dispersion", dashboard)
        self.assertNotIn("localstorage", lowered)
        self.assertNotIn("copy-csv", lowered)
        self.assertNotIn("showresultpicker", lowered)


if __name__ == "__main__":
    unittest.main()
