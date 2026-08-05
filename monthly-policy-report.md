# Monthly Tennis Policy Report

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Promotion recommendations require at least 30 hypothetical authorizations with closing-price and probability evidence.
Recommendations are advisory and never alter live thresholds automatically.

## 2026-08

### Active rejection rules

| Rule | Rejections | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| insufficient_bookmakers | 2 | -100.00% | N/A | 0.2087 |
| match_started | 12 | -100.00% | N/A | N/A |
| model_disagreement | 1 | -100.00% | N/A | 0.2083 |
| stale_price | 5 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 2 | 157.50% | 194.41% | 0.3349 |

### Threshold challengers

| Policy | Thresholds | Evaluated | Would authorize | ROI | Avg CLV | Brier | Recommendation |
|---|---|---:|---:|---:|---:|---:|---|
| threshold-conservative-v1 | movement<=0.060;dispersion<=0.080;quality>=7;risk_ev>0.070 | 15 | 3 | 162.67% | 166.99% | 0.2986 | collecting data |
| threshold-permissive-v1 | movement<=0.100;dispersion<=0.120;quality>=4;risk_ev>0.030 | 15 | 6 | 68.00% | 166.99% | 0.2747 | collecting data |
| threshold-standard-v1 | movement<=0.100;dispersion<=0.120;quality>=5;risk_ev>0.050 | 15 | 5 | 57.60% | 166.99% | 0.2764 | collecting data |
