# Tennis Source Health

Updated: 2026-08-08T18:41:17.144051+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 29 | 25 | 4 | 226.7 ms | 277.0 ms | 312.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 542.0 ms | 542.0 ms | 542.0 ms | 0 | 0 |
| site.api.espn.com | 8 | 0 | 8 | 119.8 ms | 147.0 ms | 147.0 ms | 0 | 0 |
| stats.tennismylife.org | 7 | 7 | 0 | 38.1 ms | 49.0 ms | 49.0 ms | 7 | 0 |
| www.tennisexplorer.com | 7 | 7 | 0 | 486.4 ms | 1675.0 ms | 1675.0 ms | 5 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-08T18:40:44.145233+00:00 | api.odds-api.io | ok | network | 312 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:40:44.374306+00:00 | api.odds-api.io | ok | network | 229 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:40:44.571473+00:00 | api.odds-api.io | ok | network | 197 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:40:44.771600+00:00 | api.odds-api.io | failed | network | 200 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:40:44.966949+00:00 | api.odds-api.io | failed | network | 195 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:40:45.163382+00:00 | api.odds-api.io | failed | network | 195 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:40:45.358956+00:00 | api.odds-api.io | failed | network | 196 ms | N/A | no | HTTP 429 key 2 |
| 2026-08-08T18:40:45.570056+00:00 | api.odds-api.io | ok | network | 211 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:40:45.774780+00:00 | api.odds-api.io | ok | network | 204 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:40:45.980975+00:00 | api.odds-api.io | ok | network | 205 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:40:46.194712+00:00 | api.odds-api.io | ok | network | 213 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:40:46.397971+00:00 | api.odds-api.io | ok | network | 202 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:40:46.607197+00:00 | api.odds-api.io | ok | network | 208 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:40:46.819779+00:00 | api.odds-api.io | ok | network | 211 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:40:46.949496+00:00 | www.tennisexplorer.com | ok | fresh_cache | 28 ms | 1478.7 s | no | fresh cache hit |
| 2026-08-08T18:40:46.950758+00:00 | www.tennisexplorer.com | ok | fresh_cache | 38 ms | 1486.7 s | no | fresh cache hit |
| 2026-08-08T18:40:46.952310+00:00 | www.tennisexplorer.com | ok | fresh_cache | 39 ms | 1482.3 s | no | fresh cache hit |
| 2026-08-08T18:40:47.007622+00:00 | stats.tennismylife.org | ok | fresh_cache | 45 ms | 1470.6 s | no | fresh cache hit |
| 2026-08-08T18:40:47.010483+00:00 | www.tennisexplorer.com | ok | fresh_cache | 53 ms | 1476.1 s | no | fresh cache hit |
| 2026-08-08T18:40:47.011685+00:00 | stats.tennismylife.org | ok | fresh_cache | 49 ms | 1470.6 s | no | fresh cache hit |
| 2026-08-08T18:40:47.013022+00:00 | www.tennisexplorer.com | ok | fresh_cache | 50 ms | 1474.3 s | no | fresh cache hit |
| 2026-08-08T18:40:47.040575+00:00 | stats.tennismylife.org | ok | fresh_cache | 31 ms | 1471.1 s | no | fresh cache hit |
| 2026-08-08T18:40:47.050800+00:00 | stats.tennismylife.org | ok | fresh_cache | 43 ms | 1470.9 s | no | fresh cache hit |
| 2026-08-08T18:40:47.051267+00:00 | stats.tennismylife.org | ok | fresh_cache | 40 ms | 1469.8 s | no | fresh cache hit |
| 2026-08-08T18:40:47.051309+00:00 | stats.tennismylife.org | ok | fresh_cache | 40 ms | 1469.8 s | no | fresh cache hit |
| 2026-08-08T18:40:47.051549+00:00 | site.api.espn.com | failed | network | 103 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:47.059394+00:00 | stats.tennismylife.org | ok | fresh_cache | 19 ms | 1470.0 s | no | fresh cache hit |
| 2026-08-08T18:40:47.061473+00:00 | site.api.espn.com | failed | network | 111 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:47.085313+00:00 | site.api.espn.com | failed | network | 131 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:47.086658+00:00 | site.api.espn.com | failed | network | 144 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:47.087658+00:00 | site.api.espn.com | failed | network | 132 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:47.099290+00:00 | site.api.espn.com | failed | network | 147 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:47.149102+00:00 | site.api.espn.com | failed | network | 91 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:47.161825+00:00 | site.api.espn.com | failed | network | 99 ms | N/A | no | HTTPError |
| 2026-08-08T18:40:48.469182+00:00 | www.tennisexplorer.com | ok | network | 1522 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:40:48.620814+00:00 | www.tennisexplorer.com | ok | network | 1675 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:41:10.540449+00:00 | api.odds-api.io | ok | network | 232 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:10.776075+00:00 | api.odds-api.io | ok | network | 235 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:11.007338+00:00 | api.odds-api.io | ok | network | 230 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:11.238411+00:00 | api.odds-api.io | ok | network | 230 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:11.460331+00:00 | api.odds-api.io | ok | network | 221 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:11.694854+00:00 | api.odds-api.io | ok | network | 233 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:11.921682+00:00 | api.odds-api.io | ok | network | 226 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:12.151962+00:00 | api.odds-api.io | ok | network | 229 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:12.390105+00:00 | api.odds-api.io | ok | network | 237 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:12.615268+00:00 | api.odds-api.io | ok | network | 224 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:12.870046+00:00 | api.odds-api.io | ok | network | 254 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:13.135935+00:00 | api.odds-api.io | ok | network | 265 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:13.393964+00:00 | api.odds-api.io | ok | network | 257 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:13.671636+00:00 | api.odds-api.io | ok | network | 277 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:13.919100+00:00 | api.odds-api.io | ok | network | 246 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:41:17.141680+00:00 | api.telegram.org | ok | network | 542 ms | N/A | no | HTTP 200 |
