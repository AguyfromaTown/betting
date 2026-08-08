# Tennis Source Health

Updated: 2026-08-08T18:26:38.468411+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 23 | 20 | 3 | 232.5 ms | 277.0 ms | 284.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 383.0 ms | 383.0 ms | 383.0 ms | 0 | 0 |
| site.api.espn.com | 7 | 0 | 7 | 198.4 ms | 305.0 ms | 305.0 ms | 0 | 0 |
| stats.tennismylife.org | 7 | 7 | 0 | 49.3 ms | 79.0 ms | 79.0 ms | 7 | 0 |
| www.tennisexplorer.com | 5 | 5 | 0 | 35.2 ms | 56.0 ms | 56.0 ms | 5 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-08T18:26:15.689161+00:00 | api.odds-api.io | ok | network | 236 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:26:15.887018+00:00 | api.odds-api.io | ok | network | 198 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:26:16.086188+00:00 | api.odds-api.io | ok | network | 199 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:26:16.281970+00:00 | api.odds-api.io | failed | network | 196 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:26:16.518014+00:00 | api.odds-api.io | failed | network | 236 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:26:16.770356+00:00 | api.odds-api.io | failed | network | 251 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:26:16.978533+00:00 | api.odds-api.io | ok | network | 208 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:17.218600+00:00 | api.odds-api.io | ok | network | 239 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:17.421822+00:00 | api.odds-api.io | ok | network | 202 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:17.653700+00:00 | api.odds-api.io | ok | network | 231 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:17.872180+00:00 | api.odds-api.io | ok | network | 217 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:17.917530+00:00 | www.tennisexplorer.com | ok | fresh_cache | 23 ms | 621.3 s | no | fresh cache hit |
| 2026-08-08T18:26:17.918023+00:00 | www.tennisexplorer.com | ok | fresh_cache | 24 ms | 626.0 s | no | fresh cache hit |
| 2026-08-08T18:26:17.923484+00:00 | www.tennisexplorer.com | ok | fresh_cache | 28 ms | 609.7 s | no | fresh cache hit |
| 2026-08-08T18:26:17.939960+00:00 | www.tennisexplorer.com | ok | fresh_cache | 45 ms | 617.7 s | no | fresh cache hit |
| 2026-08-08T18:26:17.966558+00:00 | www.tennisexplorer.com | ok | fresh_cache | 56 ms | 605.2 s | no | fresh cache hit |
| 2026-08-08T18:26:18.099029+00:00 | stats.tennismylife.org | ok | fresh_cache | 64 ms | 601.7 s | no | fresh cache hit |
| 2026-08-08T18:26:18.125936+00:00 | site.api.espn.com | failed | network | 197 ms | N/A | no | HTTPError |
| 2026-08-08T18:26:18.142229+00:00 | stats.tennismylife.org | ok | fresh_cache | 65 ms | 601.7 s | no | fresh cache hit |
| 2026-08-08T18:26:18.166173+00:00 | site.api.espn.com | failed | network | 173 ms | N/A | no | HTTPError |
| 2026-08-08T18:26:18.167085+00:00 | stats.tennismylife.org | ok | fresh_cache | 25 ms | 600.9 s | no | fresh cache hit |
| 2026-08-08T18:26:18.177676+00:00 | stats.tennismylife.org | ok | fresh_cache | 79 ms | 602.0 s | no | fresh cache hit |
| 2026-08-08T18:26:18.183408+00:00 | site.api.espn.com | failed | network | 191 ms | N/A | no | HTTPError |
| 2026-08-08T18:26:18.185241+00:00 | stats.tennismylife.org | ok | fresh_cache | 43 ms | 602.3 s | no | fresh cache hit |
| 2026-08-08T18:26:18.186299+00:00 | site.api.espn.com | failed | network | 185 ms | N/A | no | HTTPError |
| 2026-08-08T18:26:18.198339+00:00 | stats.tennismylife.org | ok | fresh_cache | 37 ms | 601.0 s | no | fresh cache hit |
| 2026-08-08T18:26:18.198840+00:00 | stats.tennismylife.org | ok | fresh_cache | 32 ms | 601.1 s | no | fresh cache hit |
| 2026-08-08T18:26:18.211206+00:00 | site.api.espn.com | failed | network | 218 ms | N/A | no | HTTPError |
| 2026-08-08T18:26:18.254000+00:00 | site.api.espn.com | failed | network | 120 ms | N/A | no | HTTPError |
| 2026-08-08T18:26:18.326334+00:00 | site.api.espn.com | failed | network | 305 ms | N/A | no | HTTPError |
| 2026-08-08T18:26:34.777146+00:00 | api.odds-api.io | ok | network | 214 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:35.050163+00:00 | api.odds-api.io | ok | network | 272 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:35.297856+00:00 | api.odds-api.io | ok | network | 247 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:35.519330+00:00 | api.odds-api.io | ok | network | 221 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:35.748259+00:00 | api.odds-api.io | ok | network | 228 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:35.971359+00:00 | api.odds-api.io | ok | network | 222 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:36.208082+00:00 | api.odds-api.io | ok | network | 236 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:36.473970+00:00 | api.odds-api.io | ok | network | 265 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:36.752025+00:00 | api.odds-api.io | ok | network | 277 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:37.037084+00:00 | api.odds-api.io | ok | network | 284 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:37.299084+00:00 | api.odds-api.io | ok | network | 261 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:37.508035+00:00 | api.odds-api.io | ok | network | 208 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:26:38.110974+00:00 | api.telegram.org | ok | network | 383 ms | N/A | no | HTTP 200 |
