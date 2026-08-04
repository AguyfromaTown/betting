# API Quota and Rate-Limit Health

Updated: 2026-08-04T21:23:14.904308+00:00

Keys are represented only by their configured position; no credential values are stored.

| Provider | Key | Requests this run | Latest status | Latest quota headers |
|---|---|---:|---:|---|
| Groq | key-1 | 1 | 200 | x-ratelimit-limit-requests=1000; x-ratelimit-limit-tokens=12000; x-ratelimit-remaining-requests=999; x-ratelimit-remaining-tokens=1187; x-ratelimit-reset-requests=1m26.4s; x-ratelimit-reset-tokens=54.065s |
| Odds-API.io | key-1 | 4 | 200 | not supplied |
| Odds-API.io | key-2 | 71 | 429 | not supplied |
| Odds-API.io | key-3 | 9 | 200 | not supplied |
| Odds-API.io | key-4 | 2 | 200 | not supplied |
| Odds-API.io | key-5 | 2 | 200 | not supplied |
