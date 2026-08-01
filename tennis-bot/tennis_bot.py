"""
Tennis Betting Bot — Automated daily picks pipeline.
Runs the 3-stage analysis via Groq API and logs results.
Designed for GitHub Actions execution.
"""

import argparse
import base64
import csv
import difflib
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
import time
import unicodedata
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from bs4 import BeautifulSoup
from dateutil import tz as dateutil_tz

REPO_ROOT = Path(__file__).resolve().parent.parent
BANKROLL_FILE = REPO_ROOT / "bankroll.txt"
LOG_FILE = REPO_ROOT / "bets-log.csv"
PAPER_LOG_FILE = REPO_ROOT / "paper-bets-log.csv"
AUDIT_FILE = REPO_ROOT / "predictions-log.csv"
PENDING_FILE = REPO_ROOT / "pending-bets.csv"
POLICY_FILE = REPO_ROOT / "counterfactual-log.csv"
TRANSACTION_FILE = REPO_ROOT / "bankroll-transactions.csv"
PERFORMANCE_FILE = REPO_ROOT / "performance-summary.md"
SETTLEMENT_ALERT_FILE = REPO_ROOT / "settlement-alerts.md"
API_QUOTA_FILE = REPO_ROOT / "api-quota.md"
SCHEMA_ALERT_FILE = REPO_ROOT / "provider-schema-alerts.md"
MANUAL_KILL_SWITCH_FILE = REPO_ROOT / "kill-switch.json"
RISK_CONFIG_FILE = REPO_ROOT / "risk-config.json"
EXTERNAL_CACHE_FILE = REPO_ROOT / "external-cache.json"
PREDICTION_SNAPSHOTS_DIR = REPO_ROOT / "prediction-snapshots"
BACKTEST_FILE = REPO_ROOT / "backtest-summary.md"
PLAYER_ALIASES_FILE = REPO_ROOT / "player-aliases.csv"
ALIAS_REVIEW_FILE = REPO_ROOT / "player-alias-review.csv"
PLAYER_STATUS_FILE = REPO_ROOT / "verified-player-status.csv"
TOURNAMENT_LOCATIONS_FILE = REPO_ROOT / "verified-tournament-locations.csv"
RUN_STATE_FILE = REPO_ROOT / "run-state.json"
ROLLBACK_STATE_FILE = REPO_ROOT / "model-policy-state.json"
BACKUPS_DIR = REPO_ROOT / "state-backups"
TRANSACTION_HEADERS = ["ID", "TIMESTAMP", "TYPE", "REFERENCE", "AMOUNT", "BALANCE", "PREVIOUS_HASH", "HASH"]
REPORTS_DIR = REPO_ROOT / "reports"
REQUEST_TIMEOUT = 30
MAX_TRANSIENT_RETRIES = 2
RETRY_BASE_SECONDS = 0.5
MAX_RETRY_DELAY_SECONDS = 8.0
DEFAULT_UNRESOLVED_ALERT_HOURS = 48
TRANSIENT_HTTP_STATUSES = {408, 425, 500, 502, 503, 504}
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECONDS = 300
MAX_COMPLETION_TOKENS = 2048
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_AI_MATCHES = 20
MAX_DAILY_EXPOSURE = 0.08
MAX_DAILY_BETS = 4
MAX_MARKET_OVERROUND = 1.12
MAX_ELO_MARKET_GAP = 0.15
MIN_CALIBRATION_SAMPLE = 100
MIN_SEGMENT_SAMPLE = 30
MIN_WEIGHT_TRAINING_SAMPLE = 200
MIN_WORKLOAD_TRAINING_SAMPLE = 200
MIN_WORKLOAD_TRIGGER_SAMPLE = 30
KELLY_FRACTION = 0.25
MIN_STAKE_RATE = 0.005
MAX_PRICE_MOVEMENT = 0.10
MAX_BOOKMAKER_DISPERSION = 0.12
MAX_BETS_PER_TOURNAMENT = 2
DEFAULT_TOUR_EXPOSURE_CAPS = {"ATP": .08, "WTA": .08, "Challenger": .05, "ITF": .03, "Unknown": .03}
OFFICIAL_STATUS_DOMAINS = {
    "atptour.com", "wtatennis.com", "itftennis.com", "ausopen.com",
    "rolandgarros.com", "wimbledon.com", "usopen.org",
}
BLOCKING_PHYSICAL_STATUSES = {"questionable", "injured", "withdrawn", "unavailable", "suspended"}
MAX_CACHE_ENTRY_BYTES = 2_000_000
MAX_CACHE_ENTRIES = 20
MODEL_VERSION = "tennis-2026.08-environment-models-v1"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}
SOURCE_HEALTH = []
API_QUOTA = []
SCHEMA_ALERTS = []
LAST_FIXTURE_STATUS = "not_run"
DIAGNOSTIC_MODE = False
PAPER_TRADING_MODE = False
RUN_STATE_ACTIVE = False
CIRCUIT_BREAKERS = {}


# ─── Helpers ────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def record_source_health(source: str, ok: bool, detail: str, started: float):
    SOURCE_HEALTH.append({"source": source, "ok": ok, "detail": detail,
                          "latency_ms": round((time.monotonic() - started) * 1000),
                          "timestamp": datetime.now(timezone.utc).isoformat()})


def record_api_quota(provider: str, response, key_label: str):
    """Capture safe rate-limit metadata and request counts without credentials."""
    allowed = {
        "retry-after", "x-ratelimit-limit-requests", "x-ratelimit-limit-tokens",
        "x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens",
        "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens",
        "x-requests-limit", "x-requests-used", "x-requests-remaining",
        "x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset",
    }
    metrics = {}
    try:
        header_items = list(response.headers.items())
    except (AttributeError, TypeError):
        header_items = []
    for name, value in header_items:
        normalized = str(name).casefold()
        if normalized in allowed:
            metrics[normalized] = str(value)[:100]
    status = response.status_code if isinstance(getattr(response, "status_code", None), int) else "unknown"
    API_QUOTA.append({"provider": provider, "key": key_label, "status": status,
                      "timestamp": datetime.now(timezone.utc).isoformat(), "metrics": metrics})


def save_api_quota_report():
    grouped = {}
    for item in API_QUOTA:
        grouped.setdefault((item["provider"], item["key"]), []).append(item)
    lines = ["# API Quota and Rate-Limit Health", "", f"Updated: {datetime.now(timezone.utc).isoformat()}", "",
             "Keys are represented only by their configured position; no credential values are stored.", "",
             "| Provider | Key | Requests this run | Latest status | Latest quota headers |",
             "|---|---|---:|---:|---|"]
    for (provider, key), items in sorted(grouped.items()):
        latest = items[-1]
        metrics = "; ".join(f"{name}={value}" for name, value in sorted(latest["metrics"].items())) or "not supplied"
        lines.append(f"| {provider} | {key} | {len(items)} | {latest['status']} | {metrics} |")
    if not grouped:
        lines.append("| No metered API requests | — | 0 | — | — |")
    atomic_write_text(API_QUOTA_FILE, "\n".join(lines) + "\n")


def record_schema_alert(provider: str, endpoint: str, detail: str):
    alert = {"provider": provider, "endpoint": endpoint, "detail": detail,
             "timestamp": datetime.now(timezone.utc).isoformat()}
    if not any(item["provider"] == provider and item["endpoint"] == endpoint and item["detail"] == detail for item in SCHEMA_ALERTS):
        SCHEMA_ALERTS.append(alert)
        log(f"WARNING: {provider} schema alert at {endpoint}: {detail}")


def normalize_provider_collection(payload, provider: str, endpoint: str) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("events", "data"):
            if key in payload:
                if isinstance(payload[key], list):
                    return payload[key]
                record_schema_alert(provider, endpoint, f"field '{key}' changed from list to {type(payload[key]).__name__}")
                return []
        record_schema_alert(provider, endpoint, "missing events/data collection")
        return []
    record_schema_alert(provider, endpoint, f"top-level payload changed to {type(payload).__name__}")
    return []


def validate_odds_event_schema(odds_event: dict) -> bool:
    bookmakers = odds_event.get("bookmakers")
    event_id = odds_event.get("id")
    if event_id is None or str(event_id).strip() == "" or not isinstance(bookmakers, dict):
        record_schema_alert("Odds-API.io", "/v3/odds/multi", "odds event missing id or bookmakers object")
        return False
    for bookmaker, markets in bookmakers.items():
        if not isinstance(markets, list):
            record_schema_alert("Odds-API.io", "/v3/odds/multi", f"bookmaker '{bookmaker}' markets changed to {type(markets).__name__}")
            return False
        for market in markets:
            if not isinstance(market, dict):
                record_schema_alert("Odds-API.io", "/v3/odds/multi", f"bookmaker '{bookmaker}' market changed to {type(market).__name__}")
                return False
            if "odds" in market and not isinstance(market["odds"], list):
                record_schema_alert("Odds-API.io", "/v3/odds/multi", f"bookmaker '{bookmaker}' odds changed to {type(market['odds']).__name__}")
                return False
            if any(not isinstance(price, dict) for price in market.get("odds", [])):
                record_schema_alert("Odds-API.io", "/v3/odds/multi", f"bookmaker '{bookmaker}' price item is not an object")
                return False
    return True


def save_schema_alert_report():
    lines = ["# Provider Schema Health", "", f"Updated: {datetime.now(timezone.utc).isoformat()}", ""]
    if SCHEMA_ALERTS:
        lines.extend(["## SCHEMA CHANGE ALERTS", "", "| Provider | Endpoint | Detail | Time |", "|---|---|---|---|"])
        for item in SCHEMA_ALERTS:
            lines.append(f"| {item['provider']} | {item['endpoint']} | {item['detail']} | {item['timestamp']} |")
    else:
        lines.extend(["## OK", "", "No provider schema changes were detected in this run."])
    atomic_write_text(SCHEMA_ALERT_FILE, "\n".join(lines) + "\n")


def transient_retry_delay(attempt: int, response=None) -> float:
    """Return a bounded exponential delay, honoring numeric Retry-After hints."""
    delay = RETRY_BASE_SECONDS * (2 ** attempt)
    retry_after = getattr(response, "headers", {}).get("Retry-After") if response is not None else None
    try:
        if retry_after is not None:
            delay = max(delay, float(retry_after))
    except (TypeError, ValueError):
        pass
    return min(delay, MAX_RETRY_DELAY_SECONDS)


def wait_before_retry(provider: str, attempt: int, response=None):
    delay = transient_retry_delay(attempt, response)
    log(f"  {provider} transient failure; retrying in {delay:.1f}s ({attempt + 1}/{MAX_TRANSIENT_RETRIES})")
    time.sleep(delay)


def provider_circuit_open(provider: str, now: float | None = None) -> bool:
    """Return whether a provider is temporarily isolated after repeated failures."""
    current = time.monotonic() if now is None else now
    state = CIRCUIT_BREAKERS.get(provider, {})
    opened_until = float(state.get("opened_until", 0))
    if opened_until and current >= opened_until:
        CIRCUIT_BREAKERS.pop(provider, None)
        return False
    return opened_until > current


def record_provider_success(provider: str):
    CIRCUIT_BREAKERS.pop(provider, None)


def record_provider_failure(provider: str, detail: str, now: float | None = None):
    current = time.monotonic() if now is None else now
    state = CIRCUIT_BREAKERS.setdefault(provider, {"failures": 0, "opened_until": 0, "last_error": ""})
    state["failures"] += 1
    state["last_error"] = detail
    if state["failures"] >= CIRCUIT_FAILURE_THRESHOLD:
        state["opened_until"] = current + CIRCUIT_COOLDOWN_SECONDS
        log(f"  {provider} circuit opened for {CIRCUIT_COOLDOWN_SECONDS}s after {state['failures']} failures")


def allow_provider_request(provider: str) -> bool:
    if not provider_circuit_open(provider):
        return True
    state = CIRCUIT_BREAKERS.get(provider, {})
    log(f"  {provider} circuit is open; skipping request ({state.get('last_error', 'provider failure')})")
    return False


def external_cache_key(namespace: str, url: str) -> str:
    return hashlib.sha256(f"{namespace}|{url}".encode("utf-8")).hexdigest()


def load_external_cache() -> dict:
    if not EXTERNAL_CACHE_FILE.exists():
        return {"version": 1, "entries": {}}
    try:
        payload = json.loads(EXTERNAL_CACHE_FILE.read_text(encoding="utf-8"))
        if payload.get("version") != 1 or not isinstance(payload.get("entries"), dict):
            raise ValueError("unsupported cache schema")
        return payload
    except (OSError, ValueError, TypeError):
        return {"version": 1, "entries": {}}


def get_cached_response(namespace: str, url: str, max_age_seconds: int) -> str | None:
    entry = load_external_cache()["entries"].get(external_cache_key(namespace, url))
    if not entry or time.time() - float(entry.get("cached_at", 0)) > max_age_seconds:
        return None
    try:
        return zlib.decompress(base64.b64decode(entry["content"])).decode("utf-8")
    except (KeyError, TypeError, ValueError, zlib.error, UnicodeDecodeError):
        return None


def cache_external_response(namespace: str, url: str, content: str):
    raw = content.encode("utf-8")
    if not raw or len(raw) > MAX_CACHE_ENTRY_BYTES:
        return
    payload = load_external_cache()
    entries = payload["entries"]
    key = external_cache_key(namespace, url)
    entries[key] = {"namespace": namespace, "url": url, "cached_at": time.time(),
                    "content": base64.b64encode(zlib.compress(raw, 9)).decode("ascii")}
    if len(entries) > MAX_CACHE_ENTRIES:
        oldest = sorted(entries, key=lambda item: float(entries[item].get("cached_at", 0)))
        for stale_key in oldest[:len(entries) - MAX_CACHE_ENTRIES]:
            entries.pop(stale_key, None)
    atomic_write_text(EXTERNAL_CACHE_FILE, json.dumps(payload, separators=(",", ":")) + "\n")


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8"):
    """Replace a text state file atomically so interrupted runs keep the old version."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as handle:
            handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except OSError: pass
        raise


def atomic_write_bytes(path: Path, content: bytes):
    """Replace a binary file atomically, preserving the exact supplied bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except OSError: pass
        raise


def atomic_write_csv(path: Path, headers: list[str], rows: list, dict_rows: bool = True):
    """Write a complete CSV beside the destination and atomically replace it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            if dict_rows:
                writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
                writer.writeheader(); writer.writerows(rows)
            else:
                writer = csv.writer(handle); writer.writerow(headers); writer.writerows(rows)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except OSError: pass
        raise


def read_csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    if not path.exists() or not path.stat().st_size:
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def json_safe(value):
    """Convert decision inputs to deterministic strict-JSON values without dropping fields."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (datetime, Path)):
        return str(value)
    return str(value)


def snapshot_bytes(payload: dict) -> bytes:
    return json.dumps(json_safe(payload), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_snapshot_blob(directory: Path, prefix: str, payload: dict) -> tuple[Path, str]:
    """Write a content-addressed immutable gzip blob and return its path and payload hash."""
    raw = snapshot_bytes(payload)
    digest = hashlib.sha256(raw).hexdigest()
    path = directory / f"{prefix}-{digest}.json.gz"
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    if path.exists():
        existing = gzip.decompress(path.read_bytes())
        if hashlib.sha256(existing).hexdigest() != digest:
            raise ValueError(f"snapshot hash collision or corruption: {path}")
    else:
        atomic_write_bytes(path, compressed)
    return path, digest


def cached_source_artifacts(value) -> list[dict]:
    """Capture cached raw responses referenced by the enriched match without copying unrelated cache entries."""
    urls = set()
    def visit(item):
        if isinstance(item, dict):
            for nested in item.values(): visit(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item: visit(nested)
        elif isinstance(item, str) and item.startswith(("http://", "https://")):
            urls.add(item)
    visit(value)
    entries = load_external_cache().get("entries", {})
    artifacts = []
    for url in sorted(urls):
        for namespace in ("direct", "reader"):
            entry = entries.get(external_cache_key(namespace, url))
            if entry:
                artifacts.append(json_safe(entry))
    return artifacts


def save_prediction_snapshot(date_str: str, match: dict, player: str, baseline: dict,
                             training_history: list[dict]) -> dict:
    """Persist all decision-time inputs and shared training evidence needed for an exact replay."""
    directory = PREDICTION_SNAPSHOTS_DIR / date_str
    training_payload = {"schema_version": 1, "kind": "resolved_training_history",
                        "decision_date": date_str, "rows": training_history}
    training_path, training_hash = write_snapshot_blob(directory, "training", training_payload)
    configuration = {
        "model_version": MODEL_VERSION, "groq_model": GROQ_MODEL,
        "minimum_calibration_sample": MIN_CALIBRATION_SAMPLE,
        "minimum_weight_training_sample": MIN_WEIGHT_TRAINING_SAMPLE,
        "minimum_workload_training_sample": MIN_WORKLOAD_TRAINING_SAMPLE,
        "minimum_workload_trigger_sample": MIN_WORKLOAD_TRIGGER_SAMPLE,
        "maximum_market_overround": MAX_MARKET_OVERROUND,
        "maximum_elo_market_gap": MAX_ELO_MARKET_GAP,
        "maximum_bookmaker_dispersion": MAX_BOOKMAKER_DISPERSION,
        "maximum_price_movement": MAX_PRICE_MOVEMENT,
    }
    payload = {
        "schema_version": 1, "kind": "tennis_prediction", "decision_date": date_str,
        "model_version": MODEL_VERSION, "event_id": match.get("event_id", ""), "player": player,
        "configuration": configuration, "match_input": match, "calculated_baseline": baseline,
        "cached_source_artifacts": cached_source_artifacts(match),
        "training_snapshot": {"path": training_path.name, "sha256": training_hash},
    }
    safe_label = re.sub(r"[^a-z0-9]+", "-", f"{match.get('event_id', 'event')}-{player}".casefold()).strip("-")[:80] or "prediction"
    path, digest = write_snapshot_blob(directory, safe_label, payload)
    display_path = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
    return {"path": display_path.replace("\\", "/"), "sha256": digest, "schema_version": 1}


def verify_prediction_snapshot(path: Path) -> dict:
    """Verify a prediction blob and its referenced training-history blob before replay."""
    raw = gzip.decompress(path.read_bytes())
    payload = json.loads(raw.decode("utf-8"))
    digest = hashlib.sha256(snapshot_bytes(payload)).hexdigest()
    if not path.name.endswith(f"-{digest}.json.gz"):
        raise ValueError("prediction snapshot hash mismatch")
    training = payload.get("training_snapshot") or {}
    training_path = path.parent / str(training.get("path") or "")
    training_raw = gzip.decompress(training_path.read_bytes())
    if hashlib.sha256(training_raw).hexdigest() != training.get("sha256"):
        raise ValueError("training snapshot hash mismatch")
    return {"sha256": digest, "payload": payload,
            "training": json.loads(training_raw.decode("utf-8"))}


def backup_state_for_migration(path: Path, old_headers: list[str], new_headers: list[str]) -> Path:
    """Create an exact, versioned backup before replacing a state-file schema."""
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()[:12]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = BACKUPS_DIR / path.stem
    backup_path = backup_dir / f"{path.name}.{timestamp}.{digest}.bak"
    atomic_write_bytes(backup_path, content)
    metadata = {
        "source": path.name,
        "backup": backup_path.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "old_headers": old_headers,
        "new_headers": new_headers,
    }
    atomic_write_text(backup_path.with_suffix(backup_path.suffix + ".json"), json.dumps(metadata, indent=2) + "\n")
    log(f"Backed up {path.name} before schema migration: {backup_path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else backup_path}")
    return backup_path


def save_source_health():
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "fixture_status": LAST_FIXTURE_STATUS,
               "requests": SOURCE_HEALTH, "failures": sum(not item["ok"] for item in SOURCE_HEALTH),
               "api_quota": API_QUOTA, "schema_alerts": SCHEMA_ALERTS}
    atomic_write_text(REPO_ROOT / "source-health.json", json.dumps(payload, indent=2) + "\n")
    save_api_quota_report()
    save_schema_alert_report()


def load_run_state() -> dict:
    if not RUN_STATE_FILE.exists():
        return {}
    try:
        value = json.loads(RUN_STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def begin_run_state(date_str: str, mode: str) -> dict:
    global RUN_STATE_ACTIVE
    previous = load_run_state()
    recoverable = (
        previous.get("status") in {"running", "interrupted"}
        and previous.get("date") == date_str
        and previous.get("mode") == mode
    )
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "date": date_str,
        "mode": mode,
        "status": "running",
        "phase": "recovery_started" if recoverable else "started",
        "started_at": previous.get("started_at", now) if recoverable else now,
        "updated_at": now,
        "attempt": int(previous.get("attempt", 0)) + 1 if recoverable else 1,
        "recovered_from_phase": previous.get("interrupted_from_phase", previous.get("phase", "")) if recoverable else "",
    }
    atomic_write_text(RUN_STATE_FILE, json.dumps(state, indent=2) + "\n")
    RUN_STATE_ACTIVE = True
    if recoverable:
        log(f"Recovering interrupted {mode} run from phase: {previous.get('phase', 'unknown')}")
    return state


def update_run_state(phase: str, status: str = "running", detail: str = ""):
    global RUN_STATE_ACTIVE
    state = load_run_state()
    if not state:
        return
    if status == "interrupted":
        state["interrupted_from_phase"] = state.get("phase", "")
    state.update({"phase": phase, "status": status, "updated_at": datetime.now(timezone.utc).isoformat()})
    if detail:
        state["detail"] = detail
    if status == "complete":
        state["completed_at"] = state["updated_at"]
    atomic_write_text(RUN_STATE_FILE, json.dumps(state, indent=2) + "\n")
    if status in {"complete", "interrupted"}:
        RUN_STATE_ACTIVE = False


def manual_kill_switch() -> dict:
    """Read the repository-level live-betting stop; malformed state fails closed."""
    if not MANUAL_KILL_SWITCH_FILE.exists():
        return {"active": False, "reason": "not_configured"}
    try:
        state = json.loads(MANUAL_KILL_SWITCH_FILE.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or not isinstance(state.get("active"), bool):
            raise ValueError("active must be a boolean")
        return {"active": state["active"], "reason": str(state.get("reason") or "manual_repository_switch")}
    except (OSError, ValueError, TypeError) as exc:
        log(f"WARNING: Invalid kill-switch.json; live betting disabled ({exc})")
        return {"active": True, "reason": "invalid_kill_switch_configuration"}


def apply_manual_kill_switch(recommendations: list[dict], paper_trading: bool = False) -> tuple[list[dict], str]:
    state = manual_kill_switch()
    if state["active"] and not paper_trading:
        log(f"MANUAL KILL SWITCH ACTIVE: {state['reason']}; no live candidates can be authorized")
        return [], state["reason"]
    return recommendations, ""


def load_tour_exposure_caps() -> dict[str, float]:
    caps = dict(DEFAULT_TOUR_EXPOSURE_CAPS)
    if not RISK_CONFIG_FILE.exists():
        return caps
    try:
        payload = json.loads(RISK_CONFIG_FILE.read_text(encoding="utf-8"))
        configured = payload.get("tour_exposure_caps", {})
        if not isinstance(configured, dict):
            raise ValueError("tour_exposure_caps must be an object")
        for tour in caps:
            if tour in configured:
                value = float(configured[tour])
                if not 0 <= value <= MAX_DAILY_EXPOSURE:
                    raise ValueError(f"{tour} cap must be between 0 and {MAX_DAILY_EXPOSURE}")
                caps[tour] = value
        return caps
    except (OSError, TypeError, ValueError) as exc:
        log(f"WARNING: Invalid risk-config.json; using conservative defaults ({exc})")
        return dict(DEFAULT_TOUR_EXPOSURE_CAPS)


def tour_exposure_bucket(match: dict) -> str:
    text = f"{match.get('level', '')} {match.get('tournament', '')}".casefold()
    if "itf" in text: return "ITF"
    if "challenger" in text: return "Challenger"
    if "wta" in text: return "WTA"
    if "atp" in text: return "ATP"
    return "Unknown"


def fetch(url: str, cache_ttl: int = 0, stale_if_error: int = 0) -> str | None:
    provider = url.split("/")[2]
    if cache_ttl:
        cached = get_cached_response("direct", url, cache_ttl)
        if cached is not None:
            log(f"  Using fresh cached response for {provider}")
            return cached
    if not allow_provider_request(provider):
        if stale_if_error:
            return get_cached_response("direct", url, stale_if_error)
        return None
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        started = time.monotonic()
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code in TRANSIENT_HTTP_STATUSES and attempt < MAX_TRANSIENT_RETRIES:
                record_source_health(provider, False, f"HTTP {resp.status_code} retry {attempt + 1}", started)
                wait_before_retry(provider, attempt, resp); continue
            resp.raise_for_status()
            record_source_health(provider, True, f"HTTP {resp.status_code}", started)
            record_provider_success(provider)
            if cache_ttl:
                cache_external_response("direct", url, resp.text)
            return resp.text
        except requests.RequestException as exc:
            if attempt < MAX_TRANSIENT_RETRIES and getattr(exc, "response", None) is None:
                wait_before_retry(provider, attempt); continue
            record_source_health(provider, False, type(exc).__name__, started)
            record_provider_failure(provider, type(exc).__name__)
            log(f"  Failed to fetch {url}: {exc}")
            if stale_if_error:
                cached = get_cached_response("direct", url, stale_if_error)
                if cached is not None:
                    log(f"  Using stale cached response for {provider} after provider failure")
                    return cached
            return None
    return None


def fetch_reader(target_url: str, cache_ttl: int = 0, stale_if_error: int = 0) -> str | None:
    """Fetch a page through Jina Reader using API headers, not browser headers."""
    reader_headers = {
        "Accept": "text/plain",
        "User-Agent": "tennis-betting-bot/1.0",
        "X-Return-Format": "markdown",
    }
    targets = [target_url]
    if target_url.startswith("https://"):
        targets.append("http://" + target_url.removeprefix("https://"))

    provider = "r.jina.ai"
    if cache_ttl:
        cached = get_cached_response("reader", target_url, cache_ttl)
        if cached is not None:
            log("  Using fresh cached Jina Reader response")
            return cached
    if not allow_provider_request(provider):
        if stale_if_error:
            return get_cached_response("reader", target_url, stale_if_error)
        return None
    for target in targets:
        reader_url = f"https://r.jina.ai/{target}"
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                response = requests.get(reader_url, headers=reader_headers, timeout=REQUEST_TIMEOUT)
                if response.status_code in TRANSIENT_HTTP_STATUSES and attempt < MAX_TRANSIENT_RETRIES:
                    wait_before_retry("Jina Reader", attempt, response); continue
                response.raise_for_status()
                if response.text.strip():
                    record_provider_success(provider)
                    if cache_ttl:
                        cache_external_response("reader", target_url, response.text)
                    return response.text
                break
            except requests.RequestException as exc:
                if attempt < MAX_TRANSIENT_RETRIES and getattr(exc, "response", None) is None:
                    wait_before_retry("Jina Reader", attempt); continue
                log(f"  Reader request failed for {target}: {exc}")
                record_provider_failure(provider, type(exc).__name__)
                break
    if stale_if_error:
        cached = get_cached_response("reader", target_url, stale_if_error)
        if cached is not None:
            log("  Using stale cached Jina Reader response after provider failure")
            return cached
    return None


def fetch_json(url: str, params: dict | None = None):
    """Fetch JSON while keeping API keys out of log output."""
    provider = url.split("/")[2]
    if not allow_provider_request(provider):
        return None
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        started = time.monotonic()
        try:
            response = requests.get(url, params=params, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            if response.status_code in TRANSIENT_HTTP_STATUSES and attempt < MAX_TRANSIENT_RETRIES:
                record_source_health(provider, False, f"HTTP {response.status_code} retry {attempt + 1}", started)
                wait_before_retry(url.split("/")[2], attempt, response); continue
            response.raise_for_status()
            payload = response.json()
            record_source_health(provider, True, f"HTTP {response.status_code}", started)
            record_provider_success(provider)
            return payload
        except requests.RequestException as exc:
            if attempt < MAX_TRANSIENT_RETRIES and getattr(exc, "response", None) is None:
                record_source_health(provider, False, f"{type(exc).__name__} retry {attempt + 1}", started)
                wait_before_retry(url.split("/")[2], attempt); continue
            record_source_health(provider, False, type(exc).__name__, started)
            log(f"  API request failed for {url}: {exc}")
            record_provider_failure(provider, type(exc).__name__)
            return None
        except ValueError as exc:
            record_source_health(provider, False, "invalid_json", started)
            log(f"  API request failed for {url}: {exc}")
            record_provider_failure(provider, "invalid_json")
            return None
    return None


def fetch_odds_json(
    url: str,
    params: dict,
    api_keys: list[str],
    key_index: int,
) -> tuple[object | None, int]:
    """Fetch Odds-API.io JSON, rotating keys on quota or authentication errors."""
    if not api_keys:
        return None, key_index
    provider = "api.odds-api.io"
    if not allow_provider_request(provider):
        return None, key_index

    for offset in range(len(api_keys)):
        candidate_index = (key_index + offset) % len(api_keys)
        request_params = {**params, "apiKey": api_keys[candidate_index]}
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                started = time.monotonic()
                response = requests.get(
                    url,
                    params=request_params,
                    headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )
                record_api_quota("Odds-API.io", response, f"key-{candidate_index + 1}")
                if response.status_code in {401, 403, 429}:
                    record_source_health("api.odds-api.io", False, f"HTTP {response.status_code} key {candidate_index + 1}", started)
                    log(
                        f"  Odds API key {candidate_index + 1}/{len(api_keys)} "
                        f"unavailable ({response.status_code}); rotating"
                    )
                    break
                if response.status_code in TRANSIENT_HTTP_STATUSES and attempt < MAX_TRANSIENT_RETRIES:
                    record_source_health("api.odds-api.io", False, f"HTTP {response.status_code} retry {attempt + 1}", started)
                    wait_before_retry("Odds API", attempt, response)
                    continue
                response.raise_for_status()
                record_source_health("api.odds-api.io", True, f"HTTP {response.status_code} key {candidate_index + 1}", started)
                payload = response.json()
                record_provider_success(provider)
                return payload, candidate_index
            except requests.RequestException as exc:
                if attempt < MAX_TRANSIENT_RETRIES and getattr(exc, "response", None) is None:
                    record_source_health("api.odds-api.io", False, f"{type(exc).__name__} retry {attempt + 1}", started)
                    wait_before_retry("Odds API", attempt)
                    continue
                record_source_health("api.odds-api.io", False, type(exc).__name__, started)
                status = getattr(getattr(exc, "response", None), "status_code", None)
                detail = f"HTTP {status}" if status else type(exc).__name__
                log(f"  Odds API request failed for {url}: {detail}")
                record_provider_failure(provider, detail)
                return None, candidate_index
            except ValueError as exc:
                record_source_health("api.odds-api.io", False, type(exc).__name__, started)
                log(f"  Odds API request failed for {url}: invalid JSON")
                record_provider_failure(provider, "invalid_json")
                return None, candidate_index

    log("  All configured Odds API keys are unavailable or out of quota")
    return None, key_index


def parse_args():
    parser = argparse.ArgumentParser(description="Tennis betting bot")
    parser.add_argument("--date", default=None, help="Match date (YYYY-MM-DD)")
    parser.add_argument("--odds-min", type=float, default=1.5, help="Min decimal odds")
    parser.add_argument("--odds-max", type=float, default=1.6, help="Max decimal odds")
    parser.add_argument("--bankroll", type=float, default=None, help="Override bankroll")
    parser.add_argument("--force", action="store_true", help="Run even if bets already logged for this date")
    parser.add_argument("--settle-only", action="store_true", help="Settle pending bets without generating picks")
    parser.add_argument("--revalidate-only", action="store_true", help="Refresh and authorize pending bets near match time")
    parser.add_argument("--backtest-only", action="store_true", help="Rebuild analytics without API calls")
    parser.add_argument("--diagnostic", action="store_true", help="Collect and validate data without writing files, calling AI, staking, or settling")
    parser.add_argument("--paper-trading", action="store_true", help="Simulate authorized bets without changing the real bankroll")
    return parser.parse_args()


def resolve_date(raw: str | None) -> str:
    if raw:
        return raw
    return datetime.now().strftime("%Y-%m-%d")


def load_bankroll(args_bankroll: float | None) -> float | None:
    if args_bankroll is not None:
        previous = None
        if BANKROLL_FILE.exists():
            try: previous = float(BANKROLL_FILE.read_text().strip())
            except ValueError: pass
        if previous is not None:
            ensure_bankroll_ledger(previous)
            record_bankroll_transaction("manual_adjustment", f"override:{datetime.now(timezone.utc).isoformat()}", args_bankroll - previous)
        atomic_write_text(BANKROLL_FILE, str(args_bankroll))
        log(f"Bankroll overridden to €{args_bankroll:.2f}")
        return args_bankroll

    if BANKROLL_FILE.exists():
        content = BANKROLL_FILE.read_text().strip()
        if content:
            try:
                val = float(content)
                log(f"Loaded bankroll: €{val:.2f}")
                return val
            except ValueError:
                pass

    log("No bankroll found. Run with --bankroll <amount> to set it.")
    return None


def save_bankroll(bankroll: float | None, total_stake: float):
    if bankroll is None:
        return
    remaining = reconcile_bankroll(bankroll)
    log(f"Bankroll reconciled: €{remaining:.2f} (was €{bankroll:.2f}, newly staked €{total_stake:.2f})")


def bankroll_reference(row: dict) -> str:
    pick = normalize_player_name(re.sub(r"\s+to win\s*$", "", row.get("BET", ""), flags=re.I))
    return f"{row.get('DATE', '')}|{pick}|{normalize_player_name(row.get('MATCH', ''))}"


def transaction_id(kind: str, reference: str) -> str:
    return hashlib.sha256(f"{kind}|{reference}".encode("utf-8")).hexdigest()[:24]


def seal_transaction(row: dict, previous_hash: str) -> dict:
    row = {**row, "PREVIOUS_HASH": previous_hash}
    payload = "|".join(str(row.get(field, "")) for field in TRANSACTION_HEADERS[:-1])
    row["HASH"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return row


def validate_transaction_ledger(rows: list[dict]) -> bool:
    previous_hash = "GENESIS"
    for row in rows:
        expected = seal_transaction({key: value for key, value in row.items() if key not in {"PREVIOUS_HASH", "HASH"}}, previous_hash)
        if row.get("PREVIOUS_HASH") != previous_hash or row.get("HASH") != expected["HASH"]:
            raise RuntimeError(f"Bankroll ledger integrity failure at transaction {row.get('ID', 'unknown')}")
        previous_hash = row["HASH"]
    return True


def ensure_bankroll_ledger(balance: float) -> list[dict]:
    """Create a ledger baseline while marking pre-existing bets as already reflected."""
    headers, rows = read_csv_rows(TRANSACTION_FILE)
    if rows:
        validate_transaction_ledger(rows)
        return rows
    now = datetime.now(timezone.utc).isoformat()
    rows = [seal_transaction({"ID": transaction_id("opening_balance", "ledger"), "TIMESTAMP": now,
             "TYPE": "opening_balance", "REFERENCE": "ledger", "AMOUNT": f"{balance:.2f}", "BALANCE": f"{balance:.2f}"}, "GENESIS")]
    _, bets = read_csv_rows(LOG_FILE)
    for bet in bets:
        reference = bankroll_reference(bet)
        rows.append(seal_transaction({"ID": transaction_id("stake", reference), "TIMESTAMP": now, "TYPE": "legacy_stake",
                     "REFERENCE": reference, "AMOUNT": "0.00", "BALANCE": f"{balance:.2f}"}, rows[-1]["HASH"]))
        if bet.get("RESULT") in {"W", "L", "V"}:
            rows.append(seal_transaction({"ID": transaction_id("return", reference), "TIMESTAMP": now, "TYPE": "legacy_return",
                         "REFERENCE": reference, "AMOUNT": "0.00", "BALANCE": f"{balance:.2f}"}, rows[-1]["HASH"]))
    atomic_write_csv(TRANSACTION_FILE, TRANSACTION_HEADERS, rows)
    return rows


def record_bankroll_transaction(kind: str, reference: str, amount: float) -> float:
    _, rows = read_csv_rows(TRANSACTION_FILE)
    if not rows:
        raise RuntimeError("Bankroll ledger must be initialized before recording transactions")
    validate_transaction_ledger(rows)
    identifier = transaction_id(kind, reference)
    existing = next((row for row in rows if row.get("ID") == identifier), None)
    if existing:
        return float(existing["BALANCE"])
    balance = round(float(rows[-1]["BALANCE"]) + amount, 2)
    rows.append(seal_transaction(
        {"ID": identifier, "TIMESTAMP": datetime.now(timezone.utc).isoformat(), "TYPE": kind,
         "REFERENCE": reference, "AMOUNT": f"{amount:.2f}", "BALANCE": f"{balance:.2f}"},
        rows[-1]["HASH"],
    ))
    atomic_write_csv(TRANSACTION_FILE, TRANSACTION_HEADERS, rows)
    return balance


def reconcile_bankroll(current_balance: float | None = None) -> float:
    """Import missing bet transactions and make bankroll.txt match the ledger."""
    if current_balance is None:
        current_balance = float(BANKROLL_FILE.read_text().strip() or 0) if BANKROLL_FILE.exists() else 0.0
    ensure_bankroll_ledger(current_balance)
    _, bets = read_csv_rows(LOG_FILE)
    for bet in bets:
        reference = bankroll_reference(bet)
        try: stake = float(bet.get("STAKE") or 0)
        except ValueError: stake = 0.0
        record_bankroll_transaction("stake", reference, -stake)
        if bet.get("RESULT") in {"W", "L", "V"}:
            try: returned = float(bet.get("RETURN") or 0)
            except ValueError: returned = 0.0
            record_bankroll_transaction("return", reference, returned)
    _, transactions = read_csv_rows(TRANSACTION_FILE)
    balance = round(float(transactions[-1]["BALANCE"]), 2)
    atomic_write_text(BANKROLL_FILE, f"{balance:.2f}")
    return balance


# ─── Stage 1: Data Collection ────────────────────────────────────────

def parse_tournament_level(url: str, name: str) -> str:
    name_lower = name.lower()
    url_lower = url.lower()
    if "challenger" in url_lower or "challenger" in name_lower:
        return "Challenger"
    if "itf" in url_lower or "itf" in name_lower:
        return "ITF"
    if "atp" in url_lower or "atp" in name_lower:
        return "ATP"
    if "wta" in url_lower or "wta" in name_lower:
        return "WTA"
    return "Unknown"


def fetch_matches_from_atp(date_str: str) -> list[dict]:
    """Fetch ATP-level matches from the ATP tour scores page."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    url = f"https://www.atptour.com/en/scores/{dt.year}-{dt.month:02d}-{dt.day:02d}/all/results"
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    matches = []
    # ATP uses 'day-scores' divs with match cards
    day_scores = soup.select("div.day-scores")
    for day in day_scores:
        tournament_name_el = day.select_one("div.tournament-title a, a.tournament-title")
        tournament_name = tournament_name_el.get_text(strip=True) if tournament_name_el else "ATP Event"
        match_cards = day.select("div.match-card, div.day-match")
        for card in match_cards:
            players = card.select("a.player-name, span.player-name")
            if len(players) >= 2:
                p1 = players[0].get_text(strip=True)
                p2 = players[1].get_text(strip=True)
                matches.append({
                    "player1": p1,
                    "player2": p2,
                    "tournament": tournament_name,
                    "level": "ATP",
                    "source": url,
                })
    return matches


def fetch_matches_from_wta(date_str: str) -> list[dict]:
    """Fetch WTA-level matches."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    url = f"https://www.wtatennis.com/scores/{dt.year}-{dt.month:02d}-{dt.day:02d}"
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    matches = []
    event_cards = soup.select("div.event-card, div.match-wrapper")
    for card in event_cards:
        tournament_el = card.select_one("a.event-title, span.event-title, div.event-name")
        tournament = tournament_el.get_text(strip=True) if tournament_el else "WTA Event"
        players = card.select("span.player-name, a.player-name, div.player-name")
        if len(players) >= 2:
            p1 = players[0].get_text(strip=True)
            p2 = players[1].get_text(strip=True)
            matches.append({
                "player1": p1,
                "player2": p2,
                "tournament": tournament,
                "level": "WTA",
                "source": url,
            })
    return matches


def fetch_matches_all(date_str: str) -> list[dict]:
    """Aggregate matches from all sources."""
    all_matches = []
    log("Fetching ATP matches...")
    all_matches.extend(fetch_matches_from_atp(date_str))
    log(f"  Found {sum(1 for m in all_matches if m['level'] == 'ATP')} ATP matches")
    log("Fetching WTA matches...")
    all_matches.extend(fetch_matches_from_wta(date_str))
    log(f"  Found {sum(1 for m in all_matches if m['level'] == 'WTA')} WTA matches")

    # Deduplicate by player1+player2
    seen = set()
    unique = []
    for m in all_matches:
        key = tuple(sorted([m["player1"].lower(), m["player2"].lower()]))
        if key not in seen:
            seen.add(key)
            unique.append(m)
    log(f"Total unique matches: {len(unique)}")
    return unique


def parse_espn_scoreboard(payload, date_str: str, tour: str) -> list[dict]:
    """Parse singles fixtures from ESPN's structured tennis scoreboard."""
    events = normalize_provider_collection(payload, "ESPN", f"/{tour}/scoreboard")
    fixtures = []
    for event in events:
        if not isinstance(event, dict):
            record_schema_alert("ESPN", f"/{tour}/scoreboard", f"event item changed to {type(event).__name__}")
            continue
        tournament = str(event.get("name") or event.get("shortName") or f"{tour.upper()} Event")
        groupings = event.get("groupings")
        if not isinstance(groupings, list):
            record_schema_alert("ESPN", f"/{tour}/scoreboard", "event missing groupings list")
            continue
        for grouping in groupings:
            if not isinstance(grouping, dict):
                record_schema_alert("ESPN", f"/{tour}/scoreboard", "grouping item is not an object")
                continue
            grouping_meta = grouping.get("grouping") or {}
            if not isinstance(grouping_meta, dict):
                record_schema_alert("ESPN", f"/{tour}/scoreboard", "grouping metadata is not an object")
                continue
            if "singles" not in str(grouping_meta.get("slug") or grouping_meta.get("displayName") or "").casefold():
                continue
            competitions = grouping.get("competitions")
            if not isinstance(competitions, list):
                record_schema_alert("ESPN", f"/{tour}/scoreboard", "singles grouping missing competitions list")
                continue
            for competition in competitions:
                if not isinstance(competition, dict):
                    record_schema_alert("ESPN", f"/{tour}/scoreboard", "competition item is not an object")
                    continue
                start_time = str(competition.get("startDate") or competition.get("date") or "")
                if not start_time.startswith(date_str):
                    continue
                competitors = competition.get("competitors")
                if not isinstance(competitors, list) or len(competitors) != 2:
                    record_schema_alert("ESPN", f"/{tour}/scoreboard", "dated singles match does not have two competitors")
                    continue
                names = []
                for competitor in competitors:
                    athlete = competitor.get("athlete") if isinstance(competitor, dict) else None
                    name = athlete.get("displayName") if isinstance(athlete, dict) else None
                    if name:
                        names.append(str(name).strip())
                if len(names) != 2:
                    record_schema_alert("ESPN", f"/{tour}/scoreboard", "competitor displayName is missing")
                    continue
                status = competition.get("status") or {}
                status_type = status.get("type") if isinstance(status, dict) else {}
                fixtures.append({
                    "event_id": f"espn:{tour}:{competition.get('id', '')}",
                    "player1": names[0], "player2": names[1], "tournament": tournament,
                    "level": tour.upper(), "start_time": start_time,
                    "status": status_type.get("state", "") if isinstance(status_type, dict) else "",
                    "fixture_source": "ESPN",
                })
    return fixtures


def fetch_secondary_fixtures(date_str: str) -> list[dict]:
    """Fetch an independent, keyless ATP/WTA fixture cross-check."""
    compact_date = date_str.replace("-", "")
    fixtures = []
    for tour in ("atp", "wta"):
        url = f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"
        payload = fetch_json(url, {"dates": compact_date})
        if payload is not None:
            fixtures.extend(parse_espn_scoreboard(payload, date_str, tour))
    log(f"  Found {len(fixtures)} independent fixtures from ESPN")
    return fixtures


def cross_check_fixture_sources(matches: list[dict], secondary: list[dict]) -> list[dict]:
    """Annotate primary priced fixtures when the independent feed confirms the pairing."""
    secondary_by_pair = {
        frozenset((normalize_player_name(item.get("player1", "")), normalize_player_name(item.get("player2", "")))): item
        for item in secondary
        if item.get("player1") and item.get("player2")
    }
    confirmed = 0
    for match in matches:
        pair = frozenset((normalize_player_name(match.get("player1", "")), normalize_player_name(match.get("player2", ""))))
        corroborating = secondary_by_pair.get(pair)
        match["fixture_sources"] = ["Odds-API.io"]
        match["secondary_fixture_confirmed"] = bool(corroborating)
        if corroborating:
            match["fixture_sources"].append("ESPN")
            match["secondary_event_id"] = corroborating.get("event_id", "")
            confirmed += 1
    log(f"  Independently confirmed {confirmed}/{len(matches)} priced fixtures")
    return matches


def fetch_verified_matches(date_str: str, api_keys: list[str]) -> list[dict]:
    """Collect priced fixtures and independently cross-check ATP/WTA coverage."""
    secondary = fetch_secondary_fixtures(date_str)
    primary = fetch_matches_from_odds_api(date_str, api_keys)
    return cross_check_fixture_sources(primary, secondary)


def extract_moneyline_odds(payload: dict) -> tuple[float | None, float | None, str | None]:
    """Return the best available home and away prices across bookmakers."""
    market = extract_moneyline_market(payload)
    return market["best_home"], market["best_away"], market["source"]


def extract_moneyline_market(payload: dict) -> dict:
    prices_found = []
    for bookmaker, markets in (payload.get("bookmakers") or {}).items():
        for market in markets or []:
            name = str(market.get("name", "")).strip().lower()
            if name not in {"ml", "moneyline", "match winner", "winner"}:
                continue
            for prices in market.get("odds") or []:
                try:
                    home = float(prices.get("home"))
                    away = float(prices.get("away"))
                except (TypeError, ValueError):
                    continue
                if home > 1 and away > 1:
                    prices_found.append((home, away, bookmaker))
    if not prices_found:
        return {"best_home": None, "best_away": None, "consensus_home": None, "consensus_away": None, "source": None, "bookmaker_count": 0, "home_dispersion": None, "away_dispersion": None, "quotes": []}
    homes, aways = sorted(p[0] for p in prices_found), sorted(p[1] for p in prices_found)
    midpoint = len(homes) // 2
    median_home = homes[midpoint] if len(homes) % 2 else (homes[midpoint - 1] + homes[midpoint]) / 2
    median_away = aways[midpoint] if len(aways) % 2 else (aways[midpoint - 1] + aways[midpoint]) / 2
    eligible_home = [p for p in prices_found if p[0] <= median_home * 1.12] or prices_found
    eligible_away = [p for p in prices_found if p[1] <= median_away * 1.12] or prices_found
    best_home = max(eligible_home, key=lambda p: p[0])
    best_away = max(eligible_away, key=lambda p: p[1])
    source = best_home[2] if best_home[2] == best_away[2] else f"{best_home[2]}/{best_away[2]}"
    return {"best_home": best_home[0], "best_away": best_away[1], "consensus_home": median_home, "consensus_away": median_away, "source": source, "bookmaker_count": len(prices_found),
            "home_dispersion": (max(homes) - min(homes)) / median_home,
            "away_dispersion": (max(aways) - min(aways)) / median_away,
            "quotes": [{"home": home, "away": away, "bookmaker": bookmaker}
                       for home, away, bookmaker in sorted(prices_found, key=lambda item: item[2])]}


def detect_surface(event: dict, tournament: str) -> str | None:
    """Use provider metadata first, then conservative tournament-name hints."""
    raw = event.get("surface") or (event.get("league") or {}).get("surface")
    if raw and str(raw).lower() in {"hard", "clay", "grass"}:
        return str(raw).lower()
    name = tournament.casefold()
    hints = {
        "grass": ("wimbledon", "queens", "halle", "eastbourne", "nottingham"),
        "clay": ("roland garros", "french open", "rome", "madrid", "monte carlo", "barcelona", "hamburg", "bastad", "gstaad", "umag", "kitzbuhel"),
    }
    for surface, terms in hints.items():
        if any(term in name for term in terms):
            return surface
    return None


def provider_location(event: dict, source: str, as_of: str) -> dict | None:
    """Extract coordinates/timezone only when the provider supplies them explicitly."""
    candidates = [event]
    for field in ("location", "venue"):
        if isinstance(event.get(field), dict):
            candidates.append(event[field])
    for candidate in candidates:
        latitude = candidate.get("latitude", candidate.get("lat"))
        longitude = candidate.get("longitude", candidate.get("lon", candidate.get("lng")))
        timezone_name = (candidate.get("timezone") or candidate.get("timeZone") or
                         candidate.get("utcOffset") or candidate.get("utc_offset"))
        location = verified_location(latitude, longitude, timezone_name, source, as_of)
        if location:
            return location
    return None


def fetch_matches_from_odds_api(date_str: str, api_keys: list[str]) -> list[dict]:
    """Fetch verified tennis fixtures and match-winner odds from Odds-API.io."""
    global LAST_FIXTURE_STATUS
    schema_alert_count_before = len(SCHEMA_ALERTS)
    events_payload, key_index = fetch_odds_json(
        "https://api.odds-api.io/v3/events",
        {"sport": "tennis"},
        api_keys,
        0,
    )
    if events_payload is None:
        LAST_FIXTURE_STATUS = "provider_failure"
        return []

    events = normalize_provider_collection(events_payload, "Odds-API.io", "/v3/events")
    valid_events = []
    for event in events:
        if not isinstance(event, dict):
            record_schema_alert("Odds-API.io", "/v3/events", f"event item changed to {type(event).__name__}")
            continue
        missing = [field for field in ("id", "date", "home", "away")
                   if event.get(field) is None or str(event.get(field)).strip() == ""]
        if missing:
            record_schema_alert("Odds-API.io", "/v3/events", f"event missing required field(s): {','.join(missing)}")
            continue
        valid_events.append(event)

    dated_events = [
        event for event in valid_events
        if str(event.get("date", "")).startswith(date_str)
        and event.get("home")
        and event.get("away")
    ]
    log(f"  Found {len(dated_events)} tennis events from Odds-API.io")
    if not dated_events:
        LAST_FIXTURE_STATUS = "provider_schema_failure" if len(SCHEMA_ALERTS) > schema_alert_count_before else "valid_empty_schedule"
        return []

    events_by_id = {str(event.get("id")): event for event in dated_events}
    matches = []
    for start in range(0, len(dated_events), 10):
        batch = dated_events[start:start + 10]
        payload, key_index = fetch_odds_json(
            "https://api.odds-api.io/v3/odds/multi",
            {
                "eventIds": ",".join(str(event.get("id")) for event in batch),
                "bookmakers": "Bet365,Unibet,Pinnacle,William Hill,Betway",
            },
            api_keys,
            key_index,
        )
        odds_events = normalize_provider_collection(payload, "Odds-API.io", "/v3/odds/multi") if payload is not None else []

        for odds_event in odds_events:
            if not isinstance(odds_event, dict):
                record_schema_alert("Odds-API.io", "/v3/odds/multi", f"odds item changed to {type(odds_event).__name__}")
                continue
            if not validate_odds_event_schema(odds_event):
                continue
            event = events_by_id.get(str(odds_event.get("id")), odds_event)
            home = event.get("home") or odds_event.get("home")
            away = event.get("away") or odds_event.get("away")
            if not home or not away:
                continue
            market = extract_moneyline_market(odds_event)
            home_odds, away_odds, bookmaker = market["best_home"], market["best_away"], market["source"]
            if home_odds is None or away_odds is None:
                continue
            league = event.get("league") or odds_event.get("league") or {}
            if not isinstance(league, dict):
                record_schema_alert("Odds-API.io", "/v3/odds/multi", f"league changed to {type(league).__name__}")
                league = {}
            tournament = league.get("name") or "Tennis"
            matches.append({
                "event_id": str(event.get("id", odds_event.get("id", ""))),
                "start_time": event.get("date") or odds_event.get("date"),
                "status": event.get("status") or odds_event.get("status"),
                "surface": detect_surface(event, tournament),
                "player1": home,
                "player2": away,
                "tournament": tournament,
                "level": parse_tournament_level("", tournament),
                "source": "https://api.odds-api.io",
                "home_odds": home_odds,
                "away_odds": away_odds,
                "consensus_home_odds": market["consensus_home"],
                "consensus_away_odds": market["consensus_away"],
                "odds_source": bookmaker or "Odds-API.io",
                "bookmaker_count": market["bookmaker_count"],
                "home_dispersion": market["home_dispersion"],
                "away_dispersion": market["away_dispersion"],
                "bookmaker_quotes": market["quotes"],
                "indoor": event.get("indoor") if event.get("indoor") is not None else odds_event.get("indoor"),
                "best_of": event.get("bestOf") or odds_event.get("bestOf"),
                "location": (provider_location(event, "https://api.odds-api.io", date_str) or
                             provider_location(odds_event, "https://api.odds-api.io", date_str)),
            })
    log(f"  Found verified moneyline odds for {len(matches)} matches")
    LAST_FIXTURE_STATUS = "ok" if matches else "fixtures_without_verified_odds"
    return matches


def fetch_odds_for_match(player1: str, player2: str) -> tuple[float | None, str | None, str | None]:
    """Try to find odds for a match. Returns (odds, player_name, source_url)."""
    # Try Oddspedia search
    search_name = f"{player1} {player2}".replace(" ", "-").lower()
    urls_to_try = [
        f"https://oddspedia.com/tennis/{search_name}",
    ]

    for url in urls_to_try:
        html = fetch(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")

        # Oddspedia often has odds in data attributes or specific divs
        odds_elements = soup.select(
            "[data-odds], span.odds-value, div.odds-value, span.market-odd"
        )
        odds_values = []
        for el in odds_elements:
            text = el.get("data-odds", el.get_text(strip=True))
            try:
                val = float(text)
                odds_values.append(val)
            except (ValueError, TypeError):
                continue

        if odds_values:
            # First odds value is typically for player1
            odds = odds_values[0]
            return odds, player1, url

    return None, None, None


def attach_odds(matches: list[dict], odds_min: float, odds_max: float) -> list[dict]:
    """Fetch odds for each match and filter by range."""
    log("Fetching odds for matches...")
    enriched = []
    needs_lookup = []
    for match in matches:
        available = [
            odd for odd in (match.get("home_odds"), match.get("away_odds"))
            if odd is not None and odds_min <= odd <= odds_max
        ]
        if available:
            match["odds"] = available[0]
            enriched.append(match)
            log(
                f"  {match['player1']} {match.get('home_odds')} vs "
                f"{match['player2']} {match.get('away_odds')} ✓"
            )
        elif match.get("home_odds") is None and match.get("away_odds") is None:
            needs_lookup.append(match)

    if not needs_lookup:
        log(f"Qualifying matches in odds range [{odds_min}-{odds_max}]: {len(enriched)}")
        return enriched

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {}
        for m in needs_lookup:
            future = executor.submit(
                fetch_odds_for_match, m["player1"], m["player2"]
            )
            future_map[future] = m

        for future in as_completed(future_map):
            m = future_map[future]
            try:
                odds, player_name, source = future.result()
            except Exception as e:
                log(f"  Odds fetch error for {m['player1']} vs {m['player2']}: {e}")
                continue

            if odds and odds_min <= odds <= odds_max:
                m["odds"] = odds
                m["odds_source"] = source or "unknown"
                enriched.append(m)
                log(f"  {m['player1']} vs {m['player2']} → {odds:.2f} ✓")
            else:
                log(f"  {m['player1']} vs {m['player2']} → {'no odds' if odds is None else f'{odds:.2f} (out of range)'}")

    log(f"Qualifying matches in odds range [{odds_min}-{odds_max}]: {len(enriched)}")
    return enriched


def parse_tennis_abstract_elo(html: str) -> dict[str, dict]:
    """Parse Tennis Abstract's weekly Elo leaderboard into compact profiles."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table")
    if not tables:
        return {}

    profiles = {}
    for row in tables[-1].select("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        if len(cells) < 16:
            continue
        try:
            profile = {
                "name": cells[1],
                "age": float(cells[2]) if cells[2] else None,
                "elo_rank": int(cells[0]),
                "elo": float(cells[3]),
                "hard_elo": float(cells[6]) if cells[6] else None,
                "clay_elo": float(cells[8]) if cells[8] else None,
                "grass_elo": float(cells[10]) if cells[10] else None,
                "peak_elo": float(cells[12]) if cells[12] else None,
                "peak_month": cells[13] or None,
                "official_rank": int(cells[15]) if cells[15] else None,
            }
        except (TypeError, ValueError):
            continue
        profiles[normalize_player_name(profile["name"])] = profile
    return profiles


def parse_tennis_abstract_reader(text: str) -> dict[str, dict]:
    """Parse the tab-separated leaderboard returned by Jina Reader."""
    profiles = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split("\t")]
        if len(cells) < 16 or not cells[0].isdigit():
            continue
        try:
            profile = {
                "name": cells[1],
                "age": float(cells[2]) if cells[2] else None,
                "elo_rank": int(cells[0]),
                "elo": float(cells[3]),
                "hard_elo": float(cells[6]) if cells[6] else None,
                "clay_elo": float(cells[8]) if cells[8] else None,
                "grass_elo": float(cells[10]) if cells[10] else None,
                "peak_elo": float(cells[12]) if cells[12] else None,
                "peak_month": cells[13] or None,
                "official_rank": int(cells[15]) if cells[15] else None,
            }
        except (TypeError, ValueError):
            continue
        profiles[normalize_player_name(profile["name"])] = profile
    return profiles


def load_player_aliases() -> dict[str, str]:
    aliases = {}
    if PLAYER_ALIASES_FILE.exists() and PLAYER_ALIASES_FILE.stat().st_size:
        with PLAYER_ALIASES_FILE.open(newline="", encoding="utf-8") as handle:
            aliases.update({
            normalize_player_name(row.get("PROVIDER_NAME", "")): normalize_player_name(row.get("CANONICAL_NAME", ""))
            for row in csv.DictReader(handle)
            if row.get("PROVIDER_NAME") and row.get("CANONICAL_NAME")
            })
    if ALIAS_REVIEW_FILE.exists() and ALIAS_REVIEW_FILE.stat().st_size:
        with ALIAS_REVIEW_FILE.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("STATUS") or "").strip().casefold() not in {"approved", "applied"}:
                    continue
                canonical = row.get("REVIEWED_CANONICAL") or row.get("SUGGESTED_CANONICAL")
                if row.get("PROVIDER_NAME") and canonical:
                    aliases[normalize_player_name(row["PROVIDER_NAME"])] = normalize_player_name(canonical)
    return aliases


def load_player_alias_confidence() -> dict[str, tuple[float, str]]:
    """Load confidence and provenance without changing the alias lookup contract."""
    metadata = {}
    if PLAYER_ALIASES_FILE.exists() and PLAYER_ALIASES_FILE.stat().st_size:
        with PLAYER_ALIASES_FILE.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = normalize_player_name(row.get("PROVIDER_NAME", ""))
                if not key:
                    continue
                try:
                    confidence = min(1.0, max(0.0, float(row.get("CONFIDENCE") or 0)))
                except ValueError:
                    confidence = 0.0
                metadata[key] = (confidence, str(row.get("SOURCE") or "alias"))
    if ALIAS_REVIEW_FILE.exists() and ALIAS_REVIEW_FILE.stat().st_size:
        with ALIAS_REVIEW_FILE.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("STATUS") or "").strip().casefold() not in {"approved", "applied"}:
                    continue
                key = normalize_player_name(row.get("PROVIDER_NAME", ""))
                if key:
                    metadata[key] = (1.0, "manual_review")
    return metadata


def queue_alias_review(player: str, candidates: list[tuple[float, str, str]], reason: str):
    """Persist an unresolved identity once for manual approval or rejection."""
    if DIAGNOSTIC_MODE:
        return
    provider_key = normalize_player_name(player)
    if not provider_key:
        return
    headers = [
        "PROVIDER_NAME", "NORMALIZED_NAME", "SUGGESTED_CANONICAL", "SUGGESTED_CONFIDENCE",
        "ALTERNATIVES", "REASON", "STATUS", "REVIEWED_CANONICAL", "CREATED_AT", "UPDATED_AT",
    ]
    _, rows = read_csv_rows(ALIAS_REVIEW_FILE)
    if any(normalize_player_name(row.get("PROVIDER_NAME", "")) == provider_key for row in rows):
        return
    suggestions = sorted(candidates, reverse=True)[:3]
    best = suggestions[0] if suggestions else None
    now = datetime.now(timezone.utc).isoformat()
    rows.append({
        "PROVIDER_NAME": player, "NORMALIZED_NAME": provider_key,
        "SUGGESTED_CANONICAL": best[2] if best else "",
        "SUGGESTED_CONFIDENCE": f"{best[0]:.3f}" if best else "",
        "ALTERNATIVES": "; ".join(f"{item[2]} ({item[0]:.3f})" for item in suggestions[1:]),
        "REASON": reason, "STATUS": "pending", "REVIEWED_CANONICAL": "",
        "CREATED_AT": now, "UPDATED_AT": now,
    })
    atomic_write_csv(ALIAS_REVIEW_FILE, headers, rows)
    log(f"  Queued player identity for manual review: {player}")


def save_player_alias(provider_name: str, canonical_name: str, confidence: float):
    if DIAGNOSTIC_MODE:
        return
    aliases = load_player_aliases()
    provider_key = normalize_player_name(provider_name)
    if not provider_key or provider_key in aliases:
        return
    headers = ["PROVIDER_NAME", "CANONICAL_NAME", "SOURCE", "CONFIDENCE"]
    _, rows = read_csv_rows(PLAYER_ALIASES_FILE)
    rows.append({"PROVIDER_NAME": provider_name, "CANONICAL_NAME": canonical_name,
                 "SOURCE": "auto_unique", "CONFIDENCE": f"{confidence:.3f}"})
    atomic_write_csv(PLAYER_ALIASES_FILE, headers, rows)


def resolve_profile_identity(player: str, profiles: dict[str, dict], aliases: dict[str, str],
                             alias_metadata: dict[str, tuple[float, str]] | None = None) -> dict | None:
    """Resolve a profile while retaining explicit confidence and resolution provenance."""
    key = normalize_player_name(player)
    if key in profiles:
        return {"key": key, "confidence": 1.0, "method": "exact"}
    alias_key = aliases.get(key)
    if alias_key in profiles:
        confidence, source = (alias_metadata or {}).get(key, (1.0, "approved_alias"))
        return {"key": alias_key, "confidence": confidence, "method": source}
    candidates = []
    for candidate, profile in profiles.items():
        score = difflib.SequenceMatcher(None, key, candidate).ratio()
        if score >= 0.72:
            candidates.append((score, candidate, profile["name"]))
    candidates.sort(reverse=True)
    high_confidence = [item for item in candidates if item[0] >= 0.92]
    if len(high_confidence) == 1 or (len(high_confidence) > 1 and high_confidence[0][0] - high_confidence[1][0] >= 0.05):
        score, candidate, canonical = high_confidence[0]
        save_player_alias(player, canonical, score)
        return {"key": candidate, "confidence": score, "method": "auto_unique"}
    reason = "ambiguous_high_confidence" if high_confidence else "low_confidence" if candidates else "no_candidate"
    queue_alias_review(player, candidates, reason)
    return None


def resolve_profile_key(player: str, profiles: dict[str, dict], aliases: dict[str, str]) -> str | None:
    """Compatibility wrapper returning only the resolved canonical profile key."""
    identity = resolve_profile_identity(player, profiles, aliases)
    return identity["key"] if identity else None


def fetch_tennis_abstract_profiles(matches: list[dict]) -> dict[str, dict]:
    """Download each tour leaderboard once and retain only relevant singles players."""
    wanted = {
        normalize_player_name(player)
        for match in matches
        for player in (match["player1"], match["player2"])
        if "/" not in player
    }
    profiles = {}
    for tour, url in (
        ("ATP", "https://tennisabstract.com/reports/atp_elo_ratings.html"),
        ("WTA", "https://tennisabstract.com/reports/wta_elo_ratings.html"),
    ):
        html = fetch(url, cache_ttl=43_200, stale_if_error=604_800)
        tour_profiles = parse_tennis_abstract_elo(html) if html else {}
        source_method = "direct"
        if not tour_profiles:
            log(f"  Direct Tennis Abstract {tour} access unavailable; trying reader")
            reader_text = fetch_reader(url, cache_ttl=43_200, stale_if_error=604_800)
            tour_profiles = (
                parse_tennis_abstract_reader(reader_text)
                if reader_text
                else {}
            )
            source_method = "reader"
        if tour_profiles:
            for profile in tour_profiles.values():
                profile["_source_url"] = url
                profile["_source_method"] = source_method
            profiles.update(tour_profiles)
            log(f"  Loaded {len(tour_profiles)} Tennis Abstract {tour} profiles")
        else:
            log(f"  Tennis Abstract {tour} leaderboard unavailable from all sources")

    aliases = load_player_aliases()
    alias_metadata = load_player_alias_confidence()
    selected = {}
    for match in matches:
        for player in (match["player1"], match["player2"]):
            if "/" in player:
                continue
            identity = resolve_profile_identity(player, profiles, aliases, alias_metadata)
            if identity:
                profile = dict(profiles[identity["key"]])
                profile["identity_confidence"] = identity["confidence"]
                profile["identity_method"] = identity["method"]
                profile["canonical_name"] = profiles[identity["key"]].get("name", "")
                selected[normalize_player_name(player)] = profile
    log(f"  Tennis Abstract profiles matched: {len(selected)}/{len(wanted)}")
    return selected


def compact_profile_line(player: str, profiles: dict[str, dict]) -> str:
    """Render verified profile data without sending page HTML to the model."""
    profile = profiles.get(normalize_player_name(player))
    if not profile:
        return f"- {player}: profile unavailable"

    def shown(value):
        return "N/A" if value is None else f"{value:g}"

    ranking_history = profile.get("ranking_history") or {}
    bio_parts = []
    if profile.get("handedness"):
        bio_parts.append(f"handedness={profile['handedness']}")
    if profile.get("nationality"):
        bio_parts.append(f"nationality={profile['nationality']}")
    bio_text = f"; {'; '.join(bio_parts)}" if bio_parts else ""
    ranking_trend = ""
    if ranking_history:
        change = ranking_history.get("improvement_90d")
        ranking_trend = (
            f"; pre-match rank={shown(ranking_history.get('latest_rank'))}"
            f" as of {ranking_history.get('latest_date') or 'N/A'}"
            f"; 90d rank change={change:+g}" if change is not None else
            f"; pre-match rank={shown(ranking_history.get('latest_rank'))} as of {ranking_history.get('latest_date') or 'N/A'}"
        )
    return (
        f"- {player}: official rank={shown(profile['official_rank'])}; "
        f"age={shown(profile['age'])}; Elo={shown(profile['elo'])} "
        f"(Elo rank #{shown(profile['elo_rank'])}); "
        f"hard Elo={shown(profile['hard_elo'])}; "
        f"clay Elo={shown(profile['clay_elo'])}; "
        f"grass Elo={shown(profile['grass_elo'])}; "
        f"peak Elo={shown(profile['peak_elo'])}"
        f"{' (' + profile['peak_month'] + ')' if profile['peak_month'] else ''}"
        f"{ranking_trend}"
        f"{bio_text}"
    )


def enrich_matches_with_profiles(matches: list[dict]) -> dict[str, dict]:
    """Attach compact Tennis Abstract records for later Python validation."""
    profiles = fetch_tennis_abstract_profiles(matches)
    for match in matches:
        match["player1_profile"] = profiles.get(
            normalize_player_name(match["player1"])
        )
        match["player2_profile"] = profiles.get(
            normalize_player_name(match["player2"])
        )
        for side in ("player1", "player2"):
            profile = match.get(f"{side}_profile") or {}
            match[f"{side}_identity_confidence"] = float(profile.get("identity_confidence", 0.0))
            match[f"{side}_identity_method"] = profile.get("identity_method", "unresolved")
    return profiles


def calculate_ranking_history(history: list[dict], player: str, as_of: str) -> dict | None:
    """Build compact, leakage-safe ranking history from pre-match observations."""
    player_key = normalize_player_name(player)
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    observations = {}
    for row in history:
        winner_key = normalize_player_name(row.get("winner_name", ""))
        loser_key = normalize_player_name(row.get("loser_name", ""))
        if player_key not in {winner_key, loser_key}:
            continue
        try:
            played = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
            rank = int(float(row.get("winner_rank") if player_key == winner_key else row.get("loser_rank")))
        except (TypeError, ValueError):
            continue
        if played >= cutoff or rank <= 0:
            continue
        observations[played] = rank
    if not observations:
        return None
    ordered = sorted(observations.items())
    latest_date, latest_rank = ordered[-1]

    def rank_at(days_ago: int) -> tuple[int | None, str | None]:
        target = cutoff - timedelta(days=days_ago)
        eligible = [(date, rank) for date, rank in ordered if date <= target]
        if not eligible:
            return None, None
        date, rank = eligible[-1]
        return rank, date.strftime("%Y-%m-%d")

    rank_30, date_30 = rank_at(30)
    rank_90, date_90 = rank_at(90)
    rank_180, date_180 = rank_at(180)
    recent_year = [(date, rank) for date, rank in ordered if (cutoff - date).days <= 365]
    return {
        "latest_rank": latest_rank, "latest_date": latest_date.strftime("%Y-%m-%d"),
        "latest_age_days": (cutoff - latest_date).days,
        "rank_30d": rank_30, "rank_30d_date": date_30,
        "rank_90d": rank_90, "rank_90d_date": date_90,
        "rank_180d": rank_180, "rank_180d_date": date_180,
        "improvement_30d": rank_30 - latest_rank if rank_30 is not None else None,
        "improvement_90d": rank_90 - latest_rank if rank_90 is not None else None,
        "improvement_180d": rank_180 - latest_rank if rank_180 is not None else None,
        "best_rank_365d": min((rank for _, rank in recent_year), default=None),
        "worst_rank_365d": max((rank for _, rank in recent_year), default=None),
        "samples_365d": len(recent_year),
        "recent_snapshots": [{"date": date.strftime("%Y-%m-%d"), "rank": rank} for date, rank in ordered[-12:]],
        "source": "historical_match_rankings",
    }


def calculate_player_bio(history: list[dict], player: str, as_of: str) -> dict | None:
    """Collect leakage-safe handedness and nationality from dated match records."""
    player_key = normalize_player_name(player)
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    observations = []
    for row in history:
        winner_key = normalize_player_name(row.get("winner_name", ""))
        loser_key = normalize_player_name(row.get("loser_name", ""))
        if player_key not in {winner_key, loser_key}:
            continue
        prefix = "winner_" if player_key == winner_key else "loser_"
        try:
            played = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
        except ValueError:
            continue
        if played >= cutoff:
            continue
        raw_hand = str(row.get(prefix + "hand") or "").strip().upper()
        hand = {"R": "Right", "L": "Left"}.get(raw_hand)
        nationality = str(row.get(prefix + "ioc") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", nationality):
            nationality = None
        if hand or nationality:
            observations.append((played, hand, nationality, str(row.get("_source_url") or "historical_match_records")))
    if not observations:
        return None
    observations.sort(reverse=True)

    hand_observation = next((item for item in observations if item[1]), None)
    nationality_observation = next((item for item in observations if item[2]), None)
    hand, hand_date, hand_source = ((hand_observation[1], hand_observation[0], hand_observation[3]) if hand_observation else (None, None, None))
    nationality, nationality_date, nationality_source = ((nationality_observation[2], nationality_observation[0], nationality_observation[3]) if nationality_observation else (None, None, None))
    recent = [item for item in observations if (cutoff - item[0]).days <= 365]
    hand_values = [item[1] for item in recent if item[1]]
    nationality_values = [item[2] for item in recent if item[2]]

    def consistency(values: list[str], selected: str | None) -> float | None:
        return sum(value == selected for value in values) / len(values) if values and selected else None

    return {
        "handedness": hand, "handedness_date": hand_date.strftime("%Y-%m-%d") if hand_date else None,
        "handedness_consistency": consistency(hand_values, hand), "handedness_source": hand_source,
        "nationality": nationality, "nationality_date": nationality_date.strftime("%Y-%m-%d") if nationality_date else None,
        "nationality_consistency": consistency(nationality_values, nationality), "nationality_source": nationality_source,
        "samples_365d": len(recent),
        "source": ";".join(dict.fromkeys(source for source in (hand_source, nationality_source) if source)),
    }


def official_status_source(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").casefold()
    except ValueError:
        return False
    return url.startswith("https://") and any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_STATUS_DOMAINS)


def load_verified_player_status(as_of: str) -> dict[str, dict]:
    """Load active, time-bounded physical statuses cited to official tennis sources."""
    if not PLAYER_STATUS_FILE.exists() or not PLAYER_STATUS_FILE.stat().st_size:
        return {}
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    accepted = {"cleared", "questionable", "injured", "withdrawn", "unavailable", "suspended"}
    active = {}
    with PLAYER_STATUS_FILE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            player_key = normalize_player_name(row.get("PLAYER", ""))
            status = str(row.get("STATUS") or "").strip().casefold()
            try:
                effective = datetime.strptime(str(row.get("EFFECTIVE_DATE") or ""), "%Y-%m-%d")
                expires = datetime.strptime(str(row.get("EXPIRES_DATE") or ""), "%Y-%m-%d")
                verified = datetime.fromisoformat(str(row.get("VERIFIED_AT") or "").replace("Z", "+00:00")).replace(tzinfo=None)
            except (TypeError, ValueError):
                continue
            source = str(row.get("SOURCE_URL") or "").strip()
            if (not player_key or status not in accepted or not official_status_source(source)
                    or effective > cutoff or expires < cutoff or verified > cutoff + timedelta(days=1)
                    or expires < effective or (expires - effective).days > 90):
                continue
            candidate = {
                "status": status, "effective_date": effective.strftime("%Y-%m-%d"),
                "expires_date": expires.strftime("%Y-%m-%d"), "verified_at": verified.isoformat(),
                "source": source, "detail": str(row.get("DETAIL") or "").strip(), "kind": "official_status",
            }
            previous = active.get(player_key)
            if not previous or candidate["verified_at"] > previous["verified_at"]:
                active[player_key] = candidate
    return active


def calculate_recent_retirement(history: list[dict], player: str, as_of: str, lookback_days: int = 45) -> dict | None:
    """Flag an objectively recorded recent retirement without guessing its medical cause."""
    player_key = normalize_player_name(player)
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    observations = []
    for row in history:
        if normalize_player_name(row.get("loser_name", "")) != player_key or "RET" not in str(row.get("score") or "").upper():
            continue
        try:
            played = datetime.strptime(str(row.get("tourney_date") or ""), "%Y%m%d")
        except ValueError:
            continue
        age = (cutoff - played).days
        if 0 < age <= lookback_days:
            observations.append((played, str(row.get("_source_url") or "historical_match_records")))
    if not observations:
        return None
    played, source = max(observations)
    return {
        "status": "recent_retirement", "effective_date": played.strftime("%Y-%m-%d"),
        "expires_date": (played + timedelta(days=lookback_days)).strftime("%Y-%m-%d"),
        "verified_at": played.strftime("%Y-%m-%d"), "source": source,
        "detail": "Recorded retirement; medical cause not verified", "kind": "match_record",
    }


def physical_status_for_player(match: dict, side: str, player: str, official: dict[str, dict],
                               history: list[dict], as_of: str) -> dict:
    provider_status = str(match.get("status") or "").casefold()
    if any(token in provider_status for token in ("withdraw", "walkover", "cancel", "suspend")):
        return {"status": "unavailable", "effective_date": as_of, "expires_date": as_of,
                "verified_at": as_of, "source": match.get("odds_source") or "fixture_provider",
                "detail": f"Fixture status: {match.get('status')}", "kind": "fixture_status"}
    cited = official.get(normalize_player_name(player))
    if cited:
        return cited
    recent = calculate_recent_retirement(history, player, as_of)
    if recent:
        return recent
    return {"status": "unknown", "effective_date": "", "expires_date": "", "verified_at": "",
            "source": "", "detail": "No active verified physical-status report", "kind": "none"}


def calculate_head_to_head(history: list[dict], player1: str, player2: str,
                           surface: str | None, as_of: str) -> dict | None:
    """Calculate a recency/surface-weighted H2H with strong small-sample shrinkage."""
    player1_key, player2_key = normalize_player_name(player1), normalize_player_name(player2)
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    observations = []
    for row in history:
        winner_key = normalize_player_name(row.get("winner_name", ""))
        loser_key = normalize_player_name(row.get("loser_name", ""))
        if {winner_key, loser_key} != {player1_key, player2_key}:
            continue
        score = str(row.get("score") or "").upper()
        if not score or any(flag in score for flag in ("W/O", "RET", "DEF")):
            continue
        try:
            played = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
        except ValueError:
            continue
        if played >= cutoff:
            continue
        same_surface = bool(surface and str(row.get("surface") or "").casefold() == surface.casefold())
        weight = 0.5 ** ((cutoff - played).days / 730)
        if same_surface:
            weight *= 1.25
        observations.append((played, winner_key == player1_key, same_surface, weight,
                             str(row.get("_source_url") or "historical_match_records")))
    if not observations:
        return None
    observations.sort(reverse=True)
    weighted_total = sum(item[3] for item in observations)
    weighted_wins = sum(item[3] for item in observations if item[1])
    # Four neutral prior matches prevent a tiny or stale H2H from dominating.
    shrunk_probability = (weighted_wins + 2.0) / (weighted_total + 4.0)
    model_weight = min(0.03, max(0.0, (len(observations) - 2) * 0.01))
    model_probability = max(0.42, min(0.58, shrunk_probability)) if model_weight else None
    return {
        "sample": len(observations), "player1_wins": sum(item[1] for item in observations),
        "surface_sample": sum(item[2] for item in observations),
        "weighted_player1_win_rate": weighted_wins / weighted_total if weighted_total else 0.5,
        "player1_probability": model_probability, "player2_probability": 1 - model_probability if model_probability is not None else None,
        "model_weight": model_weight, "last_meeting": observations[0][0].strftime("%Y-%m-%d"),
        "source": ";".join(dict.fromkeys(item[4] for item in observations)),
    }


def calculate_recent_form(history: list[dict], player: str, surface: str | None, as_of: str, limit: int = 20) -> dict | None:
    """Calculate recency-, surface-, and opponent-rank-adjusted form."""
    player_key = normalize_player_name(player)
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    observations = []
    for row in history:
        winner_key, loser_key = normalize_player_name(row.get("winner_name", "")), normalize_player_name(row.get("loser_name", ""))
        if player_key not in {winner_key, loser_key} or any(flag in (row.get("score") or "").upper() for flag in ("W/O", "RET", "DEF")):
            continue
        try:
            played = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
        except ValueError:
            continue
        if played >= cutoff:
            continue
        won = player_key == winner_key
        try:
            own_rank = float(row.get("winner_rank") if won else row.get("loser_rank"))
            opponent_rank = float(row.get("loser_rank") if won else row.get("winner_rank"))
            if own_rank <= 0 or opponent_rank <= 0:
                raise ValueError
            expected = opponent_rank / (own_rank + opponent_rank)
        except (TypeError, ValueError):
            expected = 0.5
        days = max(0, (cutoff - played).days)
        weight = 0.5 ** (days / 120)
        if surface and str(row.get("surface", "")).casefold() == surface.casefold():
            weight *= 1.35
        observations.append((played, 1.0 if won else 0.0, expected, weight))
    observations.sort(key=lambda item: item[0], reverse=True)
    observations = observations[:limit]
    if len(observations) < 8:
        return None
    total_weight = sum(item[3] for item in observations)
    residual = sum((outcome - expected) * weight for _, outcome, expected, weight in observations) / total_weight
    win_rate = sum(outcome * weight for _, outcome, _, weight in observations) / total_weight
    return {"sample": len(observations), "probability": max(0.35, min(0.65, 0.5 + residual)), "win_rate": win_rate, "residual": residual}


def hold_probability(point_probability: float) -> float:
    """Convert an independent service-point probability to game hold probability."""
    p = max(0.01, min(0.99, point_probability)); q = 1 - p
    before_deuce = p ** 4 * (1 + 4 * q + 10 * q ** 2)
    reach_deuce = 20 * p ** 3 * q ** 3
    win_from_deuce = p ** 2 / (1 - 2 * p * q)
    return before_deuce + reach_deuce * win_from_deuce


def calculate_serve_return_profile(history: list[dict], player: str, surface: str | None, as_of: str, limit: int = 30) -> dict | None:
    """Aggregate verified service and return points with recency/surface weighting."""
    player_key = normalize_player_name(player); cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    observations = []
    for row in history:
        winner_key, loser_key = normalize_player_name(row.get("winner_name", "")), normalize_player_name(row.get("loser_name", ""))
        if player_key not in {winner_key, loser_key} or any(flag in (row.get("score") or "").upper() for flag in ("W/O", "RET", "DEF")):
            continue
        won = player_key == winner_key; own, opp = ("w_", "l_") if won else ("l_", "w_")
        try:
            played = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
            values = {name: float(row[own + name]) for name in ("svpt", "1stIn", "1stWon", "2ndWon")}
            for name in ("ace", "df", "bpSaved", "bpFaced"):
                try:
                    values[name] = float(row.get(own + name) or 0)
                except (TypeError, ValueError):
                    values[name] = 0.0
            opp_svpt = float(row[opp + "svpt"]); opp_won = float(row[opp + "1stWon"]) + float(row[opp + "2ndWon"])
            opp_bp_faced = float(row.get(opp + "bpFaced") or 0)
            opp_bp_saved = float(row.get(opp + "bpSaved") or 0)
            opp_service_games = float(row.get(opp + "SvGms") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if played >= cutoff or values["svpt"] <= 0 or opp_svpt <= 0:
            continue
        weight = 0.5 ** (max(0, (cutoff - played).days) / 120)
        if surface and str(row.get("surface", "")).casefold() == surface.casefold():
            weight *= 1.35
        observations.append((played, weight, values, opp_svpt, opp_won, opp_bp_faced, opp_bp_saved, opp_service_games,
                             str(row.get("_source_url") or "historical_match_records")))
    observations.sort(key=lambda item: item[0], reverse=True); observations = observations[:limit]
    service_points = sum(item[1] * item[2]["svpt"] for item in observations)
    return_points = sum(item[1] * item[3] for item in observations)
    if len(observations) < 8 or service_points < 400 or return_points < 400:
        return None
    total = lambda field: sum(item[1] * item[2][field] for item in observations)
    service_won = total("1stWon") + total("2ndWon")
    return_won = sum(item[1] * (item[3] - item[4]) for item in observations)
    break_points = sum(item[1] * item[5] for item in observations)
    breaks = sum(item[1] * max(0.0, item[5] - item[6]) for item in observations)
    return_games = sum(item[1] * item[7] for item in observations)
    bp_faced = total("bpFaced")
    service_probability = service_won / service_points
    return_probability = return_won / return_points
    return {
        "sample": len(observations), "service_points": service_points, "return_points": return_points,
        "ace_rate": total("ace") / service_points, "double_fault_rate": total("df") / service_points,
        "first_serve_in": total("1stIn") / service_points,
        "first_serve_won": total("1stWon") / total("1stIn") if total("1stIn") else None,
        "second_serve_won": total("2ndWon") / max(1, service_points - total("1stIn")),
        "service_points_won": service_probability, "return_points_won": return_probability,
        "break_points_saved": total("bpSaved") / bp_faced if bp_faced else None,
        "break_points_converted": breaks / break_points if break_points else None,
        "break_rate": breaks / return_games if return_games else None,
        "return_games": return_games,
        "hold_probability": hold_probability(service_probability),
        "source": ";".join(dict.fromkeys(item[8] for item in observations)),
    }


def parse_standard_sets(score: str) -> list[tuple[int, int]]:
    """Parse completed conventional sets, excluding match-tiebreak scores."""
    parsed_sets = []
    for token in str(score or "").upper().split():
        parsed = re.fullmatch(r"(\d+)-(\d+)(?:\(\d+\))?", token)
        if not parsed:
            continue
        winner_games, loser_games = int(parsed.group(1)), int(parsed.group(2))
        if max(winner_games, loser_games) <= 7:
            parsed_sets.append((winner_games, loser_games))
    return parsed_sets


def calculate_clutch_profile(history: list[dict], player: str, surface: str | None,
                             as_of: str, limit: int = 50) -> dict | None:
    """Calculate leakage-safe tiebreak and deciding-set records from completed scores."""
    player_key = normalize_player_name(player)
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    matches = []
    for row in history:
        winner_key = normalize_player_name(row.get("winner_name", ""))
        loser_key = normalize_player_name(row.get("loser_name", ""))
        if player_key not in {winner_key, loser_key}:
            continue
        score = str(row.get("score") or "").upper()
        if not score or any(flag in score for flag in ("W/O", "RET", "DEF")):
            continue
        try:
            played = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
        except ValueError:
            continue
        if played >= cutoff:
            continue
        parsed_sets = parse_standard_sets(score)
        if not parsed_sets:
            continue
        won_match = player_key == winner_key
        weight = 0.5 ** ((cutoff - played).days / 730)
        if surface and str(row.get("surface") or "").casefold() == surface.casefold():
            weight *= 1.25
        try:
            best_of = int(row.get("best_of") or (5 if len(parsed_sets) > 3 else 3))
        except (TypeError, ValueError):
            best_of = 5 if len(parsed_sets) > 3 else 3
        tiebreak_results = []
        for winner_games, loser_games in parsed_sets:
            if {winner_games, loser_games} == {6, 7}:
                player_games = winner_games if won_match else loser_games
                tiebreak_results.append(player_games == 7)
        deciding_result = won_match if best_of in {3, 5} and len(parsed_sets) == best_of else None
        matches.append((played, weight, tiebreak_results, deciding_result,
                        str(row.get("_source_url") or "historical_match_records")))
    if not matches:
        return None
    matches.sort(reverse=True); matches = matches[:limit]
    tiebreak_sample = sum(len(item[2]) for item in matches)
    tiebreak_weight = sum(item[1] for item in matches for _ in item[2])
    tiebreak_wins = sum(item[1] for item in matches for won in item[2] if won)
    deciding = [(item[1], item[3]) for item in matches if item[3] is not None]
    deciding_weight = sum(item[0] for item in deciding)
    deciding_wins = sum(weight for weight, won in deciding if won)

    def shrunk(wins: float, total: float) -> float | None:
        return (wins + 2.0) / (total + 4.0) if total else None

    return {
        "match_sample": len(matches),
        "tiebreak_sample": tiebreak_sample, "tiebreak_wins": sum(won for item in matches for won in item[2]),
        "tiebreak_win_rate": shrunk(tiebreak_wins, tiebreak_weight),
        "deciding_set_sample": len(deciding), "deciding_set_wins": sum(won for _, won in deciding),
        "deciding_set_win_rate": shrunk(deciding_wins, deciding_weight),
        "source": ";".join(dict.fromkeys(item[4] for item in matches)),
    }


def calculate_best_of_five_profile(history: list[dict], player: str, surface: str | None,
                                   as_of: str, limit: int = 40) -> dict | None:
    """Build a dedicated leakage-safe profile for completed best-of-five matches."""
    player_key = normalize_player_name(player)
    cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    observations = []
    for row in history:
        winner_key = normalize_player_name(row.get("winner_name", ""))
        loser_key = normalize_player_name(row.get("loser_name", ""))
        if player_key not in {winner_key, loser_key}:
            continue
        try:
            played = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
            best_of = int(row.get("best_of") or 0)
        except (TypeError, ValueError):
            continue
        score = str(row.get("score") or "").upper()
        if played >= cutoff or best_of != 5 or not score or any(flag in score for flag in ("W/O", "RET", "DEF")):
            continue
        sets = parse_standard_sets(score)
        if len(sets) < 3:
            continue
        won_match = player_key == winner_key
        player_set_wins = sum((winner_games > loser_games) if won_match else (loser_games > winner_games)
                              for winner_games, loser_games in sets)
        weight = 0.5 ** ((cutoff - played).days / 1095)
        same_surface = bool(surface and str(row.get("surface") or "").casefold() == surface.casefold())
        if same_surface:
            weight *= 1.20
        lost_first_two = all((winner_games < loser_games) if won_match else (loser_games < winner_games)
                             for winner_games, loser_games in sets[:2])
        observations.append({
            "date": played, "weight": weight, "won": won_match, "sets": len(sets),
            "set_wins": player_set_wins, "same_surface": same_surface,
            "five_set_decider": len(sets) == 5, "comeback_opportunity": lost_first_two,
            "source": str(row.get("_source_url") or "historical_match_records"),
        })
    if not observations:
        return None
    observations.sort(key=lambda item: item["date"], reverse=True); observations = observations[:limit]
    match_weight = sum(item["weight"] for item in observations)
    match_wins = sum(item["weight"] for item in observations if item["won"])
    set_weight = sum(item["weight"] * item["sets"] for item in observations)
    set_wins = sum(item["weight"] * item["set_wins"] for item in observations)
    deciders = [item for item in observations if item["five_set_decider"]]
    decider_weight = sum(item["weight"] for item in deciders)
    decider_wins = sum(item["weight"] for item in deciders if item["won"])
    comebacks = [item for item in observations if item["comeback_opportunity"]]
    comeback_weight = sum(item["weight"] for item in comebacks)
    comeback_wins = sum(item["weight"] for item in comebacks if item["won"])

    def shrunk(wins: float, total: float, prior: float = 4.0) -> float | None:
        return (wins + prior / 2) / (total + prior) if total else None

    return {
        "match_sample": len(observations), "match_wins": sum(item["won"] for item in observations),
        "match_win_rate": shrunk(match_wins, match_weight),
        "set_sample": sum(item["sets"] for item in observations), "set_win_rate": shrunk(set_wins, set_weight, 8.0),
        "same_surface_sample": sum(item["same_surface"] for item in observations),
        "five_set_sample": len(deciders), "five_set_wins": sum(item["won"] for item in deciders),
        "five_set_win_rate": shrunk(decider_wins, decider_weight),
        "comeback_0_2_sample": len(comebacks), "comeback_0_2_wins": sum(item["won"] for item in comebacks),
        "comeback_0_2_rate": shrunk(comeback_wins, comeback_weight),
        "source": ";".join(dict.fromkeys(item["source"] for item in observations)),
    }


def calculate_serve_return_matchup(player_profile: dict | None, opponent_profile: dict | None) -> dict | None:
    if not player_profile or not opponent_profile:
        return None
    player_point = (player_profile["service_points_won"] + (1 - opponent_profile["return_points_won"])) / 2
    opponent_point = (opponent_profile["service_points_won"] + (1 - player_profile["return_points_won"])) / 2
    player_hold, opponent_hold = hold_probability(player_point), hold_probability(opponent_point)
    probability = max(0.25, min(0.75, 0.5 + 0.9 * (player_hold - opponent_hold)))
    return {"probability": probability, "player_hold": player_hold, "opponent_hold": opponent_hold, "sample": min(player_profile["sample"], opponent_profile["sample"])}


def verified_location(latitude, longitude, timezone_name, source: str, as_of: str) -> dict | None:
    """Validate sourced coordinates and resolve the location's UTC offset for the decision date."""
    if not str(source or "").strip():
        return None
    try:
        latitude, longitude = float(latitude), float(longitude)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return None
    except (TypeError, ValueError):
        return None
    timezone_text = str(timezone_name or "").strip()
    offset = None
    if timezone_text:
        try:
            offset = float(timezone_text)
        except ValueError:
            try:
                local = datetime.strptime(as_of, "%Y-%m-%d").replace(hour=12, tzinfo=ZoneInfo(timezone_text))
                offset_delta = local.utcoffset()
                offset = offset_delta.total_seconds() / 3600 if offset_delta is not None else None
            except (ValueError, ZoneInfoNotFoundError):
                fallback_zone = dateutil_tz.gettz(timezone_text)
                if fallback_zone is not None:
                    local = datetime.strptime(as_of, "%Y-%m-%d").replace(hour=12, tzinfo=fallback_zone)
                    offset_delta = local.utcoffset()
                    offset = offset_delta.total_seconds() / 3600 if offset_delta is not None else None
    return {"latitude": latitude, "longitude": longitude, "timezone": timezone_text,
            "utc_offset": offset, "source": str(source).strip()}


def travel_between_locations(previous: dict | None, current: dict | None) -> dict:
    """Calculate great-circle distance and timezone change only from verified locations."""
    result = {"travel_distance_km": None, "timezone_change_hours": None, "travel_source": ""}
    if not previous or not current:
        return result
    lat1, lon1 = math.radians(previous["latitude"]), math.radians(previous["longitude"])
    lat2, lon2 = math.radians(current["latitude"]), math.radians(current["longitude"])
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    arc = 2 * math.asin(math.sqrt(math.sin(delta_lat / 2) ** 2 +
                                  math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2))
    result["travel_distance_km"] = 6371.0088 * arc
    if previous.get("utc_offset") is not None and current.get("utc_offset") is not None:
        result["timezone_change_hours"] = current["utc_offset"] - previous["utc_offset"]
    result["travel_source"] = ";".join(dict.fromkeys((previous["source"], current["source"])))
    return result


def load_verified_tournament_locations(as_of: str) -> dict[str, dict]:
    """Load source-backed tournament coordinates; incomplete or unsourced rows are ignored."""
    locations = {}
    if not TOURNAMENT_LOCATIONS_FILE.exists():
        return locations
    with open(TOURNAMENT_LOCATIONS_FILE, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            name = normalize_player_name(row.get("TOURNAMENT", ""))
            location = verified_location(row.get("LATITUDE"), row.get("LONGITUDE"), row.get("TIMEZONE"),
                                         row.get("SOURCE", ""), as_of)
            if name and location:
                locations[name] = location
    return locations


def calculate_workload(history: list[dict], player: str, as_of: str, current_tournament: str = "",
                       current_surface: str | None = None, current_location: dict | None = None) -> dict:
    """Measure recent match density, sets and rest without inventing unavailable durations."""
    key = normalize_player_name(player); cutoff = datetime.strptime(as_of, "%Y-%m-%d")
    played = []
    for row in history:
        if key not in {normalize_player_name(row.get("winner_name", "")), normalize_player_name(row.get("loser_name", ""))}:
            continue
        try: date = datetime.strptime(str(row.get("tourney_date", "")), "%Y%m%d")
        except ValueError: continue
        if date >= cutoff or any(flag in (row.get("score") or "").upper() for flag in ("W/O", "DEF")): continue
        score = row.get("score") or ""
        sets = sum(1 for token in score.split() if re.search(r"\d", token) and token.upper() not in {"RET"})
        try:
            minutes = float(row.get("minutes"))
            if not 0 < minutes <= 1440:
                raise ValueError
        except (TypeError, ValueError):
            minutes = None
        try:
            best_of = int(row.get("best_of") or 3)
        except (TypeError, ValueError):
            best_of = 3
        long_threshold = 240 if best_of == 5 else 180
        historical_surface = str(row.get("surface") or "").strip().casefold()
        if historical_surface not in {"hard", "clay", "grass", "carpet"}:
            historical_surface = ""
        source = str(row.get("_location_source") or row.get("_source_url") or "")
        historical_location = verified_location(
            row.get("_latitude", row.get("latitude")), row.get("_longitude", row.get("longitude")),
            row.get("_timezone", row.get("timezone")), source, as_of
        )
        played.append((date, max(1, sets), row.get("tourney_name") or row.get("tournament") or "",
                       minutes, str(row.get("_source_url") or "historical_match_records"),
                       best_of, bool(minutes is not None and minutes >= long_threshold), long_threshold,
                       historical_surface, historical_location))
    played.sort(reverse=True)
    last = played[0] if played else None
    matches_7 = sum((cutoff - item[0]).days <= 7 for item in played)
    matches_14 = sum((cutoff - item[0]).days <= 14 for item in played)
    matches_30 = sum((cutoff - item[0]).days <= 30 for item in played)
    sets_7 = sum(item[1] for item in played if (cutoff - item[0]).days <= 7)
    minutes_7 = sum(item[3] for item in played if item[3] is not None and (cutoff - item[0]).days <= 7)
    minutes_14 = sum(item[3] for item in played if item[3] is not None and (cutoff - item[0]).days <= 14)
    minutes_30 = sum(item[3] for item in played if item[3] is not None and (cutoff - item[0]).days <= 30)
    duration_30 = [item for item in played if item[3] is not None and (cutoff - item[0]).days <= 30]
    latest_duration = next((item for item in played if item[3] is not None), None)
    long_matches_7 = [item for item in played if item[6] and (cutoff - item[0]).days <= 7]
    long_matches_30 = [item for item in played if item[6] and (cutoff - item[0]).days <= 30]
    latest_long = next((item for item in played if item[6]), None)
    rest_days = (cutoff - last[0]).days if last else None
    tournament_change = bool(last and last[2] and current_tournament and normalize_player_name(last[2]) != normalize_player_name(current_tournament) and rest_days <= 5)
    current_surface_key = str(current_surface or "").strip().casefold()
    if current_surface_key not in {"hard", "clay", "grass", "carpet"}:
        current_surface_key = ""
    previous_tournament = next((item for item in played if item[2] and current_tournament and
                                normalize_player_name(item[2]) != normalize_player_name(current_tournament)), None)
    previous_surface = previous_tournament[8] if previous_tournament else ""
    surface_change = (previous_surface != current_surface_key
                      if previous_surface and current_surface_key else None)
    travel = travel_between_locations(previous_tournament[9] if previous_tournament else None, current_location)
    penalty = .025 if matches_7 >= 4 or sets_7 >= 10 else .015 if matches_7 >= 3 or sets_7 >= 8 else .01 if rest_days is not None and rest_days <= 1 else 0.0
    if tournament_change and rest_days is not None and rest_days <= 3: penalty += .005
    return {"matches_7": matches_7, "matches_14": matches_14, "matches_30": matches_30,
            "sets_7": sets_7, "rest_days": rest_days,
            "last_match_minutes": last[3] if last else None,
            "latest_verified_minutes": latest_duration[3] if latest_duration else None,
            "latest_duration_date": latest_duration[0].strftime("%Y-%m-%d") if latest_duration else None,
            "minutes_7": minutes_7, "minutes_14": minutes_14, "minutes_30": minutes_30,
            "duration_sample_30": len(duration_30),
            "duration_source": ";".join(dict.fromkeys(item[4] for item in duration_30)),
            "last_match_long": last[6] if last and last[3] is not None else None,
            "last_match_long_threshold": last[7] if last else None,
            "long_matches_7": len(long_matches_7), "long_matches_30": len(long_matches_30),
            "latest_long_match_minutes": latest_long[3] if latest_long else None,
            "latest_long_match_date": latest_long[0].strftime("%Y-%m-%d") if latest_long else None,
            "latest_long_match_days_ago": (cutoff - latest_long[0]).days if latest_long else None,
            "latest_long_match_source": latest_long[4] if latest_long else "",
            "previous_tournament": previous_tournament[2] if previous_tournament else "",
            "previous_tournament_surface": previous_surface or None,
            "previous_tournament_days_ago": (cutoff - previous_tournament[0]).days if previous_tournament else None,
            "surface_transition_source": previous_tournament[4] if previous_tournament else "",
            "current_surface": current_surface_key or None,
            "surface_change": surface_change,
            **travel,
            "tournament_change": tournament_change, "penalty": min(.03, penalty)}


def fetch_recent_match_history(matches: list[dict], date_str: str) -> list[dict]:
    """Download compact current/previous season histories without paid API calls."""
    year = int(date_str[:4])
    urls = [
        f"https://raw.githubusercontent.com/Tennismylife/TML-Database/master/{year - 1}.csv",
        f"https://raw.githubusercontent.com/Tennismylife/TML-Database/master/{year}.csv",
        "https://raw.githubusercontent.com/36-SURE/2026/main/data/wta_matches_2021_2026.csv",
    ]
    history = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for url, text in zip(urls, executor.map(fetch, urls)):
            if text:
                for row in csv.DictReader(io.StringIO(text)):
                    row["_source_url"] = url
                    history.append(row)
    wanted = {normalize_player_name(player) for match in matches for player in (match["player1"], match["player2"])}
    filtered = [row for row in history if normalize_player_name(row.get("winner_name", "")) in wanted or normalize_player_name(row.get("loser_name", "")) in wanted]
    log(f"  Loaded {len(filtered)} relevant historical matches for opponent-adjusted form")
    return filtered


def enrich_matches_with_recent_form(matches: list[dict], date_str: str):
    history = fetch_recent_match_history(matches, date_str)
    tournament_locations = load_verified_tournament_locations(date_str)
    for row in history:
        location = tournament_locations.get(normalize_player_name(row.get("tourney_name") or row.get("tournament") or ""))
        if location:
            row.update({"_latitude": location["latitude"], "_longitude": location["longitude"],
                        "_timezone": location["timezone"], "_location_source": location["source"]})
    official_statuses = load_verified_player_status(date_str)
    for match in matches:
        player_keys = {normalize_player_name(match["player1"]), normalize_player_name(match["player2"])}
        match["source_history"] = [row for row in history if
                                   normalize_player_name(row.get("winner_name", "")) in player_keys or
                                   normalize_player_name(row.get("loser_name", "")) in player_keys]
        match["location"] = (match.get("location") or
                             tournament_locations.get(normalize_player_name(match.get("tournament", ""))))
        match["head_to_head"] = calculate_head_to_head(
            history, match["player1"], match["player2"], match.get("surface"), date_str
        )
        match["player1_recent_form"] = calculate_recent_form(history, match["player1"], match.get("surface"), date_str)
        match["player2_recent_form"] = calculate_recent_form(history, match["player2"], match.get("surface"), date_str)
        match["player1_serve_return"] = calculate_serve_return_profile(history, match["player1"], match.get("surface"), date_str)
        match["player2_serve_return"] = calculate_serve_return_profile(history, match["player2"], match.get("surface"), date_str)
        match["player1_clutch"] = calculate_clutch_profile(history, match["player1"], match.get("surface"), date_str)
        match["player2_clutch"] = calculate_clutch_profile(history, match["player2"], match.get("surface"), date_str)
        match["player1_best_of_five"] = calculate_best_of_five_profile(history, match["player1"], match.get("surface"), date_str)
        match["player2_best_of_five"] = calculate_best_of_five_profile(history, match["player2"], match.get("surface"), date_str)
        match["player1_workload"] = calculate_workload(history, match["player1"], date_str, match.get("tournament", ""), match.get("surface"), match.get("location"))
        match["player2_workload"] = calculate_workload(history, match["player2"], date_str, match.get("tournament", ""), match.get("surface"), match.get("location"))
        for side in ("player1", "player2"):
            ranking_history = calculate_ranking_history(history, match[side], date_str)
            bio = calculate_player_bio(history, match[side], date_str)
            match[f"{side}_ranking_history"] = ranking_history
            match[f"{side}_bio"] = bio
            match[f"{side}_physical_status"] = physical_status_for_player(
                match, side, match[side], official_statuses, history, date_str
            )
            if match.get(f"{side}_profile") is not None:
                match[f"{side}_profile"]["ranking_history"] = ranking_history
                match[f"{side}_profile"]["handedness"] = (bio or {}).get("handedness")
                match[f"{side}_profile"]["nationality"] = (bio or {}).get("nationality")
                match[f"{side}_profile"]["bio_source"] = (bio or {}).get("source")


def tennis_context_uncertainty(match: dict) -> tuple[float, str]:
    text = f"{match.get('tournament', '')} {match.get('level', '')}".casefold()
    if "itf" in text: return .02, "itf"
    if any(token in text for token in ("qualifying", "qualification")): return .015, "qualifying"
    if "challenger" in text: return .01, "challenger"
    return 0.0, "main_draw"


def inferred_best_of(match: dict) -> int:
    try:
        value = int(match.get("best_of"))
        if value in {3, 5}: return value
    except (TypeError, ValueError):
        pass
    text = f"{match.get('tournament', '')} {match.get('level', '')}".casefold()
    slams = ("australian open", "roland garros", "french open", "wimbledon", "us open")
    return 5 if match.get("level") == "ATP" and any(name in text for name in slams) else 3


def load_resolved_predictions(before_date: str | None = None) -> list[dict]:
    """Load only predictions recorded and resolved before the current decision date."""
    if not AUDIT_FILE.exists() or not AUDIT_FILE.stat().st_size:
        return []
    with AUDIT_FILE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row.get("RESULT") in {"W", "L"} and row.get("MODEL_PROBABILITY")
            and (not before_date or (row.get("DATE") or "") < before_date)]


def brier_score(rows: list[dict], probability_field: str) -> float | None:
    usable = []
    for row in rows:
        try:
            probability = float(row.get(probability_field) or "")
        except ValueError:
            continue
        usable.append((probability - (row.get("RESULT") == "W")) ** 2)
    return sum(usable) / len(usable) if usable else None


def probability_metrics(rows: list[dict], probability_field: str = "MODEL_PROBABILITY", bins: int = 10) -> dict:
    """Return proper scoring and fixed-bin calibration metrics for settled predictions."""
    usable = []
    for row in rows:
        if row.get("RESULT") not in {"W", "L"}:
            continue
        try:
            probability = float(row.get(probability_field) or "")
        except (TypeError, ValueError):
            continue
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            continue
        usable.append((probability, 1.0 if row["RESULT"] == "W" else 0.0))
    if not usable:
        return {"sample": 0, "brier": None, "log_loss": None, "ece": None, "bins": bins}
    epsilon = 1e-15
    brier = sum((probability - outcome) ** 2 for probability, outcome in usable) / len(usable)
    log_loss = -sum(
        outcome * math.log(min(1 - epsilon, max(epsilon, probability))) +
        (1 - outcome) * math.log(min(1 - epsilon, max(epsilon, 1 - probability)))
        for probability, outcome in usable
    ) / len(usable)
    calibration_error = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        bucket = [(probability, outcome) for probability, outcome in usable
                  if low <= probability < high or (index == bins - 1 and probability == 1)]
        if bucket:
            mean_probability = sum(item[0] for item in bucket) / len(bucket)
            observed_rate = sum(item[1] for item in bucket) / len(bucket)
            calibration_error += len(bucket) / len(usable) * abs(mean_probability - observed_rate)
    return {"sample": len(usable), "brier": brier, "log_loss": log_loss,
            "ece": calibration_error, "bins": bins}


def learned_component_weights(rows: list[dict]) -> dict | None:
    """Walk-forward challenger weights: train chronologically, require holdout improvement."""
    rows = sorted(rows, key=lambda row: row.get("DATE", ""))
    if len(rows) < MIN_WEIGHT_TRAINING_SAMPLE:
        return None
    split = max(100, int(len(rows) * .7)); training, holdout = rows[:split], rows[split:]
    fields = {"elo": "ELO_PROBABILITY", "market": "MARKET_PROBABILITY", "form": "FORM_PROBABILITY", "serve_return": "SERVE_RETURN_PROBABILITY"}
    inverse = {}
    for name, field in fields.items():
        score = brier_score(training, field)
        if score is not None:
            inverse[name] = 1 / max(score, .01)
    if "elo" not in inverse or "market" not in inverse:
        return None
    total = sum(inverse.values()); weights = {name: value / total for name, value in inverse.items()}
    challenger_errors = []
    for row in holdout:
        available = {name: float(row[field]) for name, field in fields.items() if row.get(field)}
        used = {name: weights[name] for name in available if name in weights}
        if not used:
            continue
        probability = sum(available[name] * weight for name, weight in used.items()) / sum(used.values())
        challenger_errors.append((probability - (row.get("RESULT") == "W")) ** 2)
    active_brier = brier_score(holdout, "MODEL_PROBABILITY")
    challenger_brier = sum(challenger_errors) / len(challenger_errors) if challenger_errors else None
    return {"weights": weights, "sample": len(rows), "holdout": len(holdout),
            "active_brier": active_brier, "challenger_brier": challenger_brier,
            "promoted": bool(active_brier and challenger_brier and challenger_brier <= active_brier * .97)}


def canonical_best_of(value) -> int | None:
    try:
        best_of = int(float(value))
    except (TypeError, ValueError):
        return None
    return best_of if best_of in {3, 5} else None


def learned_format_component_weights(rows: list[dict], best_of: int) -> dict | None:
    """Train an isolated component-weight challenger for one verified match format."""
    format_value = canonical_best_of(best_of)
    if format_value is None:
        return None
    format_rows = [row for row in rows if canonical_best_of(row.get("BEST_OF")) == format_value]
    learned = learned_component_weights(format_rows)
    if learned:
        learned = {**learned, "format": f"BO{format_value}", "format_value": format_value}
    return learned


def canonical_environment(value) -> str | None:
    if isinstance(value, bool):
        return "Indoor" if value else "Outdoor"
    text = str(value or "").strip().casefold()
    if text in {"true", "1", "yes", "indoor"}:
        return "Indoor"
    if text in {"false", "0", "no", "outdoor"}:
        return "Outdoor"
    return None


def learned_environment_component_weights(rows: list[dict], indoor) -> dict | None:
    """Train indoor and outdoor component-weight challengers without cross-environment borrowing."""
    environment = canonical_environment(indoor)
    if environment is None:
        return None
    environment_rows = [row for row in rows if canonical_environment(row.get("INDOOR")) == environment]
    learned = learned_component_weights(environment_rows)
    if learned:
        learned = {**learned, "environment": environment}
    return learned


def component_challenger_probability(learned: dict | None, components: dict[str, float]) -> tuple[float | None, dict]:
    if not learned:
        return None, {}
    used = {name: learned["weights"][name] for name in components if name in learned["weights"]}
    if not used:
        return None, {}
    probability = sum(components[name] * weight for name, weight in used.items()) / sum(used.values())
    return probability, used


def choose_promoted_component_model(candidates: list[dict], rollback: bool) -> dict | None:
    """Choose one proven challenger by relative holdout improvement; never blend overlapping models."""
    if rollback:
        return None
    eligible = [candidate for candidate in candidates if candidate.get("learned") and
                candidate["learned"].get("promoted") and candidate.get("probability") is not None]
    if not eligible:
        return None
    def ratio(candidate):
        active = candidate["learned"].get("active_brier")
        challenger = candidate["learned"].get("challenger_brier")
        return challenger / active if active and challenger is not None else float("inf")
    return min(eligible, key=lambda candidate: (ratio(candidate), candidate["name"]))


def workload_policy_penalty(values: dict, policy: dict) -> float:
    """Apply a bounded workload policy to either live lower-case or audit upper-case fields."""
    def number(lower: str, upper: str, default=0.0):
        try:
            return float(values.get(lower, values.get(upper, default)) or default)
        except (TypeError, ValueError):
            return float(default)

    matches_7 = number("matches_7", "MATCHES_7")
    sets_7 = number("sets_7", "SETS_7")
    rest_days = number("rest_days", "REST_DAYS", 999)
    if matches_7 >= policy["matches_threshold"] or sets_7 >= policy["sets_threshold"]:
        penalty = policy["dense_penalty"]
    elif rest_days <= policy["rest_threshold"]:
        penalty = policy["rest_penalty"]
    else:
        penalty = 0.0
    tournament_change = str(values.get("tournament_change", values.get("TOURNAMENT_CHANGE", ""))).casefold() == "true"
    if tournament_change and rest_days <= 3:
        penalty += .005
    return min(.03, max(0.0, penalty))


def learned_workload_policy(rows: list[dict]) -> dict | None:
    """Fit workload thresholds chronologically and promote only after holdout improvement."""
    usable = []
    for row in sorted(rows, key=lambda item: (item.get("DATE", ""), item.get("EVENT_ID", ""), item.get("PICK", ""))):
        if any(row.get(field, "") == "" for field in ("MATCHES_7", "SETS_7", "REST_DAYS")):
            continue
        try:
            model_probability = float(row.get("MODEL_PROBABILITY") or "")
            active_penalty = float(row.get("WORKLOAD_PENALTY") or 0)
        except (TypeError, ValueError):
            continue
        if row.get("RESULT") not in {"W", "L"}:
            continue
        enriched = dict(row)
        enriched["_BASE_PROBABILITY"] = min(.98, max(.02, model_probability + active_penalty))
        usable.append(enriched)
    if len(usable) < MIN_WORKLOAD_TRAINING_SAMPLE:
        return None
    split = max(140, int(len(usable) * .7))
    training, holdout = usable[:split], usable[split:]
    if len(holdout) < 60:
        return None

    candidates = [
        {"matches_threshold": matches, "sets_threshold": sets, "dense_penalty": dense,
         "rest_threshold": rest, "rest_penalty": rest_penalty}
        for matches in (3, 4, 5)
        for sets in (8, 10, 12)
        for dense in (.01, .015, .02, .025)
        for rest in (0, 1, 2)
        for rest_penalty in (.005, .01)
    ]

    def score(sample: list[dict], policy: dict) -> tuple[float, int]:
        errors, triggered = [], 0
        for row in sample:
            penalty = workload_policy_penalty(row, policy)
            triggered += penalty > 0
            probability = max(.02, row["_BASE_PROBABILITY"] - penalty)
            errors.append((probability - (row["RESULT"] == "W")) ** 2)
        return sum(errors) / len(errors), triggered

    eligible = []
    for policy in candidates:
        training_brier, training_triggered = score(training, policy)
        if training_triggered >= MIN_WORKLOAD_TRIGGER_SAMPLE:
            eligible.append((training_brier, policy, training_triggered))
    if not eligible:
        return None
    training_brier, policy, training_triggered = min(
        eligible, key=lambda item: (item[0], item[1]["matches_threshold"], item[1]["sets_threshold"],
                                    item[1]["dense_penalty"], item[1]["rest_threshold"], item[1]["rest_penalty"])
    )
    holdout_brier, holdout_triggered = score(holdout, policy)
    active_training_brier = brier_score(training, "MODEL_PROBABILITY")
    active_holdout_brier = brier_score(holdout, "MODEL_PROBABILITY")
    promoted = bool(
        active_training_brier is not None and active_holdout_brier is not None
        and training_triggered >= MIN_WORKLOAD_TRIGGER_SAMPLE
        and holdout_triggered >= max(20, MIN_WORKLOAD_TRIGGER_SAMPLE // 2)
        and training_brier <= active_training_brier * .97
        and holdout_brier <= active_holdout_brier * .97
    )
    policy_id = (f"m{policy['matches_threshold']}-s{policy['sets_threshold']}-d{policy['dense_penalty']:.3f}-"
                 f"r{policy['rest_threshold']}-p{policy['rest_penalty']:.3f}")
    return {"policy": policy, "policy_id": policy_id, "sample": len(usable), "training": len(training),
            "holdout": len(holdout), "training_triggered": training_triggered,
            "holdout_triggered": holdout_triggered, "active_training_brier": active_training_brier,
            "challenger_training_brier": training_brier, "active_holdout_brier": active_holdout_brier,
            "challenger_holdout_brier": holdout_brier, "promoted": promoted}


def calibrate_probability(probability: float, rows: list[dict]) -> tuple[float, int]:
    """Apply a shrunk empirical correction only when the local probability bin is mature."""
    bucket = []
    for row in rows:
        try:
            historical = float(row.get("MODEL_PROBABILITY") or "")
        except ValueError:
            continue
        if abs(historical - probability) <= .05:
            bucket.append(row)
    if len(bucket) < MIN_CALIBRATION_SAMPLE:
        return probability, len(bucket)
    actual = sum(row.get("RESULT") == "W" for row in bucket) / len(bucket)
    strength = min(.5, len(bucket) / 500)
    return max(.02, min(.98, probability * (1 - strength) + actual * strength)), len(bucket)


def canonical_tour(value: str | None) -> str:
    text = str(value or "").strip().casefold()
    if "challenger" in text:
        return "Challenger"
    if "itf" in text:
        return "ITF"
    if text == "wta" or text.startswith("wta "):
        return "WTA"
    if text == "atp" or text.startswith("atp "):
        return "ATP"
    return "Unknown"


def calibrate_probability_by_tour(probability: float, rows: list[dict], tour: str | None) -> dict:
    """Calibrate from the current tour only; sparse/unknown segments remain unchanged."""
    segment = canonical_tour(tour)
    if segment == "Unknown":
        return {"probability": probability, "sample": 0, "segment": segment, "applied": False}
    tour_rows = [row for row in rows if canonical_tour(row.get("TOUR")) == segment]
    calibrated, sample = calibrate_probability(probability, tour_rows)
    return {"probability": calibrated, "sample": sample, "segment": segment,
            "applied": sample >= MIN_CALIBRATION_SAMPLE}


def segment_health(match: dict, rows: list[dict]) -> dict:
    """Suspend a mature surface/tour segment only when ROI and CLV both confirm harm."""
    surface, tour = match.get("surface") or "Unknown", match.get("level") or "Unknown"
    segment = [row for row in rows if (row.get("SURFACE") or "Unknown") == surface and (row.get("TOUR") or "Unknown") == tour]
    roi = sum((float(row.get("OPENING_ODDS") or 0) - 1) if row["RESULT"] == "W" else -1 for row in segment) / len(segment) if segment else None
    clv = [float(row["CLV"]) for row in segment if row.get("CLV")]
    average_clv = sum(clv) / len(clv) if clv else None
    suspended = len(segment) >= MIN_SEGMENT_SAMPLE and roi is not None and roi < -.05 and average_clv is not None and average_clv < -.02
    return {"sample": len(segment), "roi": roi, "clv": average_clv, "suspended": suspended}


def tennis_kill_switch(rows: list[dict], window: int = 30) -> dict:
    ordered = sorted(rows, key=lambda row: row.get("DATE", ""))
    if len(ordered) < window * 2: return {"active": False, "reason": "insufficient_data", "sample": len(ordered)}
    previous, recent = ordered[-2 * window:-window], ordered[-window:]
    old_brier, new_brier = brier_score(previous, "MODEL_PROBABILITY"), brier_score(recent, "MODEL_PROBABILITY")
    old_clv = [float(row["CLV"]) for row in previous if row.get("CLV")]; new_clv = [float(row["CLV"]) for row in recent if row.get("CLV")]
    clv_drop = bool(old_clv and new_clv and sum(new_clv) / len(new_clv) < sum(old_clv) / len(old_clv) - .04)
    calibration_drop = bool(old_brier and new_brier and new_brier > old_brier * 1.20)
    return {"active": calibration_drop or clv_drop, "reason": "calibration_or_clv_drift" if calibration_drop or clv_drop else "stable", "sample": len(ordered)}


def automated_rollback_state(rows: list[dict], window: int = 30) -> dict:
    """Revert learned model/policy behavior when mature live evidence deteriorates."""
    ordered = sorted(rows, key=lambda row: row.get("DATE", ""))
    promoted = [row for row in ordered if str(row.get("CHALLENGER_PROMOTED", "")).casefold() == "true"
                and row.get("RAW_PROBABILITY") and row.get("MODEL_PROBABILITY")][-window:]
    active_brier = brier_score(promoted, "MODEL_PROBABILITY")
    baseline_errors = []
    for row in promoted:
        try:
            probability = float(row["RAW_PROBABILITY"]) - float(row.get("CONTEXT_PENALTY") or 0) - float(row.get("WORKLOAD_PENALTY") or 0)
            baseline_errors.append((max(.02, min(.98, probability)) - (row.get("RESULT") == "W")) ** 2)
        except (TypeError, ValueError):
            pass
    baseline_brier = sum(baseline_errors) / len(baseline_errors) if baseline_errors else None
    model_rollback = bool(
        len(promoted) >= window and active_brier is not None and baseline_brier is not None
        and active_brier > baseline_brier * 1.10
    )

    authorized = [row for row in ordered if row.get("DECISION") in {"Top Pick", "Value Pick"}
                  and row.get("RESULT") in {"W", "L"}][-window:]
    roi = None
    if authorized:
        returns = []
        for row in authorized:
            try:
                returns.append(float(row.get("OPENING_ODDS") or 0) - 1 if row["RESULT"] == "W" else -1)
            except ValueError:
                pass
        roi = sum(returns) / len(returns) if returns else None
    clv = []
    for row in authorized:
        try:
            if row.get("CLV"):
                clv.append(float(row["CLV"]))
        except ValueError:
            pass
    average_clv = sum(clv) / len(clv) if clv else None
    policy_rollback = bool(
        len(authorized) >= window and roi is not None and roi < -.05
        and average_clv is not None and average_clv < -.02
    )
    return {
        "model_mode": "static_baseline" if model_rollback else "eligible_for_challenger",
        "policy_mode": "safe_baseline" if policy_rollback else "standard",
        "model_rollback": model_rollback,
        "policy_rollback": policy_rollback,
        "model_sample": len(promoted),
        "active_brier": active_brier,
        "baseline_brier": baseline_brier,
        "policy_sample": len(authorized),
        "policy_roi": roi,
        "policy_clv": average_clv,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_rollback_state(rows: list[dict] | None = None) -> dict:
    state = automated_rollback_state(rows if rows is not None else load_resolved_predictions())
    atomic_write_text(ROLLBACK_STATE_FILE, json.dumps(state, indent=2) + "\n")
    return state


def calculate_tennis_baseline(match: dict, player: str) -> dict | None:
    """Blend de-vigged two-way market probability with independent overall Elo."""
    if "/" in match.get("player1", "") or "/" in match.get("player2", ""):
        return None
    home_odds = match.get("home_odds")
    away_odds = match.get("away_odds")
    if not all(isinstance(odds, (int, float)) and odds > 1 for odds in (home_odds, away_odds)):
        return None
    match_best_of = inferred_best_of(match)

    player_key = normalize_player_name(player)
    if player_key == normalize_player_name(match["player1"]):
        player_odds = float(home_odds)
        player_profile = match.get("player1_profile")
        opponent_profile = match.get("player2_profile")
        recent_form = match.get("player1_recent_form")
        player_serve_profile = match.get("player1_serve_return")
        serve_return = calculate_serve_return_matchup(player_serve_profile, match.get("player2_serve_return"))
        clutch = match.get("player1_clutch") or {}
        best_of_five_profile = match.get("player1_best_of_five") or {}
        physical_status = match.get("player1_physical_status") or {"status": "unknown"}
        workload = match.get("player1_workload") or {}
        h2h_probability = (match.get("head_to_head") or {}).get("player1_probability")
    elif player_key == normalize_player_name(match["player2"]):
        player_odds = float(away_odds)
        player_profile = match.get("player2_profile")
        opponent_profile = match.get("player1_profile")
        recent_form = match.get("player2_recent_form")
        player_serve_profile = match.get("player2_serve_return")
        serve_return = calculate_serve_return_matchup(player_serve_profile, match.get("player1_serve_return"))
        clutch = match.get("player2_clutch") or {}
        best_of_five_profile = match.get("player2_best_of_five") or {}
        physical_status = match.get("player2_physical_status") or {"status": "unknown"}
        workload = match.get("player2_workload") or {}
        h2h_probability = (match.get("head_to_head") or {}).get("player2_probability")
    else:
        return None
    active_best_of_five = best_of_five_profile if match_best_of == 5 else {}
    physical_block = str(physical_status.get("status") or "unknown").casefold() in BLOCKING_PHYSICAL_STATUSES

    consensus_home = match.get("consensus_home_odds") or home_odds
    consensus_away = match.get("consensus_away_odds") or away_odds
    overround = 1 / float(consensus_home) + 1 / float(consensus_away)
    consensus_player_odds = float(consensus_home) if player_key == normalize_player_name(match["player1"]) else float(consensus_away)
    market_probability = (1 / consensus_player_odds) / overround
    surface = match.get("surface")
    elo_field = f"{surface}_elo" if surface in {"hard", "clay", "grass"} else "elo"
    try:
        player_elo = float(player_profile.get(elo_field) or player_profile["elo"])
        opponent_elo = float(opponent_profile.get(elo_field) or opponent_profile["elo"])
    except (KeyError, TypeError, ValueError):
        return None
    elo_probability = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    if recent_form and serve_return:
        assessed_probability = 0.40 * elo_probability + 0.30 * market_probability + 0.15 * recent_form["probability"] + 0.15 * serve_return["probability"]
        component_weights = "elo=.40;market=.30;form=.15;serve_return=.15"
    elif recent_form and recent_form.get("sample", 0) >= 8:
        assessed_probability = 0.50 * elo_probability + 0.35 * market_probability + 0.15 * recent_form["probability"]
        component_weights = "elo=.50;market=.35;form=.15;serve_return=0"
    elif serve_return:
        assessed_probability = 0.50 * elo_probability + 0.35 * market_probability + 0.15 * serve_return["probability"]
        component_weights = "elo=.50;market=.35;form=0;serve_return=.15"
    else:
        assessed_probability = 0.55 * elo_probability + 0.45 * market_probability
        component_weights = "elo=.55;market=.45;form=0;serve_return=0"
    decision_date = str(match.get("start_time") or "")[:10] or None
    history = load_resolved_predictions(decision_date)
    format_challenger = learned_format_component_weights(history, match_best_of)
    environment_challenger = learned_environment_component_weights(history, match.get("indoor"))
    rollback = automated_rollback_state(history)
    components = {"elo": elo_probability, "market": market_probability}
    if recent_form:
        components["form"] = recent_form["probability"]
    if serve_return:
        components["serve_return"] = serve_return["probability"]
    format_probability, format_used = component_challenger_probability(format_challenger, components)
    environment_probability, environment_used = component_challenger_probability(environment_challenger, components)
    candidates = [
        {"name": f"format:BO{match_best_of}", "learned": format_challenger,
         "probability": format_probability, "weights": format_used},
        {"name": f"environment:{canonical_environment(match.get('indoor')) or 'Unknown'}",
         "learned": environment_challenger, "probability": environment_probability, "weights": environment_used},
    ]
    selected_challenger = choose_promoted_component_model(candidates, rollback["model_rollback"])
    shadow_challenger = selected_challenger or next((candidate for candidate in candidates if candidate["probability"] is not None), None)
    challenger_probability = shadow_challenger["probability"] if shadow_challenger else None
    challenger = shadow_challenger["learned"] if shadow_challenger else None
    active_component_model = "static"
    if selected_challenger:
        assessed_probability = selected_challenger["probability"]
        active_component_model = selected_challenger["name"]
        component_weights = "learned:" + ";".join(
            f"{name}={weight:.3f}" for name, weight in sorted(selected_challenger["weights"].items())
        )
    h2h_weight = float((match.get("head_to_head") or {}).get("model_weight") or 0)
    if h2h_probability is not None and h2h_weight > 0:
        assessed_probability = (1 - h2h_weight) * assessed_probability + h2h_weight * float(h2h_probability)
        component_weights += f";h2h={h2h_weight:.3f}"
    raw_probability = assessed_probability
    calibration = calibrate_probability_by_tour(assessed_probability, history, match.get("level"))
    assessed_probability, calibration_sample = calibration["probability"], calibration["sample"]
    context_penalty, context_reason = tennis_context_uncertainty(match)
    static_workload_penalty = float(workload.get("penalty") or 0)
    workload_challenger = learned_workload_policy(history)
    workload_policy_promoted = bool(workload_challenger and workload_challenger["promoted"] and not rollback["model_rollback"])
    workload_penalty = (workload_policy_penalty(workload, workload_challenger["policy"])
                        if workload_policy_promoted else static_workload_penalty)
    assessed_probability = max(.02, assessed_probability - context_penalty - workload_penalty)
    health = segment_health(match, history)
    kill_switch = tennis_kill_switch(history)
    ev = assessed_probability * player_odds - 1
    uncertainty_margin = .015 if recent_form and serve_return else .025
    risk_adjusted_ev = max(.02, assessed_probability - uncertainty_margin) * player_odds - 1
    score = max(0.0, min(10.0, 6.0 + max(0.0, ev) * 30))
    return {
        "player_odds": player_odds,
        "market_probability": market_probability,
        "elo_probability": elo_probability,
        "form_probability": recent_form["probability"] if recent_form else None,
        "form_sample": recent_form["sample"] if recent_form else 0,
        "serve_return_probability": serve_return["probability"] if serve_return else None,
        "serve_return_sample": serve_return["sample"] if serve_return else 0,
        "h2h_probability": h2h_probability,
        "h2h_sample": (match.get("head_to_head") or {}).get("sample", 0),
        "h2h_surface_sample": (match.get("head_to_head") or {}).get("surface_sample", 0),
        "h2h_weight": h2h_weight,
        "expected_hold": serve_return["player_hold"] if serve_return else None,
        "opponent_expected_hold": serve_return["opponent_hold"] if serve_return else None,
        "break_rate": (player_serve_profile or {}).get("break_rate"),
        "break_points_converted": (player_serve_profile or {}).get("break_points_converted"),
        "break_return_games": (player_serve_profile or {}).get("return_games", 0),
        "serve_return_source": (player_serve_profile or {}).get("source", ""),
        "tiebreak_win_rate": clutch.get("tiebreak_win_rate"),
        "tiebreak_sample": clutch.get("tiebreak_sample", 0),
        "deciding_set_win_rate": clutch.get("deciding_set_win_rate"),
        "deciding_set_sample": clutch.get("deciding_set_sample", 0),
        "clutch_source": clutch.get("source", ""),
        "bo5_match_win_rate": active_best_of_five.get("match_win_rate"),
        "bo5_match_sample": active_best_of_five.get("match_sample", 0),
        "bo5_set_win_rate": active_best_of_five.get("set_win_rate"),
        "bo5_set_sample": active_best_of_five.get("set_sample", 0),
        "bo5_same_surface_sample": active_best_of_five.get("same_surface_sample", 0),
        "bo5_five_set_win_rate": active_best_of_five.get("five_set_win_rate"),
        "bo5_five_set_sample": active_best_of_five.get("five_set_sample", 0),
        "bo5_comeback_0_2_rate": active_best_of_five.get("comeback_0_2_rate"),
        "bo5_comeback_0_2_sample": active_best_of_five.get("comeback_0_2_sample", 0),
        "bo5_source": active_best_of_five.get("source", ""),
        "physical_status": physical_status.get("status", "unknown"),
        "physical_status_detail": physical_status.get("detail", ""),
        "physical_status_source": physical_status.get("source", ""),
        "physical_status_expires": physical_status.get("expires_date", ""),
        "physical_block": physical_block,
        "component_weights": component_weights,
        "raw_probability": raw_probability,
        "challenger_probability": challenger_probability,
        "challenger_sample": challenger["sample"] if challenger else 0,
        "challenger_promoted": bool(selected_challenger),
        "format_model": f"BO{match_best_of}",
        "format_model_probability": format_probability,
        "format_model_sample": format_challenger["sample"] if format_challenger else 0,
        "format_model_holdout": format_challenger["holdout"] if format_challenger else 0,
        "format_model_promoted": bool(format_challenger and format_challenger["promoted"] and not rollback["model_rollback"]),
        "environment_model": canonical_environment(match.get("indoor")) or "Unknown",
        "environment_model_probability": environment_probability,
        "environment_model_sample": environment_challenger["sample"] if environment_challenger else 0,
        "environment_model_holdout": environment_challenger["holdout"] if environment_challenger else 0,
        "environment_model_promoted": bool(environment_challenger and environment_challenger["promoted"] and not rollback["model_rollback"]),
        "active_component_model": active_component_model,
        "calibration_sample": calibration_sample,
        "calibration_segment": calibration["segment"],
        "calibration_applied": calibration["applied"],
        "context_penalty": context_penalty,
        "context_reason": context_reason,
        "workload_penalty": workload_penalty,
        "static_workload_penalty": static_workload_penalty,
        "workload_policy_id": workload_challenger["policy_id"] if workload_challenger else "static-v1",
        "workload_policy_sample": workload_challenger["sample"] if workload_challenger else 0,
        "workload_policy_holdout": workload_challenger["holdout"] if workload_challenger else 0,
        "workload_policy_active_brier": workload_challenger["active_holdout_brier"] if workload_challenger else None,
        "workload_policy_challenger_brier": workload_challenger["challenger_holdout_brier"] if workload_challenger else None,
        "workload_policy_promoted": workload_policy_promoted,
        "workload": workload,
        "best_of": match_best_of,
        "indoor": match.get("indoor"),
        "segment_sample": health["sample"],
        "segment_roi": health["roi"],
        "segment_clv": health["clv"],
        "segment_suspended": health["suspended"],
        "kill_switch": kill_switch["active"],
        "kill_switch_reason": kill_switch["reason"],
        "uncertainty_margin": uncertainty_margin,
        "risk_adjusted_ev": risk_adjusted_ev,
        "assessed_probability": assessed_probability,
        "ev": ev,
        "score": score,
        "market_overround": overround,
        "elo_market_gap": abs(elo_probability - market_probability),
        "elo_type": elo_field,
    }


def tennis_baseline_is_reliable(baseline: dict | None) -> bool:
    return bool(
        baseline
        and 0.98 <= baseline["market_overround"] <= MAX_MARKET_OVERROUND
        and baseline["elo_market_gap"] <= MAX_ELO_MARKET_GAP
        and not baseline.get("segment_suspended")
        and not baseline.get("kill_switch")
        and not baseline.get("physical_block")
    )


def build_statistical_candidates(matches: list[dict], odds_min: float, odds_max: float) -> list[dict]:
    """Scan all eligible singles players independently of model output."""
    candidates = []
    for match in matches:
        for player, opponent in (
            (match["player1"], match["player2"]),
            (match["player2"], match["player1"]),
        ):
            baseline = calculate_tennis_baseline(match, player)
            if (
                tennis_baseline_is_reliable(baseline)
                and odds_min <= baseline["player_odds"] <= odds_max
                and baseline["ev"] > 0
            ):
                candidates.append({
                    "player": player,
                    "opponent": opponent,
                    "score": baseline["score"],
                    "assessed_probability": baseline["assessed_probability"],
                })
    return candidates


def select_analysis_matches(matches: list[dict], limit: int = MAX_AI_MATCHES) -> list[dict]:
    ranked = []
    for index, match in enumerate(matches):
        baselines = [
            calculate_tennis_baseline(match, match["player1"]),
            calculate_tennis_baseline(match, match["player2"]),
        ]
        best_ev = max(
            (item["ev"] for item in baselines if tennis_baseline_is_reliable(item)),
            default=-999,
        )
        ranked.append((best_ev, -index, match))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:limit]]


# ─── Stage 2 & 3: AI Analysis ───────────────────────────────────────

def build_prompt(
    date_str: str,
    matches: list[dict],
    bankroll: float | None,
    odds_min: float,
    odds_max: float,
) -> str:
    """Construct the full 3-stage prompt with embedded data."""
    profiles = {
        normalize_player_name(player): profile
        for match in matches
        for player, profile in (
            (match["player1"], match.get("player1_profile")),
            (match["player2"], match.get("player2_profile")),
        )
        if profile
    }
    if not profiles and matches:
        profiles = enrich_matches_with_profiles(matches)

    # Build match data section
    match_lines = []
    for i, m in enumerate(matches, 1):
        market_odds = (
            f"{m['player1']} {m['home_odds']:.2f}, {m['player2']} {m['away_odds']:.2f}"
            if m.get("home_odds") is not None and m.get("away_odds") is not None
            else str(m.get("odds", "N/A"))
        )
        baseline_lines = []
        for player in (m["player1"], m["player2"]):
            baseline = calculate_tennis_baseline(m, player)
            if baseline:
                form_text = (
                    f"{baseline['form_probability']:.1%} (n={baseline['form_sample']})"
                    if baseline.get("form_probability") is not None else "unavailable"
                )
                serve_text = (
                    f"{baseline['serve_return_probability']:.1%} (n={baseline['serve_return_sample']}, hold {baseline['expected_hold']:.1%} vs {baseline['opponent_expected_hold']:.1%})"
                    if baseline.get("serve_return_probability") is not None else "unavailable"
                )
                h2h_text = (
                    f"{baseline['h2h_probability']:.1%} (n={baseline['h2h_sample']}, same surface={baseline['h2h_surface_sample']}, weight={baseline['h2h_weight']:.1%})"
                    if baseline.get("h2h_probability") is not None else "unavailable"
                )
                clutch_parts = []
                if baseline.get("break_rate") is not None:
                    clutch_parts.append(f"break rate {baseline['break_rate']:.1%}")
                if baseline.get("tiebreak_win_rate") is not None:
                    clutch_parts.append(f"tiebreak {baseline['tiebreak_win_rate']:.1%} (n={baseline['tiebreak_sample']})")
                if baseline.get("deciding_set_win_rate") is not None:
                    clutch_parts.append(f"deciding set {baseline['deciding_set_win_rate']:.1%} (n={baseline['deciding_set_sample']})")
                clutch_text = ", ".join(clutch_parts) if clutch_parts else "unavailable"
                bo5_parts = []
                if baseline.get("bo5_match_win_rate") is not None:
                    bo5_parts.append(f"matches {baseline['bo5_match_win_rate']:.1%} (n={baseline['bo5_match_sample']})")
                if baseline.get("bo5_set_win_rate") is not None:
                    bo5_parts.append(f"sets {baseline['bo5_set_win_rate']:.1%} (n={baseline['bo5_set_sample']})")
                if baseline.get("bo5_five_set_win_rate") is not None:
                    bo5_parts.append(f"five-set deciders {baseline['bo5_five_set_win_rate']:.1%} (n={baseline['bo5_five_set_sample']})")
                if baseline.get("bo5_comeback_0_2_rate") is not None:
                    bo5_parts.append(f"0-2 comebacks {baseline['bo5_comeback_0_2_rate']:.1%} (n={baseline['bo5_comeback_0_2_sample']})")
                if baseline.get("bo5_match_sample"):
                    bo5_parts.append(f"same-surface matches n={baseline['bo5_same_surface_sample']}")
                bo5_text = ", ".join(bo5_parts) if bo5_parts else "not applicable/unavailable"
                physical_text = baseline.get("physical_status") or "unknown"
                if baseline.get("physical_status_detail"):
                    physical_text += f" ({baseline['physical_status_detail']})"
                workload = baseline.get("workload") or {}
                travel_text = (f"{workload['travel_distance_km']:.0f} km"
                               if workload.get("travel_distance_km") is not None else "unknown")
                timezone_text = (f"{workload['timezone_change_hours']:+g}h"
                                 if workload.get("timezone_change_hours") is not None else "unknown")
                workload_text = (
                    f"rest={workload.get('rest_days', 'N/A')}d, matches 7/14/30d="
                    f"{workload.get('matches_7', 0)}/{workload.get('matches_14', 0)}/{workload.get('matches_30', 0)}, "
                    f"sets 7d={workload.get('sets_7', 0)}, verified minutes 7/14/30d="
                    f"{workload.get('minutes_7', 0):g}/{workload.get('minutes_14', 0):g}/{workload.get('minutes_30', 0):g} "
                    f"(30d duration n={workload.get('duration_sample_30', 0)}), long matches 7/30d="
                    f"{workload.get('long_matches_7', 0)}/{workload.get('long_matches_30', 0)}, "
                    f"last match long={'unknown' if workload.get('last_match_long') is None else workload.get('last_match_long')}"
                    f", previous tournament={workload.get('previous_tournament') or 'unknown'} "
                    f"({workload.get('previous_tournament_surface') or 'unknown'} -> "
                    f"{workload.get('current_surface') or 'unknown'}, surface change="
                    f"{'unknown' if workload.get('surface_change') is None else workload.get('surface_change')}), "
                    f"verified travel={travel_text}, timezone change={timezone_text}"
                    f", workload policy={baseline.get('workload_policy_id', 'static-v1')} "
                    f"(n={baseline.get('workload_policy_sample', 0)}, promoted={baseline.get('workload_policy_promoted', False)})"
                )
                baseline_lines.append(
                    f"  Python baseline for {player}: market fair "
                    f"{baseline['market_probability']:.1%}, Elo "
                    f"{baseline['elo_probability']:.1%}, opponent-adjusted form {form_text}, serve/return {serve_text}, H2H {h2h_text}, clutch {clutch_text}, BO5 {bo5_text}, physical status {physical_text}, workload {workload_text}, "
                    f"format model {baseline.get('format_model', 'unknown')} "
                    f"(n={baseline.get('format_model_sample', 0)}, promoted={baseline.get('format_model_promoted', False)}), "
                    f"environment model {baseline.get('environment_model', 'Unknown')} "
                    f"(n={baseline.get('environment_model_sample', 0)}, promoted={baseline.get('environment_model_promoted', False)}), "
                    f"active component model={baseline.get('active_component_model', 'static')}, "
                    f"tour calibration {baseline.get('calibration_segment', 'Unknown')} "
                    f"(n={baseline.get('calibration_sample', 0)}, applied={baseline.get('calibration_applied', False)}), blended assessed "
                    f"{baseline['assessed_probability']:.1%}, EV "
                    f"{baseline['ev']:.2%}, score {baseline['score']:.2f}"
                )
        match_lines.append(
            f"Match {i}: {m['player1']} vs {m['player2']}\n"
            f"  Tournament: {m['tournament']} ({m['level']})\n"
            f"  Moneyline odds: {market_odds} (source: {m.get('odds_source', 'N/A')})\n"
            + "\n".join(baseline_lines)
        )

    matches_text = "\n".join(match_lines) if match_lines else "No matches found in odds range."

    prompt = f"""You are a tennis betting analyst executing a 3-stage pipeline for matches on {date_str}.

## RAW DATA COLLECTED

Matches in odds range [{odds_min}-{odds_max}]:

{matches_text}

## Player Profile Data

"""

    seen_players = set()
    for match in matches:
        for player in (match["player1"], match["player2"]):
            key = normalize_player_name(player)
            if key not in seen_players:
                prompt += compact_profile_line(player, profiles) + "\n"
                seen_players.add(key)
    prompt += (
        "\nSources: Tennis Abstract weekly Elo leaderboards and dated historical "
        "match records. Any current form, H2H, serve/return, physical-status, or "
        "tactical field not explicitly shown above is unavailable and MUST NOT be invented.\n"
    )

    # Add the analysis instructions
    prompt += f"""

## ANALYSIS INSTRUCTIONS

You MUST now perform the full 3-stage pipeline using only the verified matches
and odds above. Historical knowledge may provide context, but do not present it
as current form, injury news, or confirmed availability. If no verified matches
are supplied, return no picks and explain that live data was unavailable.

### STAGE 1 — Verification & Refinement
Review the match data above. Verify the tournament levels and identify any issues. Cross-reference with your knowledge of tennis schedules.

### STAGE 2 — Performance Analysis
For each player whose odds fall within {odds_min}-{odds_max}, analyze:

1. **Recent form**: Assess based on the player data above and your knowledge
2. **Head-to-head**: Note if profiles show H2H data
3. **Surface suitability**: Note surface stats from profiles
4. **Physical condition**: Flag any concerns
5. **Tournament context**: Assess the matchup

Score each player 1-10 on the Five-Factor system:
- Recent Form (25%)
- Surface Suitability (25%)
- Head-to-Head (15%)
- Physical & Context (20%)
- Opponent Quality (15%)

Then calculate: Total = (Form×0.25) + (Surface×0.25) + (H2H×0.15) + (Physical×0.20) + (Opponent×0.15)

Grade: 8.5-10 Elite | 7.0-8.4 Strong | 5.5-6.9 Moderate | <5.5 Weak

For each candidate, calculate:
- Implied Probability = 1 / odds
- Your assessed probability
- Expected Value = (assessed_prob × odds) - 1

Python's de-vigged market/Elo blend is authoritative in GitHub mode. Copy its
score and assessed probability exactly; do not substitute model intuition.

Run the Red Flag checklist:
- Lost 3+ consecutive?
- 3rd match in 4 days?
- Recent retirement/medical timeout?
- Losing H2H?
- Odds lengthened significantly?
- Career win % on surface below 45%?

### STAGE 3 — Recommendations

Assign final calls:

- **Top Pick** (score > 8.0, EV > 8%)
- **Value Pick** (score > 7.0, EV > 5%)
- **Moderate Pick / Watchlist** (score > 5.5, EV > 0%; no stake)
- **No Bet** (everything else)
"""

    if bankroll is not None:
        prompt += f"""

### Staking (Tiered Proportional Betting)
Current bankroll: €{bankroll:.2f}

For each recommendation, include:
- Top Pick: €{bankroll * 0.03:.2f} (3% of bankroll)
- Value Pick: €{bankroll * 0.02:.2f} (2% of bankroll)
- Moderate Pick: watchlist only (no stake)
"""

    prompt += """

### Report Format
Present your output with these sections:

## MARKET OVERVIEW
Brief summary of the day's matches in this odds range.

## TOP PICKS
Player, opponent, tournament, level, odds, EV, assessed win %, stake, key stats, rationale.

## VALUE PICKS
Same format as above, for lower-confidence picks.

## PICKS TO AVOID
Players whose odds look appealing but the numbers don't support it.

## DISCLAIMER
Odds change, no guarantees, bet responsibly.

## MACHINE READABLE PICKS
End the report with exactly one JSON array in a fenced `json` block. Include only
players you recommend. Every object must contain:
`player`, `opponent`, `score`, and `assessed_probability`.
Use a 1-10 score and a probability from 0 to 1. Do not include odds, EV, grade,
or stake in this JSON because the application calculates those from verified
bookmaker data. Use an empty array when there are no justified recommendations.

### Tone
Direct and analytical. Quantify confidence. No marketing language. Aim for 500-800 words of dense analysis.
"""
    return prompt


def call_ai(prompt: str, api_keys: list[str]) -> str:
    """Call Groq, rotating API keys while keeping the model fixed."""
    if not api_keys:
        raise ValueError("No Groq API keys configured")
    provider = "api.groq.com"
    if not allow_provider_request(provider):
        raise RuntimeError("Groq circuit is open")

    last_response = None
    for key_index, api_key in enumerate(api_keys):
        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_COMPLETION_TOKENS,
            "temperature": 0.3,
        }
        log(
            f"Calling Groq API ({GROQ_MODEL}, "
            f"key {key_index + 1}/{len(api_keys)})..."
        )
        rotate_key = False
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=120,
                )
                record_api_quota("Groq", response, f"key-{key_index + 1}")
                last_response = response
                if response.status_code in {401, 403, 429} and key_index < len(api_keys) - 1:
                    log(f"  Groq key unavailable ({response.status_code}); rotating to next key")
                    rotate_key = True
                    break
                if response.status_code in TRANSIENT_HTTP_STATUSES and attempt < MAX_TRANSIENT_RETRIES:
                    wait_before_retry("Groq", attempt, response)
                    continue
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                record_provider_success(provider)
                log(f"Groq response: {len(content)} chars")
                return content
            except requests.RequestException as exc:
                if attempt < MAX_TRANSIENT_RETRIES and getattr(exc, "response", None) is None:
                    wait_before_retry("Groq", attempt)
                    continue
                log(f"Groq API error: {exc}")
                if exc.response is not None:
                    log(f"Response body: {exc.response.text[:500]}")
                record_provider_failure(provider, type(exc).__name__)
                raise
            except (KeyError, IndexError, ValueError) as exc:
                log(f"Groq API error: {exc}")
                record_provider_failure(provider, type(exc).__name__)
                raise
        if rotate_key:
            continue

    if last_response is not None:
        last_response.raise_for_status()
    raise RuntimeError("No Groq models were available")


# ─── Stage 4: Logging ───────────────────────────────────────────────

def parse_recommendations(report: str) -> list[dict]:
    """Parse recommended bets from the AI's Markdown report."""
    json_blocks = re.findall(r"```json\s*(.*?)```", report, re.IGNORECASE | re.DOTALL)
    for block in reversed(json_blocks):
        try:
            items = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(items, list):
            continue
        recommendations = []
        for item in items:
            if not isinstance(item, dict) or not item.get("player"):
                continue
            try:
                score = float(item["score"])
                probability = float(item["assessed_probability"])
            except (KeyError, TypeError, ValueError):
                continue
            recommendations.append({
                "player": str(item["player"]).strip(),
                "opponent": str(item.get("opponent", "")).strip(),
                "score": score,
                "assessed_probability": probability,
            })
        return recommendations

    recommendations = []
    current_type = None
    last_player = None

    for line in report.split("\n"):
        line_lower = line.strip().lower()
        line_clean = re.sub(r"\*+", "", line.strip().lstrip("-# ")).strip()
        line_clean = re.sub(r"^\d+[.)]\s*", "", line_clean)

        if "## top picks" in line_lower or "## top pick" in line_lower:
            current_type = "Top Pick"
            last_player = None
            continue
        if "## value picks" in line_lower or "## value pick" in line_lower:
            current_type = "Value Pick"
            last_player = None
            continue
        if "## picks to avoid" in line_lower or "## avoid" in line_lower:
            current_type = None
            last_player = None
            continue
        if line_lower.startswith("## "):
            current_type = None
            last_player = None
            continue

        if not current_type:
            continue

        player_match = re.search(
            r'^(.+?)\s+v(?:s)?\.?\s+(.+)$',
            line_clean,
            flags=re.IGNORECASE,
        )
        if player_match:
            last_player = player_match.group(1).strip()

        odds_match = None
        if re.match(r'^odds?\s*:', line_clean, re.IGNORECASE):
            odds_match = re.search(r'\b([1-9]\d*\.\d+)\b', line_clean)
        if odds_match and last_player:
            try:
                odds_val = float(odds_match.group(1))
                recommendations.append({
                    "player": last_player,
                    "odds": odds_val,
                    "grade": current_type,
                })
                last_player = None
            except ValueError:
                pass

    return recommendations


def normalize_player_name(name: str) -> str:
    """Normalize bookmaker/model name order and punctuation for comparisons."""
    name = re.sub(r"\s*\(\d{4}\)\s*$", "", name)
    if "," in name:
        parts = [part.strip() for part in name.split(",", 1)]
        name = f"{parts[1]} {parts[0]}"
    ascii_name = unicodedata.normalize("NFKD", name.casefold()).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_name)


def validate_recommendations(
    recommendations: list[dict],
    matches: list[dict],
    odds_min: float | None = None,
    odds_max: float | None = None,
) -> list[dict]:
    """Authorize picks from verified odds and the Python Elo/market baseline."""
    validated = []
    for recommendation in recommendations:
        player_key = normalize_player_name(recommendation.get("player", ""))
        try:
            score = float(recommendation["score"])
            probability = float(recommendation["assessed_probability"])
        except (KeyError, TypeError, ValueError):
            log(f"  Rejected {recommendation.get('player', 'unknown')}: missing score/probability")
            continue
        if probability > 1:
            probability /= 100
        if not 0 < probability < 1 or not 0 <= score <= 10:
            log(f"  Rejected {recommendation.get('player', 'unknown')}: invalid score/probability")
            continue

        match_info = None
        verified_odds = None
        verified_player = None
        for match in matches:
            if player_key == normalize_player_name(match["player1"]):
                match_info = match
                verified_player = match["player1"]
                verified_odds = match.get("home_odds") or match.get("odds")
                break
            if player_key == normalize_player_name(match["player2"]):
                match_info = match
                verified_player = match["player2"]
                verified_odds = match.get("away_odds") or match.get("odds")
                break
        if not match_info or verified_odds is None:
            log(f"  Rejected {recommendation.get('player', 'unknown')}: no verified odds")
            continue
        verified_odds = float(verified_odds)
        if (
            (odds_min is not None and verified_odds < odds_min)
            or (odds_max is not None and verified_odds > odds_max)
        ):
            log(f"  Rejected {verified_player}: own odds outside requested range")
            continue

        baseline = calculate_tennis_baseline(match_info, verified_player)
        if not tennis_baseline_is_reliable(baseline):
            if baseline and baseline.get("physical_block"):
                log(f"  Rejected {verified_player}: verified physical status is {baseline['physical_status']}")
            else:
                log(f"  Rejected {verified_player}: missing Elo, excessive market margin, or large Elo/market disagreement")
            continue
        if abs(probability - baseline["assessed_probability"]) > 0.005:
            log(
                f"  Ignored AI estimate for {verified_player}: using Python "
                f"Elo/market baseline {baseline['assessed_probability']:.2%}"
            )
        probability = baseline["assessed_probability"]

        ev = probability * verified_odds - 1
        score = max(0.0, min(10.0, 6.0 + max(0.0, ev) * 30))
        if score > 8 and ev > 0.08:
            grade = "Top Pick"
        elif score > 7 and ev > 0.05:
            grade = "Value Pick"
        elif score > 5.5 and ev > 0:
            grade = "Moderate Pick"
        else:
            log(
                f"  Rejected {recommendation['player']}: score {score:.2f}, "
                f"recalculated EV {ev:.2%}"
            )
            continue

        validated.append({
            **recommendation,
            "player": verified_player,
            "score": score,
            "assessed_probability": probability,
            "odds": verified_odds,
            "ev": ev,
            "grade": grade,
            "match": match_info,
            "baseline": baseline,
        })
        log(
            f"  Validated {recommendation['player']}: {grade}, "
            f"score {score:.2f}, EV {ev:.2%}"
        )
    return validated


def select_portfolio(
    recommendations: list[dict],
    max_exposure: float = MAX_DAILY_EXPOSURE,
    max_bets: int = MAX_DAILY_BETS,
) -> list[dict]:
    """Rank independent matches and constrain total planned bankroll exposure."""
    rollback = automated_rollback_state(load_resolved_predictions())
    if rollback["policy_rollback"]:
        max_exposure, max_bets = min(max_exposure, .03), min(max_bets, 1)
        recommendations = [item for item in recommendations if item.get("grade") == "Top Pick"]
        log("Policy rollback active: using one-bet Top-Pick-only safe baseline")
    stake_rates = {"Top Pick": 0.03, "Value Pick": 0.02}
    tour_caps = load_tour_exposure_caps()
    ranked = sorted(
        recommendations,
        key=lambda rec: (rec.get("ev", 0), rec.get("score", 0)),
        reverse=True,
    )
    selected = []
    seen_matches = set()
    tournament_counts = {}
    tour_exposure = {}
    exposure = 0.0
    for recommendation in ranked:
        stake_rate = stake_rates.get(recommendation.get("grade"))
        match = recommendation.get("match") or {}
        if stake_rate is None or not match:
            continue
        match_key = tuple(sorted((
            normalize_player_name(match.get("player1", "")),
            normalize_player_name(match.get("player2", "")),
        )))
        if match_key in seen_matches:
            log(f"  Portfolio rejected {recommendation['player']}: match already selected")
            continue
        tournament = normalize_player_name(match.get("tournament", "Unknown"))
        tour = tour_exposure_bucket(match)
        if tournament_counts.get(tournament, 0) >= MAX_BETS_PER_TOURNAMENT:
            log(f"  Portfolio rejected {recommendation['player']}: tournament correlation cap reached")
            continue
        if tour_exposure.get(tour, 0.0) + stake_rate > tour_caps[tour] + 1e-9:
            log(f"  Portfolio rejected {recommendation['player']}: {tour} exposure cap reached")
            continue
        if len(selected) >= max_bets or exposure + stake_rate > max_exposure + 1e-9:
            log(f"  Portfolio rejected {recommendation['player']}: daily risk cap reached")
            continue
        selected.append(recommendation)
        seen_matches.add(match_key)
        tournament_counts[tournament] = tournament_counts.get(tournament, 0) + 1
        tour_exposure[tour] = tour_exposure.get(tour, 0.0) + stake_rate
        exposure += stake_rate
    log(f"Portfolio selected {len(selected)} bet(s), planned exposure {exposure:.1%}")
    return selected


def evidence_quality(match: dict, baseline: dict) -> tuple[int, str]:
    """Score whether a candidate has enough independent, relevant evidence."""
    points = 0
    points += 2 if match.get("player1_profile") and match.get("player2_profile") else 0
    points += 2 if match.get("surface") in {"hard", "clay", "grass"} else 0
    points += 2 if baseline.get("elo_type") != "elo" else 1
    bookmakers = int(match.get("bookmaker_count") or 0)
    points += 2 if bookmakers >= 3 else 1 if bookmakers >= 2 else 0
    points += 1 if baseline.get("market_overround", 9) <= 1.08 else 0
    points += 1 if baseline.get("elo_market_gap", 9) <= 0.12 else 0
    points += 1 if baseline.get("form_sample", 0) >= 8 else 0
    points += 1 if baseline.get("serve_return_sample", 0) >= 8 else 0
    grade = "A" if points >= 9 else "B" if points >= 7 else "C" if points >= 5 else "D"
    return points, grade


def player_market_dispersion(match: dict, player: str) -> float | None:
    field = "home_dispersion" if normalize_player_name(player) == normalize_player_name(match.get("player1", "")) else "away_dispersion"
    value = match.get(field)
    return float(value) if isinstance(value, (int, float)) else None


def tennis_data_quality(match: dict, baseline: dict, player: str) -> dict:
    score, reasons = 0, []
    books = int(match.get("bookmaker_count") or 0)
    if books >= 3: score += 3
    elif books >= 2: score += 2
    else: reasons.append("insufficient_bookmakers")
    dispersion = player_market_dispersion(match, player)
    if dispersion is not None and dispersion <= .08: score += 2
    elif dispersion is not None and dispersion <= MAX_BOOKMAKER_DISPERSION: score += 1
    else: reasons.append("bookmaker_conflict")
    if match.get("player1_profile") and match.get("player2_profile"): score += 2
    else: reasons.append("identity_or_elo_missing")
    if match.get("surface") in {"hard", "clay", "grass"}: score += 1
    else: reasons.append("surface_unverified")
    if baseline.get("form_sample", 0) >= 8: score += 1
    if baseline.get("serve_return_sample", 0) >= 8: score += 1
    return {"score": score, "grade": "A" if score >= 9 else "B" if score >= 7 else "C" if score >= 5 else "D",
            "reasons": reasons, "dispersion": dispersion}


def identity_audit_values(match: dict, player: str) -> tuple[float, str, float, str]:
    """Return explicit pick/opponent identity confidence for an audit row."""
    pick_side, opponent_side = ("player1", "player2") if normalize_player_name(player) == normalize_player_name(match.get("player1", "")) else ("player2", "player1")
    pick_profile = match.get(f"{pick_side}_profile") or {}
    opponent_profile = match.get(f"{opponent_side}_profile") or {}

    def values(side: str, profile: dict) -> tuple[float, str]:
        raw_confidence = match.get(f"{side}_identity_confidence", profile.get("identity_confidence", 0.0))
        try:
            confidence = min(1.0, max(0.0, float(raw_confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        method = str(match.get(f"{side}_identity_method") or profile.get("identity_method") or "unresolved")
        return confidence, method

    pick_confidence, pick_method = values(pick_side, pick_profile)
    opponent_confidence, opponent_method = values(opponent_side, opponent_profile)
    return pick_confidence, pick_method, opponent_confidence, opponent_method


def ranking_audit_values(match: dict, player: str) -> tuple[dict, dict]:
    """Return the pick and opponent pre-match ranking histories in row order."""
    pick_side, opponent_side = ("player1", "player2") if normalize_player_name(player) == normalize_player_name(match.get("player1", "")) else ("player2", "player1")
    return match.get(f"{pick_side}_ranking_history") or {}, match.get(f"{opponent_side}_ranking_history") or {}


def bio_audit_values(match: dict, player: str) -> tuple[dict, dict]:
    """Return the pick and opponent verified bio records in row order."""
    pick_side, opponent_side = ("player1", "player2") if normalize_player_name(player) == normalize_player_name(match.get("player1", "")) else ("player2", "player1")
    return match.get(f"{pick_side}_bio") or {}, match.get(f"{opponent_side}_bio") or {}


def append_prediction_audit(date_str, matches, recommendations, authorized, authorization_block_reason: str = ""):
    """Persist all Elo-modelled singles candidates and final decisions."""
    headers = [
        "DATE", "MODEL_VERSION", "SNAPSHOT_PATH", "SNAPSHOT_SHA256", "SNAPSHOT_SCHEMA_VERSION",
        "EVENT_ID", "MATCH", "PICK",
        "PICK_IDENTITY_CONFIDENCE", "PICK_IDENTITY_METHOD",
        "OPPONENT_IDENTITY_CONFIDENCE", "OPPONENT_IDENTITY_METHOD",
        "PICK_RANK_AS_OF", "PICK_RANK_DATE", "PICK_RANK_90D", "PICK_RANK_IMPROVEMENT_90D", "PICK_RANK_SAMPLES_365",
        "OPPONENT_RANK_AS_OF", "OPPONENT_RANK_DATE", "OPPONENT_RANK_90D", "OPPONENT_RANK_IMPROVEMENT_90D", "OPPONENT_RANK_SAMPLES_365",
        "PICK_HANDEDNESS", "PICK_NATIONALITY", "PICK_BIO_DATE", "PICK_BIO_SOURCE",
        "OPPONENT_HANDEDNESS", "OPPONENT_NATIONALITY", "OPPONENT_BIO_DATE", "OPPONENT_BIO_SOURCE",
        "PHYSICAL_STATUS", "PHYSICAL_STATUS_DETAIL", "PHYSICAL_STATUS_EXPIRES", "PHYSICAL_STATUS_SOURCE", "PHYSICAL_BLOCK",
        "OPENING_ODDS",
        "MARKET_PROBABILITY", "ELO_PROBABILITY", "MODEL_PROBABILITY",
        "FORM_PROBABILITY", "FORM_SAMPLE", "H2H_PROBABILITY", "H2H_SAMPLE", "H2H_SURFACE_SAMPLE", "H2H_WEIGHT", "H2H_SOURCE", "SERVE_RETURN_PROBABILITY",
        "SERVE_RETURN_SAMPLE", "EXPECTED_HOLD", "OPPONENT_EXPECTED_HOLD",
        "BREAK_RATE", "BREAK_POINTS_CONVERTED", "BREAK_RETURN_GAMES", "SERVE_RETURN_SOURCE", "TIEBREAK_WIN_RATE", "TIEBREAK_SAMPLE",
        "DECIDING_SET_WIN_RATE", "DECIDING_SET_SAMPLE", "CLUTCH_SOURCE",
        "BO5_MATCH_WIN_RATE", "BO5_MATCH_SAMPLE", "BO5_SET_WIN_RATE", "BO5_SET_SAMPLE", "BO5_SAME_SURFACE_SAMPLE",
        "BO5_FIVE_SET_WIN_RATE", "BO5_FIVE_SET_SAMPLE", "BO5_COMEBACK_0_2_RATE", "BO5_COMEBACK_0_2_SAMPLE", "BO5_SOURCE",
        "COMPONENT_WEIGHTS", "RAW_PROBABILITY", "CHALLENGER_PROBABILITY",
        "CHALLENGER_SAMPLE", "CHALLENGER_PROMOTED", "FORMAT_MODEL", "FORMAT_MODEL_SAMPLE",
        "FORMAT_MODEL_HOLDOUT", "FORMAT_MODEL_PROBABILITY", "FORMAT_MODEL_PROMOTED",
        "ENVIRONMENT_MODEL", "ENVIRONMENT_MODEL_SAMPLE", "ENVIRONMENT_MODEL_HOLDOUT",
        "ENVIRONMENT_MODEL_PROBABILITY", "ENVIRONMENT_MODEL_PROMOTED", "ACTIVE_COMPONENT_MODEL",
        "CALIBRATION_SAMPLE", "CALIBRATION_SEGMENT", "CALIBRATION_APPLIED",
        "CONTEXT_PENALTY", "CONTEXT_REASON", "WORKLOAD_PENALTY", "STATIC_WORKLOAD_PENALTY",
        "WORKLOAD_POLICY_ID", "WORKLOAD_POLICY_SAMPLE", "WORKLOAD_POLICY_HOLDOUT",
        "WORKLOAD_POLICY_ACTIVE_BRIER", "WORKLOAD_POLICY_CHALLENGER_BRIER", "WORKLOAD_POLICY_PROMOTED", "REST_DAYS",
        "MATCHES_7", "MATCHES_14", "MATCHES_30", "SETS_7", "LAST_MATCH_MINUTES",
        "MINUTES_7", "MINUTES_14", "MINUTES_30", "DURATION_SAMPLE_30", "DURATION_SOURCE",
        "LAST_MATCH_LONG", "LAST_MATCH_LONG_THRESHOLD", "LONG_MATCHES_7", "LONG_MATCHES_30",
        "LATEST_LONG_MATCH_MINUTES", "LATEST_LONG_MATCH_DATE", "LATEST_LONG_MATCH_DAYS_AGO", "LATEST_LONG_MATCH_SOURCE",
        "TOURNAMENT_CHANGE", "PREVIOUS_TOURNAMENT", "PREVIOUS_TOURNAMENT_SURFACE",
        "PREVIOUS_TOURNAMENT_DAYS_AGO", "CURRENT_SURFACE", "SURFACE_CHANGE", "SURFACE_TRANSITION_SOURCE",
        "TRAVEL_DISTANCE_KM", "TIMEZONE_CHANGE_HOURS", "TRAVEL_SOURCE",
        "BEST_OF", "INDOOR",
        "MARKET_DISPERSION", "PRICE_SNAPSHOT_COUNT", "PRICE_VELOCITY_PER_HOUR",
        "PRICE_ACCELERATION_PER_HOUR2", "DATA_QUALITY_SCORE", "DATA_QUALITY_GRADE",
        "UNCERTAINTY_MARGIN", "RISK_ADJUSTED_EV", "KILL_SWITCH", "KILL_SWITCH_REASON",
        "SEGMENT_SAMPLE", "SEGMENT_ROI", "SEGMENT_CLV", "SEGMENT_SUSPENDED",
        "EV", "SCORE", "EVIDENCE", "QUALITY_SCORE", "QUALITY_GRADE",
        "TOUR", "SURFACE", "BOOKMAKERS", "FIXTURE_SOURCES", "SECONDARY_FIXTURE_CONFIRMED",
        "DECISION", "REASON", "RESULT",
        "CLOSING_ODDS", "CLV",
    ]
    if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size:
        with open(AUDIT_FILE, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            old_rows, old_headers = list(reader), reader.fieldnames or []
        if old_headers != headers:
            backup_state_for_migration(AUDIT_FILE, list(old_headers), headers)
            for row in old_rows:
                row.setdefault("REASON", "legacy")
                row.setdefault("QUALITY_GRADE", "legacy")
                row.setdefault("PICK_IDENTITY_CONFIDENCE", "0.000")
                row.setdefault("PICK_IDENTITY_METHOD", "legacy_unknown")
                row.setdefault("OPPONENT_IDENTITY_CONFIDENCE", "0.000")
                row.setdefault("OPPONENT_IDENTITY_METHOD", "legacy_unknown")
            atomic_write_csv(AUDIT_FILE, headers, old_rows)
    validated = {normalize_player_name(item["player"]): item for item in recommendations}
    selected = {normalize_player_name(item["player"]) for item in authorized}
    existing = set()
    if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size:
        with open(AUDIT_FILE, newline="", encoding="utf-8") as handle:
            existing = {(r["DATE"], r["EVENT_ID"], r["PICK"]) for r in csv.DictReader(handle)}
    rows = []
    training_history = load_resolved_predictions(date_str)
    for match in matches:
        for player in (match["player1"], match["player2"]):
            baseline = calculate_tennis_baseline(match, player)
            if not baseline:
                continue
            key = (date_str, match.get("event_id", ""), player)
            if key in existing:
                continue
            item = validated.get(normalize_player_name(player))
            decision = item["grade"] if normalize_player_name(player) in selected else "Watchlist" if item else "Rejected"
            if normalize_player_name(player) in selected:
                reason = "authorized"
            elif item and authorization_block_reason:
                reason = authorization_block_reason
            elif item and item.get("grade") in {"Top Pick", "Value Pick"}:
                reason = "portfolio_limit"
            elif item:
                reason = "below_staking_threshold"
            elif baseline.get("physical_block"):
                reason = f"verified_physical_status:{baseline.get('physical_status', 'unavailable')}"
            elif not tennis_baseline_is_reliable(baseline):
                reason = "missing_elo_or_market_disagreement"
            elif baseline["ev"] <= 0:
                reason = "non_positive_ev"
            else:
                reason = "not_selected"
            quality_score, quality_grade = evidence_quality(match, baseline)
            data_quality = tennis_data_quality(match, baseline, player)
            workload = baseline.get("workload") or {}
            snapshot = save_prediction_snapshot(date_str, match, player, baseline, training_history)
            pick_identity, pick_identity_method, opponent_identity, opponent_identity_method = identity_audit_values(match, player)
            pick_ranking, opponent_ranking = ranking_audit_values(match, player)
            pick_bio, opponent_bio = bio_audit_values(match, player)
            rows.append([
                date_str, MODEL_VERSION, snapshot["path"], snapshot["sha256"], snapshot["schema_version"],
                match.get("event_id", ""),
                f"{match['player1']} vs {match['player2']}", player,
                f"{pick_identity:.3f}", pick_identity_method,
                f"{opponent_identity:.3f}", opponent_identity_method,
                pick_ranking.get("latest_rank", ""), pick_ranking.get("latest_date", ""),
                pick_ranking.get("rank_90d", ""), pick_ranking.get("improvement_90d", ""), pick_ranking.get("samples_365d", 0),
                opponent_ranking.get("latest_rank", ""), opponent_ranking.get("latest_date", ""),
                opponent_ranking.get("rank_90d", ""), opponent_ranking.get("improvement_90d", ""), opponent_ranking.get("samples_365d", 0),
                pick_bio.get("handedness", ""), pick_bio.get("nationality", ""),
                pick_bio.get("handedness_date") or pick_bio.get("nationality_date") or "", pick_bio.get("source", ""),
                opponent_bio.get("handedness", ""), opponent_bio.get("nationality", ""),
                opponent_bio.get("handedness_date") or opponent_bio.get("nationality_date") or "", opponent_bio.get("source", ""),
                baseline.get("physical_status", "unknown"), baseline.get("physical_status_detail", ""),
                baseline.get("physical_status_expires", ""), baseline.get("physical_status_source", ""), baseline.get("physical_block", False),
                f"{baseline['player_odds']:.3f}",
                f"{baseline['market_probability']:.6f}",
                f"{baseline['elo_probability']:.6f}",
                f"{baseline['assessed_probability']:.6f}",
                f"{baseline['form_probability']:.6f}" if baseline.get("form_probability") is not None else "",
                baseline.get("form_sample", 0),
                f"{baseline['h2h_probability']:.6f}" if baseline.get("h2h_probability") is not None else "",
                baseline.get("h2h_sample", 0), baseline.get("h2h_surface_sample", 0), f"{baseline.get('h2h_weight', 0):.3f}",
                (match.get("head_to_head") or {}).get("source", ""),
                f"{baseline['serve_return_probability']:.6f}" if baseline.get("serve_return_probability") is not None else "",
                baseline.get("serve_return_sample", 0),
                f"{baseline['expected_hold']:.6f}" if baseline.get("expected_hold") is not None else "",
                f"{baseline['opponent_expected_hold']:.6f}" if baseline.get("opponent_expected_hold") is not None else "",
                f"{baseline['break_rate']:.6f}" if baseline.get("break_rate") is not None else "",
                f"{baseline['break_points_converted']:.6f}" if baseline.get("break_points_converted") is not None else "",
                f"{baseline.get('break_return_games', 0):.3f}", baseline.get("serve_return_source", ""),
                f"{baseline['tiebreak_win_rate']:.6f}" if baseline.get("tiebreak_win_rate") is not None else "",
                baseline.get("tiebreak_sample", 0),
                f"{baseline['deciding_set_win_rate']:.6f}" if baseline.get("deciding_set_win_rate") is not None else "",
                baseline.get("deciding_set_sample", 0), baseline.get("clutch_source", ""),
                f"{baseline['bo5_match_win_rate']:.6f}" if baseline.get("bo5_match_win_rate") is not None else "",
                baseline.get("bo5_match_sample", 0),
                f"{baseline['bo5_set_win_rate']:.6f}" if baseline.get("bo5_set_win_rate") is not None else "",
                baseline.get("bo5_set_sample", 0), baseline.get("bo5_same_surface_sample", 0),
                f"{baseline['bo5_five_set_win_rate']:.6f}" if baseline.get("bo5_five_set_win_rate") is not None else "",
                baseline.get("bo5_five_set_sample", 0),
                f"{baseline['bo5_comeback_0_2_rate']:.6f}" if baseline.get("bo5_comeback_0_2_rate") is not None else "",
                baseline.get("bo5_comeback_0_2_sample", 0), baseline.get("bo5_source", ""),
                baseline.get("component_weights", ""),
                f"{baseline['raw_probability']:.6f}",
                f"{baseline['challenger_probability']:.6f}" if baseline.get("challenger_probability") is not None else "",
                baseline.get("challenger_sample", 0), baseline.get("challenger_promoted", False),
                baseline.get("format_model", ""), baseline.get("format_model_sample", 0),
                baseline.get("format_model_holdout", 0),
                f"{baseline['format_model_probability']:.6f}" if baseline.get("format_model_probability") is not None else "",
                baseline.get("format_model_promoted", False), baseline.get("environment_model", "Unknown"),
                baseline.get("environment_model_sample", 0), baseline.get("environment_model_holdout", 0),
                f"{baseline['environment_model_probability']:.6f}" if baseline.get("environment_model_probability") is not None else "",
                baseline.get("environment_model_promoted", False), baseline.get("active_component_model", "static"),
                baseline.get("calibration_sample", 0), baseline.get("calibration_segment", "Unknown"),
                baseline.get("calibration_applied", False), f"{baseline.get('context_penalty', 0):.6f}", baseline.get("context_reason", "main_draw"),
                f"{baseline.get('workload_penalty', 0):.6f}", f"{baseline.get('static_workload_penalty', 0):.6f}",
                baseline.get("workload_policy_id", "static-v1"), baseline.get("workload_policy_sample", 0),
                baseline.get("workload_policy_holdout", 0),
                f"{baseline['workload_policy_active_brier']:.6f}" if baseline.get("workload_policy_active_brier") is not None else "",
                f"{baseline['workload_policy_challenger_brier']:.6f}" if baseline.get("workload_policy_challenger_brier") is not None else "",
                baseline.get("workload_policy_promoted", False), workload.get("rest_days", ""), workload.get("matches_7", 0),
                workload.get("matches_14", 0), workload.get("matches_30", 0), workload.get("sets_7", 0),
                workload.get("last_match_minutes", ""), workload.get("minutes_7", 0), workload.get("minutes_14", 0),
                workload.get("minutes_30", 0), workload.get("duration_sample_30", 0), workload.get("duration_source", ""),
                workload.get("last_match_long", ""), workload.get("last_match_long_threshold", ""),
                workload.get("long_matches_7", 0), workload.get("long_matches_30", 0),
                workload.get("latest_long_match_minutes", ""), workload.get("latest_long_match_date", ""),
                workload.get("latest_long_match_days_ago", ""), workload.get("latest_long_match_source", ""),
                workload.get("tournament_change", False),
                workload.get("previous_tournament", ""), workload.get("previous_tournament_surface", ""),
                workload.get("previous_tournament_days_ago", ""), workload.get("current_surface", ""),
                workload.get("surface_change", ""), workload.get("surface_transition_source", ""),
                f"{workload['travel_distance_km']:.3f}" if workload.get("travel_distance_km") is not None else "",
                f"{workload['timezone_change_hours']:.3f}" if workload.get("timezone_change_hours") is not None else "",
                workload.get("travel_source", ""),
                baseline.get("best_of", 3), baseline.get("indoor", ""),
                f"{data_quality['dispersion']:.6f}" if data_quality.get("dispersion") is not None else "",
                "", "", "",
                data_quality["score"], data_quality["grade"], f"{baseline['uncertainty_margin']:.6f}",
                f"{baseline['risk_adjusted_ev']:.6f}", baseline.get("kill_switch", False), baseline.get("kill_switch_reason", ""),
                baseline.get("segment_sample", 0),
                f"{baseline['segment_roi']:.6f}" if baseline.get("segment_roi") is not None else "",
                f"{baseline['segment_clv']:.6f}" if baseline.get("segment_clv") is not None else "",
                baseline.get("segment_suspended", False),
                f"{baseline['ev']:.6f}", f"{baseline['score']:.3f}",
                "reliable" if tennis_baseline_is_reliable(baseline) else "insufficient",
                quality_score, quality_grade, match.get("level") or "Unknown",
                match.get("surface") or "Unknown", match.get("bookmaker_count") or 0,
                ";".join(match.get("fixture_sources") or ["Odds-API.io"]),
                match.get("secondary_fixture_confirmed", False),
                decision, reason, "", "", "",
            ])
    if not rows:
        return
    _, existing_rows = read_csv_rows(AUDIT_FILE)
    existing_rows.extend(dict(zip(headers, row)) for row in rows)
    atomic_write_csv(AUDIT_FILE, headers, existing_rows)
    log(f"Audited {len(rows)} evaluated player(s) to {AUDIT_FILE.name}")


def update_audit_result(date_str, pick_key, result, closing_odds):
    if not AUDIT_FILE.exists() or not AUDIT_FILE.stat().st_size:
        return
    with open(AUDIT_FILE, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows, headers = list(reader), reader.fieldnames
    changed = False
    for row in rows:
        if row["DATE"] == date_str and normalize_player_name(row["PICK"]) == pick_key:
            row["RESULT"] = result
            if closing_odds:
                row["CLOSING_ODDS"] = f"{closing_odds:.3f}"
                opening = float(row.get("OPENING_ODDS") or 0)
                row["CLV"] = f"{opening / closing_odds - 1:.6f}" if opening else ""
            changed = True
    if changed:
        atomic_write_csv(AUDIT_FILE, list(headers or []), rows)


def tennis_void_reason(event: dict) -> str | None:
    """Identify non-completed matches that should not be graded as model wins/losses."""
    status = str(event.get("status") or "").casefold()
    detail = " ".join(str(event.get(key) or "") for key in ("result", "reason", "note", "score", "scores"))
    detail = detail.casefold()
    if status in {"cancelled", "canceled", "postponed", "abandoned"}:
        return status
    if event.get("retired") or event.get("walkover"):
        return "walkover_or_retirement"
    if any(token in detail for token in ("walkover", "w/o", "retired", "retirement", "abandoned")):
        return "walkover_or_retirement"
    return None


def unresolved_alert_hours() -> int:
    try:
        return max(1, int(os.environ.get("TENNIS_UNRESOLVED_HOURS", DEFAULT_UNRESOLVED_ALERT_HOURS)))
    except ValueError:
        return DEFAULT_UNRESOLVED_ALERT_HOURS


def save_settlement_alerts(real_rows: list[dict], paper_rows: list[dict], now: datetime | None = None) -> int:
    """Publish overdue unresolved outcomes for human review and workflow alerts."""
    now = now or datetime.now(timezone.utc)
    threshold = unresolved_alert_hours()
    overdue = []
    for mode, rows in (("live", real_rows), ("paper", paper_rows)):
        for row in rows:
            if row.get("RESULT", "").strip() or not row.get("DATE"):
                continue
            try:
                match_day_end = datetime.strptime(row["DATE"], "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError:
                continue
            age_hours = (now - match_day_end).total_seconds() / 3600
            if age_hours >= threshold:
                overdue.append((mode, row, age_hours))
    lines = ["# Tennis Settlement Alerts", "", f"Updated: {now.isoformat()}",
             f"Alert threshold: {threshold} hours after the match date ends.", ""]
    if overdue:
        lines.extend(["## OVERDUE UNRESOLVED OUTCOMES", "",
                      "| Mode | Date | Match | Bet | Age |", "|---|---|---|---|---:|"])
        for mode, row, age in overdue:
            lines.append(f"| {mode} | {row.get('DATE', '')} | {row.get('MATCH', '')} | {row.get('BET', '')} | {age:.0f}h |")
        log(f"WARNING: {len(overdue)} outcome(s) remain unresolved beyond {threshold} hours")
    else:
        lines.extend(["## OK", "", "No outcomes are overdue."])
    atomic_write_text(SETTLEMENT_ALERT_FILE, "\n".join(lines) + "\n")
    return len(overdue)


def settle_pending_bets(api_keys: list[str], include_real: bool = True) -> int:
    """Settle finished tennis bets and add bookmaker returns to bankroll."""
    if not api_keys:
        return 0
    rows = []
    if include_real and LOG_FILE.exists() and LOG_FILE.stat().st_size:
        with open(LOG_FILE, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    paper_rows = []
    if PAPER_LOG_FILE.exists() and PAPER_LOG_FILE.stat().st_size:
        with PAPER_LOG_FILE.open(newline="", encoding="utf-8") as handle:
            paper_rows = list(csv.DictReader(handle))
    if rows and BANKROLL_FILE.exists():
        try: reconcile_bankroll(float(BANKROLL_FILE.read_text().strip() or 0))
        except ValueError: pass
    policy_rows = []
    if POLICY_FILE.exists() and POLICY_FILE.stat().st_size:
        with POLICY_FILE.open(newline="", encoding="utf-8") as handle:
            policy_rows = list(csv.DictReader(handle))
    dates = sorted({r.get("DATE", "") for r in rows + paper_rows + policy_rows if not r.get("RESULT", "").strip() and r.get("DATE")})
    if not dates:
        save_settlement_alerts(rows, paper_rows)
        return 0
    events = []
    key_index = 0
    for date in dates:
        payload, key_index = fetch_odds_json(
            "https://api.odds-api.io/v3/events",
            {"sport": "tennis", "status": "settled", "from": f"{date}T00:00:00Z", "to": f"{date}T23:59:59Z"},
            api_keys, key_index,
        )
        if isinstance(payload, list):
            events.extend(payload)
    closing_by_id = {}
    event_ids = [str(event.get("id")) for event in events if event.get("id")]
    for start in range(0, len(event_ids), 10):
        payload, key_index = fetch_odds_json(
            "https://api.odds-api.io/v3/odds/multi",
            {"eventIds": ",".join(event_ids[start:start + 10]), "bookmakers": "Bet365,Unibet"},
            api_keys, key_index,
        )
        odds_events = payload if isinstance(payload, list) else []
        for odds_event in odds_events:
            home_odds, away_odds, _ = extract_moneyline_odds(odds_event)
            closing_by_id[str(odds_event.get("id"))] = (home_odds, away_odds)
    settled = 0
    paper_settled = 0
    credited = 0.0
    for row, is_paper in [(item, False) for item in rows] + [(item, True) for item in paper_rows]:
        if row.get("RESULT", "").strip():
            continue
        label = normalize_player_name(row.get("MATCH", ""))
        pick = normalize_player_name(re.sub(r"\s+to win\s*$", "", row.get("BET", ""), flags=re.I))
        event = next((e for e in events if str(e.get("date", "")).startswith(row.get("DATE", ""))
                      and normalize_player_name(str(e.get("home", ""))) in label
                      and normalize_player_name(str(e.get("away", ""))) in label), None)
        if not event:
            continue
        void_reason = tennis_void_reason(event)
        if void_reason:
            stake = float(row.get("STAKE") or 0)
            row["RESULT"], row["RETURN"] = "V", f"{stake:.2f}"
            if not is_paper: credited += stake
            if is_paper: paper_settled += 1
            else: settled += 1
            update_audit_result(row.get("DATE", ""), pick, "V", None)
            continue
        scores = event.get("scores") or {}
        try:
            home_score, away_score = float(scores["home"]), float(scores["away"])
        except (KeyError, TypeError, ValueError):
            continue
        home_pick = pick == normalize_player_name(str(event.get("home", "")))
        away_pick = pick == normalize_player_name(str(event.get("away", "")))
        if not (home_pick or away_pick) or home_score == away_score:
            continue
        won = (home_pick and home_score > away_score) or (away_pick and away_score > home_score)
        closing_pair = closing_by_id.get(str(event.get("id")), (None, None))
        closing = closing_pair[0] if home_pick else closing_pair[1]
        stake, odds = float(row.get("STAKE") or 0), float(row.get("ODDS") or 0)
        returned = stake * odds if won else 0.0
        row["RESULT"], row["RETURN"] = ("W" if won else "L"), f"{returned:.2f}"
        if not is_paper: credited += returned
        if is_paper: paper_settled += 1
        else: settled += 1
        update_audit_result(row.get("DATE", ""), pick, row["RESULT"], closing)
    if settled:
        headers = ["DATE", "MATCH", "BET", "ODDS", "STAKE", "RESULT", "RETURN", "STARTING BALANCE"]
        atomic_write_csv(LOG_FILE, headers, rows)
        balance = reconcile_bankroll()
        log(f"Settled {settled} bet(s); credited €{credited:.2f}")
        log(f"Bankroll reconciled to ledger: €{balance:.2f}")
    if paper_settled:
        headers = ["DATE", "MATCH", "BET", "ODDS", "STAKE", "RESULT", "RETURN", "STARTING BALANCE"]
        atomic_write_csv(PAPER_LOG_FILE, headers, paper_rows)
        log(f"Settled {paper_settled} paper bet(s); real bankroll unchanged")
    policy_settled = 0
    for row in policy_rows:
        if row.get("RESULT"): continue
        event = next((event for event in events if (row.get("EVENT_ID") and str(event.get("id")) == row["EVENT_ID"]) or
                      (str(event.get("date", "")).startswith(row.get("DATE", "")) and
                       {normalize_player_name(str(event.get("home", ""))), normalize_player_name(str(event.get("away", "")))} ==
                       {normalize_player_name(row.get("PLAYER1", "")), normalize_player_name(row.get("PLAYER2", ""))})), None)
        if not event: continue
        if tennis_void_reason(event): row["RESULT"], row["FLAT_RETURN"] = "V", "0.000"; policy_settled += 1; continue
        try: home_score, away_score = float(event["scores"]["home"]), float(event["scores"]["away"])
        except (KeyError, TypeError, ValueError): continue
        pick = normalize_player_name(row.get("PICK", "")); home_pick = pick == normalize_player_name(str(event.get("home", "")))
        won = (home_pick and home_score > away_score) or (not home_pick and away_score > home_score)
        odds = float(row.get("ODDS") or 0); row["RESULT"] = "W" if won else "L"; row["FLAT_RETURN"] = f"{odds - 1 if won else -1:.3f}"; policy_settled += 1
    if policy_settled:
        atomic_write_csv(POLICY_FILE, POLICY_HEADERS, policy_rows)
        log(f"Settled {policy_settled} counterfactual policy decision(s)")
    save_settlement_alerts(rows, paper_rows)
    return settled + paper_settled


def generate_performance_summary():
    bets = []
    if LOG_FILE.exists() and LOG_FILE.stat().st_size:
        with open(LOG_FILE, newline="", encoding="utf-8") as handle:
            bets = list(csv.DictReader(handle))
    settled = [row for row in bets if row.get("RESULT") in {"W", "L"}]
    stakes = sum(float(row.get("STAKE") or 0) for row in settled)
    profit = sum(float(row.get("RETURN") or 0) - float(row.get("STAKE") or 0) for row in settled)
    wins = sum(row.get("RESULT") == "W" for row in settled)
    audit = []
    if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size:
        with open(AUDIT_FILE, newline="", encoding="utf-8") as handle:
            audit = list(csv.DictReader(handle))
    resolved = [row for row in audit if row.get("RESULT") in {"W", "L"} and row.get("MODEL_PROBABILITY")]
    active_metrics = probability_metrics(resolved)
    brier = active_metrics["brier"]
    challenger_rows = [row for row in resolved if row.get("CHALLENGER_PROBABILITY")]
    challenger_metrics = probability_metrics(challenger_rows, "CHALLENGER_PROBABILITY")
    challenger_brier = challenger_metrics["brier"]
    clv = [float(row["CLV"]) for row in resolved if row.get("CLV")]
    policy = []
    if POLICY_FILE.exists() and POLICY_FILE.stat().st_size:
        with POLICY_FILE.open(newline="", encoding="utf-8") as handle: policy = list(csv.DictReader(handle))
    policy_resolved = [row for row in policy if row.get("RESULT") in {"W", "L"}]
    lines = [
        "# Tennis Bot Performance", "",
        f"- Settled bets: {len(settled)}",
        f"- Win rate: {wins / len(settled):.1%}" if settled else "- Win rate: N/A",
        f"- Profit/loss: €{profit:.2f}",
        f"- ROI: {profit / stakes:.2%}" if stakes else "- ROI: N/A",
        f"- Brier score: {brier:.4f}" if brier is not None else "- Brier score: N/A",
        f"- Log loss: {active_metrics['log_loss']:.4f}" if active_metrics["log_loss"] is not None else "- Log loss: N/A",
        f"- Expected calibration error (10 bins): {active_metrics['ece']:.2%}" if active_metrics["ece"] is not None else "- Expected calibration error (10 bins): N/A",
        f"- Shadow challenger Brier: {challenger_brier:.4f}" if challenger_brier is not None else "- Shadow challenger Brier: N/A",
        f"- Shadow challenger log loss: {challenger_metrics['log_loss']:.4f}" if challenger_metrics["log_loss"] is not None else "- Shadow challenger log loss: N/A",
        f"- Shadow challenger ECE (10 bins): {challenger_metrics['ece']:.2%}" if challenger_metrics["ece"] is not None else "- Shadow challenger ECE (10 bins): N/A",
        f"- Average CLV: {sum(clv) / len(clv):.2%}" if clv else "- Average CLV: N/A",
        f"- Settled counterfactual decisions: {len(policy_resolved)}",
        "", "## Calibration", "",
        "| Predicted probability | Predictions | Actual win rate |", "|---|---:|---:|",
    ]
    for low, high in ((.50, .55), (.55, .60), (.60, .65), (.65, .70), (.70, 1.01)):
        bucket = [row for row in resolved if low <= float(row["MODEL_PROBABILITY"]) < high]
        actual = sum(row["RESULT"] == "W" for row in bucket) / len(bucket) if bucket else None
        label = f"{low:.0%}–{high:.0%}" if high <= 1 else "70%+"
        lines.append(f"| {label} | {len(bucket)} | {actual:.1%} |" if actual is not None else f"| {label} | 0 | N/A |")
    atomic_write_text(PERFORMANCE_FILE, "\n".join(lines) + "\n")
    health = ["# Weekly Tennis Policy Health", "", f"Model version: `{MODEL_VERSION}`", "", "| Rule | Decisions | Flat-unit ROI |", "|---|---:|---:|"]
    for rule in sorted({row.get("RULE", "unknown") for row in policy_resolved}):
        group = [row for row in policy_resolved if row.get("RULE", "unknown") == rule]
        roi = sum(float(row.get("FLAT_RETURN") or 0) for row in group) / len(group)
        health.append(f"| {rule} | {len(group)} | {roi:.2%} |")
    if not policy_resolved: health.append("| No settled policy decisions | 0 | N/A |")
    atomic_write_text(REPO_ROOT / "weekly-health.md", "\n".join(health) + "\n")
    generate_backtest_summary(resolved)
    log(f"Performance summary saved: {PERFORMANCE_FILE.name}")


def _segment_metrics(rows: list[dict]) -> tuple[int, float, float, float, float, float, float | None]:
    count = len(rows)
    if not count:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0, None
    wins = sum(row.get("RESULT") == "W" for row in rows)
    profit = sum(
        (float(row.get("OPENING_ODDS") or 0) - 1) if row.get("RESULT") == "W" else -1
        for row in rows
    )
    metrics = probability_metrics(rows)
    clv_values = [float(row["CLV"]) for row in rows if row.get("CLV")]
    return (count, wins / count, profit / count, metrics["brier"] or 0.0,
            metrics["log_loss"] or 0.0, metrics["ece"] or 0.0,
            (sum(clv_values) / len(clv_values) if clv_values else None))


def _append_segment_table(lines: list[str], title: str, groups: list[tuple[str, list[dict]]]):
    lines.extend(["", f"## {title}", "", "| Segment | Bets | Win rate | Flat-unit ROI | Brier | Log loss | ECE | Avg CLV | Reliability |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"])
    for label, rows in groups:
        count, win_rate, roi, brier, log_loss, ece, clv = _segment_metrics(rows)
        reliability = "usable" if count >= 100 else "developing" if count >= 30 else "small sample"
        clv_text = f"{clv:.2%}" if clv is not None else "N/A"
        lines.append(f"| {label} | {count} | {win_rate:.1%} | {roi:.2%} | {brier:.4f} | {log_loss:.4f} | {ece:.2%} | {clv_text} | {reliability} |")


def walk_forward_staking_simulation(rows: list[dict], starting_bankroll: float = 100.0) -> dict:
    """Compare fixed-unit and capped quarter-Kelly staking without future-result leakage."""
    eligible = [row for row in rows if row.get("RESULT") in {"W", "L"}
                and row.get("DECISION") in {"Top Pick", "Value Pick"}]
    by_date = {}
    for row in sorted(eligible, key=lambda item: (item.get("DATE", ""), item.get("EVENT_ID", ""), item.get("PICK", ""))):
        by_date.setdefault(row.get("DATE", ""), []).append(row)

    balances = {"fixed": starting_bankroll, "kelly": starting_bankroll}
    peaks = dict(balances)
    drawdowns = {"fixed": 0.0, "kelly": 0.0}
    staked = {"fixed": 0.0, "kelly": 0.0}
    bets = 0
    for date in sorted(by_date):
        day_start = dict(balances)
        day_profit = {"fixed": 0.0, "kelly": 0.0}
        allocated = {"fixed": 0.0, "kelly": 0.0}
        for row in by_date[date]:
            try:
                odds = float(row.get("OPENING_ODDS") or 0)
                probability = float(row.get("MODEL_PROBABILITY") or 0)
            except ValueError:
                continue
            if odds <= 1 or not 0 < probability < 1:
                continue
            bets += 1
            fixed_stake = min(1.0, max(0.0, day_start["fixed"] - allocated["fixed"]))
            full_kelly = max(0.0, (probability * odds - 1) / (odds - 1))
            cap = .03 if row.get("DECISION") == "Top Pick" else .02
            kelly_rate = min(cap, max(MIN_STAKE_RATE, full_kelly * KELLY_FRACTION))
            kelly_stake = min(
                day_start["kelly"] * kelly_rate,
                max(0.0, day_start["kelly"] * MAX_DAILY_EXPOSURE - allocated["kelly"]),
                max(0.0, day_start["kelly"] - allocated["kelly"]),
            )
            for name, stake in (("fixed", fixed_stake), ("kelly", kelly_stake)):
                allocated[name] += stake
                staked[name] += stake
                day_profit[name] += stake * (odds - 1) if row["RESULT"] == "W" else -stake
        for name in balances:
            balances[name] = max(0.0, balances[name] + day_profit[name])
            peaks[name] = max(peaks[name], balances[name])
            if peaks[name] > 0:
                drawdowns[name] = max(drawdowns[name], (peaks[name] - balances[name]) / peaks[name])
    return {"bets": bets, **{
        name: {"ending_bankroll": balances[name], "profit": balances[name] - starting_bankroll,
               "staked": staked[name], "roi": (balances[name] - starting_bankroll) / staked[name] if staked[name] else None,
               "max_drawdown": drawdowns[name]}
        for name in balances
    }}


def generate_backtest_summary(resolved: list[dict]):
    """Create a leakage-free report using only predictions recorded before results."""
    lines = [
        "# Tennis Bot Backtest", "",
        "This report uses the opening odds and model probabilities saved before settlement.",
        "Flat-unit ROI makes segments comparable; fewer than 30 settled bets is a small sample.",
    ]
    odds_bands = [(1.0, 1.5), (1.5, 1.75), (1.75, 2.0), (2.0, 2.5), (2.5, 99.0)]
    _append_segment_table(lines, "Odds bands", [
        (f"{low:.2f}–{high:.2f}" if high < 99 else "2.50+", [r for r in resolved if low <= float(r.get("OPENING_ODDS") or 0) < high])
        for low, high in odds_bands
    ])
    ev_bands = [(-99, 0), (0, .03), (.03, .06), (.06, .10), (.10, 99)]
    _append_segment_table(lines, "Expected-value bands", [
        ("Negative" if high == 0 else f"{low:.0%}–{high:.0%}" if high < 99 else "10%+", [r for r in resolved if low <= float(r.get("EV") or 0) < high])
        for low, high in ev_bands
    ])
    for field, title in (("TOUR", "Tour and level"), ("SURFACE", "Surface"), ("BEST_OF", "Match format"), ("INDOOR", "Environment"),
                         ("QUALITY_GRADE", "Evidence quality")):
        values = sorted({row.get(field) or "Unknown" for row in resolved})
        _append_segment_table(lines, title, [(value, [r for r in resolved if (r.get(field) or "Unknown") == value]) for value in values])
    lines.extend(["", "## Tour calibration maturity", "",
                  "Calibration is isolated by tour and activates only when the local ±5-point probability bucket has at least 100 settled predictions.", "",
                  "| Tour | Settled predictions | Largest 10-point bucket | Status |", "|---|---:|---:|---|"])
    for tour in ("ATP", "WTA", "Challenger", "ITF"):
        tour_rows = [row for row in resolved if canonical_tour(row.get("TOUR")) == tour]
        bucket_counts = []
        for low in (0, .1, .2, .3, .4, .5, .6, .7, .8, .9):
            bucket_counts.append(sum(low <= float(row.get("MODEL_PROBABILITY") or -1) < low + .1 for row in tour_rows))
        largest = max(bucket_counts, default=0)
        lines.append(f"| {tour} | {len(tour_rows)} | {largest} | {'locally eligible' if largest >= MIN_CALIBRATION_SAMPLE else 'collecting data'} |")
    lines.extend(["", "## Format model maturity", "",
                  "BO3 and BO5 component-weight challengers train and pass holdout gates independently.", "",
                  "| Format | Settled predictions | Holdout | Promotion |", "|---|---:|---:|---|"])
    for best_of in (3, 5):
        format_rows = [row for row in resolved if canonical_best_of(row.get("BEST_OF")) == best_of]
        learned = learned_format_component_weights(resolved, best_of)
        lines.append(
            f"| BO{best_of} | {len(format_rows)} | {learned['holdout'] if learned else 0} | "
            f"{'approved' if learned and learned['promoted'] else 'shadow/collecting'} |"
        )
    lines.extend(["", "## Indoor/outdoor model maturity", "",
                  "Indoor and outdoor component-weight challengers train and pass holdout gates independently.", "",
                  "| Environment | Settled predictions | Holdout | Promotion |", "|---|---:|---:|---|"])
    for environment, value in (("Indoor", True), ("Outdoor", False)):
        environment_rows = [row for row in resolved if canonical_environment(row.get("INDOOR")) == environment]
        learned = learned_environment_component_weights(resolved, value)
        lines.append(
            f"| {environment} | {len(environment_rows)} | {learned['holdout'] if learned else 0} | "
            f"{'approved' if learned and learned['promoted'] else 'shadow/collecting'} |"
        )
    months = sorted({(row.get("DATE") or "")[:7] for row in resolved if row.get("DATE")})
    _append_segment_table(lines, "Monthly performance", [(month, [r for r in resolved if (r.get("DATE") or "").startswith(month)]) for month in months])
    simulation = walk_forward_staking_simulation(resolved)
    lines.extend(["", "## Walk-forward staking comparison", "",
                  "Bets are sized from the bankroll available before that match date; outcomes from the same date cannot affect one another.", "",
                  "| Strategy | Bets | Ending bankroll | Profit | ROI on stakes | Max drawdown |",
                  "|---|---:|---:|---:|---:|---:|"])
    for key, label in (("fixed", "Fixed €1 unit"), ("kelly", "Capped quarter-Kelly")):
        result = simulation[key]
        roi = f"{result['roi']:.2%}" if result["roi"] is not None else "N/A"
        lines.append(f"| {label} | {simulation['bets']} | €{result['ending_bankroll']:.2f} | €{result['profit']:.2f} | {roi} | {result['max_drawdown']:.2%} |")
    workload_policy = learned_workload_policy(resolved)
    lines.extend(["", "## Workload threshold challenger", ""])
    if workload_policy is None:
        lines.append(
            f"The workload learner remains inactive: it requires at least {MIN_WORKLOAD_TRAINING_SAMPLE} "
            "chronologically settled prediction rows with usable pre-match workload fields."
        )
    else:
        policy = workload_policy["policy"]
        lines.extend([
            f"- Candidate policy: `{workload_policy['policy_id']}`",
            f"- Sample: {workload_policy['sample']} ({workload_policy['training']} training, {workload_policy['holdout']} holdout)",
            f"- Dense schedule: matches/7d >= {policy['matches_threshold']} or sets/7d >= {policy['sets_threshold']}; penalty {policy['dense_penalty']:.1%}",
            f"- Short rest: rest days <= {policy['rest_threshold']}; penalty {policy['rest_penalty']:.1%}",
            f"- Holdout Brier: active {workload_policy['active_holdout_brier']:.4f}, challenger {workload_policy['challenger_holdout_brier']:.4f}",
            f"- Promotion: {'approved' if workload_policy['promoted'] else 'shadow only'}",
        ])
    atomic_write_text(BACKTEST_FILE, "\n".join(lines) + "\n")
    log(f"Backtest summary saved: {BACKTEST_FILE.name}")


PENDING_HEADERS = [
    "DATE", "MATCH", "PLAYER1", "PLAYER2", "PICK", "TOURNAMENT", "SURFACE",
    "START_TIME", "EVENT_ID", "GRADE", "ODDS_MIN", "ODDS_MAX",
    "DISCOVERY_ODDS", "DISCOVERY_PROBABILITY", "DISCOVERY_EV", "DISCOVERED_AT",
    "MODE", "STATUS", "REASON", "FINAL_ODDS", "FINAL_PROBABILITY", "FINAL_EV",
    "FINAL_BOOKMAKERS", "FINAL_SOURCE", "REVALIDATED_AT", "PRICE_MOVEMENT",
    "PRICE_VELOCITY_PER_HOUR", "PRICE_ACCELERATION_PER_HOUR2", "PRICE_SNAPSHOT_COUNT",
]


def stage_pending_bets(date_str: str, recommendations: list[dict], odds_min: float, odds_max: float) -> int:
    """Persist selected candidates without staking money before the final price check."""
    rows, existing = [], set()
    if PENDING_FILE.exists() and PENDING_FILE.stat().st_size:
        with PENDING_FILE.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        existing = {(row.get("DATE"), normalize_player_name(row.get("PICK", ""))) for row in rows}
    captured_at = datetime.now(timezone.utc)
    now = captured_at.isoformat()
    staged = 0
    for rec in recommendations:
        match = rec.get("match") or {}
        key = (date_str, normalize_player_name(rec.get("player", "")))
        if key in existing:
            continue
        pending_row = {
            "DATE": date_str, "MATCH": f"{match.get('player1', '')} vs {match.get('player2', '')}",
            "PLAYER1": match.get("player1", ""), "PLAYER2": match.get("player2", ""),
            "PICK": rec["player"], "TOURNAMENT": match.get("tournament", ""),
            "SURFACE": match.get("surface", ""), "START_TIME": match.get("start_time", ""),
            "EVENT_ID": match.get("event_id", ""), "GRADE": rec["grade"],
            "ODDS_MIN": odds_min, "ODDS_MAX": odds_max,
            "DISCOVERY_ODDS": f"{rec['odds']:.3f}",
            "DISCOVERY_PROBABILITY": f"{rec['assessed_probability']:.6f}",
            "DISCOVERY_EV": f"{rec['ev']:.6f}", "DISCOVERED_AT": now,
            "MODE": "paper" if PAPER_TRADING_MODE else "live",
            "STATUS": "pending_revalidation", "REASON": "awaiting_pre_match_check",
        }
        rows.append(pending_row)
        append_price_snapshot(captured_at, pending_row, match, {"player_odds": rec["odds"]})
        existing.add(key); staged += 1
    if staged:
        atomic_write_csv(PENDING_FILE, PENDING_HEADERS, rows)
    log(f"Staged {staged} candidate(s) for pre-match revalidation")
    return staged


def update_audit_lifecycle(date_str: str, pick: str, decision: str, reason: str,
                           price_dynamics: dict | None = None):
    if not AUDIT_FILE.exists() or not AUDIT_FILE.stat().st_size:
        return
    with AUDIT_FILE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle); rows, headers = list(reader), reader.fieldnames
    changed = False
    for row in rows:
        if row.get("DATE") == date_str and normalize_player_name(row.get("PICK", "")) == normalize_player_name(pick):
            row["DECISION"], row["REASON"] = decision, reason
            if price_dynamics:
                row["PRICE_SNAPSHOT_COUNT"] = price_dynamics.get("snapshot_count", 0)
                row["PRICE_VELOCITY_PER_HOUR"] = (f"{price_dynamics['velocity_per_hour']:.6f}"
                                                   if price_dynamics.get("velocity_per_hour") is not None else "")
                row["PRICE_ACCELERATION_PER_HOUR2"] = (f"{price_dynamics['acceleration_per_hour2']:.6f}"
                                                        if price_dynamics.get("acceleration_per_hour2") is not None else "")
            changed = True
    if changed:
        atomic_write_csv(AUDIT_FILE, list(headers or []), rows)


def match_time_state(value: str, now: datetime, window_minutes: int = 90) -> str:
    if not value:
        return "missing"
    try:
        start = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except ValueError:
        return "missing"
    minutes = (start - now).total_seconds() / 60
    if minutes < -5:
        return "passed"
    if minutes > window_minutes:
        return "waiting"
    return "ready"


def calculate_price_dynamics(rows: list[dict], date_str: str, match_label: str, pick: str,
                             event_id: str = "") -> dict:
    """Calculate relative price velocity/hour and acceleration/hour² from ordered snapshots."""
    wanted_pick = normalize_player_name(pick)
    wanted_match = normalize_player_name(match_label)
    observations = []
    for item in rows:
        if item.get("DATE") != date_str or normalize_player_name(item.get("PICK", "")) != wanted_pick:
            continue
        if event_id:
            if item.get("EVENT_ID") and item.get("EVENT_ID") != event_id:
                continue
            if not item.get("EVENT_ID") and normalize_player_name(item.get("MATCH", "")) != wanted_match:
                continue
        elif normalize_player_name(item.get("MATCH", "")) != wanted_match:
            continue
        try:
            timestamp = datetime.fromisoformat(str(item.get("TIMESTAMP") or "").replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            odds = float(item.get("ODDS") or "")
            if odds <= 1:
                continue
        except (TypeError, ValueError):
            continue
        observations.append((timestamp.astimezone(timezone.utc), odds))
    observations.sort(key=lambda item: item[0])
    deduplicated = []
    for observation in observations:
        if deduplicated and observation[0] == deduplicated[-1][0]:
            deduplicated[-1] = observation
        else:
            deduplicated.append(observation)
    result = {"snapshot_count": len(deduplicated), "price_movement": None,
              "velocity_per_hour": None, "acceleration_per_hour2": None}
    if len(deduplicated) >= 2:
        first_odds = deduplicated[0][1]
        previous_time, previous_odds = deduplicated[-2]
        latest_time, latest_odds = deduplicated[-1]
        elapsed = (latest_time - previous_time).total_seconds() / 3600
        result["price_movement"] = latest_odds / first_odds - 1
        if elapsed > 0:
            result["velocity_per_hour"] = (latest_odds / previous_odds - 1) / elapsed
    if len(deduplicated) >= 3:
        first_time, first_odds = deduplicated[-3]
        middle_time, middle_odds = deduplicated[-2]
        latest_time, latest_odds = deduplicated[-1]
        first_interval = (middle_time - first_time).total_seconds() / 3600
        second_interval = (latest_time - middle_time).total_seconds() / 3600
        midpoint_interval = (latest_time - first_time).total_seconds() / 7200
        if first_interval > 0 and second_interval > 0 and midpoint_interval > 0:
            first_velocity = (middle_odds / first_odds - 1) / first_interval
            second_velocity = (latest_odds / middle_odds - 1) / second_interval
            result["acceleration_per_hour2"] = (second_velocity - first_velocity) / midpoint_interval
    return result


def append_price_snapshot(now: datetime, row: dict, match: dict | None, baseline: dict | None) -> dict:
    path = PENDING_FILE.with_name("price-history.csv")
    headers = ["TIMESTAMP", "DATE", "EVENT_ID", "MATCH", "PICK", "ODDS", "BOOKMAKERS", "DISPERSION", "SOURCE", "EVENT_STATUS",
               "PRICE_MOVEMENT", "VELOCITY_PER_HOUR", "ACCELERATION_PER_HOUR2", "SNAPSHOT_COUNT"]
    _, rows = read_csv_rows(path)
    dispersion = player_market_dispersion(match, row.get("PICK", "")) if match else None
    snapshot = dict(zip(headers, [now.isoformat(), row.get("DATE", ""), row.get("EVENT_ID", ""), row.get("MATCH", ""), row.get("PICK", ""),
                         f"{baseline['player_odds']:.3f}" if baseline else "", (match or {}).get("bookmaker_count", 0),
                         f"{dispersion:.6f}" if dispersion is not None else "", (match or {}).get("odds_source", ""), (match or {}).get("status", ""),
                         "", "", "", ""]))
    rows.append(snapshot)
    dynamics = calculate_price_dynamics(rows, row.get("DATE", ""), row.get("MATCH", ""), row.get("PICK", ""), row.get("EVENT_ID", ""))
    snapshot.update({
        "PRICE_MOVEMENT": f"{dynamics['price_movement']:.6f}" if dynamics["price_movement"] is not None else "",
        "VELOCITY_PER_HOUR": f"{dynamics['velocity_per_hour']:.6f}" if dynamics["velocity_per_hour"] is not None else "",
        "ACCELERATION_PER_HOUR2": f"{dynamics['acceleration_per_hour2']:.6f}" if dynamics["acceleration_per_hour2"] is not None else "",
        "SNAPSHOT_COUNT": dynamics["snapshot_count"],
    })
    atomic_write_csv(path, headers, rows)
    return dynamics


POLICY_HEADERS = ["DATE", "MODEL_VERSION", "EVENT_ID", "MATCH", "PLAYER1", "PLAYER2", "PICK", "DECISION", "RULE",
                  "ODDS", "PROBABILITY", "EV", "TIMESTAMP", "RESULT", "FLAT_RETURN"]


def record_policy_decision(now: datetime, row: dict, match: dict | None, baseline: dict | None, decision: str, rule: str):
    rows = []
    if POLICY_FILE.exists() and POLICY_FILE.stat().st_size:
        with POLICY_FILE.open(newline="", encoding="utf-8") as handle: rows = list(csv.DictReader(handle))
    key = (row.get("DATE"), row.get("EVENT_ID"), normalize_player_name(row.get("PICK", "")))
    if any((item.get("DATE"), item.get("EVENT_ID"), normalize_player_name(item.get("PICK", ""))) == key for item in rows): return
    rows.append({"DATE": row.get("DATE", ""), "MODEL_VERSION": MODEL_VERSION, "EVENT_ID": row.get("EVENT_ID", ""),
                 "MATCH": row.get("MATCH", ""), "PLAYER1": row.get("PLAYER1", ""), "PLAYER2": row.get("PLAYER2", ""),
                 "PICK": row.get("PICK", ""), "DECISION": decision, "RULE": rule,
                 "ODDS": f"{baseline['player_odds']:.3f}" if baseline else "", "PROBABILITY": f"{baseline['assessed_probability']:.6f}" if baseline else "",
                 "EV": f"{baseline['ev']:.6f}" if baseline else "", "TIMESTAMP": now.isoformat(), "RESULT": "", "FLAT_RETURN": ""})
    atomic_write_csv(POLICY_FILE, POLICY_HEADERS, rows)


def revalidate_pending_bets(api_keys: list[str], now: datetime | None = None) -> tuple[int, int]:
    """Authorize only candidates whose price and model edge survive near match time."""
    if not PENDING_FILE.exists() or not PENDING_FILE.stat().st_size:
        log("No pending tennis bets to revalidate")
        return 0, 0
    now = now or datetime.now(timezone.utc)
    manual_stop = manual_kill_switch()
    with PENDING_FILE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    ready_by_date, cancelled = {}, 0
    for row in rows:
        if row.get("STATUS") != "pending_revalidation":
            continue
        if manual_stop["active"] and (row.get("MODE") or "live") != "paper":
            reason = f"manual_kill_switch:{manual_stop['reason']}"
            row.update({"STATUS": "cancelled", "REASON": reason, "REVALIDATED_AT": now.isoformat()})
            record_policy_decision(now, row, None, None, "cancelled", "manual_kill_switch")
            update_audit_lifecycle(row["DATE"], row["PICK"], "Cancelled", reason)
            cancelled += 1
            continue
        state = match_time_state(row.get("START_TIME", ""), now)
        if state == "waiting":
            continue
        if state in {"missing", "passed"}:
            reason = "start_time_unknown" if state == "missing" else "match_started"
            row.update({"STATUS": "cancelled", "REASON": reason, "REVALIDATED_AT": now.isoformat()})
            record_policy_decision(now, row, None, None, "cancelled", reason)
            update_audit_lifecycle(row["DATE"], row["PICK"], "Cancelled", reason)
            cancelled += 1
        else:
            ready_by_date.setdefault(row["DATE"], []).append(row)

    bankroll = float(BANKROLL_FILE.read_text().strip() or 0) if BANKROLL_FILE.exists() else None
    has_live_candidates = any((row.get("MODE") or "live") != "paper" for candidates in ready_by_date.values() for row in candidates)
    if bankroll is not None and has_live_candidates:
        bankroll = reconcile_bankroll(bankroll)
    authorized_recs, authorized_matches = [], []
    for date_str, candidates in ready_by_date.items():
        fresh = fetch_verified_matches(date_str, api_keys)
        wanted_ids = {row.get("EVENT_ID") for row in candidates}
        wanted_pairs = [{normalize_player_name(row["PLAYER1"]), normalize_player_name(row["PLAYER2"])} for row in candidates]
        matches = [m for m in fresh if m.get("event_id") in wanted_ids or {normalize_player_name(m["player1"]), normalize_player_name(m["player2"])} in wanted_pairs]
        enrich_matches_with_profiles(matches)
        enrich_matches_with_recent_form(matches, date_str)
        for row in candidates:
            pair = {normalize_player_name(row["PLAYER1"]), normalize_player_name(row["PLAYER2"])}
            match = next((m for m in matches if m.get("event_id") == row.get("EVENT_ID") or {normalize_player_name(m["player1"]), normalize_player_name(m["player2"])} == pair), None)
            baseline = calculate_tennis_baseline(match, row["PICK"]) if match else None
            price_dynamics = append_price_snapshot(now, row, match, baseline)
            row.update({
                "PRICE_VELOCITY_PER_HOUR": (f"{price_dynamics['velocity_per_hour']:.6f}"
                                             if price_dynamics["velocity_per_hour"] is not None else ""),
                "PRICE_ACCELERATION_PER_HOUR2": (f"{price_dynamics['acceleration_per_hour2']:.6f}"
                                                  if price_dynamics["acceleration_per_hour2"] is not None else ""),
                "PRICE_SNAPSHOT_COUNT": price_dynamics["snapshot_count"],
            })
            reason = None
            status = str((match or {}).get("status") or "").casefold()
            quality = tennis_data_quality(match, baseline, row["PICK"]) if match and baseline else None
            movement = baseline["player_odds"] / float(row["DISCOVERY_ODDS"]) - 1 if baseline else None
            if any(token in status for token in ("cancel", "postpon", "settled", "live", "inplay", "in-play", "withdraw", "walkover", "retir", "suspend")):
                reason = "event_not_pre_match"
            elif not match or not baseline:
                reason = "market_or_model_unavailable"
            elif int(match.get("bookmaker_count") or 0) < 2:
                reason = "insufficient_bookmakers"
            elif quality and quality["dispersion"] is not None and quality["dispersion"] > MAX_BOOKMAKER_DISPERSION:
                reason = "bookmaker_conflict"
            elif quality and quality["score"] < 5:
                reason = "data_quality_too_low"
            elif movement is not None and abs(movement) > MAX_PRICE_MOVEMENT:
                reason = "extreme_price_movement"
            elif row.get("SURFACE") and match.get("surface") and row["SURFACE"] != match["surface"]:
                reason = "surface_changed"
            elif not float(row["ODDS_MIN"]) <= baseline["player_odds"] <= float(row["ODDS_MAX"]):
                reason = "price_outside_range"
            elif baseline.get("physical_block"):
                reason = f"verified_physical_status:{baseline.get('physical_status', 'unavailable')}"
            elif not tennis_baseline_is_reliable(baseline):
                reason = "model_disagreement"
            elif baseline.get("risk_adjusted_ev", baseline["ev"]) <= 0.05:
                reason = "uncertainty_adjusted_edge_too_low"
            row["REVALIDATED_AT"] = now.isoformat()
            if reason:
                row.update({"STATUS": "cancelled", "REASON": reason}); cancelled += 1
                record_policy_decision(now, row, match, baseline, "cancelled", reason)
                update_audit_lifecycle(row["DATE"], row["PICK"], "Cancelled", reason, price_dynamics)
                continue
            row.update({
                "STATUS": "authorized", "REASON": "pre_match_validated",
                "FINAL_ODDS": f"{baseline['player_odds']:.3f}",
                "FINAL_PROBABILITY": f"{baseline['assessed_probability']:.6f}",
                "FINAL_EV": f"{baseline['ev']:.6f}",
                "FINAL_BOOKMAKERS": match.get("bookmaker_count", 0),
                "FINAL_SOURCE": match.get("odds_source", ""),
                "PRICE_MOVEMENT": f"{movement:.6f}",
            })
            authorized_recs.append({"_date": row["DATE"], "_paper": row.get("MODE") == "paper", "player": row["PICK"], "grade": row["GRADE"], "odds": baseline["player_odds"], "assessed_probability": baseline["assessed_probability"], "ev": baseline["ev"], "match": match})
            record_policy_decision(now, row, match, baseline, "authorized", "pre_match_validated")
            authorized_matches.append(match)
            update_audit_lifecycle(row["DATE"], row["PICK"], "Authorized", "pre_match_validated", price_dynamics)
    total_stake = 0.0
    for date_str, paper in sorted({(rec["_date"], rec["_paper"]) for rec in authorized_recs}):
        recs = [rec for rec in authorized_recs if rec["_date"] == date_str and rec["_paper"] == paper]
        stake = log_bets(date_str, recs, authorized_matches, bankroll - total_stake if bankroll is not None else None, paper_trading=paper)
        if not paper:
            total_stake += stake
    if total_stake:
        save_bankroll(bankroll, total_stake)
    atomic_write_csv(PENDING_FILE, PENDING_HEADERS, rows)
    recent = [row for row in rows if row.get("REVALIDATED_AT") == now.isoformat()]
    lines = ["# Tennis Bet Lifecycle", "", f"Updated: {now.isoformat()}", "", "| Match | Pick | Status | Reason | Final odds | Final EV |", "|---|---|---|---|---:|---:|"]
    for row in recent:
        final_ev = f"{float(row['FINAL_EV']):.1%}" if row.get("FINAL_EV") else "—"
        lines.append(f"| {row.get('MATCH', '')} | {row.get('PICK', '')} | {row.get('STATUS', '')} | {row.get('REASON', '')} | {row.get('FINAL_ODDS') or '—'} | {final_ev} |")
    if not recent: lines.append("| — | — | waiting | No candidates were ready in this run | — | — |")
    atomic_write_text(PENDING_FILE.with_name("lifecycle-summary.md"), "\n".join(lines) + "\n")
    log(f"Pre-match revalidation authorized {len(authorized_recs)}, cancelled {cancelled}")
    return len(authorized_recs), cancelled


def log_bets(
    date_str: str,
    recommendations: list[dict],
    matches: list[dict],
    bankroll: float | None,
    paper_trading: bool = False,
):
    """Append real or simulated bets to their isolated log CSV."""
    target_log = PAPER_LOG_FILE if paper_trading else LOG_FILE
    file_exists = target_log.exists()
    rows_to_append = []
    current_balance = bankroll
    total_stake = 0.0
    existing_bets = set()
    if file_exists and LOG_FILE.stat().st_size > 0:
        with open(target_log, newline="", encoding="utf-8") as existing_file:
            for row in csv.DictReader(existing_file):
                existing_bets.add((
                    row.get("DATE", "").strip(),
                    normalize_player_name(
                        re.sub(r"\s+to win\s*$", "", row.get("BET", ""), flags=re.I)
                    ),
                ))

    for rec in recommendations:
        if rec["grade"] not in ("Top Pick", "Value Pick"):
            continue
        bet_key = (date_str, normalize_player_name(rec["player"]))
        if bet_key in existing_bets:
            log(f"  Skipped duplicate logged bet: {rec['player']} on {date_str}")
            continue

        # Find match info
        match_info = None
        for m in matches:
            if rec["player"].lower() in m["player1"].lower() or rec["player"].lower() in m["player2"].lower():
                match_info = m
                break

        if not match_info:
            continue

        # Capped quarter-Kelly: probability drives sizing, grade remains the hard cap.
        if current_balance is not None:
            cap = 0.03 if rec["grade"] == "Top Pick" else 0.02
            try:
                odds = float(rec["odds"]); probability = float(rec["assessed_probability"])
                full_kelly = max(0.0, (probability * odds - 1) / (odds - 1))
                stake_pct = min(cap, max(MIN_STAKE_RATE, full_kelly * KELLY_FRACTION))
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                stake_pct = MIN_STAKE_RATE

            stake = round(current_balance * stake_pct, 2)
            total_stake += stake
        else:
            stake = 0.0

        match_label = f"{match_info['player1']} vs {match_info['player2']} ({match_info['tournament']})"
        bet_label = f"{rec['player']} to win"
        odds_str = f"{rec['odds']:.2f}" if rec["odds"] else ""
        stake_str = f"{stake:.2f}" if stake else ""
        balance_str = f"{current_balance:.2f}" if current_balance is not None else ""

        rows_to_append.append({
            "date": date_str,
            "match": match_label,
            "bet": bet_label,
            "odds": odds_str,
            "stake": stake_str,
            "result": "",
            "return": "",
            "starting_balance": balance_str,
        })
        existing_bets.add(bet_key)

        if current_balance is not None:
            current_balance -= stake

    if not rows_to_append:
        log("No bets to log.")
        return total_stake

    headers = ["DATE", "MATCH", "BET", "ODDS", "STAKE", "RESULT", "RETURN", "STARTING BALANCE"]
    _, existing_rows = read_csv_rows(target_log)
    existing_rows.extend({
        "DATE": row["date"], "MATCH": row["match"], "BET": row["bet"], "ODDS": row["odds"],
        "STAKE": row["stake"], "RESULT": row["result"], "RETURN": row["return"],
        "STARTING BALANCE": row["starting_balance"],
    } for row in rows_to_append)
    atomic_write_csv(target_log, headers, existing_rows)

    log(f"Logged {len(rows_to_append)} {'paper ' if paper_trading else ''}bets to {target_log.name}")
    return total_stake


# ─── Report ──────────────────────────────────────────────────────────

def save_report(date_str: str, report: str):
    """Save the AI report to a dated file."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"picks-{date_str}.md"
    path = REPORTS_DIR / filename
    atomic_write_text(path, report)
    log(f"Report saved: {path}")


# ─── Main ────────────────────────────────────────────────────────────

def already_logged_today(date_str: str, paper_trading: bool = False) -> bool:
    """Check if bets for this date already exist in the log."""
    target = PAPER_LOG_FILE if paper_trading else LOG_FILE
    if not target.exists() or target.stat().st_size == 0:
        return False
    with open(target, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if row and row[0].strip() == date_str:
                return True
    return False


def already_staged_today(date_str: str, paper_trading: bool = False) -> bool:
    if not PENDING_FILE.exists() or not PENDING_FILE.stat().st_size:
        return False
    with PENDING_FILE.open(newline="", encoding="utf-8") as handle:
        wanted_mode = "paper" if paper_trading else "live"
        return any(row.get("DATE") == date_str and row.get("STATUS") == "pending_revalidation"
                   and (row.get("MODE") or "live") == wanted_mode for row in csv.DictReader(handle))


def add_validation_summary(
    report: str,
    candidate_count: int,
    recommendations: list[dict],
) -> str:
    """Make the saved report agree with Python's authoritative decision."""
    lines = [
        "",
        "## PYTHON VALIDATION RESULT",
        "",
        (
            f"The analysis produced {candidate_count} candidate(s). "
            f"Python accepted {len(recommendations)} candidate(s) for staging after matching "
            "verified odds and recalculating expected value. They are not actual bets "
            "until the pre-match workflow authorizes them."
        ),
    ]
    if recommendations:
        for rec in recommendations:
            lines.append(
                f"- **{rec['player']}** — {rec['grade']}, odds "
                f"{rec['odds']:.2f}, assessed probability "
                f"{rec['assessed_probability']:.1%}, verified EV {rec['ev']:.2%}."
            )
    else:
        lines.extend([
            "",
            "**Final betting decision: NO BETS.** Any narrative picks above were "
            "rejected and must not be treated as recommendations.",
        ])
    return report.rstrip() + "\n" + "\n".join(lines) + "\n"


def build_deterministic_report(
    date_str: str,
    matches: list[dict],
    candidates: list[dict],
) -> str:
    """Provide usable output when Groq is unavailable or omits candidates."""
    lines = [
        "## MARKET OVERVIEW",
        "",
        f"Python evaluated {len(matches)} verified singles matches for {date_str} "
        "using de-vigged moneyline prices and Tennis Abstract overall Elo.",
        "",
        "## TOP PICKS",
        "",
        "See the authoritative Python validation result below.",
        "",
        "## VALUE PICKS",
        "",
        "Positive-EV baseline candidates are supplied to the validator below.",
        "",
        "## PICKS TO AVOID",
        "",
        "Players with missing Elo, excessive market margin, large market/Elo "
        "disagreement, or non-positive EV.",
        "",
        "## DISCLAIMER",
        "",
        "The Elo/market blend is a heuristic, not a guarantee. Odds change and "
        "betting involves risk.",
        "",
        "## MACHINE READABLE PICKS",
        "",
        "```json",
        json.dumps(candidates, indent=2, ensure_ascii=False),
        "```",
    ]
    return "\n".join(lines) + "\n"


def finalize_analysis(
    date_str: str,
    report: str,
    matches: list[dict],
    bankroll: float | None,
    odds_min: float,
    odds_max: float,
    statistical_candidates: list[dict] | None = None,
):
    """Run the shared safety, staking, logging, and reporting pipeline."""
    parsed = parse_recommendations(report)
    log(f"Parsed {len(parsed)} recommendation candidates from report")
    candidates_by_player = {
        normalize_player_name(item["player"]): item
        for item in (statistical_candidates or [])
    }
    for item in parsed:
        candidates_by_player[normalize_player_name(item["player"])] = item
    candidates = list(candidates_by_player.values())
    recommendations = validate_recommendations(
        candidates,
        matches,
        odds_min,
        odds_max,
    )
    log(f"Validated {len(recommendations)} recommendations")
    authorized = select_portfolio(recommendations)
    authorized, block_reason = apply_manual_kill_switch(authorized, PAPER_TRADING_MODE)
    append_prediction_audit(date_str, matches, recommendations, authorized, block_reason)
    save_rollback_state()
    stage_pending_bets(date_str, authorized, odds_min, odds_max)

    final_report = add_validation_summary(report, len(candidates), authorized)
    save_report(date_str, final_report)
    generate_performance_summary()
    log("=== Done ===")
    print("\n" + final_report)


def run_diagnostic(date_str: str, odds_min: float, odds_max: float, api_keys: list[str]) -> dict:
    """Exercise collection and deterministic validation without mutating project state."""
    matches = fetch_verified_matches(date_str, api_keys)
    qualified = attach_odds(matches, odds_min, odds_max)
    if qualified:
        enrich_matches_with_profiles(qualified)
        enrich_matches_with_recent_form(qualified, date_str)
    baselines = sum(calculate_tennis_baseline(match, player) is not None for match in qualified for player in (match["player1"], match["player2"]))
    return {"mode": "diagnostic", "date": date_str, "fixture_status": LAST_FIXTURE_STATUS,
            "verified_matches": len(matches), "qualified_matches": len(qualified), "modelled_players": baselines,
            "source_requests": len(SOURCE_HEALTH), "source_failures": sum(not item["ok"] for item in SOURCE_HEALTH),
            "would_write": False, "would_settle": False, "would_call_ai": False, "would_stake": False}


def main():
    global DIAGNOSTIC_MODE, PAPER_TRADING_MODE
    args = parse_args()
    DIAGNOSTIC_MODE = args.diagnostic
    PAPER_TRADING_MODE = args.paper_trading

    date_str = resolve_date(args.date)
    odds_min = args.odds_min
    odds_max = args.odds_max

    log(f"=== Tennis Bot — {date_str} ===")
    log(f"Odds range: {odds_min}-{odds_max}")

    if args.backtest_only:
        generate_performance_summary()
        log("Backtest-only run complete")
        return

    odds_api_keys = [
        value for value in (
            os.environ.get("ODDS_API_KEY"),
            os.environ.get("ODDS_API_KEY_2"),
            os.environ.get("ODDS_API_KEY_3"),
            os.environ.get("ODDS_API_KEY_4"),
            os.environ.get("ODDS_API_KEY_5"),
        )
        if value
    ]
    if not odds_api_keys:
        log("ERROR: No odds keys configured.")
        sys.exit(1)
    log(f"Loaded {len(odds_api_keys)} Odds API key(s)")
    if args.diagnostic:
        if args.bankroll is not None:
            log("Diagnostic mode ignores --bankroll to guarantee no writes")
        result = run_diagnostic(date_str, odds_min, odds_max, odds_api_keys)
        print(json.dumps(result, indent=2))
        return
    mode = "settlement" if args.settle_only else "revalidation" if args.revalidate_only else "paper_daily" if args.paper_trading else "daily"
    begin_run_state(date_str, mode)
    settle_pending_bets(odds_api_keys, include_real=not args.paper_trading)
    update_run_state("settlement_complete")
    generate_performance_summary()
    save_source_health()

    if args.settle_only:
        update_run_state("complete", "complete")
        log("Settlement-only run complete")
        return

    if args.revalidate_only:
        revalidate_pending_bets(odds_api_keys)
        update_run_state("revalidation_complete")
        generate_performance_summary()
        save_source_health()
        update_run_state("complete", "complete")
        log("Revalidation-only run complete")
        return

    if not args.force and (already_logged_today(date_str, args.paper_trading) or already_staged_today(date_str, args.paper_trading)):
        log(f"Bets already logged or awaiting revalidation for {date_str}. Skipping to avoid duplicates.")
        log("(Use --force to override.)")
        update_run_state("duplicate_safe_skip", "complete")
        return

    bankroll = args.bankroll if args.paper_trading and args.bankroll is not None else load_bankroll(None if args.paper_trading else args.bankroll)
    if args.paper_trading:
        log(f"Paper-trading mode active; real bankroll and ledger will not change (virtual bankroll €{bankroll:.2f})" if bankroll is not None else "Paper-trading mode active; using zero virtual stakes because no bankroll is available")
    if bankroll is None:
        log("WARNING: No bankroll set. Run with --bankroll <amount>")

    # Stage 1: Collect verified matches and odds
    log("Fetching tennis fixtures and odds...")
    all_matches = fetch_verified_matches(date_str, odds_api_keys)
    if not all_matches:
        if LAST_FIXTURE_STATUS in {"provider_failure", "provider_schema_failure"}:
            title, explanation = "DATA COLLECTION FAILURE", "The fixture provider failed, so this run is not evidence that no qualifying bets existed."
        elif LAST_FIXTURE_STATUS == "valid_empty_schedule":
            title, explanation = "VALID EMPTY SCHEDULE", "The provider responded successfully but returned no tennis fixtures for the requested date."
        else:
            title, explanation = "ODDS UNAVAILABLE", "Fixtures existed, but no verified moneyline market could be constructed."
        report = f"# {title}\n\nDate: {date_str}\n\n{explanation}\n\nNo bets were staged and no bankroll was changed.\n"
        log(f"{title}: {explanation}")
        save_report(date_str, report); save_source_health(); print("\n" + report)
        update_run_state("no_data_complete", "complete", LAST_FIXTURE_STATUS)
        return
    update_run_state("collection_complete", detail=f"{len(all_matches)} verified matches")

    # Attach odds
    qualified = attach_odds(all_matches, odds_min, odds_max)

    log("Fetching Tennis Abstract profiles for Python validation...")
    enrich_matches_with_profiles(qualified)
    log("Fetching recent results for opponent-adjusted form...")
    enrich_matches_with_recent_form(qualified, date_str)
    statistical_candidates = build_statistical_candidates(
        qualified, odds_min, odds_max
    )
    log(f"Found {len(statistical_candidates)} positive-EV Elo/market candidates")

    # Stage 2 & 3: AI Analysis
    analysis_matches = select_analysis_matches(qualified)
    log(
        f"Building bounded analysis prompt with {len(analysis_matches)}/"
        f"{len(qualified)} qualifying matches..."
    )
    prompt = build_prompt(date_str, analysis_matches, bankroll, odds_min, odds_max)

    groq_api_keys = [
        value for value in (
            os.environ.get("GROQ_API_KEY"),
            os.environ.get("GROQ_API_KEY_2"),
            os.environ.get("GROQ_API_KEY_3"),
            os.environ.get("GROQ_API_KEY_4"),
            os.environ.get("GROQ_API_KEY_5"),
        )
        if value
    ]
    report = None
    if groq_api_keys:
        log(f"Loaded {len(groq_api_keys)} Groq API key(s)")
        try:
            report = call_ai(prompt, groq_api_keys)
        except (requests.RequestException, RuntimeError, ValueError):
            log("Groq unavailable; continuing with deterministic Python report")
    else:
        log("No Groq API keys configured; using deterministic Python report")
    if report is None:
        report = build_deterministic_report(
            date_str, qualified, statistical_candidates
        )
    finalize_analysis(
        date_str,
        report,
        qualified,
        bankroll,
        odds_min,
        odds_max,
        statistical_candidates,
    )
    save_source_health()
    update_run_state("complete", "complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if RUN_STATE_ACTIVE:
            update_run_state("interrupted", "interrupted", type(exc).__name__)
        raise
