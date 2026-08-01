# Tennis Source Health

Updated: 2026-08-01T19:06:56.673344+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 176.7 ms | 339.0 ms | 339.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 360.0 ms | 360.0 ms | 360.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T19:06:55.391000+00:00 | api.odds-api.io | ok | network | 339 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-01T19:06:55.528626+00:00 | api.odds-api.io | ok | network | 138 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-01T19:06:55.700383+00:00 | api.odds-api.io | ok | network | 172 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-01T19:06:55.836275+00:00 | api.odds-api.io | failed | network | 136 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-01T19:06:55.972134+00:00 | api.odds-api.io | failed | network | 136 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-01T19:06:56.144915+00:00 | api.odds-api.io | ok | network | 172 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T19:06:56.290855+00:00 | api.odds-api.io | ok | network | 144 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T19:06:56.671280+00:00 | api.telegram.org | ok | network | 360 ms | N/A | no | HTTP 200 |
