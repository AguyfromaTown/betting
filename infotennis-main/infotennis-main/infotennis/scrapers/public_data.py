"""GitHub-compatible ATP/WTA source catalog for the Infotennis collector.

The original ATP HTML/Infosys scrapers are retained for optional granular data,
but those endpoints may deny automated access.  These MIT-licensed CSV feeds are
the reliable primary path and require neither Selenium nor MySQL.
"""

TML_ROOT = "https://stats.tennismylife.org/data"


def season_sources(year: int, history_years: int = 3) -> list[tuple[str, int, str]]:
    """Return main, lower-tour, qualifying and ongoing ATP/WTA CSV sources."""
    first_year = year - max(1, history_years) + 1
    sources: list[tuple[str, int, str]] = []
    for season in range(first_year, year + 1):
        sources.extend([
            ("ATP", season, f"{TML_ROOT}/{season}.csv"),
            ("ATP", season, f"{TML_ROOT}/{season}_challenger.csv"),
            ("ATP", season, f"{TML_ROOT}/atp_quali/{season}_atp_quali.csv"),
            ("WTA", season, f"{TML_ROOT}/{season}_wta.csv"),
        ])
    sources.extend([
        ("ATP", year, f"{TML_ROOT}/ongoing_tourneys.csv"),
        ("ATP", year, f"{TML_ROOT}/challenger_ongoing_tourneys.csv"),
        ("WTA", year, f"{TML_ROOT}/wta_ongoing_tourneys.csv"),
    ])
    return sources

