"""
Tennis Betting Bot — Automated daily picks pipeline.
Runs the 3-stage analysis via Groq API and logs results.
Designed for GitHub Actions execution.
"""

import argparse
import csv
import difflib
import io
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
BANKROLL_FILE = REPO_ROOT / "bankroll.txt"
LOG_FILE = REPO_ROOT / "bets-log.csv"
AUDIT_FILE = REPO_ROOT / "predictions-log.csv"
PERFORMANCE_FILE = REPO_ROOT / "performance-summary.md"
BACKTEST_FILE = REPO_ROOT / "backtest-summary.md"
PLAYER_ALIASES_FILE = REPO_ROOT / "player-aliases.csv"
REPORTS_DIR = REPO_ROOT / "reports"
REQUEST_TIMEOUT = 30
MAX_COMPLETION_TOKENS = 2048
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_AI_MATCHES = 20
MAX_DAILY_EXPOSURE = 0.08
MAX_DAILY_BETS = 4
MAX_MARKET_OVERROUND = 1.12
MAX_ELO_MARKET_GAP = 0.15
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}


# ─── Helpers ────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        log(f"  Failed to fetch {url}: {e}")
        return None


def fetch_reader(target_url: str) -> str | None:
    """Fetch a page through Jina Reader using API headers, not browser headers."""
    reader_headers = {
        "Accept": "text/plain",
        "User-Agent": "tennis-betting-bot/1.0",
        "X-Return-Format": "markdown",
    }
    targets = [target_url]
    if target_url.startswith("https://"):
        targets.append("http://" + target_url.removeprefix("https://"))

    for target in targets:
        reader_url = f"https://r.jina.ai/{target}"
        try:
            response = requests.get(
                reader_url,
                headers=reader_headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            if response.text.strip():
                return response.text
        except requests.RequestException as exc:
            log(f"  Reader request failed for {target}: {exc}")
    return None


def fetch_json(url: str, params: dict | None = None):
    """Fetch JSON while keeping API keys out of log output."""
    try:
        response = requests.get(
            url,
            params=params,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        log(f"  API request failed for {url}: {exc}")
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

    for offset in range(len(api_keys)):
        candidate_index = (key_index + offset) % len(api_keys)
        request_params = {**params, "apiKey": api_keys[candidate_index]}
        try:
            response = requests.get(
                url,
                params=request_params,
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code in {401, 403, 429}:
                log(
                    f"  Odds API key {candidate_index + 1}/{len(api_keys)} "
                    f"unavailable ({response.status_code}); rotating"
                )
                continue
            response.raise_for_status()
            return response.json(), candidate_index
        except (requests.RequestException, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            detail = f"HTTP {status}" if status else type(exc).__name__
            log(f"  Odds API request failed for {url}: {detail}")
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
    parser.add_argument("--backtest-only", action="store_true", help="Rebuild analytics without API calls")
    return parser.parse_args()


def resolve_date(raw: str | None) -> str:
    if raw:
        return raw
    return datetime.now().strftime("%Y-%m-%d")


def load_bankroll(args_bankroll: float | None) -> float | None:
    if args_bankroll is not None:
        with open(BANKROLL_FILE, "w") as f:
            f.write(str(args_bankroll))
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
    remaining = round(bankroll - total_stake, 2)
    with open(BANKROLL_FILE, "w") as f:
        f.write(str(remaining))
    log(f"Bankroll saved: €{remaining:.2f} (was €{bankroll:.2f}, staked €{total_stake:.2f})")


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
        return {"best_home": None, "best_away": None, "consensus_home": None, "consensus_away": None, "source": None, "bookmaker_count": 0}
    homes, aways = sorted(p[0] for p in prices_found), sorted(p[1] for p in prices_found)
    midpoint = len(homes) // 2
    median_home = homes[midpoint] if len(homes) % 2 else (homes[midpoint - 1] + homes[midpoint]) / 2
    median_away = aways[midpoint] if len(aways) % 2 else (aways[midpoint - 1] + aways[midpoint]) / 2
    best_home = max(prices_found, key=lambda p: p[0])
    best_away = max(prices_found, key=lambda p: p[1])
    source = best_home[2] if best_home[2] == best_away[2] else f"{best_home[2]}/{best_away[2]}"
    return {"best_home": best_home[0], "best_away": best_away[1], "consensus_home": median_home, "consensus_away": median_away, "source": source, "bookmaker_count": len(prices_found)}


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


def fetch_matches_from_odds_api(date_str: str, api_keys: list[str]) -> list[dict]:
    """Fetch verified tennis fixtures and match-winner odds from Odds-API.io."""
    events_payload, key_index = fetch_odds_json(
        "https://api.odds-api.io/v3/events",
        {"sport": "tennis"},
        api_keys,
        0,
    )
    if events_payload is None:
        return []

    if isinstance(events_payload, list):
        events = events_payload
    else:
        events = events_payload.get("events") or events_payload.get("data") or []

    dated_events = [
        event for event in events
        if str(event.get("date", "")).startswith(date_str)
        and event.get("home")
        and event.get("away")
    ]
    log(f"  Found {len(dated_events)} tennis events from Odds-API.io")

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
        if isinstance(payload, list):
            odds_events = payload
        elif isinstance(payload, dict):
            odds_events = payload.get("events") or payload.get("data") or []
        else:
            odds_events = []

        for odds_event in odds_events:
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
            tournament = league.get("name") or "Tennis"
            matches.append({
                "event_id": str(event.get("id", odds_event.get("id", ""))),
                "start_time": event.get("date") or odds_event.get("date"),
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
            })
    log(f"  Found verified moneyline odds for {len(matches)} matches")
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
    if not PLAYER_ALIASES_FILE.exists() or not PLAYER_ALIASES_FILE.stat().st_size:
        return {}
    with PLAYER_ALIASES_FILE.open(newline="", encoding="utf-8") as handle:
        return {
            normalize_player_name(row.get("PROVIDER_NAME", "")): normalize_player_name(row.get("CANONICAL_NAME", ""))
            for row in csv.DictReader(handle)
            if row.get("PROVIDER_NAME") and row.get("CANONICAL_NAME")
        }


def save_player_alias(provider_name: str, canonical_name: str, confidence: float):
    aliases = load_player_aliases()
    provider_key = normalize_player_name(provider_name)
    if not provider_key or provider_key in aliases:
        return
    write_header = not PLAYER_ALIASES_FILE.exists() or not PLAYER_ALIASES_FILE.stat().st_size
    with PLAYER_ALIASES_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(["PROVIDER_NAME", "CANONICAL_NAME", "SOURCE", "CONFIDENCE"])
        writer.writerow([provider_name, canonical_name, "auto_unique", f"{confidence:.3f}"])


def resolve_profile_key(player: str, profiles: dict[str, dict], aliases: dict[str, str]) -> str | None:
    """Resolve exact/approved aliases first; allow only unique high-confidence fuzzy matches."""
    key = normalize_player_name(player)
    if key in profiles:
        return key
    alias_key = aliases.get(key)
    if alias_key in profiles:
        return alias_key
    candidates = []
    for candidate, profile in profiles.items():
        score = difflib.SequenceMatcher(None, key, candidate).ratio()
        if score >= 0.92:
            candidates.append((score, candidate, profile["name"]))
    candidates.sort(reverse=True)
    if len(candidates) == 1 or (candidates and len(candidates) > 1 and candidates[0][0] - candidates[1][0] >= 0.05):
        score, candidate, canonical = candidates[0]
        save_player_alias(player, canonical, score)
        return candidate
    return None


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
        html = fetch(url)
        tour_profiles = parse_tennis_abstract_elo(html) if html else {}
        if not tour_profiles:
            log(f"  Direct Tennis Abstract {tour} access unavailable; trying reader")
            reader_text = fetch_reader(url)
            tour_profiles = (
                parse_tennis_abstract_reader(reader_text)
                if reader_text
                else {}
            )
        if tour_profiles:
            profiles.update(tour_profiles)
            log(f"  Loaded {len(tour_profiles)} Tennis Abstract {tour} profiles")
        else:
            log(f"  Tennis Abstract {tour} leaderboard unavailable from all sources")

    aliases = load_player_aliases()
    selected = {}
    for match in matches:
        for player in (match["player1"], match["player2"]):
            if "/" in player:
                continue
            resolved = resolve_profile_key(player, profiles, aliases)
            if resolved:
                selected[normalize_player_name(player)] = profiles[resolved]
    log(f"  Tennis Abstract profiles matched: {len(selected)}/{len(wanted)}")
    return selected


def compact_profile_line(player: str, profiles: dict[str, dict]) -> str:
    """Render verified profile data without sending page HTML to the model."""
    profile = profiles.get(normalize_player_name(player))
    if not profile:
        return f"- {player}: profile unavailable"

    def shown(value):
        return "N/A" if value is None else f"{value:g}"

    return (
        f"- {player}: official rank={shown(profile['official_rank'])}; "
        f"age={shown(profile['age'])}; Elo={shown(profile['elo'])} "
        f"(Elo rank #{shown(profile['elo_rank'])}); "
        f"hard Elo={shown(profile['hard_elo'])}; "
        f"clay Elo={shown(profile['clay_elo'])}; "
        f"grass Elo={shown(profile['grass_elo'])}; "
        f"peak Elo={shown(profile['peak_elo'])}"
        f"{' (' + profile['peak_month'] + ')' if profile['peak_month'] else ''}"
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
    return profiles


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
        for text in executor.map(fetch, urls):
            if text:
                history.extend(csv.DictReader(io.StringIO(text)))
    wanted = {normalize_player_name(player) for match in matches for player in (match["player1"], match["player2"])}
    filtered = [row for row in history if normalize_player_name(row.get("winner_name", "")) in wanted or normalize_player_name(row.get("loser_name", "")) in wanted]
    log(f"  Loaded {len(filtered)} relevant historical matches for opponent-adjusted form")
    return filtered


def enrich_matches_with_recent_form(matches: list[dict], date_str: str):
    history = fetch_recent_match_history(matches, date_str)
    for match in matches:
        match["player1_recent_form"] = calculate_recent_form(history, match["player1"], match.get("surface"), date_str)
        match["player2_recent_form"] = calculate_recent_form(history, match["player2"], match.get("surface"), date_str)


def calculate_tennis_baseline(match: dict, player: str) -> dict | None:
    """Blend de-vigged two-way market probability with independent overall Elo."""
    if "/" in match.get("player1", "") or "/" in match.get("player2", ""):
        return None
    home_odds = match.get("home_odds")
    away_odds = match.get("away_odds")
    if not all(isinstance(odds, (int, float)) and odds > 1 for odds in (home_odds, away_odds)):
        return None

    player_key = normalize_player_name(player)
    if player_key == normalize_player_name(match["player1"]):
        player_odds = float(home_odds)
        player_profile = match.get("player1_profile")
        opponent_profile = match.get("player2_profile")
        recent_form = match.get("player1_recent_form")
    elif player_key == normalize_player_name(match["player2"]):
        player_odds = float(away_odds)
        player_profile = match.get("player2_profile")
        opponent_profile = match.get("player1_profile")
        recent_form = match.get("player2_recent_form")
    else:
        return None

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
    if recent_form and recent_form.get("sample", 0) >= 8:
        assessed_probability = 0.50 * elo_probability + 0.35 * market_probability + 0.15 * recent_form["probability"]
    else:
        assessed_probability = 0.55 * elo_probability + 0.45 * market_probability
    ev = assessed_probability * player_odds - 1
    score = max(0.0, min(10.0, 6.0 + max(0.0, ev) * 30))
    return {
        "player_odds": player_odds,
        "market_probability": market_probability,
        "elo_probability": elo_probability,
        "form_probability": recent_form["probability"] if recent_form else None,
        "form_sample": recent_form["sample"] if recent_form else 0,
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
                baseline_lines.append(
                    f"  Python baseline for {player}: market fair "
                    f"{baseline['market_probability']:.1%}, Elo "
                    f"{baseline['elo_probability']:.1%}, opponent-adjusted form {form_text}, "
                    f"blended assessed "
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
        "\nSource: Tennis Abstract weekly Elo leaderboards. Fields not shown "
        "above, including current form, head-to-head, serve/return splits, "
        "physical status, and Match Charting Project tactics, are unavailable "
        "for this run and MUST NOT be invented.\n"
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
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        last_response = response
        if response.status_code in {401, 403, 429} and key_index < len(api_keys) - 1:
            log(
                f"  Groq key unavailable ({response.status_code}); "
                "rotating to next key"
            )
            continue
        try:
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            log(f"Groq response: {len(content)} chars")
            return content
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            log(f"Groq API error: {exc}")
            if isinstance(exc, requests.RequestException) and exc.response is not None:
                log(f"Response body: {exc.response.text[:500]}")
            raise

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
            log(
                f"  Rejected {verified_player}: missing Elo, excessive market "
                "margin, or large Elo/market disagreement"
            )
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
    stake_rates = {"Top Pick": 0.03, "Value Pick": 0.02}
    ranked = sorted(
        recommendations,
        key=lambda rec: (rec.get("ev", 0), rec.get("score", 0)),
        reverse=True,
    )
    selected = []
    seen_matches = set()
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
        if len(selected) >= max_bets or exposure + stake_rate > max_exposure + 1e-9:
            log(f"  Portfolio rejected {recommendation['player']}: daily risk cap reached")
            continue
        selected.append(recommendation)
        seen_matches.add(match_key)
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
    grade = "A" if points >= 9 else "B" if points >= 7 else "C" if points >= 5 else "D"
    return points, grade


def append_prediction_audit(date_str, matches, recommendations, authorized):
    """Persist all Elo-modelled singles candidates and final decisions."""
    headers = [
        "DATE", "EVENT_ID", "MATCH", "PICK", "OPENING_ODDS",
        "MARKET_PROBABILITY", "ELO_PROBABILITY", "MODEL_PROBABILITY",
        "FORM_PROBABILITY", "FORM_SAMPLE", "EV", "SCORE", "EVIDENCE", "QUALITY_SCORE", "QUALITY_GRADE",
        "TOUR", "SURFACE", "BOOKMAKERS", "DECISION", "REASON", "RESULT",
        "CLOSING_ODDS", "CLV",
    ]
    if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size:
        with open(AUDIT_FILE, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            old_rows, old_headers = list(reader), reader.fieldnames or []
        if old_headers != headers:
            for row in old_rows:
                row.setdefault("REASON", "legacy")
                row.setdefault("QUALITY_GRADE", "legacy")
            with open(AUDIT_FILE, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
                writer.writeheader(); writer.writerows(old_rows)
    validated = {normalize_player_name(item["player"]): item for item in recommendations}
    selected = {normalize_player_name(item["player"]) for item in authorized}
    existing = set()
    if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size:
        with open(AUDIT_FILE, newline="", encoding="utf-8") as handle:
            existing = {(r["DATE"], r["EVENT_ID"], r["PICK"]) for r in csv.DictReader(handle)}
    rows = []
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
            elif item and item.get("grade") in {"Top Pick", "Value Pick"}:
                reason = "portfolio_limit"
            elif item:
                reason = "below_staking_threshold"
            elif not tennis_baseline_is_reliable(baseline):
                reason = "missing_elo_or_market_disagreement"
            elif baseline["ev"] <= 0:
                reason = "non_positive_ev"
            else:
                reason = "not_selected"
            quality_score, quality_grade = evidence_quality(match, baseline)
            rows.append([
                date_str, match.get("event_id", ""),
                f"{match['player1']} vs {match['player2']}", player,
                f"{baseline['player_odds']:.3f}",
                f"{baseline['market_probability']:.6f}",
                f"{baseline['elo_probability']:.6f}",
                f"{baseline['assessed_probability']:.6f}",
                f"{baseline['form_probability']:.6f}" if baseline.get("form_probability") is not None else "",
                baseline.get("form_sample", 0),
                f"{baseline['ev']:.6f}", f"{baseline['score']:.3f}",
                "reliable" if tennis_baseline_is_reliable(baseline) else "insufficient",
                quality_score, quality_grade, match.get("level") or "Unknown",
                match.get("surface") or "Unknown", match.get("bookmaker_count") or 0,
                decision, reason, "", "", "",
            ])
    if not rows:
        return
    write_header = not AUDIT_FILE.exists() or not AUDIT_FILE.stat().st_size
    with open(AUDIT_FILE, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(headers)
        writer.writerows(rows)
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
        with open(AUDIT_FILE, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader(); writer.writerows(rows)


def settle_pending_bets(api_keys: list[str]) -> int:
    """Settle finished tennis bets and add bookmaker returns to bankroll."""
    if not LOG_FILE.exists() or not LOG_FILE.stat().st_size or not api_keys:
        return 0
    with open(LOG_FILE, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    dates = sorted({r.get("DATE", "") for r in rows if not r.get("RESULT", "").strip()})
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
    credited = 0.0
    for row in rows:
        if row.get("RESULT", "").strip():
            continue
        label = normalize_player_name(row.get("MATCH", ""))
        pick = normalize_player_name(re.sub(r"\s+to win\s*$", "", row.get("BET", ""), flags=re.I))
        event = next((e for e in events if str(e.get("date", "")).startswith(row.get("DATE", ""))
                      and normalize_player_name(str(e.get("home", ""))) in label
                      and normalize_player_name(str(e.get("away", ""))) in label), None)
        if not event:
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
        credited += returned; settled += 1
        update_audit_result(row.get("DATE", ""), pick, row["RESULT"], closing)
    if settled:
        headers = ["DATE", "MATCH", "BET", "ODDS", "STAKE", "RESULT", "RETURN", "STARTING BALANCE"]
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers); writer.writeheader(); writer.writerows(rows)
        balance = float(BANKROLL_FILE.read_text().strip() or 0) + credited
        BANKROLL_FILE.write_text(f"{balance:.2f}", encoding="utf-8")
        log(f"Settled {settled} bet(s); credited €{credited:.2f}")
    return settled


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
    brier = sum((float(row["MODEL_PROBABILITY"]) - (row["RESULT"] == "W")) ** 2 for row in resolved) / len(resolved) if resolved else None
    clv = [float(row["CLV"]) for row in resolved if row.get("CLV")]
    lines = [
        "# Tennis Bot Performance", "",
        f"- Settled bets: {len(settled)}",
        f"- Win rate: {wins / len(settled):.1%}" if settled else "- Win rate: N/A",
        f"- Profit/loss: €{profit:.2f}",
        f"- ROI: {profit / stakes:.2%}" if stakes else "- ROI: N/A",
        f"- Brier score: {brier:.4f}" if brier is not None else "- Brier score: N/A",
        f"- Average CLV: {sum(clv) / len(clv):.2%}" if clv else "- Average CLV: N/A",
        "", "## Calibration", "",
        "| Predicted probability | Predictions | Actual win rate |", "|---|---:|---:|",
    ]
    for low, high in ((.50, .55), (.55, .60), (.60, .65), (.65, .70), (.70, 1.01)):
        bucket = [row for row in resolved if low <= float(row["MODEL_PROBABILITY"]) < high]
        actual = sum(row["RESULT"] == "W" for row in bucket) / len(bucket) if bucket else None
        label = f"{low:.0%}–{high:.0%}" if high <= 1 else "70%+"
        lines.append(f"| {label} | {len(bucket)} | {actual:.1%} |" if actual is not None else f"| {label} | 0 | N/A |")
    PERFORMANCE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    generate_backtest_summary(resolved)
    log(f"Performance summary saved: {PERFORMANCE_FILE.name}")


def _segment_metrics(rows: list[dict]) -> tuple[int, float, float, float, float | None]:
    count = len(rows)
    if not count:
        return 0, 0.0, 0.0, 0.0, None
    wins = sum(row.get("RESULT") == "W" for row in rows)
    profit = sum(
        (float(row.get("OPENING_ODDS") or 0) - 1) if row.get("RESULT") == "W" else -1
        for row in rows
    )
    brier = sum(
        (float(row["MODEL_PROBABILITY"]) - (row.get("RESULT") == "W")) ** 2
        for row in rows
    ) / count
    clv_values = [float(row["CLV"]) for row in rows if row.get("CLV")]
    return count, wins / count, profit / count, brier, (sum(clv_values) / len(clv_values) if clv_values else None)


def _append_segment_table(lines: list[str], title: str, groups: list[tuple[str, list[dict]]]):
    lines.extend(["", f"## {title}", "", "| Segment | Bets | Win rate | Flat-unit ROI | Brier | Avg CLV | Reliability |", "|---|---:|---:|---:|---:|---:|---|"])
    for label, rows in groups:
        count, win_rate, roi, brier, clv = _segment_metrics(rows)
        reliability = "usable" if count >= 100 else "developing" if count >= 30 else "small sample"
        clv_text = f"{clv:.2%}" if clv is not None else "N/A"
        lines.append(f"| {label} | {count} | {win_rate:.1%} | {roi:.2%} | {brier:.4f} | {clv_text} | {reliability} |")


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
    for field, title in (("TOUR", "Tour and level"), ("SURFACE", "Surface"), ("QUALITY_GRADE", "Evidence quality")):
        values = sorted({row.get(field) or "Unknown" for row in resolved})
        _append_segment_table(lines, title, [(value, [r for r in resolved if (r.get(field) or "Unknown") == value]) for value in values])
    months = sorted({(row.get("DATE") or "")[:7] for row in resolved if row.get("DATE")})
    _append_segment_table(lines, "Monthly performance", [(month, [r for r in resolved if (r.get("DATE") or "").startswith(month)]) for month in months])
    BACKTEST_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"Backtest summary saved: {BACKTEST_FILE.name}")


def log_bets(
    date_str: str,
    recommendations: list[dict],
    matches: list[dict],
    bankroll: float | None,
):
    """Append bets to the log CSV."""
    file_exists = LOG_FILE.exists()
    rows_to_append = []
    current_balance = bankroll
    total_stake = 0.0
    existing_bets = set()
    if file_exists and LOG_FILE.stat().st_size > 0:
        with open(LOG_FILE, newline="", encoding="utf-8") as existing_file:
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

        # Calculate stake
        if current_balance is not None:
            if rec["grade"] == "Top Pick":
                stake_pct = 0.03
            else:
                stake_pct = 0.02

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

    # Write to CSV
    write_header = not file_exists or LOG_FILE.stat().st_size == 0
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["DATE", "MATCH", "BET", "ODDS", "STAKE", "RESULT", "RETURN", "STARTING BALANCE"])
        for row in rows_to_append:
            writer.writerow([
                row["date"], row["match"], row["bet"], row["odds"],
                row["stake"], row["result"], row["return"], row["starting_balance"],
            ])

    log(f"Logged {len(rows_to_append)} bets to {LOG_FILE.name}")
    return total_stake


# ─── Report ──────────────────────────────────────────────────────────

def save_report(date_str: str, report: str):
    """Save the AI report to a dated file."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"picks-{date_str}.md"
    path = REPORTS_DIR / filename
    path.write_text(report, encoding="utf-8")
    log(f"Report saved: {path}")


# ─── Main ────────────────────────────────────────────────────────────

def already_logged_today(date_str: str) -> bool:
    """Check if bets for this date already exist in the log."""
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        return False
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if row and row[0].strip() == date_str:
                return True
    return False


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
            f"Python accepted {len(recommendations)} bet(s) after matching "
            "verified odds and recalculating expected value."
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
    append_prediction_audit(date_str, matches, recommendations, authorized)
    total_stake = log_bets(date_str, authorized, matches, bankroll)
    save_bankroll(bankroll, total_stake)

    final_report = add_validation_summary(report, len(candidates), authorized)
    save_report(date_str, final_report)
    generate_performance_summary()
    log("=== Done ===")
    print("\n" + final_report)


def main():
    args = parse_args()

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
    settle_pending_bets(odds_api_keys)
    generate_performance_summary()

    if args.settle_only:
        log("Settlement-only run complete")
        return

    if not args.force and already_logged_today(date_str):
        log(f"Bets already logged for {date_str}. Skipping to avoid duplicates.")
        log("(Use --force to override.)")
        return

    bankroll = load_bankroll(args.bankroll)
    if bankroll is None:
        log("WARNING: No bankroll set. Run with --bankroll <amount>")

    # Stage 1: Collect verified matches and odds
    log("Fetching tennis fixtures and odds...")
    all_matches = fetch_matches_from_odds_api(date_str, odds_api_keys)
    if not all_matches:
        log("No verified matches with moneyline odds were found.")

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


if __name__ == "__main__":
    main()
