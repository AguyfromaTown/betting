# Tennis Betting Bot — Production Roadmap

This is the authoritative implementation checklist for the tennis bot.

Status conventions:

- `[x]` Implemented and covered by the current workflow/tests.
- `[ ]` Not implemented or only partially implemented.
- Update this file in the same commit as the corresponding feature.
- A checked item must not depend on invented or unverified data.

## Data acquisition

- [ ] Use at least two independent fixture sources.
- [x] Collect prices from multiple bookmakers.
- [x] Retain timestamped pre-match price snapshots in `price-history.csv`.
- [x] Detect malformed and isolated bookmaker outlier prices.
- [x] Record discovery, authorization and closing odds when available.
- [x] Validate match date, start time, tournament and surface.
- [x] Record indoor/outdoor metadata when supplied by the provider.
- [x] Detect best-of-three and best-of-five formats conservatively.
- [x] Classify ATP, WTA, Challenger and ITF events.
- [ ] Add persistent external-response caching.
- [x] Rotate Odds and Groq API keys after quota/authentication failures.
- [x] Track provider request latency and failures in `source-health.json`.
- [ ] Track API quota consumption.
- [ ] Add provider schema-change alarms.

## Player identity

- [x] Maintain provider-to-canonical mappings in `player-aliases.csv`.
- [x] Normalize accents, punctuation and reversed names.
- [x] Require unique, high-confidence fuzzy matches before saving aliases.
- [x] Reject unresolved identities through the model/data-quality gates.
- [ ] Add a manual alias-review queue.
- [ ] Store explicit identity confidence in every audit row.

## Player information

- [x] Collect official ranking, overall Elo and surface Elo from Tennis Abstract.
- [x] Record age when present in the Tennis Abstract leaderboard.
- [ ] Collect ranking history.
- [ ] Collect handedness and nationality from dependable sources.
- [x] Track recent results and opponent-adjusted form.
- [x] Calculate surface-specific form.
- [x] Track tournament level.
- [ ] Add carefully weighted head-to-head features.
- [x] Calculate serve and return profiles.
- [x] Calculate expected hold from service-point performance.
- [ ] Add break-rate, tiebreak and deciding-set features.
- [ ] Add dedicated best-of-five historical features.
- [ ] Add verified injury and physical-status data.
- [x] Prevent AI narrative from overriding verified Python calculations.

## Workload and fatigue

- [x] Calculate rest days.
- [x] Count matches over the previous 7 and 14 days.
- [x] Count sets played over the previous 7 days.
- [ ] Count matches over the previous 30 days.
- [ ] Use verified match duration when available.
- [x] Detect consecutive-day and dense schedules through workload rules.
- [ ] Explicitly identify unusually long previous matches.
- [x] Detect recent tournament changes.
- [ ] Detect surface changes between consecutive tournaments.
- [ ] Calculate verified travel distance and timezone changes.
- [x] Apply conservative workload penalties of no more than three probability points.
- [ ] Backtest and learn workload thresholds after adequate samples.

## Statistical model

- [x] Preserve market, Elo, form and serve/return as separate components.
- [x] Calculate an explicit uncertainty margin.
- [x] Require uncertainty-adjusted EV during final authorization.
- [ ] Calibrate ATP, WTA, Challenger and ITF independently after sufficient samples.
- [x] Segment historical evaluation by surface and tour/level.
- [ ] Build separate best-of-three and best-of-five models.
- [ ] Build indoor/outdoor models after sufficient data.
- [x] Use chronological walk-forward training and holdout evaluation.
- [x] Exclude future results from decision-time training.
- [x] Require minimum sample sizes before learned weights activate.
- [x] Keep challengers in shadow mode until holdout improvement is demonstrated.
- [x] Track Brier score, ROI and CLV.
- [ ] Add log loss and expected calibration error to tennis reporting.
- [x] Store immutable model versions with predictions and policy decisions.
- [ ] Store enough source snapshots to reproduce every historical prediction exactly.

## Market model

- [x] De-vig two-way moneyline consensus prices.
- [x] Calculate median bookmaker consensus.
- [x] Reject isolated quotes more than 12% above consensus.
- [x] Measure bookmaker dispersion.
- [x] Measure discovery-to-authorization price movement.
- [ ] Measure price velocity and acceleration across snapshots.
- [ ] Add stale-price detection based on snapshot timestamps.
- [x] Distinguish broad market movement from isolated price errors.
- [x] Require at least two bookmakers at authorization.
- [x] Store opening/authorization/closing prices when available.
- [ ] Learn movement and dispersion limits by tour after adequate samples.

## Decision policy

- [x] Stage candidates without deducting bankroll.
- [x] Revalidate candidates within 90 minutes of match time.
- [x] Cancel started, live, settled or changed-status events.
- [x] Detect withdrawals, walkovers, retirements, postponements and suspensions.
- [x] Cancel surface and opponent mismatches.
- [x] Cancel insufficient bookmaker coverage.
- [x] Cancel excessive price movement and bookmaker dispersion.
- [x] Cancel low data-quality candidates.
- [x] Cancel candidates whose uncertainty-adjusted EV is too low.
- [x] Apply higher uncertainty penalties to ITF, qualifying and Challenger matches.
- [x] Limit authorization to two bets from one tournament.
- [x] Prevent opposite selections in the same match.
- [x] Prevent duplicate bets across reruns.
- [ ] Add separately configurable ATP/WTA/Challenger/ITF exposure caps.
- [x] Enforce global daily bet-count and exposure limits.
- [x] Add an automatic mature-sample emergency kill switch.
- [ ] Add a manual repository-level kill switch.

## Counterfactual evaluation

- [x] Record authorized and cancelled candidates in `counterfactual-log.csv`.
- [x] Settle policy decisions hypothetically without affecting bankroll.
- [x] Measure flat-unit ROI by decision rule.
- [ ] Add counterfactual CLV and Brier score by rejection rule.
- [x] Preserve rule and model versions.
- [x] Require mature samples before learned model promotion.
- [ ] Build multiple challenger threshold policies simultaneously.
- [x] Generate `weekly-health.md` policy reports.
- [ ] Generate monthly policy reports and threshold recommendations.

## Staking and bankroll

- [x] Use capped quarter-Kelly staking.
- [x] Base final stakes on revalidated probability and odds.
- [x] Cap Top Picks at 3% and Value Picks at 2%.
- [x] Enforce daily exposure limits.
- [x] Avoid loss chasing and recovery sequences.
- [x] Treat detected voids as refunds.
- [x] Deduct stakes only after pre-match authorization.
- [x] Prevent duplicate deductions.
- [ ] Introduce an immutable bankroll transaction ledger.
- [ ] Add automatic bankroll reconciliation.
- [ ] Add an explicit paper-trading mode.
- [ ] Add walk-forward simulations comparing fixed and Kelly staking.

## Settlement

- [x] Match settled events by event/date/player identity.
- [x] Handle wins, losses and voids separately.
- [x] Detect common retirement and walkover indicators.
- [ ] Make retirement settlement rules configurable per bookmaker.
- [x] Store closing odds and CLV when available.
- [x] Retry unresolved outcomes on later scheduled runs.
- [ ] Alert when an outcome remains unresolved beyond a configured period.
- [ ] Reconcile every return against an immutable transaction ledger.
- [x] Never infer an outcome when verified scores are unavailable.

## Reliability and recovery

- [x] Make daily generation, revalidation and settlement duplicate-safe.
- [x] Use atomic writes for all state files.
- [x] Use atomic replacement for bankroll, reports, health summaries and other text state.
- [x] Convert CSV state mutations to atomic replacement.
- [x] Use GitHub concurrency groups to avoid overlapping workflows.
- [x] Migrate prediction CSV schemas while preserving legacy rows.
- [ ] Back up state before every schema migration.
- [x] Add explicit interrupted-run recovery.
- [x] Rotate keys only on authentication/quota failures.
- [ ] Add exponential retry delays for transient errors.
- [ ] Add provider-specific circuit breakers.
- [x] Continue with deterministic Python output when Groq is unavailable.
- [x] Keep AI output non-authoritative for probabilities and staking.
- [ ] Add automated model/policy rollback.

## Testing

- [x] Unit-test core probability, EV, staking and policy rules.
- [x] Test malformed and missing API responses.
- [x] Test player identity aliases.
- [x] Test withdrawals, retirements and walkovers.
- [x] Test duplicate logging and staging.
- [x] Test API-key rotation.
- [x] Test bankroll settlement invariants.
- [x] Test walk-forward maturity gates.
- [x] Test workload, dispersion, outlier and correlation controls.
- [x] Test counterfactual recording and emergency-stop logic.
- [ ] Add fixed end-to-end historical integration fixtures.
- [x] Add interrupted-write and recovery tests.
- [ ] Add automated test coverage reporting and a required minimum.
- [x] Run tests before every GitHub workflow mutation.

## Monitoring and alerts

- [ ] Report API quota consumption.
- [ ] Report source latency and stale responses.
- [ ] Report unresolved player identities in a dedicated queue.
- [x] Publish authorization and cancellation reasons in GitHub Actions summaries.
- [ ] Add settlement-failure alerts.
- [x] Monitor CLV and probability calibration deterioration.
- [ ] Alert on abnormal rejection and pick counts.
- [x] Distinguish provider failure, a valid empty schedule and missing odds in reports.
- [ ] Add optional Telegram or email delivery without exposing secrets.

## Dashboard

- [x] Show logged bets and lifecycle candidates.
- [x] Show staged, authorized and cancelled statuses.
- [x] Show odds movement and bookmaker dispersion fields.
- [x] Show workload, rest and contextual penalties.
- [x] Show evidence and data-quality grades.
- [x] Show raw, active and challenger probabilities.
- [x] Compare active and shadow model Brier scores.
- [ ] Display counterfactual results by rejection rule.
- [x] Show performance by odds range.
- [ ] Add complete performance segmentation by tour, surface and level.
- [ ] Display model/policy version and emergency-stop state prominently.
- [ ] Display API and source health.
- [x] Label small historical samples.
- [x] Keep staged candidates visually separate from logged bets.

## Security

- [ ] Rotate every API key previously exposed outside GitHub Secrets.
- [x] Read production credentials from GitHub Secrets/environment variables.
- [x] Avoid printing API-key values in logs.
- [ ] Add automated secret scanning to CI.
- [x] Use limited GitHub workflow permissions.
- [ ] Pin GitHub Actions by immutable commit SHA.
- [x] Escape externally sourced dashboard content.
- [ ] Add automated dependency vulnerability scanning.

## Documentation and operations

- [ ] Add an authoritative architecture document.
- [ ] Document every provider, fallback and expected schema.
- [x] Document the current betting and risk policy in `how i bet.txt`.
- [ ] Document every model formula and weight in a technical reference.
- [ ] Document threshold sample requirements in one configuration reference.
- [ ] Document emergency-stop and recovery procedures.
- [ ] Document alias review and API-provider replacement procedures.
- [ ] Maintain a changelog and model/policy release notes.
- [ ] Provide a one-command local paper run.
- [x] Add a diagnostic no-write/no-stake/no-AI/no-settlement mode.

## Production validation

- [ ] Complete several months of paper trading under the frozen policy.
- [ ] Demonstrate positive closing-line value over a meaningful sample.
- [ ] Confirm calibration across supported tours and surfaces.
- [ ] Reconcile every bankroll transaction.
- [ ] Review counterfactual performance for every active rejection rule.
- [ ] Disable persistently unreliable tours, segments or sources.
- [ ] Freeze a documented production policy release.
- [x] Require champion-versus-challenger evidence before learned-weight promotion.
- [ ] Establish a recurring maintenance and provider-review schedule.

## Definition of production-complete

The project can be treated as production-complete when:

- [ ] All financially consequential paths are tested and recoverable.
- [ ] Bankroll transactions reconcile exactly.
- [ ] Provider failures cannot be mistaken for valid analysis.
- [ ] Model and policy changes are reproducible, versioned and evaluated out of sample.
- [ ] Counterfactual evidence supports every active rejection threshold.
- [ ] Paper-trading results demonstrate acceptable calibration and CLV.
- [ ] Operational, security and recovery documentation is complete.
