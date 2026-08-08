# Tennis Bot Backtest

This report uses the opening odds and model probabilities saved before settlement.
Flat-unit ROI makes segments comparable; fewer than 30 settled bets is a small sample.

## Odds bands

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00–1.50 | 60 | 65.0% | -7.08% | 0.2456 | 0.6852 | 21.49% | N/A | developing |
| 1.50–1.75 | 169 | 62.7% | 0.72% | 0.2548 | 0.7030 | 10.46% | -93.48% | usable |
| 1.75–2.00 | 71 | 46.5% | -13.55% | 0.2479 | 0.6886 | 7.69% | N/A | developing |
| 2.00–2.50 | 147 | 42.2% | -8.37% | 0.2562 | 0.7059 | 11.24% | N/A | usable |
| 2.50+ | 109 | 34.9% | -6.30% | 0.2397 | 0.6727 | 14.03% | 146.79% | usable |

## Expected-value bands

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Negative | 373 | 56.3% | -0.74% | 0.2547 | 0.7030 | 10.08% | -93.48% | usable |
| 0%–3% | 33 | 48.5% | -4.82% | 0.2403 | 0.6745 | 15.19% | N/A | developing |
| 3%–6% | 24 | 37.5% | -23.38% | 0.2196 | 0.6307 | 19.33% | N/A | small sample |
| 6%–10% | 39 | 38.5% | -11.21% | 0.2448 | 0.6825 | 16.83% | N/A | developing |
| 10%+ | 87 | 32.2% | -20.09% | 0.2463 | 0.6859 | 16.38% | 146.79% | developing |

## Tour and level

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| ATP | 72 | 50.0% | -2.51% | 0.2647 | 0.7236 | 12.02% | N/A | developing |
| Challenger | 234 | 50.0% | -7.33% | 0.2446 | 0.6823 | 5.23% | 26.66% | usable |
| ITF | 160 | 50.0% | -6.71% | 0.2537 | 0.7012 | 5.60% | N/A | usable |
| Unknown | 2 | 50.0% | -23.50% | 0.2052 | 0.6032 | 45.30% | N/A | small sample |
| WTA | 88 | 50.0% | -1.89% | 0.2486 | 0.6902 | 5.82% | N/A | developing |

## Surface

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Unknown | 322 | 50.0% | -4.56% | 0.2545 | 0.7026 | 6.64% | N/A | usable |
| grass | 234 | 50.0% | -7.33% | 0.2446 | 0.6823 | 5.23% | 26.66% | usable |

## Match format

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 3 | 556 | 50.0% | -5.72% | 0.2503 | 0.6941 | 5.89% | 26.66% | usable |

## Environment

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Unknown | 556 | 50.0% | -5.72% | 0.2503 | 0.6941 | 5.89% | 26.66% | usable |

## Evidence quality

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A | 146 | 50.0% | -6.43% | 0.2467 | 0.6867 | 6.30% | 26.66% | usable |
| B | 207 | 50.2% | -4.54% | 0.2505 | 0.6945 | 9.15% | N/A | usable |
| C | 175 | 50.3% | -4.35% | 0.2546 | 0.7028 | 5.28% | N/A | usable |
| D | 28 | 46.4% | -19.32% | 0.2408 | 0.6747 | 5.27% | N/A | small sample |

## Tour calibration maturity

Calibration is isolated by tour and activates only when the local ±5-point probability bucket has at least 100 settled predictions.

| Tour | Settled predictions | Largest 10-point bucket | Status |
|---|---:|---:|---|
| ATP | 72 | 30 | collecting data |
| WTA | 88 | 39 | collecting data |
| Challenger | 234 | 101 | locally eligible |
| ITF | 160 | 73 | collecting data |

## Format model maturity

BO3 and BO5 component-weight challengers train and pass holdout gates independently.

| Format | Settled predictions | Holdout | Promotion |
|---|---:|---:|---|
| BO3 | 556 | 167 | shadow/collecting |
| BO5 | 0 | 0 | shadow/collecting |

## Indoor/outdoor model maturity

Indoor and outdoor component-weight challengers train and pass holdout gates independently.

| Environment | Settled predictions | Holdout | Promotion |
|---|---:|---:|---|
| Indoor | 0 | 0 | shadow/collecting |
| Outdoor | 0 | 0 | shadow/collecting |

## Monthly performance

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-08 | 556 | 50.0% | -5.72% | 0.2503 | 0.6941 | 5.89% | 26.66% | usable |

## Walk-forward staking comparison

Bets are sized from the bankroll available before that match date; outcomes from the same date cannot affect one another.

| Strategy | Bets | Ending bankroll | Profit | ROI on stakes | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Fixed €1 unit | 0 | €100.00 | €0.00 | N/A | 0.00% |
| Capped quarter-Kelly | 0 | €100.00 | €0.00 | N/A | 0.00% |

## Workload threshold challenger

- Candidate policy: `m5-s10-d0.010-r0-p0.005`
- Sample: 391 (273 training, 118 holdout)
- Dense schedule: matches/7d >= 5 or sets/7d >= 10; penalty 1.0%
- Short rest: rest days <= 0; penalty 0.5%
- Holdout Brier: active 0.2458, challenger 0.2457
- Promotion: shadow only

## Tour movement/dispersion limit challengers

Limits are learned independently by tour, can only tighten the static safety limits, and require chronological holdout improvement.

| Tour | Sample | Holdout | Movement limit | Dispersion limit | Holdout Brier | Promotion |
|---|---:|---:|---:|---:|---|---|
| ATP | 72 | 0 | 10.0% | 12.0% | N/A | collecting data |
| WTA | 88 | 0 | 10.0% | 12.0% | N/A | collecting data |
| Challenger | 234 | 0 | 10.0% | 12.0% | N/A | collecting data |
| ITF | 160 | 0 | 10.0% | 12.0% | N/A | collecting data |
