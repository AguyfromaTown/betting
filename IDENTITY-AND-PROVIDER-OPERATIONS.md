# Player Alias Review and API Provider Replacement

This runbook defines how operators resolve player identities and how maintainers replace an external API without weakening the bot's evidence or safety contracts. `PROVIDERS.md` defines current schemas; `ARCHITECTURE.md` defines component and state boundaries. Code remains authoritative.

## Player identity principles

- An alias maps a provider spelling to an existing, independently verified canonical profile. It never creates a player or profile.
- Exact normalized matches are preferred over every alias or fuzzy match.
- Approved manual aliases are trusted only for the named provider spelling and canonical name.
- Similar spelling alone is not sufficient evidence. Initials, transliteration, diacritics, surname collisions, name order, juniors, and doubles teams require special care.
- Unresolved identity reduces available evidence; it must not be silently replaced with the closest player.
- Identity decisions are tracked in CSV state so they are reviewable and reversible through Git history.

## Resolution order implemented by the bot

1. Exact normalized player name in the Tennis Abstract profile collection: confidence `1.0`, method `exact`.
2. Alias from `player-aliases.csv` or an approved/applied row in `player-alias-review.csv`.
3. Unique automatic fuzzy match with similarity at least `0.92`.
4. When multiple candidates exceed `0.92`, automatic resolution is allowed only if the best candidate leads the second by at least `0.05`.
5. Otherwise the identity is unresolved and enters manual review with reason `ambiguous_high_confidence`, `low_confidence`, or `no_candidate`.

Fuzzy candidates below `0.72` are not retained as suggestions. At most the best three eligible suggestions are placed in the queue. Diagnostic mode does not write aliases or queue rows.

## Alias files and schemas

Permanent and automatically unique aliases use `player-aliases.csv`:

```text
PROVIDER_NAME,CANONICAL_NAME,SOURCE,CONFIDENCE
```

- `PROVIDER_NAME`: spelling received from the fixture/odds provider.
- `CANONICAL_NAME`: exact name shown by the verified target profile.
- `SOURCE`: provenance such as `auto_unique`; use a clear operator provenance for manually curated permanent rows.
- `CONFIDENCE`: decimal from `0.0` to `1.0`. Invalid values load as zero.

Manual review uses `player-alias-review.csv`:

```text
PROVIDER_NAME,NORMALIZED_NAME,SUGGESTED_CANONICAL,SUGGESTED_CONFIDENCE,ALTERNATIVES,REASON,STATUS,REVIEWED_CANONICAL,CREATED_AT,UPDATED_AT
```

The bot creates new rows with `STATUS=pending` and does not create a duplicate queue row for the same normalized provider name. Only `approved` and `applied` statuses enter alias lookup. `rejected` remains audit evidence and is not used. Approved manual aliases load with confidence `1.0` and method `manual_review`.

## Manual alias review procedure

1. Open `unresolved-player-identities.md` and `player-alias-review.csv`. Rows pending for at least 72 hours are flagged overdue.
2. Verify the fixture player using at least the fixture provider plus an authoritative player/profile source. Confirm the tour, full name, and that the candidate is the same person.
3. Check collision risks: identical surname/initial, alternate name order, accented/transliterated spelling, birth year or age, nationality, handedness, current ranking, and tournament participation.
4. Compare every entry in `ALTERNATIVES`; do not review only the first suggestion.
5. For a confirmed match, enter the exact target profile name in `REVIEWED_CANONICAL`, set `STATUS=approved`, and update `UPDATED_AT` with an ISO-8601 UTC timestamp.
6. For a false or unprovable match, leave `REVIEWED_CANONICAL` blank, set `STATUS=rejected`, and update `UPDATED_AT`.
7. Commit the smallest possible CSV change. Never place research notes, URLs containing tokens, or secrets in a CSV cell.
8. Run tests and diagnostic mode. Confirm the audit reports method `manual_review`, confidence `1.0`, and the intended canonical profile for the provider spelling.
9. Review the next real or paper workflow's identity evidence before considering the item closed.

Never overwrite `PROVIDER_NAME`, `NORMALIZED_NAME`, `CREATED_AT`, suggestions, or reason on an existing queue record; these fields preserve what the bot observed. If a previous approval was wrong, revert or change its status to `rejected`, preserve the record in Git history, activate the manual kill switch if affected live decisions may still authorize, and audit every affected prediction and bet.

## Alias acceptance checklist

- Provider player spelling and opponent belong to the same verified fixture.
- Canonical profile is on the correct ATP/WTA context.
- Full name or multiple independent biographical fields agree.
- No plausible alternative candidate remains unresolved.
- The canonical spelling exactly matches the profile key after normalization.
- The alias does not map two distinct active players onto one profile.
- Tests, diagnostic mode, and a paper/real evidence row confirm the mapping.

Do not approve an alias merely to raise profile coverage or create more picks.

## Alias maintenance and rollback

`player-aliases.csv` is loaded before approved review rows; approved review mappings for the same normalized provider name are applied afterward. Avoid conflicting duplicate mappings. Before consolidating an approved row into the permanent file, confirm the final canonical name and retain source/confidence provenance.

To revoke an alias:

1. Activate `kill-switch.json` if the identity can affect pending live candidates.
2. Remove or correct the permanent alias in a reviewed commit and mark any corresponding review row `rejected`.
3. Identify affected audit rows by normalized provider name and identity method.
4. Do not rewrite historical snapshots to pretend the old mapping never existed.
5. Run tests, diagnostic mode, and paper trading before reopening.

## When an API replacement is justified

Replace or supplement a provider when its availability, quota, coverage, latency, legality/terms, price independence, result semantics, or schema stability no longer meets the contract. A transient outage or exhausted single key is not by itself a reason for an untested production cutover.

Classify the role before implementation:

- fixture discovery;
- executable bookmaker odds and consensus;
- independent fixture confirmation;
- player ratings/profile evidence;
- historical results/features;
- live status and physical availability;
- settlement results and closing prices;
- optional narrative or notifications.

A provider approved for one role is not automatically authoritative for another. In particular, discovery odds do not become settlement evidence, a rendering proxy does not become an independent source, and an AI response does not become verified data.

## Replacement contract design

Before code changes, record in `PROVIDERS.md` on the replacement branch:

- provider name, base host, endpoint, authentication method, quotas, and permitted use;
- request parameters, date/timezone semantics, pagination, and batch limits;
- complete success, empty, authentication, quota, transient, and permanent failure shapes;
- required/optional fields and types with redacted examples;
- event ID stability and update/cancellation behavior;
- player-side orientation and moneyline market naming;
- bookmaker identity, quote timestamp semantics, and whether prices are truly independent;
- tournament, surface, indoor, best-of, venue, and status mappings;
- result, retirement, walkover, void, and correction semantics;
- closing-price availability and definition;
- retry, key rotation, circuit-breaker, cache, and fallback behavior;
- data retention and secret-handling requirements.

If any side, timestamp, event identity, status, or result meaning is ambiguous, the provider is not ready for live use.

## Canonical internal match adapter

The provider adapter must emit the existing internal contract rather than leaking provider-specific fields downstream:

| Internal field | Requirement |
|---|---|
| `event_id` | Stable non-empty provider event identifier |
| `start_time` | Parseable event start timestamp, never used as quote time |
| `status` | Raw/mapped state sufficient to block live, cancelled, postponed, withdrawn, or settled events |
| `player1`, `player2` | Two non-empty singles competitors with documented side mapping |
| `tournament`, `level` | Verified name and canonical level mapping |
| `surface`, `indoor`, `best_of` | Verified value or missing; never guessed beyond documented conservative detection |
| `source` | Exact non-secret source host/URL |
| `home_odds`, `away_odds` | Valid executable decimal prices greater than 1.0 |
| `consensus_home_odds`, `consensus_away_odds` | Median valid side prices |
| `odds_source`, side source fields | Actual selected bookmaker provenance |
| `bookmaker_count` | Number of valid independent bookmaker pairs |
| side dispersion fields | `(max-min)/median` over retained quotes |
| `bookmaker_quotes` | Sanitized valid quote pairs and provenance |
| `odds_timestamp` | Plausible provider quote update time; blank when unavailable |
| `location` | Coordinates/timezone only when explicitly valid and sourced |

Downstream market rules remain unchanged: outlier filtering, minimum two-bookmaker revalidation, freshness, dispersion, overround, odds range, EV, identity, portfolio, and kill-switch gates still apply.

## Implementation and test procedure

1. Activate live stop if the change is an emergency replacement; otherwise develop on a branch while the incumbent remains active.
2. Add a provider-specific transport/adapter boundary. Do not scatter new field names throughout modelling, staking, or settlement.
3. Reuse the shared request safety behavior: 30-second timeout where applicable, bounded transient retries, circuit breaker, sanitized quota metadata, and no credential in URLs/logs/state.
4. Validate collection shape before interpreting an empty response. Keep `provider_failure`, `provider_schema_failure`, `valid_empty_schedule`, and `fixtures_without_verified_odds` distinct.
5. Add redacted fixtures and tests for:
   - valid discovery and odds;
   - valid empty schedule;
   - missing required fields and changed collection shape;
   - reversed or missing player sides;
   - malformed/one-sided/non-decimal odds;
   - duplicate events and pagination/batch boundaries;
   - missing or future quote timestamp;
   - 401/403/429 key rotation and transient failures;
   - cancellation, postponement, withdrawal, live/in-play status;
   - completed result, correction, retirement, walkover, void, and missing scores;
   - closing-price association to the correct player;
   - secrets absent from errors and persisted health/quota data.
6. Add workflow secret names only under GitHub **Settings → Secrets and variables → Actions**. Reference them through `env`; never commit values or `.env` files.
7. Update source-health, quota, schema-alert, audit, snapshot, dashboard, and notification labels to identify the new source accurately.
8. Update `PROVIDERS.md`, `ARCHITECTURE.md`, tests, model/policy version if interpretation changes, and release notes.
9. Run the full suite, coverage gate, secret scan, dependency audit, and diagnostic mode.

## Shadow comparison before cutover

The replacement must run without authorizing bets until comparison evidence is reviewed. Capture both incumbent and challenger responses at the same decision times and compare:

- fixture coverage, duplicates, event IDs, start times, player-side orientation, and status;
- tournament/surface/format classification;
- bookmaker coverage and independence;
- median/best prices, overround, dispersion, timestamps, and staleness;
- cancellations and market withdrawals;
- completed results, retirement/void classification, corrections, and closing prices;
- latency, quota consumption, schema alerts, and failure rate;
- downstream eligible/rejected counts and the exact reason for every difference.

Do not combine two labels from the same underlying odds feed as independent bookmakers or independent fixture confirmation. Shadow output must not write live bets, debit bankroll, or settle existing bets.

No fixed number of days can compensate for missing edge cases. The review must include ordinary events plus at least one observed or fixture-tested cancellation, retirement/void, provider error, quota rotation, malformed response, and missing timestamp. Production validation requirements in `PROJECT-ROADMAP.md` still apply.

## Cutover procedure

1. Freeze and review the provider contract, test evidence, shadow comparison, and rollback commit.
2. Keep `kill-switch.json` active during deployment.
3. Add/verify all GitHub Secrets and workflow environment mappings without exposing values.
4. Deploy the adapter and run tests plus diagnostic mode on GitHub.
5. Run a full paper-trading daily cycle, revalidation cycle, and settlement replay.
6. Confirm health reports distinguish genuine empty schedules from provider/schema failures and contain no secrets.
7. Confirm existing open bets remain settled by a compatible verified path; do not abandon incumbent settlement access until they resolve.
8. Change the production provider selection, update model/policy version when decision semantics changed, and keep the previous adapter available only as an explicit documented rollback path.
9. Reopen live authorization under `EMERGENCY-RUNBOOK.md`, watch the full first workflow, and inspect its committed state.

## Rollback procedure

Rollback immediately if player sides, event identity, price timestamps, bookmaker independence, status, or settlement semantics are wrong or ambiguous.

1. Activate the manual kill switch and cancel pre-stop daily/revalidation runs.
2. Preserve challenger payload fixtures, logs, schema alerts, and affected state commits without credentials.
3. Revert provider selection to the last tested adapter; do not delete already recorded challenger provenance.
4. Keep settlement running only through a verified compatible result path.
5. Reconcile the transaction ledger and audit all decisions produced during the cutover window.
6. Run tests, diagnostic mode, and paper trading before reopening.

Never restore production merely by suppressing schema alerts, relabeling provider failures as empty schedules, accepting one-bookmaker markets, copying start time into quote time, or weakening identity/price/result validation.
