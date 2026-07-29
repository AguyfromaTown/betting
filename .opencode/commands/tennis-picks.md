---
description: Research tennis picks with OpenCode, then validate them through the shared bot
agent: tennis-researcher
subtask: false
---

Run the local OpenCode tennis research workflow for: **$ARGUMENTS**

Interpret the arguments for the user:

- A bare `YYYY-MM-DD` value is the match date.
- The odds range defaults to `1.5-1.6`.
- A bankroll value is optional.

Then complete every step below. Do not stop after preparing the data.

1. Run the Python collector in `opencode-prepare` mode, translating the user's
   arguments to the normal CLI flags. Example:

   `python tennis-bot/tennis_bot.py --mode opencode-prepare --date 2026-07-30 --odds-min 1.5 --odds-max 1.6`

2. Read `tennis-bot/agent-run.json`. It is the authoritative snapshot of
   verified fixtures, bookmaker odds, bankroll, and Tennis Abstract leaderboard
   data. Never change this snapshot.

3. Research both players in every qualifying singles match with web search and
   web fetch. Prioritize official tournament/ATP/WTA/ITF sources, Tennis
   Abstract, and reputable tennis-statistics sources. Verify:

   - tournament surface and indoor/outdoor conditions;
   - recent 5–10 matches and opponent quality;
   - same-surface record and relevant surface Elo;
   - head-to-head record, especially on the same surface;
   - injuries, retirements, fatigue, travel, and schedule;
   - serve/return performance when a reliable source provides it.

   Do not invent unavailable fields. Cite a direct URL beside each material
   factual claim. Exclude doubles from recommendations.

4. Establish probability with transparent arithmetic:

   - Market probability must be de-vigged from both verified moneyline prices.
   - Elo probability is
     `1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))`.
   - Use surface Elo only after verifying the tournament surface; otherwise use
     overall Elo.
   - Start from a conservative blend of 55% Elo probability and 45% de-vigged
     market probability.
   - Context adjustments must total no more than ±5 percentage points and each
     adjustment must have cited evidence.
   - Expected value is exactly
     `(assessed_probability * verified_decimal_odds) - 1`.
   - Never call negative EV a pick, regardless of name recognition or score.

5. Write a concise report to `tennis-bot/agent-report.md` with:

   - `## MARKET OVERVIEW`
   - `## TOP PICKS`
   - `## VALUE PICKS`
   - `## PICKS TO AVOID`
   - `## SOURCES`
   - `## MACHINE READABLE PICKS`

   End with exactly one fenced JSON array. Include only positive-EV candidates:

   ```json
   [
     {
       "player": "Exact snapshot player name",
       "opponent": "Exact snapshot opponent name",
       "score": 7.6,
       "assessed_probability": 0.69
     }
   ]
   ```

   Use `[]` when no player has positive EV. The narrative must agree with this
   array.

6. Run the shared finalizer:

   `python tennis-bot/tennis_bot.py --mode opencode-finalize`

   Do not edit `bets-log.csv`, `bankroll.txt`, or `reports/` yourself. Python
   performs name matching, uses the snapshot odds, recalculates EV, selects the
   grade and stake, prevents duplicate logging, updates bankroll, and saves the
   final report.

7. Report the final Python decision to the user, including accepted bets or the
   reason there were no bets.
