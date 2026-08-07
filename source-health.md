# Tennis Source Health

Updated: 2026-08-07T00:37:15.460629+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 11 | 9 | 2 | 318.5 ms | 426.0 ms | 426.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 704.0 ms | 704.0 ms | 704.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-07T00:37:11.482523+00:00 | api.odds-api.io | ok | network | 426 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-07T00:37:11.765277+00:00 | api.odds-api.io | ok | network | 283 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-07T00:37:12.050478+00:00 | api.odds-api.io | ok | network | 285 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-07T00:37:12.408220+00:00 | api.odds-api.io | failed | network | 358 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-07T00:37:12.713912+00:00 | api.odds-api.io | failed | network | 306 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-07T00:37:13.024895+00:00 | api.odds-api.io | ok | network | 310 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-07T00:37:13.341780+00:00 | api.odds-api.io | ok | network | 316 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-07T00:37:13.669029+00:00 | api.odds-api.io | ok | network | 326 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-07T00:37:13.962145+00:00 | api.odds-api.io | ok | network | 292 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-07T00:37:14.254291+00:00 | api.odds-api.io | ok | network | 291 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-07T00:37:14.564846+00:00 | api.odds-api.io | ok | network | 310 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-07T00:37:15.458774+00:00 | api.telegram.org | ok | network | 704 ms | N/A | no | HTTP 200 |
