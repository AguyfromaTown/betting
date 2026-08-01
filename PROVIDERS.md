# Provider Contracts and Fallbacks

This document is the authoritative inventory of external and operator-maintained data sources used by `tennis-bot/tennis_bot.py`. It records the expected schema, fallback order, trust boundary, and failure behavior. Update it whenever an endpoint, parser, required field, or fallback changes.

## Contract rules shared by network providers

- Network timeout: 30 seconds unless a narrower call-specific timeout is defined; Groq completion calls use 120 seconds.
- Transient HTTP statuses are `408`, `425`, `500`, `502`, `503`, and `504`. They receive at most two retries with bounded exponential delay and an eligible `Retry-After` value.
- Three provider failures open a five-minute circuit breaker. Open circuits skip requests rather than repeatedly delaying workflows.
- Odds and Groq credentials rotate only on `401`, `403`, or `429`. Ordinary transient failures retry the same credential.
- API credentials are never part of logged URLs, source-health details, dashboard data, or persisted quota reports.
- Collection schemas accept a top-level list or an object whose `events` or `data` field is a list. Other collection shapes generate `provider-schema-alerts.md` entries and yield no records.
- A schema alert is not treated as a valid empty schedule.
- Cache entries are bounded by entry size/count. Fresh cache and stale-after-error cache are recorded separately in `source-health.json`.

## Provider overview

| Provider | Role | Authentication | Production authority | Fallback |
|---|---|---|---|---|
| Odds-API.io | Fixtures, bookmaker moneylines, status, results and closing prices | `ODDS_API_KEY[_2..5]` | Primary fixture/price/result provider | Key rotation; no invented fixture fallback |
| ESPN scoreboard | Independent ATP/WTA fixture corroboration | None | Confirmation only | Missing confirmation reduces evidence; it does not replace prices |
| Tennis Abstract | ATP/WTA Elo, surface Elo, rank and age | None | Player rating evidence | Jina Reader, then bounded cache |
| TML Database | Recent ATP-style match history and statistics | None | Historical feature evidence | Other season/history files; missing rows remain missing |
| 36-SURE dataset | WTA historical match supplement | None | Historical feature evidence | TML files where coverage overlaps |
| Oddspedia HTML | Opportunistic odds lookup for an unpriced fixture | None | Low-trust discovery only | None; later authorization still requires full market controls |
| ATP Tour/WTA websites | Legacy HTML fixture helper parsers | None | Not in the production fixture path | None |
| Groq | Optional narrative and structured candidate suggestions | `GROQ_API_KEY[_2..5]` | Non-authoritative | Deterministic Python report |
| Jina Reader | Text rendering fallback for blocked public HTML | None | Transport fallback only | Stale cache within configured limit |
| Telegram/SMTP | Optional outbound operational notifications | Environment secrets | No betting authority | Non-fatal delivery failure |

## Odds-API.io

Base host: `https://api.odds-api.io`

### Events endpoint

Endpoint: `GET /v3/events`

Discovery parameters:

```text
sport=tennis
apiKey=<secret>
```

Settlement parameters additionally use:

```text
status=settled
from=<YYYY-MM-DDT00:00:00Z>
to=<YYYY-MM-DDT23:59:59Z>
```

Accepted response collection: a JSON array, or `{ "events": [...] }`, or `{ "data": [...] }`.

Required event fields for discovery:

| Field | Type | Use |
|---|---|---|
| `id` | string/number | Stable event join key |
| `date` | ISO-like timestamp string | Requested-date filtering and start time |
| `home` | non-empty string | First competitor |
| `away` | non-empty string | Second competitor |

Optional event fields:

| Field | Expected type | Use |
|---|---|---|
| `status` | string/object depending provider state | Live/started/settled/cancellation controls |
| `scores.home`, `scores.away` | numeric | Verified settlement outcome |
| `league` | object | Tournament `name` and optional `surface` |
| `surface` | `hard`, `clay`, or `grass` | Direct surface evidence |
| `indoor` | boolean-like | Environment model |
| `bestOf` | integer-like | BO3/BO5 model selection |
| `location` or `venue` | object | Coordinates/timezone if explicit and valid |
| `latitude`/`lat`, `longitude`/`lon`/`lng` | numeric | Verified travel context |
| `timezone`/`timeZone`/`utcOffset` | timezone/offset string | Local-time and travel context |
| `oddsUpdatedAt`/`lastUpdated`/`updatedAt`/`updated_at` | timestamp | Quote freshness; event start time is never substituted |

If the provider responds successfully with a valid collection containing no events for the requested date, the fixture state is `valid_empty_schedule`. If records exist but violate required fields, it is `provider_schema_failure`. A request failure is `provider_failure`.

### Multi-odds endpoint

Endpoint: `GET /v3/odds/multi`

Parameters:

```text
eventIds=<comma-separated IDs, maximum batch size 10>
bookmakers=Bet365,Unibet,Pinnacle,William Hill,Betway
apiKey=<secret>
```

Settlement closing-price requests currently ask for `Bet365,Unibet`.

Required structural contract:

```json
{
  "id": "event-id",
  "bookmakers": {
    "Bookmaker": [
      {
        "name": "ML",
        "odds": [
          {"home": "1.60", "away": "2.40"}
        ]
      }
    ]
  }
}
```

- `id` must be present.
- `bookmakers` must be an object.
- Each bookmaker value must be a list of market objects.
- If present, each market's `odds` must be a list of objects.
- Accepted market names, case-insensitive: `ml`, `moneyline`, `match winner`, and `winner`.
- Both prices must parse as decimal odds greater than `1.0`.

The parser retains all valid bookmaker pairs, calculates the median consensus, rejects an isolated side quote more than 12% above its median, selects eligible best prices, and records bookmaker count and dispersion. A fixture without a valid two-way moneyline is omitted. Revalidation requires at least two bookmakers regardless of any earlier discovery price.

### Quota metadata

Only allow-listed rate-limit headers are stored: request/token limits, remaining counts, reset values, and `Retry-After`. Keys are identified only as `key-1` through `key-5`.

## ESPN scoreboard

Endpoints:

```text
GET https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard?dates=YYYYMMDD
GET https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard?dates=YYYYMMDD
```

Expected nesting:

```text
events[]
  name | shortName
  groupings[]
    grouping.slug | grouping.displayName  (must identify singles)
    competitions[]
      id
      startDate | date
      competitors[2].athlete.displayName
      status.type.state
```

Only dated singles competitions with exactly two named competitors are accepted. Pairing is compared after player-name normalization and without relying on competitor order. ESPN adds `secondary_fixture_confirmed` and a secondary event ID; it never supplies the price used by the model. Missing ESPN coverage does not cause Odds-API.io events to be invented or deleted, but the lack of independent confirmation remains visible in the audit evidence.

## Tennis Abstract

Endpoints:

```text
https://tennisabstract.com/reports/atp_elo_ratings.html
https://tennisabstract.com/reports/wta_elo_ratings.html
```

Fallback order for each leaderboard:

1. Direct HTML request.
2. Jina Reader rendering of the same URL.
3. Fresh cached direct/reader response, where available.
4. Stale cached response only after provider failure and only within seven days.
5. No profile; identity/data-quality controls remain active.

Direct HTML uses the final table and expects at least 16 text cells per player row. Reader text expects tab-separated rows with at least 16 cells. Used column positions are:

| Index | Meaning | Type |
|---:|---|---|
| 0 | Elo rank | integer |
| 1 | Player name | string |
| 2 | Age | float/blank |
| 3 | Overall Elo | float |
| 6 | Hard-court Elo | float/blank |
| 8 | Clay-court Elo | float/blank |
| 10 | Grass-court Elo | float/blank |
| 12 | Peak Elo | float/blank |
| 13 | Peak month | string/blank |
| 15 | Official ranking | integer/blank |

Leaderboards are downloaded once per tour per run, then reduced to players appearing in qualifying singles matches. Exact normalized identities are preferred. Approved aliases are next. Automatic fuzzy aliases require a unique score of at least 0.92 or a lead of at least 0.05 over another high-confidence candidate; all others enter manual review.

## Jina Reader transport fallback

Endpoint form: `https://r.jina.ai/<original-http-or-https-url>`.

Jina is a rendering transport, not an independent evidence provider. The source contract remains the target page's contract. The bot tries HTTPS and HTTP target forms, identifies responses under the `reader` cache namespace, and records reader latency/failure separately. Reader output cannot increase source independence counts.

## Historical match CSV sources

Endpoints loaded concurrently:

```text
https://raw.githubusercontent.com/Tennismylife/TML-Database/master/<previous-year>.csv
https://raw.githubusercontent.com/Tennismylife/TML-Database/master/<current-year>.csv
https://raw.githubusercontent.com/36-SURE/2026/main/data/wta_matches_2021_2026.csv
```

Core accepted columns:

| Column | Requirement/use |
|---|---|
| `tourney_date` | `YYYYMMDD`; required for dated features and leakage prevention |
| `winner_name`, `loser_name` | Required to associate a row with a player |
| `surface` | Optional surface-specific form/H2H/serve-return context |
| `tourney_name` or `tournament` | Optional tournament change and location join |
| `winner_rank`, `loser_rank` | Optional ranking history/opponent strength |
| `score` | Optional sets, tiebreak, deciding-set, retirement and BO5 features |
| `minutes` | Optional duration and workload features |
| `best_of` | Optional format evidence |

Standard Jeff-Sackmann-style winner/loser statistics are consumed when present, including ace, double-fault, service-point, first-serve, first/second-serve-points-won, service-games and break-points-saved fields. Rows lacking optional columns remain usable only for features supported by their available fields.

Every history row receives its exact `_source_url`. Feature calculations exclude rows on or after the prediction date where necessary, so future results cannot enter decision-time inputs. These repositories are additive historical evidence; failure does not create a fixture, price, status, or outcome.

## Oddspedia discovery fallback

Endpoint pattern: `https://oddspedia.com/tennis/<player1-player2>`.

This parser is attempted only for a match object that lacks both primary home and away prices. It looks for `[data-odds]`, `span.odds-value`, `div.odds-value`, or `span.market-odd`, parses decimal values, and associates the first value with player 1.

This is deliberately low-trust discovery behavior. It does not provide bookmaker consensus, independent quote count, or a second side contract. Therefore, it cannot by itself satisfy the later two-bookmaker authorization and market-dispersion requirements. Failure simply leaves the fixture unpriced.

## ATP Tour and WTA HTML helpers

The code contains parsers for:

```text
https://www.atptour.com/en/scores/YYYY-MM-DD/all/results
https://www.wtatennis.com/scores/YYYY-MM-DD
```

ATP selectors expect `div.day-scores`, tournament links, match cards, and two player-name elements. WTA selectors expect event/match cards, an event title, and two player-name elements.

These helpers are retained for compatibility and diagnostics but are not called by the production `fetch_verified_matches` path. They must not be described operationally as a fallback for Odds-API.io. Their failure has no effect on the production fixture-state classification.

## Operator-maintained verified evidence

### Player physical status

File: `verified-player-status.csv`

```text
PLAYER,STATUS,EFFECTIVE_DATE,EXPIRES_DATE,SOURCE_URL,VERIFIED_AT,DETAIL
```

Accepted rows require a player, supported status, applicable date window, a valid HTTPS source on an official tennis domain, and verification metadata. Blocking statuses include questionable, injured, withdrawn, unavailable, and suspended. Malformed or unsourced assertions are ignored rather than treated as verified injury evidence.

### Tournament locations

File: `verified-tournament-locations.csv`

```text
TOURNAMENT,LATITUDE,LONGITUDE,TIMEZONE,SOURCE
```

Coordinates must be numeric and within geographic bounds; timezone/offset must parse; source must be present. Rows are joined by normalized tournament name. Missing locations suppress distance/timezone features rather than applying guessed travel penalties.

## Groq

Endpoint: `POST https://api.groq.com/openai/v1/chat/completions`

Request contract:

```json
{
  "model": "llama-3.3-70b-versatile",
  "messages": [{"role": "user", "content": "<bounded verified prompt>"}],
  "max_tokens": 2048,
  "temperature": 0.3
}
```

Expected response path: `choices[0].message.content` as a string. Candidate extraction prefers the last valid JSON fenced block containing a list. Narrative parsing is a compatibility fallback. Every extracted candidate is rematched and recalculated by Python.

On `401`, `403`, or `429`, the next configured Groq key is tried. Transient statuses retry the same key. If no usable content is returned, `build_deterministic_report` creates the report from Python candidates. Groq unavailability does not turn a failed provider collection into analysis and cannot bypass any validation rule.

## Settlement contract

Settlement uses Odds-API.io events with `status=settled`. An event is eligible only when its date and normalized home/away identities match the recorded bet. Standard completion requires numeric `scores.home` and `scores.away` with a non-tied result. Retirement/walkover/void indicators are interpreted through explicit functions and the bookmaker policy in `risk-config.json`. If no event, scores, identity match, or valid rule exists, the bet remains unresolved.

Closing prices come from `/v3/odds/multi` and are stored only when a matching side price exists. Missing closing prices leave CLV blank; they are never converted to zero.

## Outbound services

### Telegram

Endpoint: `POST https://api.telegram.org/bot<TOKEN>/sendMessage`.

Required environment values: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Payload fields are `chat_id`, bounded sanitized `text`, and `disable_web_page_preview=true`. The token-bearing URL is never logged or persisted.

### SMTP email

Required values: `SMTP_HOST`, `ALERT_EMAIL_FROM`, and `ALERT_EMAIL_TO`. Optional authentication requires `SMTP_USERNAME` and `SMTP_PASSWORD` as a pair. SSL defaults to port 465; non-SSL defaults to port 587 and STARTTLS unless disabled.

Notification attempts occur only after bot state is saved. Failure records only channel and exception class and cannot fail betting, revalidation, or settlement.

## Schema-change response procedure

When a provider contract changes:

1. Do not weaken validation merely to restore row counts.
2. Preserve the failing payload shape in a redacted test fixture, never with credentials.
3. Update the provider parser and its malformed/valid schema tests.
4. Update this document and increment model/policy version if decision interpretation changes.
5. Run diagnostic mode before permitting state mutation.
6. Confirm `provider-schema-alerts.md` is clear on a real workflow run.
7. Keep live authorization stopped if fixture identity, price sides, status, or result semantics remain ambiguous.
