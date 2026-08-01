# Tennis Threshold and Sample Configuration Reference

This is the single operational reference for sample-size and maturity requirements implemented by `tennis-bot/tennis_bot.py`. Formula definitions belong in `MODEL-REFERENCE.md`; provider contracts belong in `PROVIDERS.md`. The Python constants and function defaults remain authoritative.

## Reading these thresholds

- A row means a settled, chronologically eligible prediction unless stated otherwise.
- Training always precedes holdout data; future results never enter an earlier decision.
- A minimum permits evaluation, not automatic promotion. Every promotion also has performance gates.
- Segment-specific requirements apply independently. Rows from another tour, format, environment, or surface cannot fill a segment's requirement.
- Missing required fields remove a row from the usable sample; they are not treated as zeros.

## Authoritative named constants

| Code constant | Value | Scope | Effect below threshold |
|---|---:|---|---|
| `MIN_CALIBRATION_SAMPLE` | 100 | Local probability bucket within one canonical tour | Return the uncalibrated probability |
| `MIN_SEGMENT_SAMPLE` | 30 | Exact surface plus tour/level segment | Do not suspend the segment |
| `MIN_WEIGHT_TRAINING_SAMPLE` | 200 | BO3, BO5, indoor, or outdoor component challenger | Keep the static component weights |
| `MIN_WORKLOAD_TRAINING_SAMPLE` | 200 | Workload-policy usable history | Keep the static workload policy |
| `MIN_WORKLOAD_TRIGGER_SAMPLE` | 30 | Workload candidate's triggered training cases | Candidate is ineligible |
| `MIN_MARKET_LIMIT_TRAINING_SAMPLE` | 200 | Usable history within one canonical tour | Keep static market limits |
| `MIN_MARKET_LIMIT_TRIGGER_SAMPLE` | 30 | Market candidate's rejected training cases | Candidate is ineligible |
| `MIN_MONTHLY_POLICY_SAMPLE` | 30 | Settled hypothetical authorizations, CLV observations, and Brier observations | Monthly recommendation remains `collecting data` |

These constants are frozen policy values, not environment variables. Changing one is a model/policy change and requires tests, documentation, a version/release note, and a new shadow-validation period where applicable.

## Player-feature maturity

| Feature | Lookback cap | Minimum usable evidence | Behavior below minimum |
|---|---:|---:|---|
| Recent form | 20 matches | 8 completed matches | Omit the form component |
| Serve/return | 30 matches | 8 completed matches, 400 weighted service points, and 400 weighted return points | Omit the serve/return component |
| Head-to-head | All eligible meetings | 3 meetings before any model weight | Keep H2H weight at zero |
| Head-to-head maximum influence | All eligible meetings | 5 meetings reach the maximum | Cap H2H blend weight at 3% |
| Clutch profile | 50 matches | At least one parsable completed match | Omit unavailable clutch fields |
| Best-of-five profile | 40 BO5 matches | At least one parsable completed BO5 match | Omit unavailable BO5 fields |

Clutch and best-of-five summaries use shrinkage priors rather than a large activation threshold and do not add a separate term to the static probability blend. Recent form and serve/return only count completed pre-decision matches; walkovers, retirements, and defaults are excluded.

## Component-weight challengers

Component learning runs separately for BO3, BO5, indoor, and outdoor segments.

| Requirement | Threshold |
|---|---:|
| Usable segment rows | 200 |
| Chronological training share | 70% |
| Minimum training rows implied by split | 100 |
| Required components | Elo and market |
| Holdout performance | Challenger Brier ≤ 97% of active Brier |

The split is `max(100, floor(0.70 × sample))`; remaining rows are holdout. At the minimum sample of 200, this produces 140 training and 60 holdout rows. No promoted challenger is used while model rollback is active.

## Workload-policy challenger

| Requirement | Threshold |
|---|---:|
| Usable rows | 200 |
| Chronological training split | `max(140, floor(70% × sample))` |
| Holdout rows | 60 |
| Triggered training cases | 30 |
| Triggered holdout cases | 20 |
| Training Brier improvement | At least 3% |
| Holdout Brier improvement | At least 3% |

A usable row must be settled and contain matches in 7 days, sets in 7 days, rest days, model probability, and workload penalty. Both the training and holdout improvement gates must pass. Below any threshold, the static workload rules remain active.

## Tour-specific market-limit challenger

| Requirement | Threshold |
|---|---:|
| Usable rows in the same canonical tour | 200 |
| Chronological training split | `max(140, floor(70% × sample))` |
| Holdout rows | 60 |
| Accepted training cases | 60 |
| Rejected training cases | 30 |
| Accepted holdout cases | 30 |
| Rejected holdout cases | 20 |
| Training Brier improvement | At least 3% |
| Holdout Brier improvement | At least 3% |

Usable rows must be settled and contain finite authorization-time movement, dispersion, and model probability. Unknown-tour rows are ineligible. A learned policy may only tighten, never loosen, the static movement and dispersion limits.

## Calibration maturity

Calibration is isolated by ATP, WTA, Challenger, or ITF. Its local bucket contains settled rows whose historical model probability lies within `±0.05` of the current probability.

| Requirement | Threshold |
|---|---:|
| Rows in local tour/probability bucket | 100 |
| Maximum empirical calibration strength | 50% |
| Sample at which maximum strength is reached | 250 rows |

Strength is `min(0.50, sample / 500)`. Below 100 rows no calibration is applied. Unknown tours are not calibrated.

## Monitoring, suspension, and rollback maturity

| Control | Minimum evidence | Additional activation condition |
|---|---:|---|
| Surface/tour segment suspension | 30 settled segment rows | Flat ROI below -5% and average CLV below -2% |
| Drift kill switch | 30 preceding plus 30 recent rows | Recent Brier exceeds 120% of preceding Brier, or average CLV drops by more than 0.04 |
| Learned-model rollback | Latest 30 promoted-model rows | Active Brier exceeds reconstructed static Brier by more than 10% |
| Betting-policy rollback | Latest 30 authorized settled bets | Flat ROI below -5% and average CLV below -2% |
| Daily-volume anomaly baseline | 7 prior active-policy days | Current count/rate exceeds robust anomaly bounds |
| Rejection-rate anomaly | Mature daily baseline and 5 current candidates | Rate exceeds its robust anomaly bound |
| Zero-authorized alert | Mature daily baseline and 5 current candidates | Zero authorized while historical median is at least 2 |

The drift kill switch requires 60 total ordered rows because it compares two non-overlapping 30-row windows. Missing CLV prevents CLV-based activation; missing valid Brier evidence prevents Brier-based activation. Controls fail according to their explicit rules rather than manufacturing missing measurements.

## Monthly counterfactual policy review

Each challenger policy needs all three of the following within the review population:

- 30 settled hypothetical authorizations;
- 30 closing-price observations for CLV;
- 30 probability observations for Brier score.

Before those samples exist, the recommendation is `collecting data`. Positive challenger ROI and CLV are then required. A `review for promotion` recommendation additionally requires at least 30 active-policy settled observations and challenger ROI above active ROI, challenger CLV at least active CLV, and challenger Brier no worse than active Brier. The report is advisory and never changes live thresholds automatically.

## Decision-time evidence counts

These are eligibility counts rather than training samples, but they are listed here to keep every count-based gate in one place:

| Gate | Requirement |
|---|---:|
| Independent bookmaker confirmation | At least 2 bookmakers |
| Highest bookmaker-quality tier | At least 3 bookmakers |
| Portfolio daily selection count | At most 4 bets |
| Same-tournament selection count | At most 2 bets |
| Match-side selection count | At most 1 side per match |
| Groq narrative input | At most 20 matches |

## Change-control checklist

When any sample or maturity requirement changes:

1. Change the named constant or explicit function threshold in `tennis_bot.py`.
2. Update deterministic unit tests for the below-threshold, exact-threshold, and above-threshold cases.
3. Update this file and `MODEL-REFERENCE.md` if model behavior changes.
4. Change `MODEL_VERSION` for a prediction, promotion, rejection, or staking-policy change.
5. Record the change in release notes and keep it shadow-only until its own maturity gates pass.
6. Run the full test suite, coverage gate, and a no-write diagnostic run before deployment.

Thresholds must not be reduced merely to produce more picks. A reduction needs counterfactual evidence showing adequate calibration, CLV, and out-of-sample performance.
