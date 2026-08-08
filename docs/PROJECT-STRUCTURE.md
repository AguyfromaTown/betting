# Project Structure

This map distinguishes source code, configuration, documentation, and persistent operational state. The root may look state-heavy, but those filenames are stable interfaces used by Python, GitHub Actions, the dashboard, recovery tooling, and policy integrity checks.

## Maintained source

| Path | Purpose |
| --- | --- |
| `tennis-bot/tennis_bot.py` | Main application: discovery, modelling, validation, authorization, settlement, reporting, and notifications. |
| `tennis-bot/test_tennis_bot.py` | Unit, integration-style, safety-contract, and documentation-contract tests. |
| `tennis-bot/fixtures/` | Deterministic lifecycle fixtures used by tests. |
| `.github/workflows/` | Daily scans, revalidation, settlement, quality, security, and maintenance automation. |
| `docs/index.html` | GitHub Pages dashboard. |
| `run-paper.ps1` | Local paper-mode entry point. |

## External source

`infotennis-main/infotennis-main/` retains the imported Infotennis package in its upstream directory layout. The bot uses its maintained public-data collector where applicable. Treat this directory as vendored code: keep project-specific orchestration in `tennis-bot/`, and document any local vendor modification.

## Versioned configuration

| File | Contract |
| --- | --- |
| `PRODUCTION-POLICY.json` | Frozen production-policy manifest and integrity hashes. |
| `risk-config.json` | Portfolio and staking constraints. |
| `reliability-policy.json` | Provider reliability and quarantine policy. |
| `kill-switch.json` | Manual production authorization switch. |
| `player-aliases.csv` | Reviewed player identity mappings. |
| `verified-player-status.csv` | Manually verified physical-status evidence. |
| `verified-tournament-locations.csv` | Manually verified tournament location mappings. |

## Persistent operational state

These files remain at the repository root because they are consumed by multiple workflows and the dashboard:

- `bankroll.txt`, `bankroll-transactions.csv`, and `bets-log.csv` form the financial ledger.
- `pending-bets.csv`, `paper-bets-log.csv`, and `counterfactual-log.csv` track staged and non-live decisions.
- `predictions-log.csv` and `prediction-snapshots/` preserve the complete prediction audit.
- `external-cache.json` and source-health files support provider resilience and monitoring.
- Generated summaries and alert Markdown files provide workflow and operator visibility.
- `state-backups/` preserves schema-migration and recovery evidence.

Operational state must be changed by the bot or a documented recovery procedure, not reorganized manually.

## Documentation guide

- Start with `README.md`, `how i bet.txt`, and `ARCHITECTURE.md`.
- Use `MODEL-REFERENCE.md` and `THRESHOLDS.md` for modelling and maturity rules.
- Use `PROVIDERS.md` and `IDENTITY-AND-PROVIDER-OPERATIONS.md` for external-data work.
- Use `NOTIFICATIONS.md`, `MAINTENANCE-SCHEDULE.md`, and `EMERGENCY-RUNBOOK.md` for operations.
- Use `MODEL-POLICY-RELEASES.md`, `CHANGELOG.md`, and `PROJECT-ROADMAP.md` for change history and delivery status.

## Generated local files

Coverage output, Python caches, virtual environments, editor settings, and operating-system metadata are ignored. They can be regenerated and must not be committed. Use `git status --short` before every commit to distinguish local artifacts from versioned operational state.
