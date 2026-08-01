# API Quota and Rate-Limit Health

Updated: 2026-08-01T18:10:51.290025+00:00

Keys are represented only by their configured position; no credential values are stored.

| Provider | Key | Requests this run | Latest status | Latest quota headers |
|---|---|---:|---:|---|
| Groq | key-1 | 1 | 413 | retry-after=15; x-ratelimit-limit-requests=1000; x-ratelimit-limit-tokens=12000; x-ratelimit-remaining-requests=1000; x-ratelimit-remaining-tokens=12000; x-ratelimit-reset-requests=1ms; x-ratelimit-reset-tokens=1ms |
| Odds-API.io | key-1 | 17 | 200 | not supplied |
| Odds-API.io | key-2 | 2 | 200 | not supplied |
| Odds-API.io | key-3 | 2 | 200 | not supplied |
| Odds-API.io | key-4 | 2 | 200 | not supplied |
| Odds-API.io | key-5 | 2 | 200 | not supplied |
