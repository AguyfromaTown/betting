# Tennis Source Health

Updated: 2026-08-02T01:06:24.605889+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 243.4 ms | 338.0 ms | 338.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 554.0 ms | 554.0 ms | 554.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-02T01:06:22.658216+00:00 | api.odds-api.io | ok | network | 338 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-02T01:06:22.868557+00:00 | api.odds-api.io | ok | network | 210 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-02T01:06:23.079799+00:00 | api.odds-api.io | ok | network | 211 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-02T01:06:23.341262+00:00 | api.odds-api.io | failed | network | 261 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-02T01:06:23.543028+00:00 | api.odds-api.io | failed | network | 202 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-02T01:06:23.813128+00:00 | api.odds-api.io | ok | network | 269 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T01:06:24.027469+00:00 | api.odds-api.io | ok | network | 213 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T01:06:24.603717+00:00 | api.telegram.org | ok | network | 554 ms | N/A | no | HTTP 200 |
