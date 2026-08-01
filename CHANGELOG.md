# Changelog

All notable changes to the tennis betting bot are recorded here. This file tracks user-visible, operational, security, data, and documentation changes. Prediction or betting-policy behavior must also be recorded in `MODEL-POLICY-RELEASES.md` with its immutable `MODEL_VERSION`.

The format follows Keep a Changelog categories: Added, Changed, Deprecated, Removed, Fixed, and Security. Dates use `YYYY-MM-DD`. Git commit history remains the detailed implementation record.

## Unreleased

### Added

- Added `run-paper.ps1`, a one-command local paper launcher that bootstraps an isolated environment, enforces tests and coverage, accepts a temporary hidden Odds API key, and supplies an explicit virtual bankroll.
- Added local paper-run usage and safety documentation.
- Added a read-only scheduled weekly health and monthly provider-review workflow with retained evidence artifacts.
- Added recurring operational, model, provider, recovery, and security review procedures and sign-off requirements.
- Added a read-only financial state auditor for hash integrity, running balances, exact bet transaction coverage, orphan detection, and bankroll projection agreement.
- Added a guarded one-time legacy-ledger migration with input/output hashes, atomic output, self-audit, and a recovery manifest.
- Added a read-only completeness audit covering all active rejection rules and their settled, CLV, and Brier sample maturity.
- Versioned paper-bet evidence now retains decision probability, EV, grade, event, tour, surface, authorization time, closing odds, CLV, and Brier score with pre-schema-migration backups.
- Added a read-only paper-readiness audit for frozen-policy duration, meaningful positive CLV, and calibration across every supported tour and surface.
- Added a machine-verifiable frozen production-policy manifest covering the active model version, implementation reference, static risk controls and governing document hashes.
- Added a read-only policy-freeze audit to weekly maintenance so silent policy or documentation drift fails visibly.
- Added persistent cross-run provider reliability evidence and a weekly quarantine audit for sources and tour/surface segments.
- Added a version-pinned, fail-closed reliability policy with explicit enforcement and recovery-review controls.

### Fixed

- Missing Tennis Abstract profiles now produce an insufficient-evidence rejection instead of crashing statistical candidate construction.
- Fixed same-date historical profile sorting that could compare optional booleans, locations, or missing values and crash recent-form enrichment.
- Fixed Odds-API.io HTTP 400 failures caused by sending a shared hard-coded bookmaker list across accounts with different selections; selections are now discovered and applied per rotated key.
- Request-validation failures no longer open the transient provider circuit or masquerade as exhausted API credit.
- Reconstructed the missing historical transaction ledger from the verified €60.00 opening balance and five stake records; the exact hash-linked closing balance is €53.10 with no legacy placeholders.

### Changed

- No unreleased changes.

### Security

- No unreleased changes.

## 2026-08-01 — Production hardening and operations

### Added

- Deterministic data-quality gates, counterfactual policy evaluation, chronological model learning, tour calibration, workload and market-limit challengers, BO3/BO5 and indoor/outdoor segmentation, price dynamics, price freshness, reproducible prediction snapshots, and calibration metrics.
- Verified player status, ranking history, biographical evidence, H2H, serve/return, break, clutch, best-of-five, duration, workload, travel, and surface-transition features.
- Two-stage candidate staging and pre-match revalidation with duplicate-safe lifecycle tracking.
- Paper trading, walk-forward staking simulation, automated rollback, segment suspension, manual kill switch, overdue settlement alerts, and configurable bookmaker retirement rules.
- Hash-linked bankroll transaction ledger, atomic state writes, interrupted-run recovery, schema-migration backups, and content-addressed prediction snapshots.
- Provider retries, circuit breakers, bounded caching, API quota reporting, schema alarms, independent fixture corroboration, identity-confidence auditing, and a manual alias-review queue.
- Source freshness/latency, abnormal decision-count, unresolved identity, settlement, API, model/policy, and dashboard health reporting.
- Optional Telegram and SMTP operational notifications with secret-safe failure reporting.
- Integration tests, a 70% coverage gate, scheduled dependency audit, full-history secret scanning, and immutable GitHub Action pins.
- Authoritative architecture, provider, model, threshold, emergency recovery, and identity/provider operations documentation.

### Changed

- Migrated from direct AI-led selection to deterministic Python probability, EV, safety, portfolio, staking, authorization, and settlement authority.
- Made Groq optional and non-authoritative; deterministic reporting continues when Groq is unavailable.
- Isolated learned behavior behind chronological maturity, holdout, shadow-policy, and rollback gates.
- Updated the static dashboard to expose performance segments, counterfactual rejection results, source/API health, and runtime safety state.

### Removed

- Removed the OpenCode integration so GitHub automation and the standalone Python bot no longer depend on an editor agent.

### Security

- Rotated previously exposed API keys and retained credentials only in GitHub Secrets/local environment variables.
- Added repository-history secret scanning and dependency vulnerability auditing.
- Pinned third-party GitHub Actions to immutable commit SHAs.

## 2026-07-31 — Deterministic modelling and lifecycle

### Added

- Elo/market baseline validation, evidence scoring, audit logs, settlement, surface-aware calibration reporting, opponent-adjusted recent form, serve/return matchup modelling, portfolio controls, and guarded learned weights.
- Pre-match revalidation between daily candidate discovery and live authorization.

### Changed

- Removed the short-lived OpenCode research workflow from the production tennis path.

## 2026-07-29 to 2026-07-30 — Verified automation sources

### Added

- Odds-API.io fixture and moneyline collection with batched requests and five-key quota rotation.
- Groq key rotation while retaining `llama-3.3-70b-versatile`.
- Tennis Abstract profile enrichment with direct, Jina Reader, and cache fallback behavior.
- Verified-odds threshold enforcement and GitHub Actions compatibility fixes.

### Changed

- Replaced Gemini with Groq for optional analysis.

## 2026-07-28 — Initial bot

### Added

- Initial tennis betting workflow, bankroll file, pick report, bet log, dashboard, and same-day duplicate guard.

### Changed

- The initial AI provider moved from Claude-compatible assumptions to Gemini, then Gemini 2.5 Flash, before the later Groq migration.

## Maintenance rules

1. Add every user-visible change under `Unreleased` in the same pull request or commit.
2. If probability, evidence interpretation, calibration, rejection, authorization, staking, portfolio, settlement, or promotion behavior changes, also add a release entry to `MODEL-POLICY-RELEASES.md` and change `MODEL_VERSION`.
3. Do not include routine generated-state commits such as daily reports, settlements, health snapshots, or bankroll projections unless they expose a software defect or operational event worth preserving.
4. At release time, move relevant `Unreleased` entries into a dated section; keep the empty category headings for the next change.
5. Link the implementation commit and evidence in model/policy release notes. Never rewrite an old release entry to describe new behavior.
