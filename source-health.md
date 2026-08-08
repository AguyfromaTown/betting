# Tennis Source Health

Updated: 2026-08-08T18:16:22.792008+00:00

Fixture status: `not_run`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 29 | 26 | 3 | 263.1 ms | 322.0 ms | 350.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 483.0 ms | 483.0 ms | 483.0 ms | 0 | 0 |
| site.api.espn.com | 3 | 0 | 3 | 124.0 ms | 260.0 ms | 260.0 ms | 0 | 0 |
| stats.tennismylife.org | 7 | 7 | 0 | 1070.3 ms | 1592.0 ms | 1592.0 ms | 0 | 0 |
| www.tennisexplorer.com | 9 | 9 | 0 | 1143.0 ms | 1434.0 ms | 1434.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-08T18:15:36.942950+00:00 | api.odds-api.io | ok | network | 322 ms | N/A | no | loaded 2 selected bookmaker(s) for key 1 |
| 2026-08-08T18:15:37.158717+00:00 | api.odds-api.io | ok | network | 216 ms | N/A | no | loaded 2 selected bookmaker(s) for key 2 |
| 2026-08-08T18:15:37.396092+00:00 | api.odds-api.io | ok | network | 237 ms | N/A | no | loaded 2 selected bookmaker(s) for key 3 |
| 2026-08-08T18:15:37.612323+00:00 | api.odds-api.io | failed | network | 216 ms | N/A | no | no selected bookmakers for key 4 |
| 2026-08-08T18:15:37.841541+00:00 | api.odds-api.io | failed | network | 229 ms | N/A | no | no selected bookmakers for key 5 |
| 2026-08-08T18:15:38.072543+00:00 | api.odds-api.io | failed | network | 230 ms | N/A | no | HTTP 429 key 1 |
| 2026-08-08T18:15:38.289666+00:00 | api.odds-api.io | ok | network | 217 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:38.545493+00:00 | api.odds-api.io | ok | network | 255 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:38.792061+00:00 | api.odds-api.io | ok | network | 246 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:39.041796+00:00 | api.odds-api.io | ok | network | 249 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:39.255212+00:00 | api.odds-api.io | ok | network | 213 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:39.509016+00:00 | api.odds-api.io | ok | network | 253 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:39.736223+00:00 | api.odds-api.io | ok | network | 226 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:39.976143+00:00 | api.odds-api.io | ok | network | 239 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:40.201935+00:00 | api.odds-api.io | ok | network | 225 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:15:40.481031+00:00 | site.api.espn.com | failed | network | 260 ms | N/A | no | HTTPError |
| 2026-08-08T18:15:40.539186+00:00 | site.api.espn.com | failed | network | 58 ms | N/A | no | HTTPError |
| 2026-08-08T18:15:40.593718+00:00 | site.api.espn.com | failed | network | 54 ms | N/A | no | HTTPError |
| 2026-08-08T18:15:41.858909+00:00 | www.tennisexplorer.com | ok | network | 1257 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:15:47.308790+00:00 | www.tennisexplorer.com | ok | network | 1434 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:15:51.865540+00:00 | www.tennisexplorer.com | ok | network | 1414 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:15:56.561408+00:00 | www.tennisexplorer.com | ok | network | 986 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:00.232879+00:00 | www.tennisexplorer.com | ok | network | 1337 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:04.588203+00:00 | www.tennisexplorer.com | ok | network | 1098 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:08.228589+00:00 | www.tennisexplorer.com | ok | network | 991 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:10.850465+00:00 | www.tennisexplorer.com | ok | network | 869 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:12.743370+00:00 | www.tennisexplorer.com | ok | network | 901 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:15.887744+00:00 | stats.tennismylife.org | ok | network | 1164 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:15.888393+00:00 | stats.tennismylife.org | ok | network | 1159 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:15.937988+00:00 | stats.tennismylife.org | ok | network | 1219 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:16.317607+00:00 | stats.tennismylife.org | ok | network | 1592 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:17.059835+00:00 | stats.tennismylife.org | ok | network | 688 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:17.068655+00:00 | stats.tennismylife.org | ok | network | 739 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:17.099755+00:00 | stats.tennismylife.org | ok | network | 931 ms | N/A | no | HTTP 200 |
| 2026-08-08T18:16:17.655272+00:00 | api.odds-api.io | ok | network | 350 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:17.921968+00:00 | api.odds-api.io | ok | network | 266 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:18.198270+00:00 | api.odds-api.io | ok | network | 275 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:18.494344+00:00 | api.odds-api.io | ok | network | 295 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:18.754285+00:00 | api.odds-api.io | ok | network | 259 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:19.043993+00:00 | api.odds-api.io | ok | network | 289 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:19.326411+00:00 | api.odds-api.io | ok | network | 282 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:19.600974+00:00 | api.odds-api.io | ok | network | 274 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:19.876171+00:00 | api.odds-api.io | ok | network | 274 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:20.153649+00:00 | api.odds-api.io | ok | network | 277 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:20.460095+00:00 | api.odds-api.io | ok | network | 306 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:20.776516+00:00 | api.odds-api.io | ok | network | 316 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:21.085202+00:00 | api.odds-api.io | ok | network | 308 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:21.371522+00:00 | api.odds-api.io | ok | network | 285 ms | N/A | no | HTTP 200 key 2 |
| 2026-08-08T18:16:22.790209+00:00 | api.telegram.org | ok | network | 483 ms | N/A | no | HTTP 200 |
