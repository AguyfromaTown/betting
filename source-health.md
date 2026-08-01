# Tennis Source Health

Updated: 2026-08-01T23:27:21.227359+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 193.0 ms | 394.0 ms | 394.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 374.0 ms | 374.0 ms | 374.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T23:27:19.873618+00:00 | api.odds-api.io | ok | network | 394 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-01T23:27:20.021898+00:00 | api.odds-api.io | ok | network | 148 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-01T23:27:20.166608+00:00 | api.odds-api.io | ok | network | 145 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-01T23:27:20.334013+00:00 | api.odds-api.io | failed | network | 167 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-01T23:27:20.494706+00:00 | api.odds-api.io | failed | network | 161 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-01T23:27:20.650651+00:00 | api.odds-api.io | ok | network | 155 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T23:27:20.832354+00:00 | api.odds-api.io | ok | network | 181 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T23:27:21.225349+00:00 | api.telegram.org | ok | network | 374 ms | N/A | no | HTTP 200 |
