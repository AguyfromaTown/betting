# Tennis Source Health

Updated: 2026-08-08T18:38:46.336313+00:00

Fixture status: `ok`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 76 | 64 | 12 | 236.0 ms | 326.0 ms | 402.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 573.0 ms | 573.0 ms | 573.0 ms | 0 | 0 |
| site.api.espn.com | 8 | 0 | 8 | 205.6 ms | 297.0 ms | 297.0 ms | 0 | 0 |
| stats.tennismylife.org | 59 | 59 | 0 | 609.2 ms | 1593.0 ms | 1682.0 ms | 29 | 0 |
| www.tennisexplorer.com | 7 | 7 | 0 | 30.0 ms | 36.0 ms | 36.0 ms | 7 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-08T18:37:38.277284+00:00 | api.odds-api.io | ok | network | 322 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:37:38.486918+00:00 | api.odds-api.io | ok | network | 210 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:37:38.692859+00:00 | api.odds-api.io | ok | network | 206 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:37:38.914939+00:00 | api.odds-api.io | failed | network | 222 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:37:39.127718+00:00 | api.odds-api.io | failed | network | 213 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:37:39.333174+00:00 | api.odds-api.io | failed | network | 204 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:37:39.529630+00:00 | api.odds-api.io | failed | network | 196 ms | N/A | no | HTTP 429 key 2 |
| 2026-08-08T18:37:39.730939+00:00 | api.odds-api.io | ok | network | 201 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:37:39.929704+00:00 | api.odds-api.io | ok | network | 198 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:37:40.153215+00:00 | api.odds-api.io | ok | network | 222 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:37:40.372304+00:00 | api.odds-api.io | ok | network | 218 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:37:40.575080+00:00 | api.odds-api.io | ok | network | 202 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:37:40.777683+00:00 | api.odds-api.io | ok | network | 201 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:37:40.986969+00:00 | api.odds-api.io | ok | network | 208 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:37:41.092361+00:00 | www.tennisexplorer.com | ok | fresh_cache | 24 ms | 1304.5 s | no | fresh cache hit |
| 2026-08-08T18:37:41.097190+00:00 | www.tennisexplorer.com | ok | fresh_cache | 28 ms | 1296.5 s | no | fresh cache hit |
| 2026-08-08T18:37:41.098698+00:00 | www.tennisexplorer.com | ok | fresh_cache | 30 ms | 1309.2 s | no | fresh cache hit |
| 2026-08-08T18:37:41.104816+00:00 | www.tennisexplorer.com | ok | fresh_cache | 36 ms | 1300.9 s | no | fresh cache hit |
| 2026-08-08T18:37:41.118086+00:00 | www.tennisexplorer.com | ok | fresh_cache | 32 ms | 1292.9 s | no | fresh cache hit |
| 2026-08-08T18:37:41.118634+00:00 | stats.tennismylife.org | ok | fresh_cache | 19 ms | 1285.0 s | no | fresh cache hit |
| 2026-08-08T18:37:41.124127+00:00 | stats.tennismylife.org | ok | fresh_cache | 25 ms | 1284.7 s | no | fresh cache hit |
| 2026-08-08T18:37:41.124535+00:00 | www.tennisexplorer.com | ok | fresh_cache | 33 ms | 1290.2 s | no | fresh cache hit |
| 2026-08-08T18:37:41.124720+00:00 | stats.tennismylife.org | ok | fresh_cache | 28 ms | 1284.8 s | no | fresh cache hit |
| 2026-08-08T18:37:41.131849+00:00 | stats.tennismylife.org | ok | fresh_cache | 8 ms | 1283.9 s | no | fresh cache hit |
| 2026-08-08T18:37:41.132108+00:00 | stats.tennismylife.org | ok | fresh_cache | 23 ms | 1285.2 s | no | fresh cache hit |
| 2026-08-08T18:37:41.140307+00:00 | stats.tennismylife.org | ok | fresh_cache | 16 ms | 1283.9 s | no | fresh cache hit |
| 2026-08-08T18:37:41.174041+00:00 | www.tennisexplorer.com | ok | fresh_cache | 27 ms | 1288.4 s | no | fresh cache hit |
| 2026-08-08T18:37:41.188614+00:00 | stats.tennismylife.org | ok | fresh_cache | 21 ms | 1284.1 s | no | fresh cache hit |
| 2026-08-08T18:37:41.276128+00:00 | site.api.espn.com | failed | network | 146 ms | N/A | no | HTTPError |
| 2026-08-08T18:37:41.334898+00:00 | site.api.espn.com | failed | network | 195 ms | N/A | no | HTTPError |
| 2026-08-08T18:37:41.348169+00:00 | site.api.espn.com | failed | network | 210 ms | N/A | no | HTTPError |
| 2026-08-08T18:37:41.349065+00:00 | site.api.espn.com | failed | network | 210 ms | N/A | no | HTTPError |
| 2026-08-08T18:37:41.371275+00:00 | site.api.espn.com | failed | network | 238 ms | N/A | no | HTTPError |
| 2026-08-08T18:37:41.423286+00:00 | site.api.espn.com | failed | network | 297 ms | N/A | no | HTTPError |
| 2026-08-08T18:37:41.460855+00:00 | site.api.espn.com | failed | network | 156 ms | N/A | no | HTTPError |
| 2026-08-08T18:37:41.528867+00:00 | site.api.espn.com | failed | network | 193 ms | N/A | no | HTTPError |
| 2026-08-08T18:38:04.083514+00:00 | api.odds-api.io | ok | network | 223 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:04.327639+00:00 | api.odds-api.io | ok | network | 243 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:04.551588+00:00 | api.odds-api.io | ok | network | 223 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:04.776423+00:00 | api.odds-api.io | ok | network | 224 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:05.020150+00:00 | api.odds-api.io | ok | network | 243 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:05.281949+00:00 | api.odds-api.io | ok | network | 261 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:05.525492+00:00 | api.odds-api.io | ok | network | 242 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:05.752046+00:00 | api.odds-api.io | ok | network | 226 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:05.977187+00:00 | api.odds-api.io | ok | network | 224 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:06.206782+00:00 | api.odds-api.io | ok | network | 229 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:06.449040+00:00 | api.odds-api.io | ok | network | 241 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:06.740548+00:00 | api.odds-api.io | ok | network | 290 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:07.001400+00:00 | api.odds-api.io | ok | network | 260 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:07.271137+00:00 | api.odds-api.io | ok | network | 269 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:10.058984+00:00 | api.odds-api.io | failed | network | 195 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:38:10.261142+00:00 | api.odds-api.io | failed | network | 202 ms | N/A | no | HTTP 429 key 2 |
| 2026-08-08T18:38:10.472213+00:00 | api.odds-api.io | ok | network | 211 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:10.693734+00:00 | api.odds-api.io | ok | network | 218 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:38:10.907213+00:00 | api.odds-api.io | ok | network | 213 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:38:11.108133+00:00 | api.odds-api.io | ok | network | 201 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:38:11.318649+00:00 | api.odds-api.io | failed | network | 211 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:38:11.526291+00:00 | api.odds-api.io | failed | network | 208 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:38:11.762974+00:00 | api.odds-api.io | ok | network | 236 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:11.980323+00:00 | api.odds-api.io | ok | network | 216 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:12.188655+00:00 | api.odds-api.io | ok | network | 207 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:12.393594+00:00 | api.odds-api.io | ok | network | 204 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:12.615167+00:00 | api.odds-api.io | ok | network | 221 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:12.822861+00:00 | api.odds-api.io | ok | network | 207 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:13.036011+00:00 | api.odds-api.io | ok | network | 212 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:13.242997+00:00 | api.odds-api.io | ok | network | 206 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:13.472456+00:00 | api.odds-api.io | ok | network | 228 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:13.780970+00:00 | api.odds-api.io | ok | network | 307 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:14.020459+00:00 | api.odds-api.io | ok | network | 238 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:14.250171+00:00 | api.odds-api.io | ok | network | 229 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:14.509259+00:00 | api.odds-api.io | ok | network | 258 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:14.788241+00:00 | api.odds-api.io | ok | network | 278 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:15.016794+00:00 | api.odds-api.io | ok | network | 227 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:15.263523+00:00 | api.odds-api.io | ok | network | 245 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:15.304120+00:00 | stats.tennismylife.org | ok | fresh_cache | 36 ms | 42633.4 s | no | fresh cache hit |
| 2026-08-08T18:38:15.308382+00:00 | stats.tennismylife.org | ok | fresh_cache | 19 ms | 42633.3 s | no | fresh cache hit |
| 2026-08-08T18:38:15.312513+00:00 | stats.tennismylife.org | ok | fresh_cache | 8 ms | 42633.0 s | no | fresh cache hit |
| 2026-08-08T18:38:15.315759+00:00 | stats.tennismylife.org | ok | fresh_cache | 7 ms | 42632.9 s | no | fresh cache hit |
| 2026-08-08T18:38:15.319658+00:00 | stats.tennismylife.org | ok | fresh_cache | 7 ms | 1319.0 s | no | fresh cache hit |
| 2026-08-08T18:38:15.323423+00:00 | stats.tennismylife.org | ok | fresh_cache | 4 ms | 1319.2 s | no | fresh cache hit |
| 2026-08-08T18:38:15.327143+00:00 | stats.tennismylife.org | ok | fresh_cache | 11 ms | 1318.9 s | no | fresh cache hit |
| 2026-08-08T18:38:15.331000+00:00 | stats.tennismylife.org | ok | fresh_cache | 4 ms | 1318.1 s | no | fresh cache hit |
| 2026-08-08T18:38:15.331135+00:00 | stats.tennismylife.org | ok | fresh_cache | 8 ms | 1319.4 s | no | fresh cache hit |
| 2026-08-08T18:38:15.337903+00:00 | stats.tennismylife.org | ok | fresh_cache | 7 ms | 1318.3 s | no | fresh cache hit |
| 2026-08-08T18:38:15.337993+00:00 | stats.tennismylife.org | ok | fresh_cache | 7 ms | 1318.1 s | no | fresh cache hit |
| 2026-08-08T18:38:16.490851+00:00 | stats.tennismylife.org | ok | network | 1214 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:16.644670+00:00 | stats.tennismylife.org | ok | network | 1354 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:16.648164+00:00 | stats.tennismylife.org | ok | network | 1349 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:16.649165+00:00 | stats.tennismylife.org | ok | network | 1361 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:19.271993+00:00 | stats.tennismylife.org | ok | network | 1206 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:19.430791+00:00 | stats.tennismylife.org | ok | network | 1363 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:19.442668+00:00 | stats.tennismylife.org | ok | network | 1377 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:19.746136+00:00 | stats.tennismylife.org | ok | network | 1682 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:20.398601+00:00 | stats.tennismylife.org | ok | network | 1126 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:20.446298+00:00 | stats.tennismylife.org | ok | network | 992 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:20.885148+00:00 | stats.tennismylife.org | ok | network | 1132 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:20.892444+00:00 | stats.tennismylife.org | ok | network | 1460 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:20.921582+00:00 | stats.tennismylife.org | ok | network | 517 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:20.953464+00:00 | stats.tennismylife.org | ok | network | 506 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:21.702141+00:00 | stats.tennismylife.org | ok | network | 816 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:33.669718+00:00 | api.odds-api.io | failed | network | 195 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:38:33.879998+00:00 | api.odds-api.io | failed | network | 210 ms | N/A | no | HTTP 429 key 2 |
| 2026-08-08T18:38:34.164674+00:00 | api.odds-api.io | ok | network | 284 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:34.368119+00:00 | api.odds-api.io | ok | network | 200 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:38:34.563028+00:00 | api.odds-api.io | ok | network | 195 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:38:34.773057+00:00 | api.odds-api.io | ok | network | 210 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:38:34.987463+00:00 | api.odds-api.io | failed | network | 214 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:38:35.180537+00:00 | api.odds-api.io | failed | network | 193 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:38:35.420776+00:00 | api.odds-api.io | ok | network | 239 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:35.650218+00:00 | api.odds-api.io | ok | network | 228 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:35.887763+00:00 | api.odds-api.io | ok | network | 236 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:36.127834+00:00 | api.odds-api.io | ok | network | 239 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:36.374592+00:00 | api.odds-api.io | ok | network | 246 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:36.621112+00:00 | api.odds-api.io | ok | network | 245 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:36.851151+00:00 | api.odds-api.io | ok | network | 229 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:37.052048+00:00 | api.odds-api.io | ok | network | 200 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:37.379003+00:00 | api.odds-api.io | ok | network | 326 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:37.680772+00:00 | api.odds-api.io | ok | network | 300 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:38.083703+00:00 | api.odds-api.io | ok | network | 402 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:38.439743+00:00 | api.odds-api.io | ok | network | 355 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:38.737256+00:00 | api.odds-api.io | ok | network | 296 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:39.038295+00:00 | api.odds-api.io | ok | network | 300 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:39.383856+00:00 | api.odds-api.io | ok | network | 344 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:39.633502+00:00 | api.odds-api.io | ok | network | 248 ms | N/A | no | HTTP 200 key 3 |
| 2026-08-08T18:38:39.652066+00:00 | stats.tennismylife.org | ok | fresh_cache | 15 ms | 23.1 s | no | fresh cache hit |
| 2026-08-08T18:38:39.655059+00:00 | stats.tennismylife.org | ok | fresh_cache | 18 ms | 22.9 s | no | fresh cache hit |
| 2026-08-08T18:38:39.662594+00:00 | stats.tennismylife.org | ok | fresh_cache | 23 ms | 23.0 s | no | fresh cache hit |
| 2026-08-08T18:38:39.669987+00:00 | stats.tennismylife.org | ok | fresh_cache | 30 ms | 23.0 s | no | fresh cache hit |
| 2026-08-08T18:38:39.673026+00:00 | stats.tennismylife.org | ok | fresh_cache | 10 ms | 1343.3 s | no | fresh cache hit |
| 2026-08-08T18:38:39.676082+00:00 | stats.tennismylife.org | ok | fresh_cache | 3 ms | 1343.5 s | no | fresh cache hit |
| 2026-08-08T18:38:39.679159+00:00 | stats.tennismylife.org | ok | fresh_cache | 9 ms | 1343.3 s | no | fresh cache hit |
| 2026-08-08T18:38:39.681807+00:00 | stats.tennismylife.org | ok | fresh_cache | 3 ms | 1342.5 s | no | fresh cache hit |
| 2026-08-08T18:38:39.684455+00:00 | stats.tennismylife.org | ok | fresh_cache | 8 ms | 1343.8 s | no | fresh cache hit |
| 2026-08-08T18:38:39.684672+00:00 | stats.tennismylife.org | ok | fresh_cache | 3 ms | 1342.5 s | no | fresh cache hit |
| 2026-08-08T18:38:39.687198+00:00 | stats.tennismylife.org | ok | fresh_cache | 3 ms | 1342.6 s | no | fresh cache hit |
| 2026-08-08T18:38:40.466642+00:00 | stats.tennismylife.org | ok | network | 808 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:40.926068+00:00 | stats.tennismylife.org | ok | network | 1262 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:41.091515+00:00 | stats.tennismylife.org | ok | network | 1429 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:41.240043+00:00 | stats.tennismylife.org | ok | network | 1576 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:43.218061+00:00 | stats.tennismylife.org | ok | network | 1176 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:43.356565+00:00 | stats.tennismylife.org | ok | network | 1312 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:43.378702+00:00 | stats.tennismylife.org | ok | network | 1336 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:43.682887+00:00 | stats.tennismylife.org | ok | network | 1642 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:44.599953+00:00 | stats.tennismylife.org | ok | network | 910 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:44.603036+00:00 | stats.tennismylife.org | ok | network | 1218 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:44.765150+00:00 | stats.tennismylife.org | ok | network | 1546 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:44.950830+00:00 | stats.tennismylife.org | ok | network | 1593 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:45.413887+00:00 | stats.tennismylife.org | ok | network | 642 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:45.428499+00:00 | stats.tennismylife.org | ok | network | 827 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:45.430129+00:00 | stats.tennismylife.org | ok | network | 826 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:38:46.334002+00:00 | api.telegram.org | ok | network | 573 ms | N/A | no | HTTP 200 |
