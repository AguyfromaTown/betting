# Tennis Source Health

Updated: 2026-08-08T18:22:38.032277+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 23 | 20 | 3 | 270.2 ms | 363.0 ms | 392.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 558.0 ms | 558.0 ms | 558.0 ms | 0 | 0 |
| site.api.espn.com | 8 | 0 | 8 | 270.4 ms | 374.0 ms | 374.0 ms | 0 | 0 |
| stats.tennismylife.org | 7 | 7 | 0 | 54.9 ms | 88.0 ms | 88.0 ms | 7 | 0 |
| www.tennisexplorer.com | 5 | 5 | 0 | 35.8 ms | 39.0 ms | 39.0 ms | 5 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-08T18:22:18.655831+00:00 | api.odds-api.io | ok | network | 392 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:22:18.891237+00:00 | api.odds-api.io | ok | network | 235 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:22:19.116236+00:00 | api.odds-api.io | ok | network | 225 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:22:19.330743+00:00 | api.odds-api.io | failed | network | 214 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:22:19.560556+00:00 | api.odds-api.io | failed | network | 230 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:22:19.776983+00:00 | api.odds-api.io | failed | network | 215 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:22:20.000532+00:00 | api.odds-api.io | ok | network | 223 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:20.241625+00:00 | api.odds-api.io | ok | network | 240 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:20.468037+00:00 | api.odds-api.io | ok | network | 226 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:20.690917+00:00 | api.odds-api.io | ok | network | 222 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:20.941121+00:00 | api.odds-api.io | ok | network | 249 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:20.990099+00:00 | www.tennisexplorer.com | ok | fresh_cache | 30 ms | 380.7 s | no | fresh cache hit |
| 2026-08-08T18:22:20.997118+00:00 | www.tennisexplorer.com | ok | fresh_cache | 37 ms | 384.4 s | no | fresh cache hit |
| 2026-08-08T18:22:20.997511+00:00 | www.tennisexplorer.com | ok | fresh_cache | 37 ms | 372.8 s | no | fresh cache hit |
| 2026-08-08T18:22:20.998040+00:00 | www.tennisexplorer.com | ok | fresh_cache | 39 ms | 389.1 s | no | fresh cache hit |
| 2026-08-08T18:22:20.998386+00:00 | www.tennisexplorer.com | ok | fresh_cache | 36 ms | 368.2 s | no | fresh cache hit |
| 2026-08-08T18:22:21.025317+00:00 | stats.tennismylife.org | ok | fresh_cache | 36 ms | 364.7 s | no | fresh cache hit |
| 2026-08-08T18:22:21.073121+00:00 | stats.tennismylife.org | ok | fresh_cache | 75 ms | 364.8 s | no | fresh cache hit |
| 2026-08-08T18:22:21.077159+00:00 | stats.tennismylife.org | ok | fresh_cache | 32 ms | 363.9 s | no | fresh cache hit |
| 2026-08-08T18:22:21.077902+00:00 | stats.tennismylife.org | ok | fresh_cache | 88 ms | 364.6 s | no | fresh cache hit |
| 2026-08-08T18:22:21.078103+00:00 | stats.tennismylife.org | ok | fresh_cache | 33 ms | 365.2 s | no | fresh cache hit |
| 2026-08-08T18:22:21.147573+00:00 | stats.tennismylife.org | ok | fresh_cache | 52 ms | 364.1 s | no | fresh cache hit |
| 2026-08-08T18:22:21.147693+00:00 | stats.tennismylife.org | ok | fresh_cache | 68 ms | 363.9 s | no | fresh cache hit |
| 2026-08-08T18:22:21.188712+00:00 | site.api.espn.com | failed | network | 198 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:21.200105+00:00 | site.api.espn.com | failed | network | 187 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:21.373058+00:00 | site.api.espn.com | failed | network | 336 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:21.385069+00:00 | site.api.espn.com | failed | network | 307 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:21.401306+00:00 | site.api.espn.com | failed | network | 183 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:21.403606+00:00 | site.api.espn.com | failed | network | 365 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:21.404368+00:00 | site.api.espn.com | failed | network | 374 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:21.430344+00:00 | site.api.espn.com | failed | network | 213 ms | N/A | no | HTTPError |
| 2026-08-08T18:22:34.013048+00:00 | api.odds-api.io | ok | network | 266 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:34.300214+00:00 | api.odds-api.io | ok | network | 286 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:34.584982+00:00 | api.odds-api.io | ok | network | 284 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:34.882828+00:00 | api.odds-api.io | ok | network | 297 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:35.157091+00:00 | api.odds-api.io | ok | network | 273 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:35.450486+00:00 | api.odds-api.io | ok | network | 292 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:35.714854+00:00 | api.odds-api.io | ok | network | 263 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:36.056451+00:00 | api.odds-api.io | ok | network | 341 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:36.420516+00:00 | api.odds-api.io | ok | network | 363 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:36.759622+00:00 | api.odds-api.io | ok | network | 338 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:37.041388+00:00 | api.odds-api.io | ok | network | 281 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:37.302798+00:00 | api.odds-api.io | ok | network | 260 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:22:38.029949+00:00 | api.telegram.org | ok | network | 558 ms | N/A | no | HTTP 200 |
