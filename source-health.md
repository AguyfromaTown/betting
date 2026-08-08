# Tennis Source Health

Updated: 2026-08-08T18:33:16.987671+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 28 | 24 | 4 | 250.9 ms | 311.0 ms | 414.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 551.0 ms | 551.0 ms | 551.0 ms | 0 | 0 |
| site.api.espn.com | 8 | 0 | 8 | 175.6 ms | 288.0 ms | 288.0 ms | 0 | 0 |
| stats.tennismylife.org | 7 | 7 | 0 | 68.0 ms | 139.0 ms | 139.0 ms | 7 | 0 |
| www.tennisexplorer.com | 7 | 7 | 0 | 45.3 ms | 88.0 ms | 88.0 ms | 7 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-08T18:32:40.415789+00:00 | api.odds-api.io | ok | network | 414 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:32:40.638048+00:00 | api.odds-api.io | ok | network | 222 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:32:40.832615+00:00 | api.odds-api.io | ok | network | 195 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:32:41.126393+00:00 | api.odds-api.io | failed | network | 294 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:32:41.429475+00:00 | api.odds-api.io | failed | network | 303 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:32:41.636455+00:00 | api.odds-api.io | failed | network | 206 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:32:41.842604+00:00 | api.odds-api.io | ok | network | 206 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:32:42.054095+00:00 | api.odds-api.io | ok | network | 210 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:32:42.257070+00:00 | api.odds-api.io | ok | network | 202 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:32:42.470019+00:00 | api.odds-api.io | ok | network | 212 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:32:42.696625+00:00 | api.odds-api.io | ok | network | 226 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:32:42.913090+00:00 | api.odds-api.io | ok | network | 215 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:32:43.158072+00:00 | api.odds-api.io | ok | network | 244 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:32:43.327829+00:00 | www.tennisexplorer.com | ok | fresh_cache | 17 ms | 1003.1 s | no | fresh cache hit |
| 2026-08-08T18:32:43.328433+00:00 | www.tennisexplorer.com | ok | fresh_cache | 18 ms | 1006.8 s | no | fresh cache hit |
| 2026-08-08T18:32:43.329708+00:00 | www.tennisexplorer.com | ok | fresh_cache | 20 ms | 1011.4 s | no | fresh cache hit |
| 2026-08-08T18:32:43.374506+00:00 | www.tennisexplorer.com | ok | fresh_cache | 48 ms | 998.7 s | no | fresh cache hit |
| 2026-08-08T18:32:43.384367+00:00 | www.tennisexplorer.com | ok | fresh_cache | 55 ms | 990.6 s | no | fresh cache hit |
| 2026-08-08T18:32:43.400303+00:00 | www.tennisexplorer.com | ok | fresh_cache | 71 ms | 992.5 s | no | fresh cache hit |
| 2026-08-08T18:32:43.416139+00:00 | www.tennisexplorer.com | ok | fresh_cache | 88 ms | 995.1 s | no | fresh cache hit |
| 2026-08-08T18:32:43.452097+00:00 | stats.tennismylife.org | ok | fresh_cache | 62 ms | 987.0 s | no | fresh cache hit |
| 2026-08-08T18:32:43.459042+00:00 | stats.tennismylife.org | ok | fresh_cache | 53 ms | 987.3 s | no | fresh cache hit |
| 2026-08-08T18:32:43.497754+00:00 | stats.tennismylife.org | ok | fresh_cache | 39 ms | 986.3 s | no | fresh cache hit |
| 2026-08-08T18:32:43.512538+00:00 | stats.tennismylife.org | ok | fresh_cache | 53 ms | 986.3 s | no | fresh cache hit |
| 2026-08-08T18:32:43.514113+00:00 | stats.tennismylife.org | ok | fresh_cache | 139 ms | 987.1 s | no | fresh cache hit |
| 2026-08-08T18:32:43.514291+00:00 | stats.tennismylife.org | ok | fresh_cache | 98 ms | 987.6 s | no | fresh cache hit |
| 2026-08-08T18:32:43.588706+00:00 | stats.tennismylife.org | ok | fresh_cache | 32 ms | 986.5 s | no | fresh cache hit |
| 2026-08-08T18:32:43.609089+00:00 | site.api.espn.com | failed | network | 96 ms | N/A | no | HTTPError |
| 2026-08-08T18:32:43.649832+00:00 | site.api.espn.com | failed | network | 288 ms | N/A | no | HTTPError |
| 2026-08-08T18:32:43.663248+00:00 | site.api.espn.com | failed | network | 131 ms | N/A | no | HTTPError |
| 2026-08-08T18:32:43.692750+00:00 | site.api.espn.com | failed | network | 152 ms | N/A | no | HTTPError |
| 2026-08-08T18:32:43.730112+00:00 | site.api.espn.com | failed | network | 166 ms | N/A | no | HTTPError |
| 2026-08-08T18:32:43.767621+00:00 | site.api.espn.com | failed | network | 237 ms | N/A | no | HTTPError |
| 2026-08-08T18:32:43.805985+00:00 | site.api.espn.com | failed | network | 155 ms | N/A | no | HTTPError |
| 2026-08-08T18:32:43.827728+00:00 | site.api.espn.com | failed | network | 180 ms | N/A | no | HTTPError |
| 2026-08-08T18:33:05.188044+00:00 | api.odds-api.io | ok | network | 237 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:05.443177+00:00 | api.odds-api.io | ok | network | 254 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:05.754941+00:00 | api.odds-api.io | ok | network | 311 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:05.989311+00:00 | api.odds-api.io | ok | network | 233 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:06.219393+00:00 | api.odds-api.io | ok | network | 229 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:06.466013+00:00 | api.odds-api.io | ok | network | 246 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:06.770560+00:00 | api.odds-api.io | ok | network | 303 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:07.019812+00:00 | api.odds-api.io | ok | network | 248 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:07.277660+00:00 | api.odds-api.io | ok | network | 257 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:07.517981+00:00 | api.odds-api.io | ok | network | 239 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:07.792904+00:00 | api.odds-api.io | ok | network | 274 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:08.065961+00:00 | api.odds-api.io | ok | network | 272 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:08.366846+00:00 | api.odds-api.io | ok | network | 300 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:33:08.566124+00:00 | api.odds-api.io | failed | network | 198 ms | N/A | no | HTTP 429 key 2 |
| 2026-08-08T18:33:08.842614+00:00 | api.odds-api.io | ok | network | 276 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:33:16.985551+00:00 | api.telegram.org | ok | network | 551 ms | N/A | no | HTTP 200 |
