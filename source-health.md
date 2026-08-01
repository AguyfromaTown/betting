# Tennis Source Health

Updated: 2026-08-01T20:24:43.373408+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 273.7 ms | 554.0 ms | 554.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 556.0 ms | 556.0 ms | 556.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T20:24:41.428033+00:00 | api.odds-api.io | ok | network | 554 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-01T20:24:41.634970+00:00 | api.odds-api.io | ok | network | 207 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-01T20:24:41.948583+00:00 | api.odds-api.io | ok | network | 314 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-01T20:24:42.155280+00:00 | api.odds-api.io | failed | network | 207 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-01T20:24:42.353542+00:00 | api.odds-api.io | failed | network | 198 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-01T20:24:42.571821+00:00 | api.odds-api.io | ok | network | 217 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T20:24:42.792305+00:00 | api.odds-api.io | ok | network | 219 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T20:24:43.371179+00:00 | api.telegram.org | ok | network | 556 ms | N/A | no | HTTP 200 |
