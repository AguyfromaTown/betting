# Tennis Bot Emergency Stop and Recovery Runbook

This runbook is for incidents affecting live authorization, financial state, data integrity, providers, or automation. `tennis-bot/tennis_bot.py` is the executable authority; `ARCHITECTURE.md` defines state ownership. The bot does not place wagers through a bookmaker API, but it does maintain the decision and bankroll ledgers used by the operator.

## First response

When impact is uncertain, stop new live authorization first and investigate second:

1. In GitHub, edit `kill-switch.json` on `main` so `active` is the JSON boolean `true` and set a short non-secret reason.
2. Commit the change to `main`.
3. In **Actions**, cancel any currently running **Daily Tennis Picks** or **Revalidate Tennis Bets** job that checked out the repository before the stop commit.
4. Do not cancel **Settle Tennis Bets** unless settlement itself is the suspected fault. The manual stop intentionally permits settlement and paper trading.
5. Record the incident start time, affected workflow run URLs, last known good commit, symptoms, and operator actions outside secrets.

Emergency stop file:

```json
{
  "active": true,
  "reason": "incident-YYYY-MM-DD-short-description"
}
```

Malformed `kill-switch.json` fails closed and blocks live authorization. Do not rely on malformation as the normal stop procedure: valid JSON makes intent auditable. A job already past authorization cannot be reversed by changing the file; inspect the committed ledgers to determine what it recorded.

## What the stop does

- Blocks new live candidates before staging at the end of the daily selection pipeline.
- Cancels live candidates during pre-match revalidation with a `manual_kill_switch` reason.
- Does not alter previously authorized bets.
- Does not reverse stake transactions.
- Does not prevent verified settlement, void refunds, ledger reconciliation, reports, or paper trading.
- Does not affect a workflow that already loaded the old file; cancel and rerun that job after the stop commit when immediate containment matters.

## Preserve evidence before recovery

Do not delete, rewrite, or manually reorder any incident-era state. Preserve the relevant Git commit and workflow artifacts, then inspect:

- `run-state.json` for mode, status, phase, attempt, and interruption detail;
- `pending-bets.csv` for staged, authorized, and cancelled lifecycle rows;
- `bets-log.csv` and `paper-bets-log.csv` for recorded bets and outcomes;
- `bankroll-transactions.csv` for the hash-linked financial history;
- `bankroll.txt` for the current balance projection;
- `prediction-audit.csv`, `counterfactual-log.csv`, and `prediction-snapshots/` for decision evidence;
- `model-policy-state.json` and `kill-switch.json` for stop/rollback state;
- `source-health.json`, `source-health.md`, `api-quota.md`, `provider-schema-alerts.md`, `operations-alerts.md`, and `settlement-alerts.md` for operational evidence;
- `state-backups/` for automatic pre-schema-migration backups;
- the failed GitHub Actions log and uploaded coverage artifacts.

Never paste API keys or notification credentials into an incident note, issue, commit, or log.

## Safe diagnostic sequence

Run diagnostics from a clean checkout of the incident commit or current `main`. Provide Odds API secrets only through environment variables.

```powershell
python -m unittest discover -s tennis-bot -p "test_*.py"
python -m coverage run -m unittest discover -s tennis-bot -p "test_*.py"
python -m coverage report --fail-under=70
python tennis-bot/tennis_bot.py --diagnostic --date YYYY-MM-DD --odds-min 1.5 --odds-max 1.6
```

Diagnostic mode may call collection providers but performs no writes, AI calls, staking, or settlement. It reports fixture status, verified and qualified match counts, modelled player count, source request/failure counts, and explicit `would_*` safety flags. Do not use `--force` during diagnosis.

If network access is unsafe or unavailable, run tests and `python tennis-bot/tennis_bot.py --backtest-only`; backtest mode rebuilds analytics from recorded ledgers without provider or AI calls.

## Interrupted workflow recovery

Every mutating execution writes `run-state.json`. An exception marks the active run `interrupted` with its previous phase. A same-date rerun in the same mode detects `running` or `interrupted`, increments `attempt`, records `recovered_from_phase`, and continues through duplicate-safe operations.

Recovery procedure:

1. Keep the manual stop active if the cause is not understood.
2. Confirm no older job in the shared `daily-tennis-picks` concurrency group is still running.
3. Inspect `run-state.json` and the last commit made by the failed workflow.
4. Run the full tests and diagnostic sequence.
5. Rerun only the failed mode using the same date:
   - daily generation: manually dispatch **Daily Tennis Picks** with that date; use paper mode while the stop remains active;
   - revalidation: manually dispatch **Revalidate Tennis Bets**;
   - settlement: manually dispatch **Settle Tennis Bets**.
6. Verify the new workflow commit, `run-state.json` status `complete`, and the applicable lifecycle/settlement summary.

Do not use `--force` merely because a run failed. Normal reruns are duplicate-safe and skip a date already staged or logged. Use `--force` only after confirming the date guard—not a partial financial mutation—is the sole obstruction. It does not bypass duplicate bet keys, ledger transaction IDs, or safety gates.

## Financial ledger recovery

`bankroll-transactions.csv` is the financial authority. `bankroll.txt` is a projection reconciled from it. Transaction rows are hash-linked, and duplicate transaction IDs prevent the same stake or return from being applied twice.

If bankroll values appear wrong:

1. Activate the manual stop.
2. Preserve the current commit and download the relevant CSV files.
3. Run the tests; ledger-integrity failures must be treated as corruption, not ignored.
4. Compare each authorized `bets-log.csv` row with exactly one stake transaction and each settled row with exactly one return/refund transaction.
5. If the ledger is valid but `bankroll.txt` is stale, a normal settlement/revalidation path calls reconciliation and rewrites the projection from the ledger.
6. If the ledger hash chain is invalid, do not edit `bankroll.txt`, delete rows, regenerate hashes, or run live revalidation. Restore the complete affected state set from a verified Git commit or reviewed backup in a separate recovery branch, run tests, and have a second reviewer approve the correction before merging.

Manual bankroll changes must use the supported `--bankroll` override, which records a `manual_adjustment` transaction. Never change only `bankroll.txt`.

For a repository that predates the transaction ledger, `--migrate-legacy-ledger` is a one-time guarded migration. It refuses an existing ledger, invalid or duplicate bets, unexplained starting balances, returns on unresolved bets, or any opening/closing mismatch. A successful migration writes an input/output-hashed manifest under `state-backups/bankroll-transactions/` and must pass `--state-audit`. Never rerun it by deleting an existing ledger.

## State corruption and schema recovery

All normal state writes use a temporary file and atomic replacement, so an interrupted write should preserve the previous complete destination. Before a CSV schema migration, the bot writes an exact timestamped `.bak` plus JSON metadata under `state-backups/<file-stem>/` containing the source name, SHA-256, and old/new headers.

For a corrupt or incompatible state file:

1. Stop live authorization and preserve the corrupt file for analysis.
2. Identify the last valid Git version or migration backup and verify its SHA-256 against its metadata.
3. Restore in a new branch, never directly over `main` without review.
4. Restore related state consistently; for financial incidents this includes the bet log, transaction ledger, and bankroll projection from a mutually consistent point.
5. Run all tests, the coverage gate, backtest mode, and diagnostic mode.
6. Review the diff for lost lifecycle rows before merging.

Prediction snapshots are content-addressed. A filename/payload hash mismatch or referenced training-snapshot mismatch is corruption; do not use that snapshot for replay.

## Provider, quota, and schema incidents

| Symptom | Containment | Recovery evidence |
|---|---|---|
| All Odds API keys exhausted | Keep authorization stopped if prices cannot be refreshed; do not invent odds | `api-quota.md`, source health, successful diagnostic after quota/key recovery |
| Provider HTTP/transient failure | Allow bounded retries/circuit breaker; stale cache is diagnostic context, not permission to bypass freshness gates | Fresh successful request and acceptable quote age |
| Fixture provider schema failure | Keep live authorization stopped for affected path | `provider-schema-alerts.md`, updated parser fixture tests, clean diagnostic |
| Tennis Abstract unavailable | The deterministic model may fall back to available verified components; do not claim missing profile fields | Source-health report and evidence-quality output |
| Groq unavailable or rate-limited | No stop is required by itself; deterministic Python reporting remains available | Successful deterministic run; Groq cannot authorize or stake |
| Player identity unresolved | Leave identity pending; do not add a guessed alias | Reviewed alias record and successful independent match |
| Result unavailable | Leave outcome unresolved and keep settlement workflow running | Verified provider result or explicit bookmaker settlement rule |

Never loosen price age, bookmaker count, dispersion, EV, identity, or schema gates to make an incident run produce picks.

## Automated stops and rollback

The mature-sample drift kill switch blocks unreliable baselines when calibration or CLV deteriorates. Segment suspension blocks only the affected surface/tour segment. Model rollback returns component and workload learning to static behavior. Policy rollback permits only one Top Pick with at most 3% exposure. Exact maturity and activation thresholds are in `THRESHOLDS.md`.

Do not manually clear `model-policy-state.json` to defeat an automatic rollback. Investigate the underlying settled rows, CLV coverage, and model version. Recovery means proving stable out-of-sample behavior; it does not mean deleting the evidence that activated protection.

## Settlement incident procedure

Settlement is intentionally independent of new-bet authorization. If outcomes remain unresolved, leave them blank and use the scheduled or manually dispatched settlement workflow again. The bot alerts after the configured unresolved interval and never infers a result.

If retirement or void handling appears wrong:

1. Activate the manual stop for new live authorization.
2. Preserve the event payload, bookmaker, bet row, and applied `SETTLEMENT_RULE` without credentials.
3. Verify `risk-config.json`; malformed retirement configuration fails conservatively to void.
4. Do not manually credit or debit `bankroll.txt`.
5. Correct the tested settlement rule and repair the complete bet/transaction state through a reviewed recovery commit.

## Reopening live authorization

Live mode may reopen only when all applicable conditions are met:

- root cause is identified and corrected or the failed external dependency is demonstrably healthy;
- all tests and the 70% coverage gate pass;
- diagnostic output has `would_write`, `would_settle`, `would_call_ai`, and `would_stake` all false;
- provider schema alerts and stale-price conditions relevant to the incident are cleared;
- the transaction ledger validates and bankroll reconciles;
- pending candidates and unresolved settlements have been reviewed;
- automatic rollback/segment state has not been erased or bypassed;
- a paper-trading run succeeds when the incident affected selection or authorization;
- the recovery diff has been reviewed and secrets have not entered tracked files.

Then change `kill-switch.json` to valid JSON with `active: false`, commit it to `main`, and manually dispatch the appropriate workflow. Watch its full log and resulting state commit. If the same symptom recurs, reactivate the stop and begin a new incident record.

## Closure record

Record: incident window, affected dates and bets, root cause, stop/reopen commits, workflow URLs, files restored, financial reconciliation result, tests and diagnostic evidence, provider/schema evidence, whether secrets were rotated, and follow-up owner. Never mark an incident closed while any potentially affected financial row or settlement remains unexplained.
