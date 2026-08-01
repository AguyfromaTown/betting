# One-Command Local Paper Run

From PowerShell in the project directory, run:

```powershell
.\run-paper.ps1
```

That one command:

1. creates or reuses `.venv`;
2. installs `tennis-bot/requirements-test.txt` inside that environment;
3. runs the complete unit-test suite and the 70% coverage gate;
4. uses an existing `ODDS_API_KEY` through `ODDS_API_KEY_5`, or securely prompts for one temporary key when none is set;
5. launches `tennis_bot.py --paper-trading --bankroll 100 --odds-min 1.5 --odds-max 1.6`.

The prompted key is hidden, is not written to disk, and is removed from the process environment after the run. Existing environment keys are left unchanged. Groq keys are optional because the deterministic Python report is the fallback.

## Common options

```powershell
.\run-paper.ps1 -Date 2026-08-02
.\run-paper.ps1 -OddsMin 1.5 -OddsMax 2.0 -VirtualBankroll 250
.\run-paper.ps1 -Date 2026-08-02 -Force
```

- `-Date` must be `YYYY-MM-DD`; blank means today.
- `-OddsMin` and `-OddsMax` are decimal odds and minimum cannot exceed maximum.
- `-VirtualBankroll` controls paper stake sizing only.
- `-Force` bypasses the same-date paper staging/log guard, but not duplicate IDs or safety gates. Use it only after reviewing existing paper rows for that date.

## Safety boundary

The launcher always supplies both `--paper-trading` and an explicit virtual `--bankroll`. Paper mode writes its simulated lifecycle to paper state and does not change `bets-log.csv`, `bankroll-transactions.csv`, or `bankroll.txt`. Tests and coverage must pass before the bot starts. The repository manual kill switch does not block paper trading, which allows safe incident verification while live authorization is stopped.

The run still performs real provider requests and consumes Odds API quota. If Groq environment keys exist, it may use Groq quota for the optional report; remove those variables for a deterministic-only local paper run.

If PowerShell blocks local scripts under your machine policy, use a process-scoped policy for this invocation rather than changing the machine policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-paper.ps1
```

Review `paper-bets-log.csv`, `pending-bets.csv` rows marked paper, the generated report, source-health output, and `run-state.json` after completion. Do not copy local secret values into commits or support logs.
