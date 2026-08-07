# Monthly Tennis Policy Report

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Promotion recommendations require at least 30 hypothetical authorizations with closing-price and probability evidence.
Recommendations are advisory and never alter live thresholds automatically.

## 2026-08

### Active rejection rules

| Rule | Rejections | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| extreme_price_movement | 1 | -100.00% | -84.41% | 0.2315 |
| insufficient_bookmakers | 3 | -6.67% | N/A | 0.2630 |
| match_started | 15 | -100.00% | N/A | N/A |
| model_disagreement | 1 | -100.00% | N/A | 0.2083 |
| price_outside_range | 1 | -100.00% | N/A | 0.1760 |
| stale_price | 6 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 4 | 94.25% | 89.55% | 0.3203 |

### Threshold challengers

| Policy | Thresholds | Evaluated | Would authorize | ROI | Avg CLV | Brier | Recommendation |
|---|---|---:|---:|---:|---:|---:|---|
| threshold-conservative-v1 | movement<=0.060;dispersion<=0.080;quality>=7;risk_ev>0.070 | 22 | 3 | 162.67% | 166.99% | 0.2986 | collecting data |
| threshold-permissive-v1 | movement<=0.100;dispersion<=0.120;quality>=4;risk_ev>0.030 | 22 | 7 | 44.00% | 39.76% | 0.2655 | collecting data |
| threshold-standard-v1 | movement<=0.100;dispersion<=0.120;quality>=5;risk_ev>0.050 | 22 | 6 | 31.33% | 39.76% | 0.2654 | collecting data |
