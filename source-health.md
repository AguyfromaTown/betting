# Tennis Source Health

Updated: 2026-08-05T18:04:56.028654+00:00

Fixture status: `provider_failure`

| Source | Events | Success | Failure | Avg latency | p95 latency | Max latency | Cache | Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| api.odds-api.io | 14 | 0 | 14 | 225.9 ms | 290.0 ms | 290.0 ms | 0 | 0 |
| api.telegram.org | 1 | 1 | 0 | 588.0 ms | 588.0 ms | 588.0 ms | 0 | 0 |
| r.jina.ai | 2 | 2 | 0 | 1343.0 ms | 2043.0 ms | 2043.0 ms | 0 | 0 |
| site.api.espn.com | 2 | 0 | 2 | 104.0 ms | 169.0 ms | 169.0 ms | 0 | 0 |
| stats.tennismylife.org | 11 | 11 | 0 | 1244.5 ms | 1925.0 ms | 1925.0 ms | 0 | 0 |
| tennisabstract.com | 2 | 0 | 2 | 59.5 ms | 69.0 ms | 69.0 ms | 0 | 0 |

## Request events

| Time | Source | Status | Mode | Latency | Cache age | Stale | Detail |
|---|---|---|---|---:|---:|---|---|
| 2026-08-05T18:04:40.568979+00:00 | api.odds-api.io | failed | network | 290 ms | N/A | no | selected bookmakers HTTPError |
| 2026-08-05T18:04:40.771132+00:00 | api.odds-api.io | failed | network | 202 ms | N/A | no | selected bookmakers HTTPError |
| 2026-08-05T18:04:40.998154+00:00 | api.odds-api.io | failed | network | 227 ms | N/A | no | selected bookmakers HTTPError |
| 2026-08-05T18:04:41.212874+00:00 | api.odds-api.io | failed | network | 215 ms | N/A | no | selected bookmakers HTTPError |
| 2026-08-05T18:04:41.409872+00:00 | api.odds-api.io | failed | network | 197 ms | N/A | no | selected bookmakers HTTPError |
| 2026-08-05T18:04:41.641192+00:00 | api.odds-api.io | failed | network | 230 ms | N/A | no | HTTP 502 retry 1 |
| 2026-08-05T18:04:42.341611+00:00 | api.odds-api.io | failed | network | 200 ms | N/A | no | HTTP 502 retry 2 |
| 2026-08-05T18:04:43.581097+00:00 | api.odds-api.io | failed | network | 239 ms | N/A | no | HTTPError |
| 2026-08-05T18:04:43.787324+00:00 | api.odds-api.io | failed | network | 205 ms | N/A | no | HTTP 502 retry 1 |
| 2026-08-05T18:04:44.548466+00:00 | api.odds-api.io | failed | network | 261 ms | N/A | no | HTTP 502 retry 2 |
| 2026-08-05T18:04:45.770052+00:00 | api.odds-api.io | failed | network | 221 ms | N/A | no | HTTPError |
| 2026-08-05T18:04:45.981289+00:00 | api.odds-api.io | failed | network | 210 ms | N/A | no | HTTP 502 retry 1 |
| 2026-08-05T18:04:46.747863+00:00 | api.odds-api.io | failed | network | 266 ms | N/A | no | HTTP 502 retry 2 |
| 2026-08-05T18:04:47.947041+00:00 | api.odds-api.io | failed | network | 199 ms | N/A | no | HTTPError |
| 2026-08-05T18:04:48.168933+00:00 | site.api.espn.com | failed | network | 169 ms | N/A | no | HTTPError |
| 2026-08-05T18:04:48.208651+00:00 | site.api.espn.com | failed | network | 39 ms | N/A | no | HTTPError |
| 2026-08-05T18:04:48.286858+00:00 | tennisabstract.com | failed | network | 69 ms | N/A | no | HTTPError |
| 2026-08-05T18:04:48.942637+00:00 | r.jina.ai | ok | network | 643 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:49.042119+00:00 | tennisabstract.com | failed | network | 50 ms | N/A | no | HTTPError |
| 2026-08-05T18:04:51.098809+00:00 | r.jina.ai | ok | network | 2043 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:52.465987+00:00 | stats.tennismylife.org | ok | network | 1337 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:52.647156+00:00 | stats.tennismylife.org | ok | network | 1516 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:52.651526+00:00 | stats.tennismylife.org | ok | network | 1524 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:53.055086+00:00 | stats.tennismylife.org | ok | network | 1925 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:53.641260+00:00 | stats.tennismylife.org | ok | network | 978 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:53.765526+00:00 | stats.tennismylife.org | ok | network | 1298 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:54.130882+00:00 | stats.tennismylife.org | ok | network | 1482 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:54.165544+00:00 | stats.tennismylife.org | ok | network | 523 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:54.209420+00:00 | stats.tennismylife.org | ok | network | 1142 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:54.654525+00:00 | stats.tennismylife.org | ok | network | 868 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:55.244240+00:00 | stats.tennismylife.org | ok | network | 1096 ms | N/A | no | HTTP 200 |
| 2026-08-05T18:04:56.026618+00:00 | api.telegram.org | ok | network | 588 ms | N/A | no | HTTP 200 |
