# Weekly Tennis Policy Health

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Counterfactual metrics show what happened to candidates rejected by each rule; they never affect bankroll.

| Rejection rule | Decisions | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| match_started | 2 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 1 | 120.00% | N/A | 0.2663 |

## Simultaneous threshold challengers

Each challenger evaluated the same candidates in shadow mode and could not place a bet.

| Policy | Decisions | Would authorize | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|---:|
| threshold-conservative-v1 | 2 | 1 | 175.00% | 166.99% | 0.3352 |
| threshold-permissive-v1 | 2 | 2 | 147.50% | 166.99% | 0.3007 |
| threshold-standard-v1 | 2 | 1 | 175.00% | 166.99% | 0.3352 |
