# Weekly Tennis Policy Health

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Counterfactual metrics show what happened to candidates rejected by each rule; they never affect bankroll.

| Rejection rule | Decisions | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| extreme_price_movement | 1 | -100.00% | -84.41% | 0.2315 |
| insufficient_bookmakers | 4 | -30.00% | N/A | 0.2395 |
| match_started | 15 | -100.00% | N/A | N/A |
| model_disagreement | 1 | -100.00% | N/A | 0.2083 |
| price_outside_range | 1 | -100.00% | N/A | 0.1760 |
| stale_price | 6 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 5 | 55.40% | 89.55% | 0.2931 |

## Simultaneous threshold challengers

Each challenger evaluated the same candidates in shadow mode and could not place a bet.

| Policy | Decisions | Would authorize | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|---:|
| threshold-conservative-v1 | 26 | 5 | 108.60% | 158.50% | 0.2764 |
| threshold-permissive-v1 | 26 | 10 | 26.30% | 76.50% | 0.2529 |
| threshold-standard-v1 | 26 | 8 | 30.37% | 76.50% | 0.2598 |
