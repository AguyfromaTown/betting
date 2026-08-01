# Tennis Source Health

Updated: 2026-08-01T21:24:03.473228+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 159.6 ms | 310.0 ms | 310.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 319.0 ms | 319.0 ms | 319.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T21:24:02.306620+00:00 | api.odds-api.io | ok | network | 310 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-01T21:24:02.446669+00:00 | api.odds-api.io | ok | network | 140 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-01T21:24:02.582533+00:00 | api.odds-api.io | ok | network | 136 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-01T21:24:02.718960+00:00 | api.odds-api.io | failed | network | 136 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-01T21:24:02.849352+00:00 | api.odds-api.io | failed | network | 130 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-01T21:24:02.978530+00:00 | api.odds-api.io | ok | network | 128 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T21:24:03.116180+00:00 | api.odds-api.io | ok | network | 137 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T21:24:03.471135+00:00 | api.telegram.org | ok | network | 319 ms | N/A | no | HTTP 200 |
