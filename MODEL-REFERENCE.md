# Tennis Model Technical Reference

This document records the formulas, weights, caps, and promotion rules implemented by `tennis-bot/tennis_bot.py`. The Python implementation remains authoritative. All probabilities use decimal form (for example, `0.60` means 60%) and all odds are decimal odds.

## Calculation order

For each player side, the bot builds a de-vigged market probability, Elo probability, and—when mature data exists—recent-form and serve/return probabilities. It combines those components, applies a small head-to-head adjustment, calibrates by tour, subtracts context and workload uncertainty, and then calculates EV. Quality, market, physical-status, portfolio, and pre-match revalidation gates act after the probability calculation.

## Market model

- Raw implied probability: `1 / odds`.
- Two-way overround: `1 / player_odds + 1 / opponent_odds`.
- De-vigged market probability: `(1 / consensus_player_odds) / overround`.
- Each side's consensus price is the median valid bookmaker price.
- A quote more than 12% above its side's median is excluded as an isolated outlier before choosing the executable price.
- Bookmaker dispersion: `(maximum_odds - minimum_odds) / median_odds`.
- Total price movement: `latest_odds / first_odds - 1`.
- Price velocity per hour: `(latest_odds / previous_odds - 1) / elapsed_hours`.
- Price acceleration: `(second_velocity - first_velocity) / midpoint_interval_hours`.
- A quote older than 15 minutes is stale.
- Static reliability limits are overround `0.98–1.12`, absolute Elo/market probability gap at most `0.15`, price movement at most `0.10`, and dispersion at most `0.12`.

## Elo model

Surface Elo is used when present; otherwise overall Elo is used. With player rating `Rp` and opponent rating `Ro`:

`P(Elo win) = 1 / (1 + 10^((Ro - Rp) / 400))`

## Recent-form model

The model uses at most 20 completed, pre-decision matches and requires at least 8. Walkovers, retirements, and defaults are excluded.

- Ranked-opponent expectation: `opponent_rank / (player_rank + opponent_rank)`; missing ranks use `0.50`.
- Match residual: actual result (`1` or `0`) minus ranked-opponent expectation.
- Recency weight: `0.5^(age_days / 120)`.
- Same-surface matches receive a `1.35` multiplier.
- Form probability: `clamp(0.50 + weighted_mean(residual), 0.35, 0.65)`.

## Serve and return model

The model uses at most 30 completed matches. It requires at least 8 matches, 400 weighted service points, and 400 weighted return points. Recency uses the same 120-day half-life and `1.35` same-surface multiplier as form.

- Service points won: `(first_serve_points_won + second_serve_points_won) / service_points`.
- Return points won: `(opponent_service_points - opponent_first_won - opponent_second_won) / opponent_service_points`.
- Matchup service-point probability: `(player_service_points_won + (1 - opponent_return_points_won)) / 2`.
- The opponent value is calculated symmetrically.

For service-point probability `p` and `q = 1-p`, hold probability is:

- Win before deuce: `p^4 × (1 + 4q + 10q^2)`.
- Reach deuce: `20p^3q^3`.
- Win from deuce: `p^2 / (1 - 2pq)`.
- Hold: `win_before_deuce + reach_deuce × win_from_deuce`.

The serve/return matchup probability is `clamp(0.50 + 0.90 × (player_hold - opponent_hold), 0.25, 0.75)`.

Aces, double faults, first-serve percentage, first- and second-serve points won, break points saved and converted, and break rate are retained as evidence. They feed the aggregate service/return calculations where applicable; they are not separately double-counted in the static blend.

## Static component weights

The available evidence determines the blend:

| Available components | Elo | Market | Form | Serve/return |
|---|---:|---:|---:|---:|
| Form and serve/return | 0.40 | 0.30 | 0.15 | 0.15 |
| Form only | 0.50 | 0.35 | 0.15 | 0.00 |
| Serve/return only | 0.50 | 0.35 | 0.00 | 0.15 |
| Neither | 0.55 | 0.45 | 0.00 | 0.00 |

## Head-to-head adjustment

Only completed pre-decision meetings are used; walkovers, retirements, and defaults are excluded.

- Recency weight: `0.5^(age_days / 730)`.
- Same-surface multiplier: `1.25`.
- Shrunk H2H probability: `(weighted_wins + 2) / (weighted_matches + 4)`, capped to `0.42–0.58`.
- Model weight: `min(0.03, max(0, (match_count - 2) × 0.01))`.
- Adjustment: `(1 - H2H_weight) × component_probability + H2H_weight × H2H_probability`.

Thus H2H has no weight before three meetings and can never exceed 3% of the blend.

## Supporting clutch and best-of-five evidence

Clutch evidence uses at most 50 matches, a 730-day half-life, and a `1.25` same-surface multiplier. Tiebreak and deciding-set rates use `(weighted_wins + 2) / (weighted_total + 4)`.

Best-of-five evidence uses at most 40 matches, a 1095-day half-life, and a `1.20` same-surface multiplier. Generic neutral shrinkage is `(wins + prior/2) / (total + prior)`: match prior `4`, set-win prior `8`, five-set prior `4`, and comeback prior `4`. These fields support evidence and audit output; the static probability blend does not add a separate clutch or BO5 bonus.

## Calibration, uncertainty, and EV

Calibration is isolated by canonical ATP, WTA, Challenger, or ITF tour; Unknown is not calibrated. Historical rows enter the local bucket when their model probability is within `0.05` of the current probability. Calibration requires 100 rows.

- Empirical probability: historical win rate in the local bucket.
- Calibration strength: `min(0.50, sample / 500)`.
- Calibrated probability: `clamp(raw × (1-strength) + empirical × strength, 0.02, 0.98)`.

Context penalties are ITF `0.020`, qualifying `0.015`, Challenger `0.010`, and main draw `0`. Static workload penalty is `0.025` for at least 4 matches or 10 sets in 7 days; otherwise `0.015` for at least 3 matches or 8 sets; otherwise `0.010` for at most one rest day. Changing tournaments with at most three rest days adds `0.005`; total workload penalty is capped at `0.030`.

`assessed_probability = max(0.02, calibrated_probability - context_penalty - workload_penalty)`

- EV: `assessed_probability × odds - 1`.
- Uncertainty margin: `0.015` when both mature form and serve/return evidence exist; otherwise `0.025`.
- Risk-adjusted EV: `max(0.02, assessed_probability - uncertainty_margin) × odds - 1`.
- Display score: `clamp(6 + max(0, EV) × 30, 0, 10)`.

## Evidence and data-quality grades

Evidence quality awards: both profiles `+2`; verified surface `+2`; surface Elo `+2` or overall Elo `+1`; at least 3 bookmakers `+2` or 2 bookmakers `+1`; overround at most `1.08` `+1`; Elo/market gap at most `0.12` `+1`; mature form `+1`; mature serve/return `+1`.

Authorization data quality awards: at least 3 bookmakers `+3` or 2 bookmakers `+2`; dispersion at most `0.08` `+2` or at most `0.12` `+1`; both profiles `+2`; verified surface `+1`; mature form `+1`; mature serve/return `+1`.

Both systems grade `A` at 9+, `B` at 7+, `C` at 5+, and `D` below 5. Authorization requires score 5+, at least two bookmakers, a fresh price, acceptable movement and dispersion, the requested odds range, unchanged surface, no verified physical block, and a reliable baseline. Revalidation requires risk-adjusted EV greater than `0.05`.

The model labels a candidate Top Pick when score is greater than `8` and EV greater than `0.08`; Value Pick when score is greater than `7` and EV greater than `0.05`; and Moderate when score is greater than `5.5` and EV is positive. Only Top and Value picks can enter the staking portfolio. AI-supplied probability is discarded when it differs from the deterministic baseline by more than `0.005`, and the deterministic probability remains authoritative in all cases.

## Portfolio and staking

- Maximum daily exposure: 8% of bankroll.
- Maximum daily bets: 4.
- Maximum selections per tournament: 2.
- Maximum one side of any match.
- Default tour exposure caps: ATP 8%, WTA 8%, Challenger 5%, ITF 3%, Unknown 3%.
- Planning rates used by the portfolio constraint: Top 3%, Value 2%.

Full Kelly is `(probability × odds - 1) / (odds - 1)`, floored at zero. The bot uses quarter Kelly: `0.25 × full_Kelly`. Final stake rate is `min(grade_cap, max(0.005, quarter_Kelly))`, with Top cap `0.03` and Value cap `0.02`, then rounded to cents. Portfolio authorization reserves the conservative fixed grade caps before final sizing.

## Learned challengers

Learned component weights require 200 chronological rows. The split point is `max(100, floor(70% × sample))`; later rows are holdout. Each component receives inverse-Brier weight `1 / max(training_Brier, 0.01)`, normalized to sum to one. Elo and market are mandatory. A challenger is promoted only when holdout Brier is at most `0.97 ×` active-model holdout Brier. Separate BO3/BO5 and indoor/outdoor challengers are trained; if several qualify, the lowest challenger/active Brier ratio wins. Promoted models never overlap or blend, and rollback disables them.

The workload learner requires 200 rows, training split `max(140, floor(70% × sample))`, and at least 60 holdout rows. Its grid is: match threshold `3/4/5`; set threshold `8/10/12`; dense penalty `0.010/0.015/0.020/0.025`; rest threshold `0/1/2`; rest penalty `0.005/0.010`. Tournament change within three rest days adds `0.005`; total remains capped at `0.030`. Training needs 30 triggered cases and holdout needs 20. Both training and holdout Brier must improve by at least 3%.

The market-limit learner is tour-specific and uses the same 200-row, 70%, 140-training, and 60-holdout maturity structure. It tests movement `0.04/0.06/0.08/0.10` and dispersion `0.04/0.06/0.08/0.10/0.12`. Training needs 60 accepted and 30 rejected; holdout needs 30 accepted and 20 rejected. Training and holdout Brier must both improve by at least 3%. Its grid cannot loosen the static maximums.

## Drift, suspension, and rollback

A surface plus tour/level segment is suspended after at least 30 settled rows only when flat ROI is below `-5%` and average CLV is below `-2%`.

The kill switch compares the preceding 30 rows with the latest 30. It activates if recent model Brier is more than `1.20 ×` previous Brier, or average CLV falls by more than `0.04`. It needs 60 total rows.

Model rollback examines the latest 30 promoted-model rows and disables learned models when active Brier exceeds reconstructed static-baseline Brier by more than 10%. Policy rollback examines the latest 30 authorized settled bets and activates when flat ROI is below `-5%` and average CLV below `-2%`. Policy rollback permits only one Top Pick with at most 3% exposure.

## Performance metrics and versioning

- Brier score: mean `(probability - outcome)^2`.
- Log loss: mean binary cross-entropy, with probabilities bounded by epsilon `1e-15`.
- Expected calibration error: 10 equal-width probability bins, weighted by each bin's absolute mean-probability versus win-rate gap.
- CLV: `opening_odds / closing_odds - 1`.
- Flat return: win `odds - 1`, loss `-1`; flat ROI is mean flat return.

The production model identifier is `tennis-2026.08-bookmaker-retirement-rules-v1`. Financial values are rounded to cents at staking/ledger boundaries; stored diagnostic probabilities and rates retain additional precision. Any formula, threshold, weight, or model-version change must update this reference and its documentation contract test in the same commit.
