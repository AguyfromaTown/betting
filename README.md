# Tennis Betting Bot

Automated tennis-market research, candidate validation, controlled staking, result settlement, and performance reporting. GitHub Actions runs the production workflows; the local PowerShell entry point supports paper testing without changing the production bankroll.

The bot does not place wagers with a bookmaker. It records authorized selections and maintains the bankroll and audit ledgers used by the operator.

## Quick start

- Dashboard: [`docs/index.html`](docs/index.html)
- Betting rules: [`how i bet.txt`](how%20i%20bet.txt)
- Current roadmap: [`PROJECT-ROADMAP.md`](PROJECT-ROADMAP.md)
- Architecture and data flow: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Emergency procedures: [`EMERGENCY-RUNBOOK.md`](EMERGENCY-RUNBOOK.md)
- Complete folder and file map: [`docs/PROJECT-STRUCTURE.md`](docs/PROJECT-STRUCTURE.md)

### Run tests locally

```powershell
python -m coverage run -m unittest discover -s tennis-bot -p "test_*.py"
python -m coverage report --fail-under=70
```

### Run a safe local paper scan

```powershell
.\run-paper.ps1
```

Production runs require repository secrets and should normally be started from GitHub Actions. Never put API keys or Telegram credentials in source files, command history, screenshots, or reports.

## Project boundaries

- `tennis-bot/` contains the executable application and its tests.
- `.github/workflows/` contains production automation.
- `docs/` contains the dashboard and supporting documentation assets.
- `infotennis-main/infotennis-main/` is third-party scraper source retained at its upstream layout.
- Root CSV, JSON, and generated Markdown files are operational state contracts. Their locations are intentionally stable and must not be reorganized casually.
- `reports/`, `prediction-snapshots/`, and `state-backups/` contain reproducibility and recovery records.

## Change safety

Before publishing a change:

1. Run the complete test and coverage commands above.
2. Confirm no secret or local cache was staged.
3. Review `git diff --cached`.
4. Let the GitHub quality gate pass before manually running a production workflow.

Model, policy, state-schema, and settlement changes also require the corresponding architecture, threshold, provider, changelog, and roadmap documentation to remain synchronized.
