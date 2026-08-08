# Tennis Bot Backtest

This report uses the opening odds and model probabilities saved before settlement.
Flat-unit ROI makes segments comparable; fewer than 30 settled bets is a small sample.

## Odds bands

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00–1.50 | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 1.50–1.75 | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 1.75–2.00 | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 2.00–2.50 | 2 | 50.0% | 19.00% | 0.2449 | 0.6830 | 2.39% | N/A | small sample |
| 2.50+ | 4 | 50.0% | 31.25% | 0.2513 | 0.6957 | 6.72% | 146.79% | small sample |

## Expected-value bands

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Negative | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 0%–3% | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 3%–6% | 1 | 0.0% | -100.00% | 0.2213 | 0.6356 | 47.04% | N/A | small sample |
| 6%–10% | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 10%+ | 5 | 60.0% | 52.60% | 0.2548 | 0.7027 | 15.74% | 146.79% | small sample |

## Tour and level

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| ATP | 1 | 100.0% | 138.00% | 0.2686 | 0.7303 | 51.83% | N/A | small sample |
| Challenger | 4 | 25.0% | -37.50% | 0.2228 | 0.6384 | 19.51% | 146.79% | small sample |
| WTA | 1 | 100.0% | 175.00% | 0.3352 | 0.8650 | 57.89% | N/A | small sample |

## Surface

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Unknown | 2 | 100.0% | 156.50% | 0.3019 | 0.7977 | 54.86% | N/A | small sample |
| grass | 4 | 25.0% | -37.50% | 0.2228 | 0.6384 | 19.51% | 146.79% | small sample |

## Match format

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 3 | 6 | 50.0% | 27.17% | 0.2492 | 0.6915 | 5.28% | 146.79% | small sample |

## Environment

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Unknown | 6 | 50.0% | 27.17% | 0.2492 | 0.6915 | 5.28% | 146.79% | small sample |

## Evidence quality

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A | 4 | 25.0% | -37.50% | 0.2228 | 0.6384 | 19.51% | 146.79% | small sample |
| B | 2 | 100.0% | 156.50% | 0.3019 | 0.7977 | 54.86% | N/A | small sample |

## Tour calibration maturity

Calibration is isolated by tour and activates only when the local ±5-point probability bucket has at least 100 settled predictions.

| Tour | Settled predictions | Largest 10-point bucket | Status |
|---|---:|---:|---|
| ATP | 1 | 1 | collecting data |
| WTA | 1 | 1 | collecting data |
| Challenger | 4 | 4 | collecting data |
| ITF | 0 | 0 | collecting data |

## Format model maturity

BO3 and BO5 component-weight challengers train and pass holdout gates independently.

| Format | Settled predictions | Holdout | Promotion |
|---|---:|---:|---|
| BO3 | 6 | 0 | shadow/collecting |
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
| 2026-08 | 6 | 50.0% | 27.17% | 0.2492 | 0.6915 | 5.28% | 146.79% | small sample |

## Walk-forward staking comparison

Bets are sized from the bankroll available before that match date; outcomes from the same date cannot affect one another.

| Strategy | Bets | Ending bankroll | Profit | ROI on stakes | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Fixed €1 unit | 0 | €100.00 | €0.00 | N/A | 0.00% |
| Capped quarter-Kelly | 0 | €100.00 | €0.00 | N/A | 0.00% |

## Workload threshold challenger

The workload learner remains inactive: it requires at least 200 chronologically settled prediction rows with usable pre-match workload fields.

## Tour movement/dispersion limit challengers

Limits are learned independently by tour, can only tighten the static safety limits, and require chronological holdout improvement.

| Tour | Sample | Holdout | Movement limit | Dispersion limit | Holdout Brier | Promotion |
|---|---:|---:|---:|---:|---|---|
| ATP | 1 | 0 | 10.0% | 12.0% | N/A | collecting data |
| WTA | 1 | 0 | 10.0% | 12.0% | N/A | collecting data |
| Challenger | 4 | 0 | 10.0% | 12.0% | N/A | collecting data |
| ITF | 0 | 0 | 10.0% | 12.0% | N/A | collecting data |
