# Weekly Tennis Policy Health

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Counterfactual metrics show what happened to candidates rejected by each rule; they never affect bankroll.

| Rejection rule | Decisions | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| insufficient_bookmakers | 1 | -100.00% | N/A | 0.1875 |
| match_started | 11 | -100.00% | N/A | N/A |
| model_disagreement | 1 | -100.00% | N/A | 0.2083 |
| stale_price | 5 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 2 | 157.50% | 194.41% | 0.3349 |

## Simultaneous threshold challengers

Each challenger evaluated the same candidates in shadow mode and could not place a bet.

| Policy | Decisions | Would authorize | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|---:|
| threshold-conservative-v1 | 14 | 3 | 162.67% | 166.99% | 0.2986 |
| threshold-permissive-v1 | 14 | 6 | 68.00% | 166.99% | 0.2747 |
| threshold-standard-v1 | 14 | 5 | 57.60% | 166.99% | 0.2764 |
