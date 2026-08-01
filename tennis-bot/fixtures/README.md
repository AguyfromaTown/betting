# Historical integration fixtures

These immutable scenarios exercise the tennis bot's lifecycle with historical dates and fixed inputs:

- `historical_lifecycle_win.json` covers validation, authorization, a winning settlement and bankroll credit.
- `historical_lifecycle_loss.json` covers the same path with a losing settlement and no credit.

Player names and markets are intentionally synthetic. These files are regression-test evidence, not betting-performance evidence. Network and AI boundaries are replaced in the test, while the production validation, staging, revalidation, staking, logging, counterfactual, settlement and bankroll functions run unchanged.

Every additional `historical_lifecycle_*.json` file is automatically included by the integration test and must declare its expected lifecycle counts, result, bookmaker, stake and ending bankroll.
