# Monthly Tennis Policy Report

Model version: `tennis-2026.08-bookmaker-retirement-rules-v1`

Promotion recommendations require at least 30 hypothetical authorizations with closing-price and probability evidence.
Recommendations are advisory and never alter live thresholds automatically.

## 2026-08

### Active rejection rules

| Rule | Rejections | Flat-unit ROI | Avg CLV | Brier |
|---|---:|---:|---:|---:|
| insufficient_bookmakers | 1 | -100.00% | N/A | 0.1875 |
| match_started | 7 | -100.00% | N/A | N/A |
| stale_price | 3 | -100.00% | N/A | N/A |
| uncertainty_adjusted_edge_too_low | 1 | 120.00% | N/A | 0.2663 |

### Threshold challengers

| Policy | Thresholds | Evaluated | Would authorize | ROI | Avg CLV | Brier | Recommendation |
|---|---|---:|---:|---:|---:|---:|---|
| threshold-conservative-v1 | movement<=0.060;dispersion<=0.080;quality>=7;risk_ev>0.070 | 8 | 2 | 175.00% | 166.99% | 0.3136 | collecting data |
| threshold-permissive-v1 | movement<=0.100;dispersion<=0.120;quality>=4;risk_ev>0.030 | 8 | 4 | 92.50% | 166.99% | 0.2959 | collecting data |
| threshold-standard-v1 | movement<=0.100;dispersion<=0.120;quality>=5;risk_ev>0.050 | 8 | 3 | 83.33% | 166.99% | 0.3058 | collecting data |
