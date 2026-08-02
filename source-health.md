# Tennis Source Health

Updated: 2026-08-02T04:50:20.692439+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 164.9 ms | 229.0 ms | 229.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 419.0 ms | 419.0 ms | 419.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-02T04:50:19.321373+00:00 | api.odds-api.io | ok | network | 229 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-02T04:50:19.465596+00:00 | api.odds-api.io | ok | network | 144 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-02T04:50:19.616908+00:00 | api.odds-api.io | ok | network | 151 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-02T04:50:19.773930+00:00 | api.odds-api.io | failed | network | 157 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-02T04:50:19.957524+00:00 | api.odds-api.io | failed | network | 184 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-02T04:50:20.110599+00:00 | api.odds-api.io | ok | network | 152 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T04:50:20.248641+00:00 | api.odds-api.io | ok | network | 137 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T04:50:20.690436+00:00 | api.telegram.org | ok | network | 419 ms | N/A | no | HTTP 200 |
