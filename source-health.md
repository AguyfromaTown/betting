# Tennis Source Health

Updated: 2026-08-01T22:25:50.753448+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 201.7 ms | 241.0 ms | 241.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 384.0 ms | 384.0 ms | 384.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T22:25:49.173498+00:00 | api.odds-api.io | ok | network | 241 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-01T22:25:49.362950+00:00 | api.odds-api.io | ok | network | 189 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-01T22:25:49.541403+00:00 | api.odds-api.io | ok | network | 178 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-01T22:25:49.728654+00:00 | api.odds-api.io | failed | network | 187 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-01T22:25:49.927677+00:00 | api.odds-api.io | failed | network | 199 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-01T22:25:50.119494+00:00 | api.odds-api.io | ok | network | 191 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T22:25:50.347015+00:00 | api.odds-api.io | ok | network | 227 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T22:25:50.751691+00:00 | api.telegram.org | ok | network | 384 ms | N/A | no | HTTP 200 |
