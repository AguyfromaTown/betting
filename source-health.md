# Tennis Source Health

Updated: 2026-08-02T07:28:53.864560+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 224.3 ms | 386.0 ms | 386.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 407.0 ms | 407.0 ms | 407.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-02T07:28:52.247525+00:00 | api.odds-api.io | ok | network | 386 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-02T07:28:52.447184+00:00 | api.odds-api.io | ok | network | 200 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-02T07:28:52.630972+00:00 | api.odds-api.io | ok | network | 184 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-02T07:28:52.836220+00:00 | api.odds-api.io | failed | network | 205 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-02T07:28:53.033843+00:00 | api.odds-api.io | failed | network | 198 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-02T07:28:53.227179+00:00 | api.odds-api.io | ok | network | 192 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T07:28:53.432724+00:00 | api.odds-api.io | ok | network | 205 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T07:28:53.862236+00:00 | api.telegram.org | ok | network | 407 ms | N/A | no | HTTP 200 |
