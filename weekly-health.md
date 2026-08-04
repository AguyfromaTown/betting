# Weekly Tennis Policy Health

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Counterfactual metrics show what happened to candidates rejected by each rule; they never affect bankroll.

| Rejection rule | Decisions | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| insufficient_bookmakers | 1 | -100.00% | N/A | 0.1875 |
| match_started | 7 | -100.00% | N/A | N/A |
| stale_price | 3 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 1 | 120.00% | N/A | 0.2663 |

## Simultaneous threshold challengers

Each challenger evaluated the same candidates in shadow mode and could not place a bet.

| Policy | Decisions | Would authorize | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|---:|
| threshold-conservative-v1 | 8 | 2 | 175.00% | 166.99% | 0.3136 |
| threshold-permissive-v1 | 8 | 4 | 92.50% | 166.99% | 0.2959 |
| threshold-standard-v1 | 8 | 3 | 83.33% | 166.99% | 0.3058 |
