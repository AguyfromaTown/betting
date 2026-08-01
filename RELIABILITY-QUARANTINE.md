# Reliability Quarantine Policy

The bot separates measurement, recommendation, and enforcement. A bad run, a short outage, or negative ROI alone cannot disable a tour, surface, or provider.

## Evidence gates

- A tour/surface segment becomes eligible for quarantine only after at least 30 settled predictions with closing prices, flat-unit ROI below -5%, and average CLV below -2%.
- A provider becomes eligible only after at least 10 recorded runs and 30 request events, with a failure rate of at least 50% or stale-response rate of at least 25%.
- Current-run circuit breakers remain temporary and independent of persistent quarantine.
- Positive recovery evidence never re-enables a source or segment automatically; it produces an operator recovery review.

## Workflow

1. Daily, revalidation, and settlement runs append aggregate provider evidence to `source-health-history.csv`.
2. Weekly maintenance runs `python tennis-bot/tennis_bot.py --reliability-audit`.
3. `action_required` identifies mature recommendations absent from `reliability-policy.json`.
4. Before changing the policy file, review the underlying rows, provider contract, fallbacks, sample independence, CLV calculation, and possible schema incidents.
5. An approved change is financially consequential: create a new `MODEL_VERSION`, update `MODEL-POLICY-RELEASES.md`, update `PRODUCTION-POLICY.json`, run all tests and audits, and begin a new frozen-policy evidence period.

## Enforcement and recovery

`disabled_sources` contains normalized provider hostnames. The request gate blocks them before any network call. `disabled_segments` contains supported `tour` and `surface` pairs; candidate reliability rejects them even if their single-run data otherwise looks valid. A malformed policy fails closed for external provider requests.

To recover, first remove the operational cause, collect mature shadow or diagnostic evidence, review the audit's `recovery_reviews`, release a new versioned policy, and verify the frozen manifest. Never edit quarantine state merely to make a run produce picks.
