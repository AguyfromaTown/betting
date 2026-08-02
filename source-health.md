# Tennis Source Health

Updated: 2026-08-02T12:33:48.653207+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 266.4 ms | 499.0 ms | 499.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 618.0 ms | 618.0 ms | 618.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-02T12:33:46.641719+00:00 | api.odds-api.io | ok | network | 499 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-02T12:33:46.865842+00:00 | api.odds-api.io | ok | network | 224 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-02T12:33:47.072006+00:00 | api.odds-api.io | ok | network | 206 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-02T12:33:47.273128+00:00 | api.odds-api.io | failed | network | 201 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-02T12:33:47.478453+00:00 | api.odds-api.io | failed | network | 205 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-02T12:33:47.766603+00:00 | api.odds-api.io | ok | network | 287 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T12:33:48.010536+00:00 | api.odds-api.io | ok | network | 243 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T12:33:48.651275+00:00 | api.telegram.org | ok | network | 618 ms | N/A | no | HTTP 200 |
