# Weekly Tennis Policy Health

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Counterfactual metrics show what happened to candidates rejected by each rule; they never affect bankroll.

| Rejection rule | Decisions | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| insufficient_bookmakers | 2 | -100.00% | N/A | 0.2087 |
| match_started | 15 | -100.00% | N/A | N/A |
| model_disagreement | 1 | -100.00% | N/A | 0.2083 |
| price_outside_range | 1 | -100.00% | N/A | 0.1760 |
| stale_price | 6 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 4 | 94.25% | 89.55% | 0.3203 |

## Simultaneous threshold challengers

Each challenger evaluated the same candidates in shadow mode and could not place a bet.

| Policy | Decisions | Would authorize | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|---:|
| threshold-conservative-v1 | 20 | 3 | 162.67% | 166.99% | 0.2986 |
| threshold-permissive-v1 | 20 | 7 | 44.00% | 39.76% | 0.2655 |
| threshold-standard-v1 | 20 | 6 | 31.33% | 39.76% | 0.2654 |
