# Tennis Model and Policy Release Notes

This ledger records every explicit production `MODEL_VERSION` found in repository history. It explains changes that can affect probabilities, eligible candidates, authorization, staking, settlement interpretation, or performance comparison. `MODEL-REFERENCE.md` describes the current formulas and `THRESHOLDS.md` describes current maturity gates.

## Current release

### `tennis-2026.08-bookmaker-retirement-rules-v1`

- Released: 2026-08-01
- Implementation commit: `18b954c`
- Status: current production version
- Supersedes: `tennis-2026.08-monthly-policy-report-v1`

Changes:

- Added configurable bookmaker-specific retirement settlement policies.
- Supported `void`, `action_after_first_set`, and `official_result` policy semantics.
- Made malformed or unsupported retirement configuration fail conservatively to void.
- Persisted the applied settlement rule for auditability.

Compatibility and risk:

- Existing open bets must be settled using the explicitly configured bookmaker rule; missing verified evidence remains unresolved or conservatively void according to the implementation.
- This version changed settlement interpretation, not the static probability weights.
- Required evidence: settlement fixtures for standard completion, retirement, walkover, void, and invalid configuration.

## Historical releases

### `tennis-2026.08-monthly-policy-report-v1`

- Released: 2026-08-01
- Implementation commit: `fcc1f75`
- Superseded by: `tennis-2026.08-bookmaker-retirement-rules-v1`

Added monthly counterfactual policy reporting. Promotion recommendations require mature settled, CLV, and Brier evidence and remain advisory; they do not alter live thresholds automatically.

### `tennis-2026.08-threshold-challengers-v1`

- Released: 2026-08-01
- Implementation commit: `41f5fe1`
- Superseded by: `tennis-2026.08-monthly-policy-report-v1`

Added conservative, standard, and permissive threshold policies in parallel shadow evaluation. Shadow decisions cannot authorize bets, stake bankroll, or bypass later hard safety gates.

### `tennis-2026.08-counterfactual-metrics-v1`

- Released: 2026-08-01
- Implementation commit: `97e2012`
- Superseded by: `tennis-2026.08-threshold-challengers-v1`

Added settlement and reporting of hypothetical rejection-rule outcomes so thresholds can be judged using ROI, CLV, and probability evidence rather than pick count.

### `tennis-2026.08-tour-market-limits-v1`

- Released: 2026-08-01
- Implementation commit: `f0b8c88`
- Superseded by: `tennis-2026.08-counterfactual-metrics-v1`

Added chronological tour-specific movement and bookmaker-dispersion challengers. Learned policies require training/holdout maturity and at least 3% Brier improvement, and can only tighten the static limits.

### `tennis-2026.08-price-freshness-v1`

- Released: 2026-08-01
- Implementation commit: `a198a9d`
- Superseded by: `tennis-2026.08-tour-market-limits-v1`

Added authorization-time rejection of odds older than 15 minutes and prohibited event start time from being substituted for a quote timestamp.

### `tennis-2026.08-environment-models-v1`

- Released: 2026-08-01
- Implementation commit: `4c93af9`
- Superseded by: `tennis-2026.08-price-freshness-v1`

Separated learned component-weight challengers for verified indoor and outdoor matches. Unknown environment remains on the applicable static/other eligible model path.

### `tennis-2026.08-format-models-v1`

- Released: 2026-08-01
- Implementation commit: `b5a38a4`
- Superseded by: `tennis-2026.08-environment-models-v1`

Separated learned component-weight challengers for best-of-three and best-of-five matches. Each format must independently meet chronological sample and holdout gates.

### `tennis-2026.08-tour-calibration-v1`

- Released: 2026-08-01
- Implementation commit: `a3efe1f`
- Superseded by: `tennis-2026.08-format-models-v1`

Isolated empirical probability calibration by ATP, WTA, Challenger, and ITF tour. Unknown tours no longer borrow calibration evidence from unrelated competition levels.

### `tennis-2026.08-workload-v1`

- Released: 2026-08-01
- Implementation commit: `4d5708c`
- Superseded by: `tennis-2026.08-tour-calibration-v1`

Added a chronological workload-policy challenger over recent matches, sets, rest, and tournament change. Promotion requires mature triggered training and holdout samples plus at least 3% Brier improvement in both.

### `tennis-2026.08-quality-v2`

- Released: 2026-08-01
- Implementation commit: `9166792`
- Superseded by: `tennis-2026.08-workload-v1`

Established the explicit versioned policy ledger alongside counterfactual evaluation. The production system at this point already used deterministic Elo/market authority, data-quality controls, staged revalidation, and guarded learning from earlier commits.

## Release classification

A new model/policy release is mandatory when any of these change:

- probability formula, component availability, weight, prior, shrinkage, calibration, cap, or penalty;
- evidence interpretation, identity behavior, surface/tour/format/environment classification used by the model;
- EV, uncertainty, score, pick-grade, price, market-quality, physical-status, or data-quality gate;
- portfolio exposure, correlation, daily/tour/tournament limit, Kelly factor, minimum stake, or grade cap;
- challenger training population, sample threshold, split, metric, promotion condition, selection, suspension, kill switch, or rollback behavior;
- authorization/revalidation timing or semantics;
- win/loss/void/retirement/walkover/result matching, closing-price, CLV, or bankroll transaction interpretation.

Documentation, dashboards, notifications, CI, refactoring, provider retries, or performance optimizations do not require a new model version when observable decision semantics are unchanged, but they still belong in `CHANGELOG.md`.

## Version format

Use `tennis-YYYY.MM-<short-change-name>-vN`:

- `YYYY.MM` is the intended release month;
- `<short-change-name>` describes the behavior, not a ticket number;
- `vN` increments when the same named release needs a corrected contract.

Versions are immutable after producing predictions. Never reuse an old identifier for different behavior.

## Required release entry template

```markdown
### `tennis-YYYY.MM-change-v1`

- Released: YYYY-MM-DD
- Implementation commit: `<commit>`
- Status: shadow | paper | current production | rolled back | superseded
- Supersedes: `<previous MODEL_VERSION>`

Changes:
- Exact formulas, weights, thresholds, fields, or semantics changed.

Evidence:
- Training/holdout population and date boundary.
- Brier, log loss, calibration error, CLV, ROI, coverage, and counterfactual comparison as applicable.
- Edge-case and lifecycle tests.

Risk and compatibility:
- State/schema impact, migration/backup, open-bet settlement behavior, rollback trigger, and rollback commit.
```

## Release procedure

1. Create a new immutable `MODEL_VERSION` before generating predictions with changed behavior.
2. Add an `Unreleased` changelog entry and a complete release-note entry in the same change.
3. Update `MODEL-REFERENCE.md`, `THRESHOLDS.md`, `how i bet.txt`, provider/architecture documents, and dashboard contracts where applicable.
4. Include below-, exact-, and above-threshold tests plus malformed, duplicate, interruption, and rollback cases relevant to the change.
5. Produce chronological out-of-sample and shadow/counterfactual evidence. A larger pick count is not promotion evidence.
6. Run the complete test suite, coverage gate, dependency audit, secret scan, diagnostic mode, and paper lifecycle.
7. Record migration backups and open-bet compatibility where persistent state or settlement changes.
8. Promote only after documented maturity/performance gates pass; otherwise retain the release as shadow or rolled back.

Generated daily commits do not constitute model releases. Learned workload/market policy IDs may vary from evidence, but their activation remains governed by the enclosing immutable `MODEL_VERSION` and recorded promotion metrics.
