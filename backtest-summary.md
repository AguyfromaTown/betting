# Tennis Bot Backtest

This report uses the opening odds and model probabilities saved before settlement.
Flat-unit ROI makes segments comparable; fewer than 30 settled bets is a small sample.

## Odds bands

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1.00–1.50 | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 1.50–1.75 | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 1.75–2.00 | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 2.00–2.50 | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 2.50+ | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |

## Expected-value bands

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Negative | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 0%–3% | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 3%–6% | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 6%–10% | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |
| 10%+ | 0 | 0.0% | 0.00% | 0.0000 | 0.0000 | 0.00% | N/A | small sample |

## Tour and level

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|

## Surface

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|

## Match format

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|

## Environment

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|

## Evidence quality

| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |
|---|---:|---:|---:|---:|---:|---:|---:|---|

## Tour calibration maturity

Calibration is isolated by tour and activates only when the local ±5-point probability bucket has at least 100 settled predictions.

| Tour | Settled predictions | Largest 10-point bucket | Status |
|---|---:|---:|---|
| ATP | 0 | 0 | collecting data |
| WTA | 0 | 0 | collecting data |
| Challenger | 0 | 0 | collecting data |
| ITF | 0 | 0 | collecting data |

## Format model maturity

BO3 and BO5 component-weight challengers train and pass holdout gates independently.

| Format | Settled predictions | Holdout | Promotion |
|---|---:|---:|---|
| BO3 | 0 | 0 | shadow/collecting |
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
| ATP | 0 | 0 | 10.0% | 12.0% | N/A | collecting data |
| WTA | 0 | 0 | 10.0% | 12.0% | N/A | collecting data |
| Challenger | 0 | 0 | 10.0% | 12.0% | N/A | collecting data |
| ITF | 0 | 0 | 10.0% | 12.0% | N/A | collecting data |
