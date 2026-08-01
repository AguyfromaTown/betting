# Tennis Source Health

Updated: 2026-08-01T17:48:09.589515+00:00

Fixture status: `fixtures_without_verified_odds`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 6 | 3 | 3 | 154.3 ms | 181.0 ms | 181.0 ms | 0 | 0 |
| site.api.espn.com | 2 | 2 | 0 | 163.5 ms | 212.0 ms | 212.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-01T17:48:08.488855+00:00 | api.odds-api.io | ok | network | 181 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T17:48:08.643816+00:00 | api.odds-api.io | ok | network | 154 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T17:48:08.867803+00:00 | site.api.espn.com | ok | network | 212 ms | N/A | no | HTTP 200 |
| 2026-08-01T17:48:08.984294+00:00 | site.api.espn.com | ok | network | 115 ms | N/A | no | HTTP 200 |
| 2026-08-01T17:48:09.143227+00:00 | api.odds-api.io | ok | network | 155 ms | N/A | no | HTTP 200 key 1 |
| 2026-08-01T17:48:09.283811+00:00 | api.odds-api.io | failed | network | 136 ms | N/A | no | HTTPError |
| 2026-08-01T17:48:09.439667+00:00 | api.odds-api.io | failed | network | 155 ms | N/A | no | HTTPError |
| 2026-08-01T17:48:09.585383+00:00 | api.odds-api.io | failed | network | 145 ms | N/A | no | HTTPError |
