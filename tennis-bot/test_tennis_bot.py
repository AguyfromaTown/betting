import importlib.util
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("tennis_bot.py")
SPEC = importlib.util.spec_from_file_location("tennis_bot", MODULE_PATH)
bot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bot)


class TennisBotTests(unittest.TestCase):
    def test_optional_notifications_are_disabled_without_configuration(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(bot.os.environ, {}, clear=True), \
                patch.object(bot, "NOTIFICATION_STATUS_FILE", Path(directory) / "delivery.json"), \
                patch.object(bot, "send_telegram_notification") as telegram, \
                patch.object(bot, "send_email_notification") as email:
            self.assertEqual(bot.deliver_optional_notifications("2026-08-01", "daily"), [])
            telegram.assert_not_called()
            email.assert_not_called()
            self.assertFalse(bot.NOTIFICATION_STATUS_FILE.exists())

    def test_telegram_delivery_status_does_not_persist_secrets(self):
        environment = {"TELEGRAM_BOT_TOKEN": "super-secret-token", "TELEGRAM_CHAT_ID": "private-chat"}
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(bot.os.environ, environment, clear=True), \
                patch.object(bot, "NOTIFICATION_STATUS_FILE", Path(directory) / "delivery.json"), \
                patch.object(bot, "build_notification_message", return_value="safe summary"), \
                patch.object(bot, "send_telegram_notification") as telegram:
            results = bot.deliver_optional_notifications("2026-08-01", "daily")
            persisted = bot.NOTIFICATION_STATUS_FILE.read_text(encoding="utf-8")

        self.assertEqual(results[0]["status"], "delivered")
        telegram.assert_called_once_with("safe summary", "super-secret-token", "private-chat")
        self.assertNotIn("super-secret-token", persisted)
        self.assertNotIn("private-chat", persisted)

    def test_partial_and_failed_notifications_are_nonfatal_and_redacted(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(bot.os.environ, {"TELEGRAM_BOT_TOKEN": "never-persist-me"}, clear=True), \
                patch.object(bot, "NOTIFICATION_STATUS_FILE", Path(directory) / "partial.json"):
            partial = bot.deliver_optional_notifications("2026-08-01", "daily")
            persisted = bot.NOTIFICATION_STATUS_FILE.read_text(encoding="utf-8")
        self.assertEqual(partial[0]["status"], "configuration_error")
        self.assertIn("TELEGRAM_CHAT_ID", partial[0]["detail"])
        self.assertNotIn("never-persist-me", persisted)

        environment = {"TELEGRAM_BOT_TOKEN": "hidden-token", "TELEGRAM_CHAT_ID": "hidden-chat"}
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(bot.os.environ, environment, clear=True), \
                patch.object(bot, "NOTIFICATION_STATUS_FILE", Path(directory) / "failed.json"), \
                patch.object(bot, "build_notification_message", return_value="safe summary"), \
                patch.object(bot, "send_telegram_notification", side_effect=RuntimeError("sensitive detail")):
            failed = bot.deliver_optional_notifications("2026-08-01", "daily")
            persisted = bot.NOTIFICATION_STATUS_FILE.read_text(encoding="utf-8")
        self.assertEqual(failed[0], {"channel": "telegram", "status": "failed", "detail": "RuntimeError"})
        self.assertNotIn("sensitive detail", persisted)
        self.assertNotIn("hidden-token", persisted)

    def test_email_credentials_must_be_configured_as_a_pair(self):
        environment = {
            "SMTP_HOST": "smtp.example.test", "SMTP_PASSWORD": "password-only",
            "ALERT_EMAIL_FROM": "bot@example.test", "ALERT_EMAIL_TO": "owner@example.test",
        }
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(bot.os.environ, environment, clear=True), \
                patch.object(bot, "NOTIFICATION_STATUS_FILE", Path(directory) / "delivery.json"), \
                patch.object(bot, "send_email_notification") as sender:
            results = bot.deliver_optional_notifications("2026-08-01", "daily")
        self.assertEqual(results[0]["status"], "configuration_error")
        self.assertIn("SMTP_USERNAME", results[0]["detail"])
        sender.assert_not_called()

    def test_fixed_historical_fixture_runs_validation_through_settlement(self):
        from datetime import datetime
        fixture_paths = sorted((Path(__file__).with_name("fixtures")).glob("historical_lifecycle_*.json"))
        self.assertGreaterEqual(len(fixture_paths), 2)
        for fixture_path in fixture_paths:
            with self.subTest(fixture=fixture_path.name), tempfile.TemporaryDirectory() as directory:
                fixture = json.loads(fixture_path.read_text(encoding="utf-8")); match = fixture["match"]
                root = Path(directory); bankroll = root / "bankroll.txt"
                bankroll.write_text(f"{fixture['starting_bankroll']:.2f}", encoding="utf-8")
                with ExitStack() as stack:
                    for name, value in {
                        "BANKROLL_FILE": bankroll, "LOG_FILE": root / "bets-log.csv",
                        "PAPER_LOG_FILE": root / "paper-bets-log.csv", "PENDING_FILE": root / "pending-bets.csv",
                        "POLICY_FILE": root / "counterfactual-log.csv", "AUDIT_FILE": root / "predictions-log.csv",
                        "TRANSACTION_FILE": root / "bankroll-transactions.csv",
                        "SETTLEMENT_ALERT_FILE": root / "settlement-alerts.md", "RISK_CONFIG_FILE": root / "risk-config.json",
                    }.items():
                        stack.enter_context(patch.object(bot, name, value))
                    stack.enter_context(patch.object(bot, "load_resolved_predictions", return_value=[]))
                    stack.enter_context(patch.object(bot, "manual_kill_switch", return_value={"active": False, "reason": "fixture"}))
                    validated = bot.validate_recommendations([fixture["recommendation"]], [match], fixture["odds_min"], fixture["odds_max"])
                    staged = bot.stage_pending_bets(fixture["date"], validated, fixture["odds_min"], fixture["odds_max"])
                    with (patch.object(bot, "fetch_verified_matches", return_value=[match]),
                          patch.object(bot, "enrich_matches_with_profiles"), patch.object(bot, "enrich_matches_with_recent_form")):
                        authorized, cancelled = bot.revalidate_pending_bets(["fixture-key"], datetime.fromisoformat(fixture["revalidation_time"]))
                    with patch.object(bot, "fetch_odds_json", side_effect=[([fixture["settled_event"]], 0), ([fixture["closing_market"]], 0)]):
                        bot.settle_pending_bets(["fixture-key"])
                    _, bet_rows = bot.read_csv_rows(root / "bets-log.csv"); _, pending_rows = bot.read_csv_rows(root / "pending-bets.csv")

                expected = fixture["expected"]
                self.assertEqual(len(validated), expected["validated"]); self.assertEqual(staged, expected["staged"])
                self.assertEqual((authorized, cancelled), (expected["authorized"], expected["cancelled"]))
                self.assertEqual(pending_rows[0]["STATUS"], "authorized"); self.assertEqual(bet_rows[0]["RESULT"], expected["result"])
                self.assertEqual(bet_rows[0]["BOOKMAKER"], expected["bookmaker"])
                self.assertEqual(float(bet_rows[0]["STAKE"]), expected["starting_stake"])
                self.assertAlmostEqual(float(bankroll.read_text(encoding="utf-8")), expected["ending_bankroll"])

    def test_atomic_text_write_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.txt"; target.write_text("old", encoding="utf-8")
            bot.atomic_write_text(target, "new")
            self.assertEqual(target.read_text(encoding="utf-8"), "new")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_atomic_csv_write_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.csv"
            target.write_text("NAME,VALUE\nold,1\n", encoding="utf-8")

            bot.atomic_write_csv(target, ["NAME", "VALUE"], [{"NAME": "new", "VALUE": "2"}])

            headers, rows = bot.read_csv_rows(target)
            self.assertEqual(headers, ["NAME", "VALUE"])
            self.assertEqual(rows, [{"NAME": "new", "VALUE": "2"}])
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_atomic_csv_failure_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.csv"
            original = "NAME,VALUE\nold,1\n"
            target.write_text(original, encoding="utf-8")

            with patch.object(bot.os, "replace", side_effect=OSError("simulated interruption")):
                with self.assertRaises(OSError):
                    bot.atomic_write_csv(target, ["NAME", "VALUE"], [{"NAME": "new", "VALUE": "2"}])

            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_run_state_recovers_same_interrupted_mode_and_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "run-state.json"
            with patch.object(bot, "RUN_STATE_FILE", state_file):
                bot.begin_run_state("2026-08-01", "daily")
                bot.update_run_state("collection_complete")
                bot.update_run_state("interrupted", "interrupted", "RuntimeError")
                recovered = bot.begin_run_state("2026-08-01", "daily")

            self.assertEqual(recovered["status"], "running")
            self.assertEqual(recovered["phase"], "recovery_started")
            self.assertEqual(recovered["recovered_from_phase"], "collection_complete")
            self.assertEqual(recovered["attempt"], 2)

    def test_run_state_completion_is_durable(self):
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "run-state.json"
            with patch.object(bot, "RUN_STATE_FILE", state_file):
                bot.begin_run_state("2026-08-01", "settlement")
                bot.update_run_state("complete", "complete")
                completed = bot.load_run_state()

            self.assertEqual(completed["status"], "complete")
            self.assertEqual(completed["phase"], "complete")
            self.assertIn("completed_at", completed)

    def test_prediction_schema_migration_creates_exact_versioned_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "predictions-log.csv"
            backups = root / "state-backups"
            original = b"DATE,PICK\r\n2026-07-31,Legacy Player\r\n"
            audit.write_bytes(original)

            with patch.object(bot, "AUDIT_FILE", audit), patch.object(bot, "BACKUPS_DIR", backups):
                bot.append_prediction_audit("2026-08-01", [], [], [])

            backup_files = list(backups.rglob("*.bak"))
            metadata_files = list(backups.rglob("*.bak.json"))
            self.assertEqual(len(backup_files), 1)
            self.assertEqual(backup_files[0].read_bytes(), original)
            self.assertEqual(len(metadata_files), 1)
            metadata = __import__("json").loads(metadata_files[0].read_text(encoding="utf-8"))
            self.assertEqual(metadata["sha256"], __import__("hashlib").sha256(original).hexdigest())
            migrated_headers, migrated_rows = bot.read_csv_rows(audit)
            self.assertIn("MODEL_VERSION", migrated_headers)
            self.assertEqual(migrated_rows[0]["PICK"], "Legacy Player")

    def test_provider_circuit_opens_per_provider_and_recovers_after_cooldown(self):
        bot.CIRCUIT_BREAKERS.clear()
        try:
            for _ in range(bot.CIRCUIT_FAILURE_THRESHOLD):
                bot.record_provider_failure("broken.example", "HTTP 503", now=100.0)

            self.assertTrue(bot.provider_circuit_open("broken.example", now=101.0))
            self.assertFalse(bot.provider_circuit_open("healthy.example", now=101.0))
            self.assertFalse(
                bot.provider_circuit_open(
                    "broken.example", now=100.0 + bot.CIRCUIT_COOLDOWN_SECONDS
                )
            )
            self.assertNotIn("broken.example", bot.CIRCUIT_BREAKERS)
        finally:
            bot.CIRCUIT_BREAKERS.clear()

    @patch.object(bot.requests, "get")
    def test_open_provider_circuit_skips_network_request(self, get):
        bot.CIRCUIT_BREAKERS.clear()
        try:
            bot.CIRCUIT_BREAKERS["api.odds-api.io"] = {
                "failures": 3,
                "opened_until": bot.time.monotonic() + 60,
                "last_error": "HTTP 503",
            }
            payload, key_index = bot.fetch_odds_json(
                "https://api.odds-api.io/v3/events", {}, ["unused-key"], 0
            )
            self.assertIsNone(payload)
            self.assertEqual(key_index, 0)
            get.assert_not_called()
        finally:
            bot.CIRCUIT_BREAKERS.clear()

    def test_automated_rollback_detects_degraded_challenger_and_policy(self):
        rows = []
        for index in range(30):
            won = index % 2 == 0
            rows.append({
                "DATE": f"2026-07-{index + 1:02d}",
                "RESULT": "W" if won else "L",
                "CHALLENGER_PROMOTED": "True",
                "MODEL_PROBABILITY": ".10" if won else ".90",
                "RAW_PROBABILITY": ".90" if won else ".10",
                "DECISION": "Top Pick",
                "OPENING_ODDS": "1.60",
                "CLV": "-.03",
            })

        state = bot.automated_rollback_state(rows)

        self.assertTrue(state["model_rollback"])
        self.assertEqual(state["model_mode"], "static_baseline")
        self.assertTrue(state["policy_rollback"])
        self.assertEqual(state["policy_mode"], "safe_baseline")

    def test_policy_rollback_limits_portfolio_to_one_top_pick(self):
        history = [{
            "DATE": f"2026-07-{index + 1:02d}", "RESULT": "L", "DECISION": "Top Pick",
            "OPENING_ODDS": "1.60", "CLV": "-.03",
        } for index in range(30)]
        recommendations = [
            {"player": "A", "grade": "Top Pick", "ev": .12, "score": 9,
             "match": {"player1": "A", "player2": "B", "tournament": "One"}},
            {"player": "C", "grade": "Top Pick", "ev": .10, "score": 8.5,
             "match": {"player1": "C", "player2": "D", "tournament": "Two"}},
            {"player": "E", "grade": "Value Pick", "ev": .09, "score": 8,
             "match": {"player1": "E", "player2": "F", "tournament": "Three"}},
        ]
        with patch.object(bot, "load_resolved_predictions", return_value=history):
            selected = bot.select_portfolio(recommendations)

        self.assertEqual([item["player"] for item in selected], ["A"])

    def test_rollback_state_is_persisted_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "model-policy-state.json"
            with patch.object(bot, "ROLLBACK_STATE_FILE", state_file):
                state = bot.save_rollback_state([])
            saved = __import__("json").loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["model_mode"], state["model_mode"])
            self.assertEqual(saved["policy_mode"], "standard")

    def test_diagnostic_summary_has_no_mutating_actions(self):
        with patch.object(bot, "fetch_verified_matches", return_value=[]):
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

    def test_provider_collection_schema_change_is_alerted(self):
        bot.SCHEMA_ALERTS.clear()
        try:
            events = bot.normalize_provider_collection(
                {"events": "unexpected"}, "Odds-API.io", "/v3/events"
            )
            self.assertEqual(events, [])
            self.assertIn("changed from list to str", bot.SCHEMA_ALERTS[0]["detail"])
        finally:
            bot.SCHEMA_ALERTS.clear()

    def test_malformed_fixture_is_not_reported_as_empty_schedule(self):
        bot.SCHEMA_ALERTS.clear()
        malformed = [{"id": "7", "date": "2026-08-01T12:00:00Z", "home": "Player One"}]
        try:
            with patch.object(bot, "fetch_odds_json", return_value=(malformed, 0)):
                matches = bot.fetch_matches_from_odds_api("2026-08-01", ["key"])
            self.assertEqual(matches, [])
            self.assertEqual(bot.LAST_FIXTURE_STATUS, "provider_schema_failure")
            self.assertIn("away", bot.SCHEMA_ALERTS[0]["detail"])
        finally:
            bot.SCHEMA_ALERTS.clear()

    def test_nested_odds_schema_change_is_quarantined(self):
        bot.SCHEMA_ALERTS.clear()
        try:
            valid = bot.validate_odds_event_schema({
                "id": "7", "bookmakers": {"Book": {"name": "ML", "odds": []}}
            })
            self.assertFalse(valid)
            self.assertIn("markets changed to dict", bot.SCHEMA_ALERTS[0]["detail"])
        finally:
            bot.SCHEMA_ALERTS.clear()

    def test_espn_scoreboard_parses_only_dated_singles_fixtures(self):
        payload = {"events": [{
            "name": "ATP Test",
            "groupings": [
                {"grouping": {"slug": "mens-doubles"}, "competitions": []},
                {"grouping": {"slug": "mens-singles"}, "competitions": [
                    {"id": "42", "startDate": "2026-08-01T12:00Z",
                     "competitors": [
                         {"athlete": {"displayName": "Player One"}},
                         {"athlete": {"displayName": "Player Two"}},
                     ], "status": {"type": {"state": "pre"}}},
                    {"id": "43", "startDate": "2026-08-02T12:00Z",
                     "competitors": [
                         {"athlete": {"displayName": "Other One"}},
                         {"athlete": {"displayName": "Other Two"}},
                     ]},
                ]},
            ],
        }]}
        fixtures = bot.parse_espn_scoreboard(payload, "2026-08-01", "atp")
        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["event_id"], "espn:atp:42")
        self.assertEqual(fixtures[0]["status"], "pre")

    def test_independent_fixture_cross_check_is_order_insensitive(self):
        primary = [
            {"player1": "Zheng, Michael", "player2": "Arthur Gea"},
            {"player1": "Unmatched One", "player2": "Unmatched Two"},
        ]
        secondary = [{"event_id": "espn:atp:7", "player1": "Arthur Gea", "player2": "Michael Zheng"}]
        checked = bot.cross_check_fixture_sources(primary, secondary)
        self.assertTrue(checked[0]["secondary_fixture_confirmed"])
        self.assertEqual(checked[0]["fixture_sources"], ["Odds-API.io", "ESPN"])
        self.assertFalse(checked[1]["secondary_fixture_confirmed"])

    def test_verified_match_collection_calls_both_independent_sources(self):
        primary = [{"player1": "A", "player2": "B"}]
        secondary = [{"event_id": "espn:atp:1", "player1": "B", "player2": "A"}]
        with (
            patch.object(bot, "fetch_secondary_fixtures", return_value=secondary) as second,
            patch.object(bot, "fetch_matches_from_odds_api", return_value=primary) as first,
        ):
            matches = bot.fetch_verified_matches("2026-08-01", ["key"])
        second.assert_called_once_with("2026-08-01")
        first.assert_called_once_with("2026-08-01", ["key"])
        self.assertTrue(matches[0]["secondary_fixture_confirmed"])

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
        self.assertIn("CLOSING_ODDS", rows[0])
        self.assertIn("BRIER_SCORE", rows[0])

    def test_multiple_threshold_challengers_evaluate_same_candidate_independently(self):
        decisions = bot.threshold_challenger_decisions(.08, .09, 6, .06)
        self.assertEqual(len(decisions), 3)
        by_id = {item["policy_id"]: item for item in decisions}
        self.assertEqual(by_id["threshold-conservative-v1"]["decision"], "cancelled")
        self.assertEqual(by_id["threshold-conservative-v1"]["rule"], "bookmaker_conflict")
        self.assertEqual(by_id["threshold-standard-v1"]["decision"], "authorized")
        self.assertEqual(by_id["threshold-permissive-v1"]["decision"], "authorized")
        blocked = bot.threshold_challenger_decisions(.01, .01, 10, .20, "surface_changed")
        self.assertTrue(all(item["decision"] == "cancelled" and item["rule"] == "surface_changed"
                            for item in blocked))

    def test_counterfactual_log_keeps_parallel_policy_rows(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.csv"
            row = {"DATE": "2026-08-01", "EVENT_ID": "7", "MATCH": "A vs B",
                   "PLAYER1": "A", "PLAYER2": "B", "PICK": "A"}
            baseline = {"player_odds": 1.6, "assessed_probability": .7, "ev": .12}
            with patch.object(bot, "POLICY_FILE", policy):
                for item in bot.threshold_challenger_decisions(.08, .09, 6, .06):
                    bot.record_policy_decision(datetime.now(timezone.utc), row, None, baseline,
                                               item["decision"], item["rule"], item["policy_id"],
                                               "shadow", item["thresholds"])
            _, rows = bot.read_csv_rows(policy)
        self.assertEqual(len(rows), 3)
        self.assertEqual({item["POLICY_ID"] for item in rows},
                         {item["id"] for item in bot.THRESHOLD_CHALLENGER_POLICIES})
        self.assertTrue(all(item["POLICY_ROLE"] == "shadow" for item in rows))

    def test_counterfactual_settlement_records_clv_and_brier(self):
        event = {"id": 7, "date": "2026-08-01T12:00:00Z", "home": "A", "away": "B",
                 "status": "settled", "scores": {"home": 2, "away": 0}}
        odds_event = {"id": 7, "bookmakers": {"Bet365": [{"name": "ML", "odds": [{"home": "1.50", "away": "2.70"}]}]}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / "counterfactual-log.csv"
            bot.atomic_write_csv(policy, bot.POLICY_HEADERS, [{
                "DATE": "2026-08-01", "MODEL_VERSION": bot.MODEL_VERSION, "EVENT_ID": "7",
                "MATCH": "A vs B", "PLAYER1": "A", "PLAYER2": "B", "PICK": "A",
                "DECISION": "cancelled", "RULE": "bookmaker_conflict", "ODDS": "1.60",
                "PROBABILITY": "0.70", "EV": "0.12", "TIMESTAMP": "2026-08-01T11:00:00Z",
            }])
            with (
                patch.object(bot, "LOG_FILE", root / "bets.csv"),
                patch.object(bot, "PAPER_LOG_FILE", root / "paper.csv"),
                patch.object(bot, "POLICY_FILE", policy),
                patch.object(bot, "BANKROLL_FILE", root / "bankroll.txt"),
                patch.object(bot, "SETTLEMENT_ALERT_FILE", root / "settlement-alerts.md"),
                patch.object(bot, "fetch_odds_json", side_effect=[([event], 0), ([odds_event], 0)]),
            ):
                bot.settle_pending_bets(["key"])
            _, rows = bot.read_csv_rows(policy)
        self.assertEqual(rows[0]["RESULT"], "W")
        self.assertEqual(rows[0]["CLOSING_ODDS"], "1.500")
        self.assertEqual(rows[0]["CLV"], "0.066667")
        self.assertEqual(rows[0]["BRIER_SCORE"], "0.090000")

    def test_counterfactual_metrics_group_brier_and_available_clv(self):
        metrics = bot.counterfactual_rule_metrics([
            {"RESULT": "W", "FLAT_RETURN": ".6", "CLV": ".04", "PROBABILITY": ".7"},
            {"RESULT": "L", "FLAT_RETURN": "-1", "CLV": "", "PROBABILITY": ".6"},
        ])
        self.assertEqual(metrics["count"], 2)
        self.assertAlmostEqual(metrics["roi"], -.2)
        self.assertAlmostEqual(metrics["clv"], .04)
        self.assertEqual(metrics["clv_sample"], 1)
        self.assertAlmostEqual(metrics["brier"], (.09 + .36) / 2)

    def test_emergency_kill_switch_detects_calibration_drift(self):
        stable = [{"DATE": "2026-01-01", "RESULT": "W", "MODEL_PROBABILITY": ".9", "CLV": ".02"}] * 30
        degraded = [{"DATE": "2026-02-01", "RESULT": "L", "MODEL_PROBABILITY": ".9", "CLV": "-.05"}] * 30
        self.assertTrue(bot.tennis_kill_switch(stable + degraded)["active"])

    def test_workload_measures_rest_matches_and_sets(self):
        history = [
            {"tourney_date": "20260731", "winner_name": "Player One", "loser_name": "Other", "score": "6-4 6-4", "tourney_name": "Event A", "minutes": "120", "_source_url": "verified-a.csv"},
            {"tourney_date": "20260729", "winner_name": "Other", "loser_name": "Player One", "score": "6-4 4-6 6-3", "tourney_name": "Event A", "minutes": "180", "_source_url": "verified-a.csv"},
            {"tourney_date": "20260727", "winner_name": "Player One", "loser_name": "Other", "score": "7-6 6-7 6-4", "tourney_name": "Event B"},
            {"tourney_date": "20260710", "winner_name": "Player One", "loser_name": "Other", "score": "6-4 6-4", "tourney_name": "Event Old", "minutes": "90", "_source_url": "verified-b.csv"},
            {"tourney_date": "20260630", "winner_name": "Player One", "loser_name": "Other", "score": "6-4 6-4", "tourney_name": "Event Too Old", "minutes": "80"},
        ]
        workload = bot.calculate_workload(history, "Player One", "2026-08-01", "Event C", "hard")
        self.assertEqual((workload["rest_days"], workload["matches_7"], workload["sets_7"]), (1, 3, 8))
        self.assertEqual(workload["matches_14"], 3)
        self.assertEqual(workload["matches_30"], 4)
        self.assertEqual(workload["last_match_minutes"], 120)
        self.assertEqual((workload["minutes_7"], workload["minutes_14"], workload["minutes_30"]), (300, 300, 390))
        self.assertEqual(workload["duration_sample_30"], 3)
        self.assertEqual(workload["duration_source"], "verified-a.csv;verified-b.csv")
        self.assertFalse(workload["last_match_long"])
        self.assertEqual(workload["long_matches_7"], 1)
        self.assertEqual(workload["long_matches_30"], 1)
        self.assertEqual(workload["latest_long_match_minutes"], 180)
        self.assertEqual(workload["latest_long_match_days_ago"], 3)
        self.assertEqual(workload["previous_tournament"], "Event A")
        self.assertIsNone(workload["previous_tournament_surface"])
        self.assertIsNone(workload["surface_change"])
        self.assertGreater(workload["penalty"], 0)

    def test_workload_never_estimates_missing_match_duration(self):
        history = [{"tourney_date": "20260731", "winner_name": "Player", "loser_name": "Other", "score": "6-4 6-4", "minutes": ""}]
        workload = bot.calculate_workload(history, "Player", "2026-08-01")
        self.assertIsNone(workload["last_match_minutes"])
        self.assertIsNone(workload["latest_verified_minutes"])
        self.assertEqual(workload["minutes_30"], 0)
        self.assertEqual(workload["duration_sample_30"], 0)
        self.assertIsNone(workload["last_match_long"])

    def test_unusually_long_match_threshold_distinguishes_bo3_and_bo5(self):
        bo3 = [{"tourney_date": "20260731", "winner_name": "Player", "loser_name": "Other", "score": "6-4 4-6 6-4", "minutes": "200", "best_of": "3"}]
        bo5 = [{"tourney_date": "20260731", "winner_name": "Player", "loser_name": "Other", "score": "6-4 6-4 6-4", "minutes": "220", "best_of": "5"}]
        workload_bo3 = bot.calculate_workload(bo3, "Player", "2026-08-01")
        workload_bo5 = bot.calculate_workload(bo5, "Player", "2026-08-01")
        self.assertTrue(workload_bo3["last_match_long"])
        self.assertEqual(workload_bo3["last_match_long_threshold"], 180)
        self.assertFalse(workload_bo5["last_match_long"])
        self.assertEqual(workload_bo5["last_match_long_threshold"], 240)
        self.assertEqual(workload_bo3["penalty"], workload_bo5["penalty"])

    def test_surface_change_uses_previous_different_tournament(self):
        history = [
            {"tourney_date": "20260731", "winner_name": "Player", "loser_name": "Other",
             "score": "6-4 6-4", "tourney_name": "Current Event", "surface": "Hard"},
            {"tourney_date": "20260728", "winner_name": "Player", "loser_name": "Other",
             "score": "6-4 6-4", "tourney_name": "Previous Event", "surface": "Clay",
             "_source_url": "verified-history.csv", "latitude": "40.4168", "longitude": "-3.7038",
             "timezone": "Europe/Madrid"},
        ]
        current_location = bot.verified_location(51.5074, -0.1278, "Europe/London", "official-current-event", "2026-08-01")
        workload = bot.calculate_workload(history, "Player", "2026-08-01", "Current Event", "Hard", current_location)
        self.assertEqual(workload["previous_tournament"], "Previous Event")
        self.assertEqual(workload["previous_tournament_surface"], "clay")
        self.assertEqual(workload["current_surface"], "hard")
        self.assertTrue(workload["surface_change"])
        self.assertEqual(workload["previous_tournament_days_ago"], 4)
        self.assertEqual(workload["surface_transition_source"], "verified-history.csv")
        self.assertAlmostEqual(workload["travel_distance_km"], 1263.4, delta=2)
        self.assertEqual(workload["timezone_change_hours"], -1)
        self.assertEqual(workload["travel_source"], "verified-history.csv;official-current-event")

    def test_surface_change_is_unknown_without_two_verified_surfaces(self):
        history = [{"tourney_date": "20260728", "winner_name": "Player", "loser_name": "Other",
                    "score": "6-4 6-4", "tourney_name": "Previous Event", "surface": ""}]
        workload = bot.calculate_workload(history, "Player", "2026-08-01", "Current Event", "Hard")
        self.assertIsNone(workload["previous_tournament_surface"])
        self.assertIsNone(workload["surface_change"])

    def test_travel_requires_sourced_valid_coordinates(self):
        self.assertIsNone(bot.verified_location(40, -3, "Europe/Madrid", "", "2026-08-01"))
        self.assertIsNone(bot.verified_location(100, -3, "Europe/Madrid", "official", "2026-08-01"))
        current = bot.verified_location(40, -3, "invalid/timezone", "official", "2026-08-01")
        previous = bot.verified_location(41, -4, "Europe/Madrid", "history", "2026-08-01")
        travel = bot.travel_between_locations(previous, current)
        self.assertIsNotNone(travel["travel_distance_km"])
        self.assertIsNone(travel["timezone_change_hours"])

    def test_verified_tournament_location_registry_rejects_unsourced_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            location_file = Path(directory) / "locations.csv"
            location_file.write_text(
                "TOURNAMENT,LATITUDE,LONGITUDE,TIMEZONE,SOURCE\n"
                "Verified Event,40.4,-3.7,Europe/Madrid,official-calendar\n"
                "Unsourced Event,51.5,-0.1,Europe/London,\n", encoding="utf-8"
            )
            with patch.object(bot, "TOURNAMENT_LOCATIONS_FILE", location_file):
                locations = bot.load_verified_tournament_locations("2026-08-01")
        self.assertIn(bot.normalize_player_name("Verified Event"), locations)
        self.assertNotIn(bot.normalize_player_name("Unsourced Event"), locations)

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
        self.assertIn("TIMESTAMP,QUOTE_TIMESTAMP,DATE,EVENT_ID,MATCH,PICK,ODDS", text)
        self.assertIn("1.550", text)

    def test_price_velocity_and_acceleration_use_ordered_snapshots(self):
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / "pending.csv"
            row = {"DATE": "2026-08-01", "EVENT_ID": "7", "MATCH": "A vs B", "PICK": "A"}
            match = {"player1": "A", "player2": "B", "bookmaker_count": 3, "home_dispersion": .04}
            start = datetime(2026, 8, 1, 9, tzinfo=timezone.utc)
            with patch.object(bot, "PENDING_FILE", pending):
                first = bot.append_price_snapshot(start, row, match, {"player_odds": 2.0})
                second = bot.append_price_snapshot(start + timedelta(hours=1), row, match, {"player_odds": 1.8})
                third = bot.append_price_snapshot(start + timedelta(hours=2), row, match, {"player_odds": 1.53})
                _, snapshots = bot.read_csv_rows(Path(directory) / "price-history.csv")
        self.assertEqual(first["snapshot_count"], 1)
        self.assertIsNone(first["velocity_per_hour"])
        self.assertAlmostEqual(second["velocity_per_hour"], -.10)
        self.assertIsNone(second["acceleration_per_hour2"])
        self.assertAlmostEqual(third["price_movement"], -.235)
        self.assertAlmostEqual(third["velocity_per_hour"], -.15)
        self.assertAlmostEqual(third["acceleration_per_hour2"], -.05)
        self.assertEqual(snapshots[-1]["SNAPSHOT_COUNT"], "3")
        self.assertEqual(snapshots[-1]["VELOCITY_PER_HOUR"], "-0.150000")
        self.assertEqual(snapshots[-1]["ACCELERATION_PER_HOUR2"], "-0.050000")

    def test_authorization_lifecycle_persists_price_dynamics_to_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = Path(directory) / "audit.csv"
            headers = ["DATE", "PICK", "DECISION", "REASON", "PRICE_SNAPSHOT_COUNT",
                       "PRICE_VELOCITY_PER_HOUR", "PRICE_ACCELERATION_PER_HOUR2", "PRICE_AGE_MINUTES", "PRICE_STALE",
                       "AUTH_PRICE_MOVEMENT", "AUTH_MARKET_DISPERSION", "MARKET_LIMIT_POLICY_ID",
                       "MARKET_LIMIT_POLICY_SAMPLE", "MARKET_LIMIT_POLICY_HOLDOUT", "MARKET_LIMIT_MOVEMENT",
                       "MARKET_LIMIT_DISPERSION", "MARKET_LIMIT_PROMOTED"]
            bot.atomic_write_csv(audit, headers, [{"DATE": "2026-08-01", "PICK": "A"}])
            dynamics = {"snapshot_count": 3, "velocity_per_hour": -.15, "acceleration_per_hour2": -.05,
                        "price_age_minutes": 2.5, "stale": False, "authorization_price_movement": .04,
                        "authorization_market_dispersion": .03, "market_limit_policy_id": "atp-move0.060-disp0.080",
                        "market_limit_policy_sample": 240, "market_limit_policy_holdout": 72,
                        "market_limit_movement": .06, "market_limit_dispersion": .08,
                        "market_limit_promoted": True}
            with patch.object(bot, "AUDIT_FILE", audit):
                bot.update_audit_lifecycle("2026-08-01", "A", "Authorized", "pre_match_validated", dynamics)
            _, rows = bot.read_csv_rows(audit)
        self.assertEqual(rows[0]["PRICE_SNAPSHOT_COUNT"], "3")
        self.assertEqual(rows[0]["PRICE_VELOCITY_PER_HOUR"], "-0.150000")
        self.assertEqual(rows[0]["PRICE_ACCELERATION_PER_HOUR2"], "-0.050000")
        self.assertEqual(rows[0]["PRICE_AGE_MINUTES"], "2.500")
        self.assertEqual(rows[0]["PRICE_STALE"], "False")
        self.assertEqual(rows[0]["AUTH_PRICE_MOVEMENT"], "0.040000")
        self.assertEqual(rows[0]["AUTH_MARKET_DISPERSION"], "0.030000")
        self.assertEqual(rows[0]["MARKET_LIMIT_POLICY_ID"], "atp-move0.060-disp0.080")
        self.assertEqual(rows[0]["MARKET_LIMIT_PROMOTED"], "True")

    def test_stale_price_uses_provider_quote_timestamp(self):
        from datetime import datetime, timedelta, timezone
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / "pending.csv"
            now = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
            quote_time = now - timedelta(minutes=30)
            row = {"DATE": "2026-08-01", "EVENT_ID": "7", "MATCH": "A vs B", "PICK": "A"}
            match = {"player1": "A", "player2": "B", "odds_timestamp": quote_time.isoformat()}
            with patch.object(bot, "PENDING_FILE", pending):
                dynamics = bot.append_price_snapshot(now, row, match, {"player_odds": 1.6})
                _, snapshots = bot.read_csv_rows(Path(directory) / "price-history.csv")
        self.assertEqual(dynamics["price_age_minutes"], 30)
        self.assertTrue(dynamics["stale"])
        self.assertEqual(snapshots[-1]["PRICE_AGE_MINUTES"], "30.000")
        self.assertEqual(snapshots[-1]["STALE"], "True")

    def test_provider_quote_timestamp_rejects_future_metadata(self):
        from datetime import datetime, timedelta, timezone
        received = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
        old = bot.provider_quote_timestamp(received, {"updatedAt": (received - timedelta(minutes=3)).isoformat()})
        future = bot.provider_quote_timestamp(received, {"updatedAt": (received + timedelta(hours=1)).isoformat()})
        self.assertTrue(old.startswith("2026-08-01T11:57:00"))
        self.assertEqual(future, "")

    def test_tournament_correlation_cap(self):
        recs = [{"player": f"P{i}", "grade": "Value Pick", "ev": .10 - i * .01, "score": 8,
                 "match": {"player1": f"P{i}", "player2": f"O{i}", "tournament": "ATP Test", "level": "ATP"}} for i in range(3)]
        self.assertEqual(len(bot.select_portfolio(recs, max_exposure=.2, max_bets=4)), 2)

    def test_configurable_tour_exposure_caps_are_independent(self):
        recommendations = [
            {"player": "A", "grade": "Top Pick", "ev": .15, "score": 9,
             "match": {"player1": "A", "player2": "B", "tournament": "ITF One", "level": "ITF"}},
            {"player": "C", "grade": "Top Pick", "ev": .14, "score": 9,
             "match": {"player1": "C", "player2": "D", "tournament": "ITF Two", "level": "ITF"}},
            {"player": "E", "grade": "Top Pick", "ev": .13, "score": 9,
             "match": {"player1": "E", "player2": "F", "tournament": "ATP One", "level": "ATP"}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "risk-config.json"
            config.write_text('{"tour_exposure_caps":{"ITF":0.03,"ATP":0.08}}', encoding="utf-8")
            with patch.object(bot, "RISK_CONFIG_FILE", config), patch.object(bot, "load_resolved_predictions", return_value=[]):
                selected = bot.select_portfolio(recommendations, max_exposure=.08, max_bets=4)
        self.assertEqual([item["player"] for item in selected], ["A", "E"])

    def test_persistent_external_cache_avoids_repeat_network_request(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "external-cache.json"
            url = "https://tennisabstract.com/reports/atp_elo_ratings.html"
            bot.SOURCE_HEALTH.clear()
            with patch.object(bot, "EXTERNAL_CACHE_FILE", cache), patch.object(bot.time, "time", return_value=1000.0):
                bot.cache_external_response("direct", url, "cached leaderboard")
                with patch.object(bot.requests, "get") as get:
                    result = bot.fetch(url, cache_ttl=3600, stale_if_error=7200)
            self.assertEqual(result, "cached leaderboard")
            get.assert_not_called()
            self.assertEqual(bot.SOURCE_HEALTH[-1]["mode"], "fresh_cache")
            self.assertFalse(bot.SOURCE_HEALTH[-1]["stale"])
            bot.SOURCE_HEALTH.clear()

    def test_stale_external_cache_is_used_only_after_provider_failure(self):
        bot.SOURCE_HEALTH.clear()
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "external-cache.json"
            url = "https://tennisabstract.com/reports/wta_elo_ratings.html"
            with patch.object(bot, "EXTERNAL_CACHE_FILE", cache), patch.object(bot.time, "time", return_value=1000.0):
                bot.cache_external_response("direct", url, "older leaderboard")
            with (
                patch.object(bot, "EXTERNAL_CACHE_FILE", cache),
                patch.object(bot.time, "time", return_value=5000.0),
                patch.object(bot.time, "sleep"),
                patch.object(bot.requests, "get", side_effect=bot.requests.ConnectionError("offline")) as get,
            ):
                result = bot.fetch(url, cache_ttl=60, stale_if_error=7200)
            self.assertEqual(result, "older leaderboard")
            self.assertEqual(get.call_count, bot.MAX_TRANSIENT_RETRIES + 1)
            self.assertEqual(bot.SOURCE_HEALTH[-1]["mode"], "stale_cache")
            self.assertTrue(bot.SOURCE_HEALTH[-1]["stale"])
            self.assertGreater(bot.SOURCE_HEALTH[-1]["cache_age_seconds"], 0)
            bot.SOURCE_HEALTH.clear()

    def test_source_health_report_summarizes_latency_and_stale_cache(self):
        events = [
            {"source": "example.test", "ok": True, "detail": "HTTP 200", "latency_ms": 100,
             "mode": "network", "cache_age_seconds": None, "stale": False, "timestamp": "2026-08-01T10:00:00Z"},
            {"source": "example.test", "ok": False, "detail": "ConnectionError", "latency_ms": 300,
             "mode": "network", "cache_age_seconds": None, "stale": False, "timestamp": "2026-08-01T10:01:00Z"},
            {"source": "example.test", "ok": True, "detail": "stale cache after provider failure", "latency_ms": 2,
             "mode": "stale_cache", "cache_age_seconds": 4000.0, "stale": True, "timestamp": "2026-08-01T10:01:01Z"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bot.SOURCE_HEALTH[:] = events
            try:
                with (patch.object(bot, "REPO_ROOT", root), patch.object(bot, "SOURCE_HEALTH_FILE", root / "source-health.md"),
                      patch.object(bot, "save_api_quota_report"), patch.object(bot, "save_schema_alert_report"),
                      patch.object(bot, "save_identity_queue_report")):
                    bot.save_source_health()
                report = (root / "source-health.md").read_text(encoding="utf-8")
                payload = json.loads((root / "source-health.json").read_text(encoding="utf-8"))
            finally:
                bot.SOURCE_HEALTH.clear()
        self.assertIn("## STALE RESPONSES DETECTED", report)
        self.assertIn("| example.test | 3 | 2 | 1 | 134.0 ms | 300.0 ms | 300.0 ms | 1 | 1 |", report)
        self.assertEqual(payload["stale_responses"], 1)
        self.assertEqual(payload["summary"][0]["p95_latency_ms"], 300.0)

    def test_api_quota_report_tracks_safe_headers_without_credentials(self):
        response = unittest.mock.Mock(
            status_code=200,
            headers={
                "x-ratelimit-remaining-requests": "14370",
                "x-ratelimit-remaining-tokens": "17997",
                "Authorization": "Bearer secret-value",
                "Set-Cookie": "private-cookie",
            },
        )
        bot.API_QUOTA.clear()
        try:
            with tempfile.TemporaryDirectory() as directory:
                report = Path(directory) / "api-quota.md"
                with patch.object(bot, "API_QUOTA_FILE", report):
                    bot.record_api_quota("Groq", response, "key-2")
                    bot.save_api_quota_report()
                text = report.read_text(encoding="utf-8")
            self.assertIn("Groq | key-2 | 1 | 200", text)
            self.assertIn("x-ratelimit-remaining-tokens=17997", text)
            self.assertNotIn("secret-value", text)
            self.assertNotIn("private-cookie", text)
        finally:
            bot.API_QUOTA.clear()

    def test_calibration_requires_mature_probability_bucket(self):
        rows = [{"MODEL_PROBABILITY": ".60", "RESULT": "W"} for _ in range(99)]
        self.assertEqual(bot.calibrate_probability(.60, rows), (.60, 99))
        rows.append({"MODEL_PROBABILITY": ".60", "RESULT": "W"})
        probability, sample = bot.calibrate_probability(.60, rows)
        self.assertEqual(sample, 100)
        self.assertGreater(probability, .60)

    def test_log_loss_and_expected_calibration_error(self):
        rows = [
            {"MODEL_PROBABILITY": ".90", "RESULT": "W"},
            {"MODEL_PROBABILITY": ".10", "RESULT": "L"},
            {"MODEL_PROBABILITY": "invalid", "RESULT": "W"},
            {"MODEL_PROBABILITY": ".50", "RESULT": "V"},
        ]
        metrics = bot.probability_metrics(rows)
        self.assertEqual(metrics["sample"], 2)
        self.assertAlmostEqual(metrics["brier"], .01)
        self.assertAlmostEqual(metrics["log_loss"], -__import__("math").log(.9))
        self.assertAlmostEqual(metrics["ece"], .10)
        self.assertEqual(metrics["bins"], 10)

    def test_log_loss_clamps_extreme_probabilities(self):
        metrics = bot.probability_metrics([{"MODEL_PROBABILITY": "1", "RESULT": "L"}])
        self.assertTrue(__import__("math").isfinite(metrics["log_loss"]))
        self.assertEqual(metrics["ece"], 1.0)

    def test_performance_report_publishes_log_loss_and_ece(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / "predictions.csv"
            audit.write_text("MODEL_PROBABILITY,CHALLENGER_PROBABILITY,RESULT\n0.9,0.8,W\n0.1,0.2,L\n", encoding="utf-8")
            performance = root / "performance.md"
            with (patch.object(bot, "AUDIT_FILE", audit), patch.object(bot, "LOG_FILE", root / "bets.csv"),
                  patch.object(bot, "POLICY_FILE", root / "policy.csv"), patch.object(bot, "PERFORMANCE_FILE", performance),
                  patch.object(bot, "BACKTEST_FILE", root / "backtest.md"), patch.object(bot, "REPO_ROOT", root)):
                bot.generate_performance_summary()
            report = performance.read_text(encoding="utf-8")
        self.assertIn("- Log loss: 0.1054", report)
        self.assertIn("- Expected calibration error (10 bins): 10.00%", report)
        self.assertIn("- Shadow challenger log loss: 0.2231", report)
        self.assertIn("- Shadow challenger ECE (10 bins): 20.00%", report)

    def test_weekly_health_reports_counterfactual_clv_and_brier_by_rejection_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / "counterfactual.csv"
            bot.atomic_write_csv(policy, bot.POLICY_HEADERS, [{
                "DATE": "2026-08-01", "DECISION": "cancelled", "RULE": "bookmaker_conflict",
                "RESULT": "W", "FLAT_RETURN": ".600", "CLV": ".040000",
                "PROBABILITY": ".700000", "BRIER_SCORE": ".090000",
            }, {
                "DATE": "2026-08-01", "POLICY_ID": "threshold-standard-v1", "POLICY_ROLE": "shadow",
                "DECISION": "authorized", "RULE": "thresholds_passed", "RESULT": "W",
                "FLAT_RETURN": ".600", "CLV": ".040000", "PROBABILITY": ".700000",
                "BRIER_SCORE": ".090000",
            }])
            with (patch.object(bot, "AUDIT_FILE", root / "predictions.csv"),
                  patch.object(bot, "LOG_FILE", root / "bets.csv"),
                  patch.object(bot, "POLICY_FILE", policy),
                  patch.object(bot, "PERFORMANCE_FILE", root / "performance.md"),
                  patch.object(bot, "BACKTEST_FILE", root / "backtest.md"),
                  patch.object(bot, "REPO_ROOT", root)):
                bot.generate_performance_summary()
            report = (root / "weekly-health.md").read_text(encoding="utf-8")
        self.assertIn("| Rejection rule | Decisions | Flat-unit ROI | Avg CLV | Brier |", report)
        self.assertIn("| bookmaker_conflict | 1 | 60.00% | 4.00% | 0.0900 |", report)
        self.assertIn("## Simultaneous threshold challengers", report)
        self.assertIn("| threshold-standard-v1 | 1 | 1 | 60.00% | 4.00% | 0.0900 |", report)

    def test_monthly_threshold_recommendations_require_mature_superior_evidence(self):
        active = {"count": 30, "roi": .05, "clv": .01, "clv_sample": 30, "brier": .20, "brier_sample": 30}
        immature = {"count": 29, "roi": .20, "clv": .03, "clv_sample": 29, "brier": .10, "brier_sample": 29}
        superior = {"count": 30, "roi": .10, "clv": .02, "clv_sample": 30, "brier": .15, "brier_sample": 30}
        harmful = {"count": 30, "roi": -.01, "clv": -.01, "clv_sample": 30, "brier": .15, "brier_sample": 30}
        self.assertEqual(bot.monthly_threshold_recommendation(immature, active), "collecting data")
        self.assertEqual(bot.monthly_threshold_recommendation(superior, active), "review for promotion")
        self.assertEqual(bot.monthly_threshold_recommendation(harmful, active), "do not promote")

    def test_monthly_policy_report_groups_calendar_months_and_keeps_advice_non_binding(self):
        rows = [
            {"DATE": "2026-07-10", "POLICY_ROLE": "active", "DECISION": "cancelled",
             "RULE": "bookmaker_conflict", "RESULT": "L", "FLAT_RETURN": "-1",
             "PROBABILITY": ".70", "BRIER_SCORE": ".49", "CLV": "-.02"},
            {"DATE": "2026-07-10", "POLICY_ROLE": "shadow", "POLICY_ID": "threshold-standard-v1",
             "THRESHOLDS": "movement<=.100", "DECISION": "authorized", "RESULT": "W",
             "FLAT_RETURN": ".60", "PROBABILITY": ".70", "BRIER_SCORE": ".09", "CLV": ".03"},
            {"DATE": "2026-08-02", "POLICY_ROLE": "shadow", "POLICY_ID": "threshold-standard-v1",
             "THRESHOLDS": "movement<=.100", "DECISION": "authorized", "RESULT": "L",
             "FLAT_RETURN": "-1", "PROBABILITY": ".70", "BRIER_SCORE": ".49", "CLV": "-.01"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "monthly.md"
            bot.generate_monthly_policy_report(rows, output)
            report = output.read_text(encoding="utf-8")
        self.assertIn("## 2026-07", report)
        self.assertIn("## 2026-08", report)
        self.assertIn("| bookmaker_conflict | 1 | -100.00% | -2.00% | 0.4900 |", report)
        self.assertIn("threshold-standard-v1", report)
        self.assertIn("collecting data", report)
        self.assertIn("never alter live thresholds automatically", report)

    def test_abnormal_rejection_and_zero_pick_counts_use_mature_robust_baseline(self):
        rows = []
        for day in range(1, 8):
            for index in range(10):
                rows.append({"DATE": f"2026-07-{day:02d}", "POLICY_ROLE": "active",
                             "DECISION": "authorized" if index < 5 else "cancelled"})
        for index in range(10):
            rows.append({"DATE": "2026-07-08", "POLICY_ROLE": "active", "DECISION": "cancelled"})
        result = bot.detect_abnormal_policy_counts(rows, "2026-07-08")
        codes = {alert["code"] for alert in result["alerts"]}
        self.assertTrue(result["mature"])
        self.assertIn("abnormal_authorized", codes)
        self.assertIn("abnormal_rejected", codes)
        self.assertIn("abnormal_rejection_rate", codes)
        self.assertIn("zero_authorized_picks", codes)

    def test_count_alerts_wait_for_history_and_report_operator_warning(self):
        immature = [{"DATE": "2026-07-01", "POLICY_ROLE": "active", "DECISION": "cancelled"} for _ in range(20)]
        self.assertFalse(bot.detect_abnormal_policy_counts(immature, "2026-07-01")["alerts"])
        rows = []
        for day in range(1, 8):
            rows.extend({"DATE": f"2026-07-{day:02d}", "POLICY_ROLE": "active",
                         "DECISION": "authorized" if index < 5 else "cancelled"} for index in range(10))
        rows.extend({"DATE": "2026-07-08", "POLICY_ROLE": "active", "DECISION": "cancelled"} for _ in range(10))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "operations.md"
            bot.generate_operations_alert_report(rows, output, "2026-07-08")
            report = output.read_text(encoding="utf-8")
        self.assertIn("## ABNORMAL REJECTION OR PICK COUNTS", report)
        self.assertIn("zero picks were authorized from 10 candidates", report)
        self.assertIn("| Authorized picks | 5.0 | 0.0 |", report)

    def test_tour_calibration_never_borrows_other_tours(self):
        rows = ([{"MODEL_PROBABILITY": ".60", "RESULT": "W", "TOUR": "ATP"} for _ in range(99)] +
                [{"MODEL_PROBABILITY": ".60", "RESULT": "L", "TOUR": "WTA"} for _ in range(100)])
        atp = bot.calibrate_probability_by_tour(.60, rows, "ATP")
        wta = bot.calibrate_probability_by_tour(.60, rows, "WTA")
        self.assertEqual(atp["sample"], 99)
        self.assertFalse(atp["applied"])
        self.assertEqual(atp["probability"], .60)
        self.assertEqual(wta["sample"], 100)
        self.assertTrue(wta["applied"])
        self.assertLess(wta["probability"], .60)

    def test_unknown_tour_is_never_calibrated(self):
        rows = [{"MODEL_PROBABILITY": ".60", "RESULT": "W", "TOUR": "ATP"} for _ in range(200)]
        result = bot.calibrate_probability_by_tour(.60, rows, "Unknown")
        self.assertEqual(result, {"probability": .60, "sample": 0, "segment": "Unknown", "applied": False})

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

    def test_bookmaker_retirement_rules_are_configurable_and_safe_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "risk-config.json"
            config.write_text(json.dumps({"retirement_settlement": {
                "default": "void", "bookmakers": {
                    "Book A": "official_result", "Book B": "action_after_first_set"
                }}}), encoding="utf-8")
            retired_after_set = {"retired": True, "scores": {"home": 1, "away": 0}}
            retired_before_set = {"retired": True, "scores": {"home": 0, "away": 0}}
            with patch.object(bot, "RISK_CONFIG_FILE", config):
                self.assertEqual(bot.retirement_settlement_rule(retired_after_set, "Book A"),
                                 (False, "retirement:official_result"))
                self.assertEqual(bot.retirement_settlement_rule(retired_after_set, "Book B"),
                                 (False, "retirement:action_after_first_set:grade"))
                self.assertEqual(bot.retirement_settlement_rule(retired_before_set, "Book B"),
                                 (True, "retirement:action_after_first_set:void"))
                self.assertEqual(bot.retirement_settlement_rule(retired_after_set, "Unknown"),
                                 (True, "retirement:void"))

    def test_invalid_retirement_configuration_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "risk-config.json"
            config.write_text('{"retirement_settlement":{"default":"invented"}}', encoding="utf-8")
            with patch.object(bot, "RISK_CONFIG_FILE", config):
                self.assertEqual(bot.retirement_policy_for_bookmaker("Any Book"), "void")

    def test_retired_match_can_be_graded_under_recorded_bookmaker_rule(self):
        event = {"id": 7, "date": "2026-08-01T12:00:00Z", "status": "settled", "retired": True,
                 "home": "A", "away": "B", "scores": {"home": 2, "away": 0}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "bets.csv"
            log_path.write_text(
                "DATE,MATCH,BET,ODDS,BOOKMAKER,STAKE,RESULT,RETURN,STARTING BALANCE,SETTLEMENT_RULE\n"
                "2026-08-01,A vs B,A to win,2.00,Book A,3.00,,,100.00,\n", encoding="utf-8")
            config = root / "risk-config.json"
            config.write_text('{"retirement_settlement":{"default":"void","bookmakers":{"Book A":"official_result"}}}', encoding="utf-8")
            (root / "bankroll.txt").write_text("97.00", encoding="utf-8")
            with (patch.object(bot, "LOG_FILE", log_path), patch.object(bot, "PAPER_LOG_FILE", root / "paper.csv"),
                  patch.object(bot, "POLICY_FILE", root / "policy.csv"), patch.object(bot, "BANKROLL_FILE", root / "bankroll.txt"),
                  patch.object(bot, "TRANSACTION_FILE", root / "transactions.csv"), patch.object(bot, "RISK_CONFIG_FILE", config),
                  patch.object(bot, "SETTLEMENT_ALERT_FILE", root / "alerts.md"),
                  patch.object(bot, "fetch_odds_json", side_effect=[([event], 0), ([], 0)]),
                  patch.object(bot, "update_audit_result")):
                bot.settle_pending_bets(["key"])
            _, rows = bot.read_csv_rows(log_path)
        self.assertEqual(rows[0]["RESULT"], "W")
        self.assertEqual(rows[0]["RETURN"], "6.00")
        self.assertEqual(rows[0]["SETTLEMENT_RULE"], "retirement:official_result")

    def test_walk_forward_weights_stay_shadow_without_enough_history(self):
        rows = [{"DATE": f"2026-01-{(index % 28) + 1:02d}", "RESULT": "W",
                 "ELO_PROBABILITY": ".60", "MARKET_PROBABILITY": ".55",
                 "MODEL_PROBABILITY": ".58"} for index in range(199)]
        self.assertIsNone(bot.learned_component_weights(rows))

    def test_bo3_and_bo5_models_have_independent_maturity(self):
        bo3 = [{"DATE": f"2026-01-{index:03d}", "RESULT": "W" if index % 2 else "L",
                "ELO_PROBABILITY": ".60", "MARKET_PROBABILITY": ".55",
                "MODEL_PROBABILITY": ".58", "BEST_OF": "3"} for index in range(200)]
        bo5 = [{"DATE": f"2026-02-{index:03d}", "RESULT": "W" if index % 2 else "L",
                "ELO_PROBABILITY": ".60", "MARKET_PROBABILITY": ".55",
                "MODEL_PROBABILITY": ".58", "BEST_OF": "5"} for index in range(199)]
        learned_bo3 = bot.learned_format_component_weights(bo3 + bo5, 3)
        self.assertIsNotNone(learned_bo3)
        self.assertEqual(learned_bo3["sample"], 200)
        self.assertEqual(learned_bo3["format"], "BO3")
        self.assertIsNone(bot.learned_format_component_weights(bo3 + bo5, 5))

    def test_indoor_and_outdoor_models_have_independent_maturity(self):
        indoor = [{"DATE": f"2026-01-{index:03d}", "RESULT": "W" if index % 2 else "L",
                   "ELO_PROBABILITY": ".60", "MARKET_PROBABILITY": ".55",
                   "MODEL_PROBABILITY": ".58", "INDOOR": "True"} for index in range(200)]
        outdoor = [{"DATE": f"2026-02-{index:03d}", "RESULT": "W" if index % 2 else "L",
                    "ELO_PROBABILITY": ".60", "MARKET_PROBABILITY": ".55",
                    "MODEL_PROBABILITY": ".58", "INDOOR": "False"} for index in range(199)]
        learned_indoor = bot.learned_environment_component_weights(indoor + outdoor, True)
        self.assertIsNotNone(learned_indoor)
        self.assertEqual(learned_indoor["sample"], 200)
        self.assertEqual(learned_indoor["environment"], "Indoor")
        self.assertIsNone(bot.learned_environment_component_weights(indoor + outdoor, False))

    def test_best_promoted_component_model_uses_relative_holdout_gain_and_rollback(self):
        candidates = [
            {"name": "format:BO3", "probability": .61,
             "learned": {"promoted": True, "active_brier": .20, "challenger_brier": .19}},
            {"name": "environment:Outdoor", "probability": .62,
             "learned": {"promoted": True, "active_brier": .30, "challenger_brier": .27}},
        ]
        self.assertEqual(bot.choose_promoted_component_model(candidates, False)["name"], "environment:Outdoor")
        self.assertIsNone(bot.choose_promoted_component_model(candidates, True))

    def test_workload_learner_requires_mature_sample(self):
        rows = [{"DATE": f"2026-{index:03d}", "EVENT_ID": str(index), "PICK": "Player",
                 "RESULT": "W", "MODEL_PROBABILITY": ".70", "WORKLOAD_PENALTY": "0",
                 "MATCHES_7": "3", "SETS_7": "8", "REST_DAYS": "1"}
                for index in range(bot.MIN_WORKLOAD_TRAINING_SAMPLE - 1)]
        self.assertIsNone(bot.learned_workload_policy(rows))

    def test_workload_learner_promotes_only_after_holdout_improvement(self):
        rows = []
        for index in range(240):
            dense = index % 2 == 0
            rows.append({
                "DATE": f"2026-{index:03d}", "EVENT_ID": str(index), "PICK": "Player",
                "RESULT": "L" if dense else "W", "MODEL_PROBABILITY": ".70",
                "WORKLOAD_PENALTY": "0", "MATCHES_7": "5" if dense else "1",
                "SETS_7": "12" if dense else "2", "REST_DAYS": "0" if dense else "5",
                "TOURNAMENT_CHANGE": "False",
            })
        learned = bot.learned_workload_policy(rows)
        self.assertIsNotNone(learned)
        self.assertEqual(learned["holdout"], 72)
        self.assertTrue(learned["promoted"])
        self.assertGreaterEqual(learned["holdout_triggered"], 20)
        self.assertLess(learned["challenger_holdout_brier"], learned["active_holdout_brier"])
        self.assertLessEqual(bot.workload_policy_penalty({"matches_7": 9, "sets_7": 20, "rest_days": 0}, learned["policy"]), .03)

    def test_market_limit_learner_requires_mature_tour_specific_sample(self):
        rows = [{"DATE": f"2026-{index:03d}", "EVENT_ID": str(index), "PICK": "Player",
                 "TOUR": "ATP", "RESULT": "W", "MODEL_PROBABILITY": ".70",
                 "AUTH_PRICE_MOVEMENT": ".02", "AUTH_MARKET_DISPERSION": ".02"}
                for index in range(bot.MIN_MARKET_LIMIT_TRAINING_SAMPLE - 1)]
        self.assertIsNone(bot.learned_market_limits(rows, "ATP"))
        self.assertIsNone(bot.learned_market_limits(rows, "WTA"))

    def test_market_limit_learner_promotes_stricter_limits_after_holdout_gain(self):
        rows = []
        for index in range(300):
            risk_type = index % 3
            rows.append({
                "DATE": f"2026-{index:03d}", "EVENT_ID": str(index), "PICK": "Player", "TOUR": "ATP",
                "RESULT": "W" if risk_type == 0 else "L", "MODEL_PROBABILITY": ".70",
                "AUTH_PRICE_MOVEMENT": ".09" if risk_type == 1 else ".02",
                "AUTH_MARKET_DISPERSION": ".11" if risk_type == 2 else ".02",
            })
        learned = bot.learned_market_limits(rows, "ATP")
        self.assertIsNotNone(learned)
        self.assertTrue(learned["promoted"])
        self.assertEqual(learned["holdout"], 90)
        self.assertGreaterEqual(learned["holdout_rejected"], 20)
        self.assertLess(learned["policy"]["movement_limit"], bot.MAX_PRICE_MOVEMENT)
        self.assertLess(learned["policy"]["dispersion_limit"], bot.MAX_BOOKMAKER_DISPERSION)
        self.assertLess(learned["challenger_holdout_brier"], learned["active_holdout_brier"])
        self.assertIsNone(bot.learned_market_limits(rows, "WTA"))

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
            transaction_path = root / "bankroll-transactions.csv"
            log_path.write_text(
                "DATE,MATCH,BET,ODDS,STAKE,RESULT,RETURN,STARTING BALANCE\n"
                "2026-08-01,Player One vs Player Two (ATP),Player One to win,2.00,3.00,,,100.00\n",
                encoding="utf-8",
            )
            bankroll_path.write_text("97.00", encoding="utf-8")
            with (
                patch.object(bot, "LOG_FILE", log_path),
                patch.object(bot, "PAPER_LOG_FILE", root / "paper-bets-log.csv"),
                patch.object(bot, "BANKROLL_FILE", bankroll_path),
                patch.object(bot, "TRANSACTION_FILE", transaction_path),
                patch.object(bot, "SETTLEMENT_ALERT_FILE", root / "settlement-alerts.md"),
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

    def test_paper_bet_log_is_isolated_from_real_bankroll_and_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_log, paper_log = root / "bets-log.csv", root / "paper-bets-log.csv"
            bankroll, ledger = root / "bankroll.txt", root / "bankroll-transactions.csv"
            bankroll.write_text("100.00", encoding="utf-8")
            with (
                patch.object(bot, "LOG_FILE", real_log),
                patch.object(bot, "PAPER_LOG_FILE", paper_log),
                patch.object(bot, "BANKROLL_FILE", bankroll),
                patch.object(bot, "TRANSACTION_FILE", ledger),
            ):
                stake = bot.log_bets(
                    "2026-08-01",
                    [{"player": "A", "grade": "Value Pick", "odds": 1.6, "assessed_probability": .7}],
                    [{"player1": "A", "player2": "B", "tournament": "ATP"}],
                    100.0,
                    paper_trading=True,
                )

            self.assertEqual(stake, 2.0)
            self.assertTrue(paper_log.exists())
            self.assertFalse(real_log.exists())
            self.assertFalse(ledger.exists())
            self.assertEqual(bankroll.read_text(encoding="utf-8"), "100.00")

    def test_staged_paper_candidate_persists_mode_for_revalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            pending = Path(directory) / "pending.csv"
            recommendation = {"player": "A", "grade": "Top Pick", "odds": 1.55,
                              "assessed_probability": .72, "ev": .116,
                              "match": {"player1": "A", "player2": "B", "tournament": "ATP"}}
            with patch.object(bot, "PENDING_FILE", pending), patch.object(bot, "PAPER_TRADING_MODE", True):
                bot.stage_pending_bets("2026-08-01", [recommendation], 1.5, 1.6)
            _, rows = bot.read_csv_rows(pending)
            self.assertEqual(rows[0]["MODE"], "paper")

    def test_paper_settlement_records_result_without_crediting_real_bankroll(self):
        event = {"id": 7, "date": "2026-08-01T12:00:00Z", "status": "settled",
                 "home": "A", "away": "B", "scores": {"home": 2, "away": 0}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper_log, bankroll = root / "paper-bets-log.csv", root / "bankroll.txt"
            paper_log.write_text(
                "DATE,MATCH,BET,ODDS,STAKE,RESULT,RETURN,STARTING BALANCE\n"
                "2026-08-01,A vs B (ATP),A to win,2.00,3.00,,,100.00\n", encoding="utf-8"
            )
            bankroll.write_text("100.00", encoding="utf-8")
            with (
                patch.object(bot, "LOG_FILE", root / "bets-log.csv"),
                patch.object(bot, "PAPER_LOG_FILE", paper_log),
                patch.object(bot, "BANKROLL_FILE", bankroll),
                patch.object(bot, "TRANSACTION_FILE", root / "bankroll-transactions.csv"),
                patch.object(bot, "POLICY_FILE", root / "policy.csv"),
                patch.object(bot, "SETTLEMENT_ALERT_FILE", root / "settlement-alerts.md"),
                patch.object(bot, "fetch_odds_json", side_effect=[([event], 0), ([], 0)]),
                patch.object(bot, "update_audit_result"),
            ):
                settled = bot.settle_pending_bets(["key"])
            _, rows = bot.read_csv_rows(paper_log)
            self.assertEqual(settled, 1)
            self.assertEqual((rows[0]["RESULT"], rows[0]["RETURN"]), ("W", "6.00"))
            self.assertEqual(bankroll.read_text(encoding="utf-8"), "100.00")
            self.assertFalse((root / "bankroll-transactions.csv").exists())

    def test_paper_only_settlement_does_not_touch_live_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_log = root / "bets-log.csv"
            real_log.write_text("DATE,MATCH,BET,ODDS,STAKE,RESULT,RETURN,STARTING BALANCE\n2026-08-01,A vs B,A to win,2,3,,,100\n", encoding="utf-8")
            original = real_log.read_bytes()
            with (
                patch.object(bot, "LOG_FILE", real_log),
                patch.object(bot, "PAPER_LOG_FILE", root / "paper.csv"),
                patch.object(bot, "POLICY_FILE", root / "policy.csv"),
                patch.object(bot, "BANKROLL_FILE", root / "bankroll.txt"),
                patch.object(bot, "SETTLEMENT_ALERT_FILE", root / "settlement-alerts.md"),
                patch.object(bot, "fetch_odds_json") as fetch_odds,
            ):
                settled = bot.settle_pending_bets(["key"], include_real=False)
            self.assertEqual(settled, 0)
            self.assertEqual(real_log.read_bytes(), original)
            fetch_odds.assert_not_called()

    def test_overdue_unresolved_outcome_generates_configurable_alert(self):
        from datetime import datetime, timezone
        row = {"DATE": "2026-07-29", "MATCH": "A vs B", "BET": "A to win", "RESULT": ""}
        with tempfile.TemporaryDirectory() as directory:
            alert = Path(directory) / "settlement-alerts.md"
            with patch.object(bot, "SETTLEMENT_ALERT_FILE", alert), patch.dict(
                bot.os.environ, {"TENNIS_UNRESOLVED_HOURS": "24"}
            ):
                count = bot.save_settlement_alerts(
                    [row], [], datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
                )
            report = alert.read_text(encoding="utf-8")
        self.assertEqual(count, 1)
        self.assertIn("OVERDUE UNRESOLVED OUTCOMES", report)
        self.assertIn("Alert threshold: 24 hours", report)

    def test_manual_kill_switch_blocks_live_but_not_paper_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            switch = Path(directory) / "kill-switch.json"
            switch.write_text('{"active": true, "reason": "operator_pause"}', encoding="utf-8")
            recommendations = [{"player": "A"}]
            with patch.object(bot, "MANUAL_KILL_SWITCH_FILE", switch):
                live, reason = bot.apply_manual_kill_switch(recommendations, paper_trading=False)
                paper, paper_reason = bot.apply_manual_kill_switch(recommendations, paper_trading=True)
            self.assertEqual(live, [])
            self.assertEqual(reason, "operator_pause")
            self.assertEqual(paper, recommendations)
            self.assertEqual(paper_reason, "")

    def test_invalid_manual_kill_switch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            switch = Path(directory) / "kill-switch.json"
            switch.write_text('{"active": "yes"}', encoding="utf-8")
            with patch.object(bot, "MANUAL_KILL_SWITCH_FILE", switch):
                state = bot.manual_kill_switch()
            self.assertTrue(state["active"])
            self.assertEqual(state["reason"], "invalid_kill_switch_configuration")

    def test_bankroll_ledger_reconciles_stake_return_and_duplicate_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_path = root / "bets-log.csv"
            bankroll_path = root / "bankroll.txt"
            transaction_path = root / "bankroll-transactions.csv"
            bankroll_path.write_text("100.00", encoding="utf-8")
            with (
                patch.object(bot, "LOG_FILE", log_path),
                patch.object(bot, "BANKROLL_FILE", bankroll_path),
                patch.object(bot, "TRANSACTION_FILE", transaction_path),
            ):
                bot.ensure_bankroll_ledger(100.0)
                stake = bot.log_bets(
                    "2026-08-01",
                    [{"player": "A", "grade": "Value Pick", "odds": 1.6, "assessed_probability": .7}],
                    [{"player1": "A", "player2": "B", "tournament": "ATP"}],
                    100.0,
                )
                after_stake = bot.reconcile_bankroll(100.0)
                headers, bets = bot.read_csv_rows(log_path)
                bets[0].update({"RESULT": "W", "RETURN": f"{stake * 1.6:.2f}"})
                bot.atomic_write_csv(log_path, headers, bets)
                after_return = bot.reconcile_bankroll(after_stake)
                after_duplicate = bot.reconcile_bankroll(after_return)
                _, transactions = bot.read_csv_rows(transaction_path)

            self.assertEqual(after_stake, 98.0)
            self.assertEqual(after_return, 101.2)
            self.assertEqual(after_duplicate, 101.2)
            self.assertEqual([row["TYPE"] for row in transactions], ["opening_balance", "stake", "return"])
            self.assertTrue(bot.validate_transaction_ledger(transactions))

    def test_bankroll_ledger_detects_historical_tampering(self):
        opening = bot.seal_transaction({
            "ID": "one", "TIMESTAMP": "2026-08-01T00:00:00Z", "TYPE": "opening_balance",
            "REFERENCE": "ledger", "AMOUNT": "100.00", "BALANCE": "100.00",
        }, "GENESIS")
        changed = dict(opening)
        changed["BALANCE"] = "1000.00"
        with self.assertRaises(RuntimeError):
            bot.validate_transaction_ledger([changed])

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
        with tempfile.TemporaryDirectory() as directory:
            review_file = Path(directory) / "player-alias-review.csv"
            with (
                patch.object(bot, "fetch", side_effect=[None, None]),
                patch.object(bot, "fetch_reader", side_effect=[row, None]),
                patch.object(bot, "ALIAS_REVIEW_FILE", review_file),
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

    def test_ambiguous_player_identity_is_queued_once_for_manual_review(self):
        profiles = {
            bot.normalize_player_name("Anna Smith"): {"name": "Anna Smith"},
            bot.normalize_player_name("Anne Smith"): {"name": "Anne Smith"},
        }
        with tempfile.TemporaryDirectory() as directory:
            review_file = Path(directory) / "player-alias-review.csv"
            aliases_file = Path(directory) / "player-aliases.csv"
            with (
                patch.object(bot, "ALIAS_REVIEW_FILE", review_file),
                patch.object(bot, "PLAYER_ALIASES_FILE", aliases_file),
            ):
                self.assertIsNone(bot.resolve_profile_key("Ann Smith", profiles, {}))
                self.assertIsNone(bot.resolve_profile_key("Ann Smith", profiles, {}))
            _, rows = bot.read_csv_rows(review_file)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["STATUS"], "pending")
        self.assertEqual(rows[0]["REASON"], "ambiguous_high_confidence")
        self.assertIn("Smith", rows[0]["SUGGESTED_CANONICAL"])

    def test_unresolved_identity_report_is_dedicated_pending_queue(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); review_file = root / "player-alias-review.csv"
            headers = ["PROVIDER_NAME", "NORMALIZED_NAME", "SUGGESTED_CANONICAL", "SUGGESTED_CONFIDENCE",
                       "ALTERNATIVES", "REASON", "STATUS", "REVIEWED_CANONICAL", "CREATED_AT", "UPDATED_AT"]
            bot.atomic_write_csv(review_file, headers, [
                {"PROVIDER_NAME": "Ann Smith", "SUGGESTED_CANONICAL": "Anna Smith", "SUGGESTED_CONFIDENCE": ".880",
                 "ALTERNATIVES": "Anne Smith (0.870)", "REASON": "ambiguous_high_confidence", "STATUS": "pending",
                 "CREATED_AT": "2026-07-28T00:00:00+00:00"},
                {"PROVIDER_NAME": "A. Zverev", "SUGGESTED_CANONICAL": "Alexander Zverev", "STATUS": "approved",
                 "REVIEWED_CANONICAL": "Alexander Zverev", "CREATED_AT": "2026-07-29T00:00:00+00:00"},
            ])
            report_file = root / "unresolved-player-identities.md"
            with (patch.object(bot, "ALIAS_REVIEW_FILE", review_file),
                  patch.object(bot, "IDENTITY_QUEUE_REPORT_FILE", report_file)):
                pending = bot.save_identity_queue_report(datetime(2026, 8, 1, tzinfo=timezone.utc), overdue_hours=72)
            report = report_file.read_text(encoding="utf-8")
        self.assertEqual(pending, 1)
        self.assertIn("## OVERDUE UNRESOLVED IDENTITIES", report)
        self.assertIn("| Ann Smith | Anna Smith | .880 | Anne Smith (0.870)", report)
        self.assertNotIn("| A. Zverev |", report)
        self.assertIn("Approved/applied: 1", report)
        self.assertIn("Resolution procedure", report)

    def test_manually_approved_review_resolves_profile_identity(self):
        profiles = {bot.normalize_player_name("Alexander Zverev"): {"name": "Alexander Zverev"}}
        with tempfile.TemporaryDirectory() as directory:
            review_file = Path(directory) / "player-alias-review.csv"
            aliases_file = Path(directory) / "player-aliases.csv"
            review_file.write_text(
                "PROVIDER_NAME,NORMALIZED_NAME,SUGGESTED_CANONICAL,SUGGESTED_CONFIDENCE,ALTERNATIVES,REASON,STATUS,REVIEWED_CANONICAL,CREATED_AT,UPDATED_AT\n"
                "A. Zverev,azverev,Alexander Zverev,0.900,,low_confidence,approved,Alexander Zverev,2026-08-01,2026-08-01\n",
                encoding="utf-8",
            )
            with (
                patch.object(bot, "ALIAS_REVIEW_FILE", review_file),
                patch.object(bot, "PLAYER_ALIASES_FILE", aliases_file),
            ):
                aliases = bot.load_player_aliases()
                resolved = bot.resolve_profile_key("A. Zverev", profiles, aliases)
        self.assertEqual(resolved, bot.normalize_player_name("Alexander Zverev"))

    def test_manual_alias_confidence_and_provenance_are_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            review_file = Path(directory) / "player-alias-review.csv"
            aliases_file = Path(directory) / "player-aliases.csv"
            aliases_file.write_text(
                "PROVIDER_NAME,CANONICAL_NAME,SOURCE,CONFIDENCE\nProvider One,Canonical One,auto_unique,0.934\n",
                encoding="utf-8",
            )
            review_file.write_text(
                "PROVIDER_NAME,NORMALIZED_NAME,SUGGESTED_CANONICAL,SUGGESTED_CONFIDENCE,ALTERNATIVES,REASON,STATUS,REVIEWED_CANONICAL,CREATED_AT,UPDATED_AT\n"
                "Provider Two,providertwo,Canonical Two,0.800,,low_confidence,approved,Canonical Two,2026-08-01,2026-08-01\n",
                encoding="utf-8",
            )
            with (
                patch.object(bot, "ALIAS_REVIEW_FILE", review_file),
                patch.object(bot, "PLAYER_ALIASES_FILE", aliases_file),
            ):
                metadata = bot.load_player_alias_confidence()
        self.assertEqual(metadata[bot.normalize_player_name("Provider One")], (0.934, "auto_unique"))
        self.assertEqual(metadata[bot.normalize_player_name("Provider Two")], (1.0, "manual_review"))

    def test_profile_resolution_returns_explicit_exact_and_fuzzy_confidence(self):
        profiles = {bot.normalize_player_name("Alexander Zverev"): {"name": "Alexander Zverev"}}
        exact = bot.resolve_profile_identity("Alexander Zverev", profiles, {})
        with patch.object(bot, "save_player_alias"):
            fuzzy = bot.resolve_profile_identity("Alexandr Zverev", profiles, {})
        self.assertEqual(exact, {"key": bot.normalize_player_name("Alexander Zverev"), "confidence": 1.0, "method": "exact"})
        self.assertEqual(fuzzy["method"], "auto_unique")
        self.assertGreaterEqual(fuzzy["confidence"], 0.92)

    def test_identity_audit_values_follow_pick_and_opponent_order(self):
        match = {
            "player1": "Player One", "player2": "Player Two",
            "player1_profile": {"identity_confidence": 1.0, "identity_method": "exact"},
            "player2_profile": {"identity_confidence": 0.95, "identity_method": "auto_unique"},
        }
        values = bot.identity_audit_values(match, "Player Two")
        self.assertEqual(values, (0.95, "auto_unique", 1.0, "exact"))

    def test_every_prediction_audit_row_contains_both_identity_confidences(self):
        match = {
            "event_id": "7", "player1": "Player One", "player2": "Player Two",
            "home_odds": 1.6, "away_odds": 2.5, "bookmaker_count": 3, "surface": "hard", "best_of": 5, "indoor": False, "level": "ATP",
            "player1_profile": {"elo": 1800, "identity_confidence": 1.0, "identity_method": "exact"},
            "player2_profile": {"elo": 1600, "identity_confidence": 0.94, "identity_method": "auto_unique"},
            "player1_ranking_history": {"latest_rank": 12, "latest_date": "2026-07-28", "rank_90d": 20, "improvement_90d": 8, "samples_365d": 9},
            "player2_ranking_history": {"latest_rank": 24, "latest_date": "2026-07-27", "rank_90d": 18, "improvement_90d": -6, "samples_365d": 8},
            "player1_bio": {"handedness": "Right", "nationality": "ESP", "handedness_date": "2026-07-28", "source": "historical_match_records"},
            "player2_bio": {"handedness": "Left", "nationality": "USA", "handedness_date": "2026-07-27", "source": "historical_match_records"},
            "head_to_head": {"player1_probability": 0.58, "player2_probability": 0.42,
                             "sample": 5, "surface_sample": 3, "model_weight": 0.03,
                             "source": "historical_match_records"},
            "player1_clutch": {"tiebreak_win_rate": 0.60, "tiebreak_sample": 10,
                               "deciding_set_win_rate": 0.55, "deciding_set_sample": 8,
                               "source": "historical_match_records"},
            "player2_clutch": {"tiebreak_win_rate": 0.40, "tiebreak_sample": 10,
                               "deciding_set_win_rate": 0.45, "deciding_set_sample": 8,
                               "source": "historical_match_records"},
            "player1_best_of_five": {"match_win_rate": 0.60, "match_sample": 10, "set_win_rate": 0.55,
                                     "set_sample": 40, "five_set_win_rate": 0.58, "five_set_sample": 5,
                                     "comeback_0_2_rate": 0.40, "comeback_0_2_sample": 2, "source": "historical_match_records"},
            "player2_best_of_five": {"match_win_rate": 0.40, "match_sample": 8, "set_win_rate": 0.45,
                                     "set_sample": 32, "five_set_win_rate": 0.42, "five_set_sample": 4,
                                     "comeback_0_2_rate": 0.30, "comeback_0_2_sample": 2, "source": "historical_match_records"},
            "player1_physical_status": {"status": "cleared", "detail": "Available", "expires_date": "2026-08-02", "source": "official"},
            "player2_physical_status": {"status": "injured", "detail": "Official withdrawal", "expires_date": "2026-08-10", "source": "https://www.wtatennis.com/news"},
            "player1_workload": {"rest_days": 2, "matches_7": 2, "matches_14": 3, "matches_30": 5, "sets_7": 5, "penalty": 0},
            "player2_workload": {"rest_days": 1, "matches_7": 3, "matches_14": 4, "matches_30": 7, "sets_7": 8,
                                 "last_match_minutes": 185, "minutes_7": 410, "minutes_14": 610, "minutes_30": 920,
                                 "duration_sample_30": 6, "duration_source": "verified-history.csv",
                                 "last_match_long": True, "last_match_long_threshold": 180, "long_matches_7": 1,
                                 "long_matches_30": 2, "latest_long_match_minutes": 185,
                                 "latest_long_match_date": "2026-07-31", "latest_long_match_days_ago": 1,
                                 "latest_long_match_source": "verified-history.csv", "tournament_change": True,
                                 "previous_tournament": "WTA Clay Event", "previous_tournament_surface": "clay",
                                 "previous_tournament_days_ago": 4, "current_surface": "hard", "surface_change": True,
                                 "surface_transition_source": "verified-history.csv", "travel_distance_km": 1263.42,
                                 "timezone_change_hours": -1, "travel_source": "verified-history.csv;official-event",
                                 "penalty": 0.015},
        }
        with tempfile.TemporaryDirectory() as directory:
            audit_file = Path(directory) / "prediction-audit.csv"
            with (
                patch.object(bot, "AUDIT_FILE", audit_file),
                patch.object(bot, "BACKUPS_DIR", Path(directory) / "backups"),
                patch.object(bot, "PREDICTION_SNAPSHOTS_DIR", Path(directory) / "prediction-snapshots"),
            ):
                bot.append_prediction_audit("2026-08-01", [match], [], [])
            _, rows = bot.read_csv_rows(audit_file)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["PICK_IDENTITY_CONFIDENCE"] for row in rows))
        self.assertTrue(all(row["OPPONENT_IDENTITY_CONFIDENCE"] for row in rows))
        second = next(row for row in rows if row["PICK"] == "Player Two")
        self.assertEqual(second["PICK_IDENTITY_METHOD"], "auto_unique")
        self.assertEqual(second["OPPONENT_IDENTITY_METHOD"], "exact")
        self.assertEqual(second["PICK_RANK_AS_OF"], "24")
        self.assertEqual(second["PICK_RANK_IMPROVEMENT_90D"], "-6")
        self.assertEqual(second["OPPONENT_RANK_AS_OF"], "12")
        self.assertEqual(second["PICK_HANDEDNESS"], "Left")
        self.assertEqual(second["PICK_NATIONALITY"], "USA")
        self.assertEqual(second["OPPONENT_HANDEDNESS"], "Right")
        self.assertEqual(second["H2H_PROBABILITY"], "0.420000")
        self.assertEqual(second["H2H_SAMPLE"], "5")
        self.assertEqual(second["H2H_SOURCE"], "historical_match_records")
        self.assertEqual(second["TIEBREAK_WIN_RATE"], "0.400000")
        self.assertEqual(second["DECIDING_SET_WIN_RATE"], "0.450000")
        self.assertEqual(second["CLUTCH_SOURCE"], "historical_match_records")
        self.assertEqual(second["BO5_MATCH_WIN_RATE"], "0.400000")
        self.assertEqual(second["BO5_FIVE_SET_SAMPLE"], "4")
        self.assertEqual(second["BO5_SOURCE"], "historical_match_records")
        self.assertEqual(second["PHYSICAL_STATUS"], "injured")
        self.assertEqual(second["PHYSICAL_BLOCK"], "True")
        self.assertEqual(second["REASON"], "verified_physical_status:injured")
        self.assertEqual(second["MATCHES_30"], "7")
        self.assertEqual(second["LAST_MATCH_MINUTES"], "185")
        self.assertEqual(second["MINUTES_30"], "920")
        self.assertEqual(second["DURATION_SOURCE"], "verified-history.csv")
        self.assertEqual(second["LAST_MATCH_LONG"], "True")
        self.assertEqual(second["LONG_MATCHES_30"], "2")
        self.assertEqual(second["LATEST_LONG_MATCH_MINUTES"], "185")
        self.assertEqual(second["PREVIOUS_TOURNAMENT"], "WTA Clay Event")
        self.assertEqual(second["PREVIOUS_TOURNAMENT_SURFACE"], "clay")
        self.assertEqual(second["CURRENT_SURFACE"], "hard")
        self.assertEqual(second["SURFACE_CHANGE"], "True")
        self.assertEqual(second["SURFACE_TRANSITION_SOURCE"], "verified-history.csv")
        self.assertEqual(second["TRAVEL_DISTANCE_KM"], "1263.420")
        self.assertEqual(second["TIMEZONE_CHANGE_HOURS"], "-1.000")
        self.assertEqual(second["TRAVEL_SOURCE"], "verified-history.csv;official-event")
        self.assertEqual(second["WORKLOAD_POLICY_ID"], "static-v1")
        self.assertEqual(second["WORKLOAD_POLICY_PROMOTED"], "False")
        self.assertEqual(second["CALIBRATION_SEGMENT"], "ATP")
        self.assertEqual(second["CALIBRATION_APPLIED"], "False")
        self.assertEqual(second["FORMAT_MODEL"], "BO5")
        self.assertEqual(second["FORMAT_MODEL_SAMPLE"], "0")
        self.assertEqual(second["FORMAT_MODEL_PROMOTED"], "False")
        self.assertEqual(second["ENVIRONMENT_MODEL"], "Outdoor")
        self.assertEqual(second["ENVIRONMENT_MODEL_SAMPLE"], "0")
        self.assertEqual(second["ENVIRONMENT_MODEL_PROMOTED"], "False")
        self.assertEqual(second["ACTIVE_COMPONENT_MODEL"], "static")
        self.assertTrue(second["SNAPSHOT_PATH"].endswith(".json.gz"))
        self.assertEqual(len(second["SNAPSHOT_SHA256"]), 64)
        self.assertEqual(second["SNAPSHOT_SCHEMA_VERSION"], "1")

    def test_diagnostic_mode_does_not_write_alias_review_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            review_file = Path(directory) / "player-alias-review.csv"
            with patch.object(bot, "ALIAS_REVIEW_FILE", review_file), patch.object(bot, "DIAGNOSTIC_MODE", True):
                bot.queue_alias_review("Unknown Player", [], "no_candidate")
            self.assertFalse(review_file.exists())

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

    def test_ranking_history_is_pre_match_and_tracks_improvement(self):
        history = [
            {"tourney_date": "20260722", "winner_name": "Test Player", "loser_name": "A", "winner_rank": "50"},
            {"tourney_date": "20260622", "winner_name": "B", "loser_name": "Test Player", "loser_rank": "70"},
            {"tourney_date": "20260423", "winner_name": "Test Player", "loser_name": "C", "winner_rank": "100"},
            {"tourney_date": "20260802", "winner_name": "Test Player", "loser_name": "D", "winner_rank": "1"},
        ]
        ranking = bot.calculate_ranking_history(history, "Test Player", "2026-08-01")
        self.assertEqual(ranking["latest_rank"], 50)
        self.assertEqual(ranking["rank_30d"], 70)
        self.assertEqual(ranking["rank_90d"], 100)
        self.assertEqual(ranking["improvement_90d"], 50)
        self.assertEqual(ranking["samples_365d"], 3)
        self.assertNotIn(1, [item["rank"] for item in ranking["recent_snapshots"]])

    def test_ranking_audit_values_follow_evaluated_player(self):
        match = {
            "player1": "One", "player2": "Two",
            "player1_ranking_history": {"latest_rank": 10},
            "player2_ranking_history": {"latest_rank": 20},
        }
        pick, opponent = bot.ranking_audit_values(match, "Two")
        self.assertEqual(pick["latest_rank"], 20)
        self.assertEqual(opponent["latest_rank"], 10)

    def test_player_bio_uses_latest_pre_match_verified_observations(self):
        history = [
            {"tourney_date": "20260720", "winner_name": "Test Player", "loser_name": "A", "winner_hand": "L", "winner_ioc": "ESP", "_source_url": "https://example.test/verified.csv"},
            {"tourney_date": "20260620", "winner_name": "B", "loser_name": "Test Player", "loser_hand": "L", "loser_ioc": "ESP"},
            {"tourney_date": "20260802", "winner_name": "Test Player", "loser_name": "C", "winner_hand": "R", "winner_ioc": "USA"},
        ]
        bio = bot.calculate_player_bio(history, "Test Player", "2026-08-01")
        self.assertEqual(bio["handedness"], "Left")
        self.assertEqual(bio["nationality"], "ESP")
        self.assertEqual(bio["handedness_date"], "2026-07-20")
        self.assertEqual(bio["handedness_consistency"], 1.0)
        self.assertIn("https://example.test/verified.csv", bio["source"])
        self.assertEqual(bio["handedness_source"], "https://example.test/verified.csv")

    def test_player_bio_rejects_unknown_hand_and_invalid_country_code(self):
        history = [{
            "tourney_date": "20260720", "winner_name": "Test Player", "loser_name": "A",
            "winner_hand": "U", "winner_ioc": "Unknown",
        }]
        self.assertIsNone(bot.calculate_player_bio(history, "Test Player", "2026-08-01"))

    def test_verified_player_status_requires_active_official_citation(self):
        header = "PLAYER,STATUS,EFFECTIVE_DATE,EXPIRES_DATE,SOURCE_URL,VERIFIED_AT,DETAIL\n"
        rows = (
            "Active Player,injured,2026-07-30,2026-08-10,https://www.atptour.com/en/news/verified,2026-07-30T12:00:00Z,Official injury report\n"
            "Expired Player,injured,2026-06-01,2026-06-10,https://www.wtatennis.com/news/verified,2026-06-01T12:00:00Z,Old\n"
            "Rumor Player,injured,2026-07-30,2026-08-10,https://rumors.example/news,2026-07-30T12:00:00Z,Unverified\n"
            "Future Player,injured,2026-07-30,2026-08-10,https://www.itftennis.com/news,2026-08-02T12:00:00Z,Future knowledge\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            status_file = Path(directory) / "verified-player-status.csv"
            status_file.write_text(header + rows, encoding="utf-8")
            with patch.object(bot, "PLAYER_STATUS_FILE", status_file):
                statuses = bot.load_verified_player_status("2026-08-01")
        self.assertEqual(set(statuses), {bot.normalize_player_name("Active Player")})
        self.assertEqual(statuses[bot.normalize_player_name("Active Player")]["status"], "injured")

    def test_recent_retirement_flags_only_retiring_player_without_inventing_cause(self):
        history = [
            {"tourney_date": "20260720", "winner_name": "Winner", "loser_name": "Retired Player", "score": "6-4 RET", "_source_url": "verified.csv"},
            {"tourney_date": "20260802", "winner_name": "Winner", "loser_name": "Retired Player", "score": "RET"},
        ]
        status = bot.calculate_recent_retirement(history, "Retired Player", "2026-08-01")
        self.assertEqual(status["status"], "recent_retirement")
        self.assertIn("cause not verified", status["detail"])
        self.assertIsNone(bot.calculate_recent_retirement(history, "Winner", "2026-08-01"))

    def test_head_to_head_is_leakage_safe_surface_weighted_and_symmetric(self):
        history = [
            {"tourney_date": "20260701", "winner_name": "One", "loser_name": "Two", "surface": "Clay", "score": "6-4 6-4", "_source_url": "https://example.test/history.csv"},
            {"tourney_date": "20260101", "winner_name": "One", "loser_name": "Two", "surface": "Clay", "score": "7-6 6-4"},
            {"tourney_date": "20250101", "winner_name": "Two", "loser_name": "One", "surface": "Hard", "score": "6-3 6-3"},
            {"tourney_date": "20240101", "winner_name": "One", "loser_name": "Two", "surface": "Clay", "score": "6-2 6-2"},
            {"tourney_date": "20260715", "winner_name": "Two", "loser_name": "One", "surface": "Clay", "score": "RET"},
            {"tourney_date": "20260802", "winner_name": "Two", "loser_name": "One", "surface": "Clay", "score": "6-0 6-0"},
        ]
        forward = bot.calculate_head_to_head(history, "One", "Two", "clay", "2026-08-01")
        reverse = bot.calculate_head_to_head(history, "Two", "One", "clay", "2026-08-01")
        self.assertEqual(forward["sample"], 4)
        self.assertEqual(forward["surface_sample"], 3)
        self.assertEqual(forward["model_weight"], 0.02)
        self.assertGreater(forward["player1_probability"], 0.5)
        self.assertAlmostEqual(forward["player1_probability"], reverse["player2_probability"])
        self.assertIn("https://example.test/history.csv", forward["source"])

    def test_head_to_head_needs_three_completed_meetings_to_affect_model(self):
        history = [
            {"tourney_date": "20260701", "winner_name": "One", "loser_name": "Two", "surface": "Clay", "score": "6-4 6-4"},
            {"tourney_date": "20260101", "winner_name": "One", "loser_name": "Two", "surface": "Clay", "score": "6-4 6-4"},
        ]
        h2h = bot.calculate_head_to_head(history, "One", "Two", "clay", "2026-08-01")
        self.assertIsNone(h2h["player1_probability"])
        self.assertEqual(h2h["model_weight"], 0.0)

    def test_serve_return_profile_requires_points_and_calculates_rates(self):
        history = []
        for day in range(1, 9):
            history.append({
                "tourney_date": f"202605{day:02d}", "surface": "Clay", "score": "6-4 6-4",
                "winner_name": "Server", "loser_name": f"Opponent {day}",
                "w_ace": "8", "w_df": "3", "w_svpt": "100", "w_1stIn": "62", "w_1stWon": "46", "w_2ndWon": "20", "w_bpSaved": "4", "w_bpFaced": "5",
                "l_ace": "2", "l_df": "4", "l_svpt": "90", "l_1stIn": "55", "l_1stWon": "32", "l_2ndWon": "14", "l_bpSaved": "3", "l_bpFaced": "7", "l_SvGms": "10",
            })

        profile = bot.calculate_serve_return_profile(history, "Server", "clay", "2026-06-01")

        self.assertEqual(profile["sample"], 8)
        self.assertAlmostEqual(profile["service_points_won"], 0.66)
        self.assertGreater(profile["return_points_won"], 0.45)
        self.assertGreater(profile["hold_probability"], 0.7)
        self.assertAlmostEqual(profile["break_points_converted"], 4 / 7)
        self.assertAlmostEqual(profile["break_rate"], 0.4)

    def test_clutch_profile_tracks_tiebreaks_and_deciding_sets_without_leakage(self):
        history = []
        for day in range(1, 5):
            history.append({
                "tourney_date": f"202605{day:02d}", "surface": "Clay", "best_of": "3",
                "winner_name": "Player", "loser_name": f"Opponent W{day}", "score": "7-6(5) 4-6 6-4",
            })
        for day in range(5, 9):
            history.append({
                "tourney_date": f"202605{day:02d}", "surface": "Clay", "best_of": "3",
                "winner_name": f"Opponent L{day}", "loser_name": "Player", "score": "7-6(4) 4-6 6-4",
            })
        history.extend([
            {"tourney_date": "20260509", "surface": "Clay", "best_of": "3", "winner_name": "Player", "loser_name": "Retired", "score": "7-6(3) RET"},
            {"tourney_date": "20260802", "surface": "Clay", "best_of": "3", "winner_name": "Player", "loser_name": "Future", "score": "7-6(3) 4-6 6-4"},
        ])
        profile = bot.calculate_clutch_profile(history, "Player", "clay", "2026-08-01")
        self.assertEqual(profile["match_sample"], 8)
        self.assertEqual(profile["tiebreak_sample"], 8)
        self.assertEqual(profile["deciding_set_sample"], 8)
        self.assertGreater(profile["tiebreak_win_rate"], 0.49)
        self.assertLess(profile["tiebreak_win_rate"], 0.5)
        self.assertAlmostEqual(profile["tiebreak_win_rate"], profile["deciding_set_win_rate"])

    def test_best_of_five_profile_tracks_sets_deciders_and_comebacks_without_leakage(self):
        history = []
        for day in range(1, 5):
            history.append({
                "tourney_date": f"202605{day:02d}", "surface": "Clay", "best_of": "5",
                "winner_name": "Player", "loser_name": f"Won {day}", "score": "4-6 4-6 6-4 6-4 6-3",
            })
        for day in range(5, 9):
            history.append({
                "tourney_date": f"202605{day:02d}", "surface": "Clay", "best_of": "5",
                "winner_name": f"Lost {day}", "loser_name": "Player", "score": "6-4 4-6 6-4 4-6 6-3",
            })
        history.extend([
            {"tourney_date": "20260509", "surface": "Clay", "best_of": "3", "winner_name": "Player", "loser_name": "BO3", "score": "6-4 6-4"},
            {"tourney_date": "20260802", "surface": "Clay", "best_of": "5", "winner_name": "Player", "loser_name": "Future", "score": "6-4 6-4 6-4"},
            {"tourney_date": "20260510", "surface": "Clay", "best_of": "5", "winner_name": "Player", "loser_name": "Retired", "score": "6-4 RET"},
        ])
        profile = bot.calculate_best_of_five_profile(history, "Player", "clay", "2026-08-01")
        self.assertEqual(profile["match_sample"], 8)
        self.assertEqual(profile["set_sample"], 40)
        self.assertEqual(profile["same_surface_sample"], 8)
        self.assertEqual(profile["five_set_sample"], 8)
        self.assertEqual(profile["comeback_0_2_sample"], 4)
        self.assertEqual(profile["comeback_0_2_wins"], 4)
        self.assertGreater(profile["comeback_0_2_rate"], 0.5)

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
        shared_match = {"player1": "A", "player2": "B", "level": "ATP"}
        recommendations = [
            {"player": "A", "grade": "Top Pick", "ev": .20, "score": 9, "match": shared_match},
            {"player": "B", "grade": "Top Pick", "ev": .19, "score": 9, "match": shared_match},
            {"player": "C", "grade": "Top Pick", "ev": .18, "score": 9,
             "match": {"player1": "C", "player2": "D", "level": "ATP"}},
            {"player": "E", "grade": "Top Pick", "ev": .17, "score": 9,
             "match": {"player1": "E", "player2": "F", "level": "ATP"}},
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
        self.assertEqual(market["home_source"], "B")
        self.assertEqual(market["away_source"], "A")
        sourced_match = {"player1": "Home", "player2": "Away", "home_odds_source": "B", "away_odds_source": "A"}
        self.assertEqual(bot.bookmaker_for_pick(sourced_match, "Home"), "B")
        self.assertEqual(bot.bookmaker_for_pick(sourced_match, "Away"), "A")
        self.assertEqual(market["quotes"], [
            {"home": 1.5, "away": 2.6, "bookmaker": "A"},
            {"home": 1.6, "away": 2.4, "bookmaker": "B"},
            {"home": 1.55, "away": 2.5, "bookmaker": "C"},
        ])

    def test_prediction_snapshot_is_content_addressed_and_replay_verifiable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "external-cache.json"
            with (patch.object(bot, "REPO_ROOT", root),
                  patch.object(bot, "PREDICTION_SNAPSHOTS_DIR", root / "prediction-snapshots"),
                  patch.object(bot, "EXTERNAL_CACHE_FILE", cache)):
                bot.cache_external_response("direct", "https://example.test/profile", "raw profile evidence")
                match = {"event_id": "event/7", "player1": "One", "player2": "Two",
                         "source": "https://example.test/profile",
                         "bookmaker_quotes": [{"bookmaker": "A", "home": 1.6, "away": 2.4}],
                         "source_history": [{"tourney_date": "20260701", "winner_name": "One", "loser_name": "Two"}]}
                baseline = {"assessed_probability": .625, "component_weights": "elo=.55;market=.45"}
                training = [{"DATE": "2026-07-01", "PICK": "One", "MODEL_PROBABILITY": ".60", "RESULT": "W"}]
                first = bot.save_prediction_snapshot("2026-08-01", match, "One", baseline, training)
                second = bot.save_prediction_snapshot("2026-08-01", match, "One", baseline, training)
                snapshot_path = root / first["path"]
                verified = bot.verify_prediction_snapshot(snapshot_path)
                blobs = list((root / "prediction-snapshots" / "2026-08-01").glob("*.json.gz"))
            self.assertEqual(first, second)
            self.assertEqual(len(blobs), 2)
            self.assertEqual(verified["sha256"], first["sha256"])
            self.assertEqual(verified["payload"]["match_input"]["bookmaker_quotes"][0]["bookmaker"], "A")
            self.assertEqual(verified["payload"]["cached_source_artifacts"][0]["url"], "https://example.test/profile")
            self.assertEqual(verified["training"]["rows"], training)

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

    def test_head_to_head_probability_influence_is_capped_at_three_percent(self):
        match = {
            "player1": "Player", "player2": "Opponent", "home_odds": 2.0, "away_odds": 2.0,
            "player1_profile": {"elo": 1700}, "player2_profile": {"elo": 1700},
            "head_to_head": {"player1_probability": 0.58, "player2_probability": 0.42,
                             "sample": 8, "surface_sample": 5, "model_weight": 0.03},
        }
        with patch.object(bot, "load_resolved_predictions", return_value=[]):
            baseline = bot.calculate_tennis_baseline(match, "Player")
        self.assertAlmostEqual(baseline["assessed_probability"], 0.5 * 0.97 + 0.58 * 0.03)
        self.assertEqual(baseline["h2h_weight"], 0.03)
        self.assertIn("h2h=0.030", baseline["component_weights"])

    def test_best_of_five_features_activate_only_for_best_of_five_fixture(self):
        profile = {"match_win_rate": 0.60, "match_sample": 12, "set_win_rate": 0.55, "set_sample": 50,
                   "five_set_win_rate": 0.58, "five_set_sample": 6, "comeback_0_2_rate": 0.40,
                   "comeback_0_2_sample": 2, "source": "verified-history"}
        match = {
            "player1": "Player", "player2": "Opponent", "home_odds": 2.0, "away_odds": 2.0, "best_of": 5,
            "player1_profile": {"elo": 1700}, "player2_profile": {"elo": 1700},
            "player1_best_of_five": profile,
        }
        with patch.object(bot, "load_resolved_predictions", return_value=[]):
            bo5 = bot.calculate_tennis_baseline(match, "Player")
            match["best_of"] = 3
            bo3 = bot.calculate_tennis_baseline(match, "Player")
        self.assertEqual(bo5["bo5_match_sample"], 12)
        self.assertEqual(bo5["bo5_match_win_rate"], 0.60)
        self.assertIsNone(bo3["bo5_match_win_rate"])
        self.assertAlmostEqual(bo5["assessed_probability"], bo3["assessed_probability"])

    def test_verified_unavailable_status_blocks_baseline_reliability(self):
        match = {
            "player1": "Player", "player2": "Opponent", "home_odds": 2.0, "away_odds": 2.0,
            "player1_profile": {"elo": 1700}, "player2_profile": {"elo": 1700},
            "player1_physical_status": {"status": "injured", "source": "https://www.atptour.com/news",
                                        "detail": "Official withdrawal", "expires_date": "2026-08-10"},
        }
        with patch.object(bot, "load_resolved_predictions", return_value=[]):
            blocked = bot.calculate_tennis_baseline(match, "Player")
            available = bot.calculate_tennis_baseline(match, "Opponent")
        self.assertTrue(blocked["physical_block"])
        self.assertFalse(bot.tennis_baseline_is_reliable(blocked))
        self.assertFalse(available["physical_block"])
        self.assertTrue(bot.tennis_baseline_is_reliable(available))

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
            {"DATE": "2026-07-01", "OPENING_ODDS": "1.60", "MODEL_PROBABILITY": "0.65", "EV": "0.04", "RESULT": "W", "CLV": "0.02", "TOUR": "ATP", "SURFACE": "clay", "BEST_OF": "3", "INDOOR": "False", "QUALITY_GRADE": "A", "DECISION": "Top Pick"},
            {"DATE": "2026-07-02", "OPENING_ODDS": "1.70", "MODEL_PROBABILITY": "0.62", "EV": "0.03", "RESULT": "L", "CLV": "-0.01", "TOUR": "ATP", "SURFACE": "clay", "BEST_OF": "3", "INDOOR": "False", "QUALITY_GRADE": "B", "DECISION": "Value Pick"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "backtest-summary.md"
            with patch.object(bot, "BACKTEST_FILE", output):
                bot.generate_backtest_summary(rows)
            report = output.read_text(encoding="utf-8")

        self.assertIn("## Odds bands", report)
        self.assertIn("| Log loss | ECE |", report)
        self.assertIn("1.50–1.75 | 2 | 50.0%", report)
        self.assertIn("## Surface", report)
        self.assertIn("## Monthly performance", report)
        self.assertIn("## Walk-forward staking comparison", report)
        self.assertIn("Capped quarter-Kelly", report)
        self.assertIn("## Workload threshold challenger", report)
        self.assertIn("## Tour movement/dispersion limit challengers", report)
        self.assertIn("| ATP | 2 | 0 | 10.0% | 12.0% | N/A | collecting data |", report)
        self.assertIn("requires at least 200", report)
        self.assertIn("## Tour calibration maturity", report)
        self.assertIn("| ATP | 2 | 2 | collecting data |", report)
        self.assertIn("## Match format", report)
        self.assertIn("## Format model maturity", report)
        self.assertIn("| BO3 | 2 | 0 | shadow/collecting |", report)
        self.assertIn("## Environment", report)
        self.assertIn("## Indoor/outdoor model maturity", report)
        self.assertIn("| Outdoor | 2 | 0 | shadow/collecting |", report)

    def test_walk_forward_staking_compares_fixed_and_capped_kelly(self):
        rows = [
            {"DATE": "2026-07-01", "EVENT_ID": "1", "PICK": "A", "OPENING_ODDS": "2.00",
             "MODEL_PROBABILITY": ".70", "RESULT": "W", "DECISION": "Top Pick"},
            {"DATE": "2026-07-01", "EVENT_ID": "2", "PICK": "B", "OPENING_ODDS": "2.00",
             "MODEL_PROBABILITY": ".70", "RESULT": "L", "DECISION": "Top Pick"},
            {"DATE": "2026-07-02", "EVENT_ID": "3", "PICK": "C", "OPENING_ODDS": "2.00",
             "MODEL_PROBABILITY": ".70", "RESULT": "W", "DECISION": "Top Pick"},
        ]

        result = bot.walk_forward_staking_simulation(rows, 100.0)

        self.assertEqual(result["bets"], 3)
        self.assertEqual(result["fixed"]["ending_bankroll"], 101.0)
        self.assertAlmostEqual(result["kelly"]["ending_bankroll"], 103.0)
        self.assertEqual(result["kelly"]["max_drawdown"], 0)

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

    @patch.object(bot.time, "sleep")
    @patch.object(bot.requests, "get")
    def test_odds_api_retries_transient_error_without_rotating_key(self, get, sleep):
        unavailable = unittest.mock.Mock(status_code=503, headers={})
        working = unittest.mock.Mock(status_code=200, headers={})
        working.raise_for_status.return_value = None
        working.json.return_value = [{"id": 7}]
        get.side_effect = [unavailable, working]

        payload, key_index = bot.fetch_odds_json(
            "https://api.odds-api.io/v3/events", {"sport": "tennis"}, ["same-key"], 0
        )

        self.assertEqual(payload, [{"id": 7}])
        self.assertEqual(key_index, 0)
        self.assertEqual([call.kwargs["params"]["apiKey"] for call in get.call_args_list], ["same-key", "same-key"])
        sleep.assert_called_once_with(bot.RETRY_BASE_SECONDS)

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

    @patch.object(bot.time, "sleep")
    @patch.object(bot.requests, "post")
    def test_call_ai_retries_transient_error_with_exponential_delay(self, post, sleep):
        first = unittest.mock.Mock(status_code=503, headers={})
        second = unittest.mock.Mock(status_code=502, headers={})
        working = unittest.mock.Mock(status_code=200, headers={})
        working.raise_for_status.return_value = None
        working.json.return_value = {"choices": [{"message": {"content": "recovered"}}]}
        post.side_effect = [first, second, working]

        result = bot.call_ai("prompt", ["same-key"])

        self.assertEqual(result, "recovered")
        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_args_list, [unittest.mock.call(.5), unittest.mock.call(1.0)])
        self.assertTrue(all(call.kwargs["headers"]["Authorization"] == "Bearer same-key" for call in post.call_args_list))

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
        self.assertIn('const POLICY_URL = RAW_ROOT + "counterfactual-log.csv"', dashboard)
        self.assertIn('id="counterfactual-body"', dashboard)
        self.assertIn("function renderCounterfactualByRule(rows)", dashboard)
        self.assertIn('role === "active"', dashboard)
        self.assertIn('String(row.decision || "").trim().toLowerCase() === "cancelled"', dashboard)
        self.assertIn("Small sample", dashboard)
        self.assertNotIn("localstorage", lowered)
        self.assertNotIn("copy-csv", lowered)
        self.assertNotIn("showresultpicker", lowered)


if __name__ == "__main__":
    unittest.main()
