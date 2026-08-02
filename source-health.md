# Tennis Source Health

Updated: 2026-08-02T11:12:36.558041+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 248.7 ms | 321.0 ms | 321.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 755.0 ms | 755.0 ms | 755.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-02T11:12:34.355349+00:00 | api.odds-api.io | ok | network | 321 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-02T11:12:34.587118+00:00 | api.odds-api.io | ok | network | 232 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-02T11:12:34.836723+00:00 | api.odds-api.io | ok | network | 250 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-02T11:12:35.080814+00:00 | api.odds-api.io | failed | network | 244 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-02T11:12:35.307483+00:00 | api.odds-api.io | failed | network | 227 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-02T11:12:35.530595+00:00 | api.odds-api.io | ok | network | 222 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T11:12:35.776768+00:00 | api.odds-api.io | ok | network | 245 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T11:12:36.555848+00:00 | api.telegram.org | ok | network | 755 ms | N/A | no | HTTP 200 |
