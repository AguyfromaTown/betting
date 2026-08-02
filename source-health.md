# Tennis Source Health

Updated: 2026-08-02T05:41:40.247794+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 7 | 5 | 2 | 376.0 ms | 645.0 ms | 645.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 604.0 ms | 604.0 ms | 604.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-02T05:41:37.491685+00:00 | api.odds-api.io | ok | network | 645 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-02T05:41:37.795973+00:00 | api.odds-api.io | ok | network | 304 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-02T05:41:38.167144+00:00 | api.odds-api.io | ok | network | 371 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-02T05:41:38.581984+00:00 | api.odds-api.io | failed | network | 415 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-02T05:41:38.879299+00:00 | api.odds-api.io | failed | network | 297 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-02T05:41:39.180992+00:00 | api.odds-api.io | ok | network | 301 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T05:41:39.480914+00:00 | api.odds-api.io | ok | network | 299 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-02T05:41:40.245855+00:00 | api.telegram.org | ok | network | 604 ms | N/A | no | HTTP 200 |
