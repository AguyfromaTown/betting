# Tennis Source Health

Updated: 2026-08-02T09:34:09.939869+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 332.9 ms | 433.0 ms | 433.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 574.0 ms | 574.0 ms | 574.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-02T09:34:06.870074+00:00 | api.odds-api.io | ok | network | 433 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-02T09:34:07.156773+00:00 | api.odds-api.io | ok | network | 287 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-02T09:34:07.446885+00:00 | api.odds-api.io | ok | network | 290 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-02T09:34:07.856310+00:00 | api.odds-api.io | failed | network | 409 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-02T09:34:08.161738+00:00 | api.odds-api.io | failed | network | 305 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-02T09:34:08.462227+00:00 | api.odds-api.io | ok | network | 300 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T09:34:08.769898+00:00 | api.odds-api.io | ok | network | 306 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T09:34:09.937506+00:00 | api.telegram.org | ok | network | 574 ms | N/A | no | HTTP 200 |
