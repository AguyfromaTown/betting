# Tennis Bot Maintenance and Provider Review Schedule

This schedule turns operational review into a recurring process. The GitHub workflow `.github/workflows/maintenance-review.yml` runs a read-only weekly health review every Monday at 07:00 UTC and a monthly provider review on the first day of each month at 08:00 UTC. Both can also be started manually.

The scheduled workflow has `contents: read`, receives no API or notification secrets, never authorizes or settles bets, and never commits generated files. Its artifacts preserve review inputs for 90 days weekly and 365 days monthly.

## Roles

One operator may perform routine checks, but any live-policy, provider-authority, financial repair, settlement-rule, or emergency-reopen decision requires a second reviewer. Record the reviewer, date, workflow URL, findings, actions, and follow-up due date in the project's private operational record without credentials.

## Every workflow run

The daily, revalidation, and settlement run owner reviews failures and warnings before treating the run as healthy:

- test and coverage result;
- explicit fixture status rather than assuming zero matches;
- API quota/key rotation and provider schema alerts;
- source latency, circuit, cache, and stale-response warnings;
- staged, authorized, cancelled, and settled counts;
- unresolved outcomes and player identities;
- manual/automatic kill-switch, rollback, and segment suspension state;
- unexpected bankroll or ledger-integrity errors;
- notification failure only as an operational issue, never as evidence that core state failed.

Escalate immediately under `EMERGENCY-RUNBOOK.md` for ambiguous player sides, result semantics, transaction-integrity failure, secret exposure, incorrect live authorization, or provider schema changes affecting identity, price, status, or settlement.

## Weekly review — Monday 07:00 UTC

The automated job runs all tests, enforces 70% coverage, and rebuilds analytics from committed ledgers without provider or AI calls. The operator reviews its summary and artifact:

1. Confirm the workflow succeeded and no test was skipped unexpectedly.
2. Review `performance-summary.md` and `weekly-policy-health.md` by tour, surface, odds band, grade, source, evidence quality, and model version.
3. Review Brier score, log loss, calibration error, CLV sample coverage, flat ROI, and staking simulation. Do not optimize from ROI alone.
4. Inspect every active rejection rule and shadow policy in counterfactual/monthly reporting; missing outcomes or closing prices remain missing, not zero.
5. Confirm `settlement-alerts.md` has no unexplained overdue outcome.
6. Review `operations-alerts.md` for abnormal candidates, authorizations, rejections, or zero-pick days.
7. Review `unresolved-player-identities.md`; investigate pending identities before 72 hours.
8. Confirm manual stop, automatic kill switch, rollback, and suspended segments reflect known evidence.
9. Compare `bankroll.txt`, `bets-log.csv`, and the last hash-linked transaction balance when any financial mutation occurred.
10. Assign an owner and deadline for every unresolved warning.

The workflow runs `python tennis-bot/tennis_bot.py --state-audit` and retains `financial-state-audit.json`. Exact reconciliation requires a valid hash chain and running balances, one exact stake transaction per bet, one exact return/refund per settled bet, no return for an unsettled bet, no orphan or duplicate transaction, and equality between the terminal ledger balance and `bankroll.txt`. Legacy zero-value migration markers do not count as exact reconciliation.

Weekly artifacts are evidence, not authorization to change thresholds. Any proposed change remains shadow-only and follows `MODEL-POLICY-RELEASES.md`.

The workflow also runs `--counterfactual-audit`. Every active cancellation rule remains `collecting_data` until it has at least 30 settled outcomes, 30 closing-price observations, and 30 Brier observations. The audit separately identifies the tunable bookmaker-dispersion, data-quality, price-movement, and uncertainty-adjusted-EV thresholds. Hard safety rules are never relaxed automatically even after their performance sample matures.

`--paper-readiness` verifies that paper evidence is attributable to one immutable current `MODEL_VERSION` for at least 90 calendar days, includes at least 100 settled closing-line observations with positive mean CLV, and has at least 30 probability outcomes in every supported ATP/WTA/Challenger/ITF and hard/clay/grass segment. Segment readiness requires Brier score at most 0.25 and expected calibration error at most 0.10. These are minimum review gates, not proof of future profitability.

`--verify-policy-freeze` verifies the active model version, static financial-risk constants, and SHA-256 hashes of every governing policy artifact against `PRODUCTION-POLICY.json`. Any mismatch blocks production sign-off until it is released through the documented versioning process.

`--reliability-audit` reviews persistent provider history and every supported tour/surface segment. Follow `RELIABILITY-QUARANTINE.md`; never activate or remove a quarantine from a single run, ROI alone, or in order to increase pick count.

## Monthly provider review — first day 08:00 UTC

The monthly job packages the committed provider contract and health inputs without making external calls. The reviewer then evaluates each production source:

1. Confirm endpoint, authentication, request, pagination/batch, and response contracts still match `PROVIDERS.md`.
2. Review failure rate, p95/max latency, stale-cache use, circuit openings, and schema alerts across the month's workflow artifacts.
3. Review quota consumption and key rotation by anonymous key label; rotate only through GitHub Secrets and never record values.
4. Compare fixture coverage with the independent confirmation source and investigate systematic tour/date gaps.
5. Confirm bookmaker labels represent independent books and that two-way prices, timestamps, overround, and dispersion remain plausible.
6. Sample player-side orientation, event IDs, start times, tournament/level/surface/format, live/cancelled status, and identity mappings.
7. Sample completed results, closing prices, corrections, retirements, walkovers, and voids against documented semantics.
8. Review Tennis Abstract direct/reader/cache usage and profile match coverage; a rendering proxy remains the same evidence source.
9. Review historical CSV freshness, column coverage, leakage controls, and source provenance.
10. Review pending/rejected aliases and any canonical-name drift.
11. Check provider terms, availability, quota, and replacement risk. Follow `IDENTITY-AND-PROVIDER-OPERATIONS.md` for any cutover.
12. Sign off each provider as healthy, degraded-but-safe, stopped, or replacement-under-review.

Schema or semantic ambiguity is not “degraded-but-safe” for a field used in authorization or settlement; keep live authorization stopped for the affected path.

## Monthly model and policy review

After provider review, inspect `monthly-policy-report.md` and the current entry in `MODEL-POLICY-RELEASES.md`:

- verify the frozen `MODEL_VERSION` still labels all new prediction rows;
- confirm challenger training and holdout populations are chronological and segment-isolated;
- require the maturity gates in `THRESHOLDS.md` and the documented Brier improvement before promotion;
- compare calibration, CLV, ROI, rejection outcomes, and coverage against the champion;
- confirm automatic rollback has not been bypassed or its evidence deleted;
- leave insufficient samples as collecting data;
- add proposed changes to `CHANGELOG.md` under Unreleased.

No scheduled review automatically promotes a model, relaxes a threshold, removes a provider, repairs a ledger, or reopens a kill switch.

## Quarterly recovery exercise

During the first weekly review of January, April, July, and October:

1. Activate the manual stop in a recovery branch or isolated clone—never disrupt production merely for the exercise.
2. Verify tests, coverage, diagnostic mode, and paper mode.
3. Validate a prediction snapshot and referenced training snapshot by hash.
4. Verify a schema-migration backup against its metadata SHA-256 when one exists.
5. Exercise interrupted-run replay and duplicate-safe stake/return behavior using fixtures.
6. Reconcile a copy of the bet log, transaction ledger, and bankroll projection.
7. Walk through provider failure, malformed schema, exhausted keys, unresolved result, and retirement/void scenarios.
8. Record recovery time, gaps, and corrective actions.

The exercise must not mutate production ledgers or consume live authorization.

## Annual security and dependency review

Once per year, and immediately after any exposure:

- rotate all Odds, Groq, notification, and SMTP credentials;
- review GitHub collaborators, branch protections, Actions permissions, environments, and secret access;
- confirm history secret scanning and dependency audit workflows remain enabled and passing;
- review pinned action SHAs against trusted upstream releases before updating;
- inspect tracked files and artifacts for credentials or personal data;
- review provider legal/terms and data-retention obligations;
- verify emergency contacts and second-reviewer availability.

## Evidence retention and missed reviews

- Weekly workflow artifacts: 90 days.
- Monthly provider inputs: 365 days.
- Model/policy releases, changelog, incident closure records, financial ledgers, and prediction audit/snapshots: retain through repository history according to project policy.
- If a scheduled job is missed or fails, manually dispatch **Tennis Maintenance Review** after correcting the cause. Do not mark the period reviewed from an incomplete artifact.
- Two consecutive missed weekly reviews or one missed monthly provider review while live authorization remains enabled requires operator escalation and a manual review before discretionary policy/provider changes.

## Review sign-off template

```text
Period:
Workflow URL:
Reviewer:
Second reviewer (if required):
Model version:
Provider status by source:
Ledger reconciliation status:
Calibration/CLV/counterfactual status:
Open alerts and owners:
Changes proposed (release-note link):
Live authorization status:
Next review due:
```
