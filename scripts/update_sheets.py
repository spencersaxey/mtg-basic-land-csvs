#!/usr/bin/env python3
"""Generate MTG basic land CSV sheets from Scryfall."""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List

BASE_URL = "https://api.scryfall.com/cards/search"
USER_AGENT = "mtg-basic-land-csvs-updater/1.0"
DEFAULT_CUTOFF = dt.date.today()
ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "sheets"

COLUMNS = [
    "card",
    "released_at",
    "set",
    "set_name",
    "collector_number",
    "scryfall_uri",
]

# Query definitions in release order.
SHEETS: Dict[str, str] = {
    "all-paper-basics-by-appearance.csv": "t:basic game:paper unique:prints",
    "all-paper-forests-by-appearance.csv": "t:basic t:forest game:paper unique:prints",
    "all-paper-plains-by-appearance.csv": "t:basic t:plains game:paper unique:prints",
    "all-paper-islands-by-appearance.csv": "t:basic t:island game:paper unique:prints",
    "all-paper-swamps-by-appearance.csv": "t:basic t:swamp game:paper unique:prints",
    "all-paper-mountains-by-appearance.csv": "t:basic t:mountain game:paper unique:prints",
    "english-paper-basics-by-appearance.csv": "t:basic game:paper lang:en unique:prints",
    "english-paper-forests-by-appearance.csv": "t:basic t:forest game:paper lang:en unique:prints",
    "english-paper-plains-by-appearance.csv": "t:basic t:plains game:paper lang:en unique:prints",
    "english-paper-islands-by-appearance.csv": "t:basic t:island game:paper lang:en unique:prints",
    "english-paper-swamps-by-appearance.csv": "t:basic t:swamp game:paper lang:en unique:prints",
    "english-paper-mountains-by-appearance.csv": "t:basic t:mountain game:paper lang:en unique:prints",
}


def fetch_all_prints(query: str) -> List[dict]:
    params = {
        "q": query,
        "order": "released",
        "dir": "asc",
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    cards: List[dict] = []
    while url:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))

        if payload.get("object") == "error":
            raise RuntimeError(f"Scryfall API error: {payload.get('details', 'unknown error')}")

        cards.extend(payload.get("data", []))
        if payload.get("has_more"):
            url = payload.get("next_page")
            time.sleep(0.12)
        else:
            url = ""

    return cards


def row_from_card(card: dict) -> Dict[str, str]:
    return {
        "card": card.get("name", ""),
        "released_at": card.get("released_at", ""),
        "set": card.get("set", ""),
        "set_name": card.get("set_name", ""),
        "collector_number": card.get("collector_number", ""),
        "scryfall_uri": card.get("scryfall_uri", ""),
    }


def within_cutoff(card: dict, cutoff: dt.date) -> bool:
    release = card.get("released_at")
    if not release:
        return False
    try:
        release_date = dt.date.fromisoformat(release)
    except ValueError:
        return False
    return release_date <= cutoff


def write_csv(path: Path, rows: Iterable[Dict[str, str]]) -> int:
    rows_list = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows_list)
    return len(rows_list)


def parse_cutoff(argv: List[str]) -> dt.date:
    if len(argv) < 2:
        return DEFAULT_CUTOFF
    try:
        return dt.date.fromisoformat(argv[1])
    except ValueError as exc:
        raise SystemExit("Cutoff date must be YYYY-MM-DD") from exc


def main(argv: List[str]) -> int:
    cutoff = parse_cutoff(argv)
    SHEETS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Updating sheets with cutoff date: {cutoff.isoformat()}")
    for filename, query in SHEETS.items():
        cards = fetch_all_prints(query)
        filtered = [row_from_card(c) for c in cards if within_cutoff(c, cutoff)]
        count = write_csv(SHEETS_DIR / filename, filtered)
        print(f"- {filename}: {count} rows")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
