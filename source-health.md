# Tennis Source Health

Updated: 2026-08-01T23:29:45.363767+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 169.0 ms | 304.0 ms | 304.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 518.0 ms | 518.0 ms | 518.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T23:29:43.824598+00:00 | api.odds-api.io | ok | network | 183 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-01T23:29:43.965652+00:00 | api.odds-api.io | ok | network | 141 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-01T23:29:44.084787+00:00 | api.odds-api.io | ok | network | 119 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-01T23:29:44.217979+00:00 | api.odds-api.io | failed | network | 133 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-01T23:29:44.388135+00:00 | api.odds-api.io | failed | network | 170 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-01T23:29:44.522247+00:00 | api.odds-api.io | ok | network | 133 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T23:29:44.826875+00:00 | api.odds-api.io | ok | network | 304 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T23:29:45.361439+00:00 | api.telegram.org | ok | network | 518 ms | N/A | no | HTTP 200 |
