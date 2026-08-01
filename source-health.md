# Tennis Source Health

Updated: 2026-08-01T19:12:32.327427+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 229.9 ms | 296.0 ms | 296.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 522.0 ms | 522.0 ms | 522.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T19:12:30.433779+00:00 | api.odds-api.io | ok | network | 262 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-01T19:12:30.666880+00:00 | api.odds-api.io | ok | network | 233 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-01T19:12:30.861849+00:00 | api.odds-api.io | ok | network | 195 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-01T19:12:31.072013+00:00 | api.odds-api.io | failed | network | 210 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-01T19:12:31.282663+00:00 | api.odds-api.io | failed | network | 211 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-01T19:12:31.485225+00:00 | api.odds-api.io | ok | network | 202 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T19:12:31.782701+00:00 | api.odds-api.io | ok | network | 296 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T19:12:32.325314+00:00 | api.telegram.org | ok | network | 522 ms | N/A | no | HTTP 200 |
