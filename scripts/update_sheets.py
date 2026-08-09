#!/usr/bin/env python3
"""Generate MTG basic land CSV sheets from Scryfall."""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

BASE_URL = "https://api.scryfall.com/cards/search"
USER_AGENT = "mtg-basic-land-csvs-updater/1.0"
DEFAULT_CUTOFF = dt.date.today()
ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "sheets"
README_PATH = ROOT / "README.md"

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
    "all-paper-wastes-by-appearance.csv": "t:basic !\"Wastes\" game:paper unique:prints",
    "english-paper-basics-by-appearance.csv": "t:basic game:paper lang:en unique:prints",
    "english-paper-forests-by-appearance.csv": "t:basic t:forest game:paper lang:en unique:prints",
    "english-paper-plains-by-appearance.csv": "t:basic t:plains game:paper lang:en unique:prints",
    "english-paper-islands-by-appearance.csv": "t:basic t:island game:paper lang:en unique:prints",
    "english-paper-swamps-by-appearance.csv": "t:basic t:swamp game:paper lang:en unique:prints",
    "english-paper-mountains-by-appearance.csv": "t:basic t:mountain game:paper lang:en unique:prints",
    "english-paper-wastes-by-appearance.csv": "t:basic !\"Wastes\" game:paper lang:en unique:prints",
    "all-paper-basics-no-secret-lairs-by-appearance.csv": "t:basic game:paper -set:sld -set:slp unique:prints",
    "all-paper-forests-no-secret-lairs-by-appearance.csv": "t:basic t:forest game:paper -set:sld -set:slp unique:prints",
    "all-paper-plains-no-secret-lairs-by-appearance.csv": "t:basic t:plains game:paper -set:sld -set:slp unique:prints",
    "all-paper-islands-no-secret-lairs-by-appearance.csv": "t:basic t:island game:paper -set:sld -set:slp unique:prints",
    "all-paper-swamps-no-secret-lairs-by-appearance.csv": "t:basic t:swamp game:paper -set:sld -set:slp unique:prints",
    "all-paper-mountains-no-secret-lairs-by-appearance.csv": "t:basic t:mountain game:paper -set:sld -set:slp unique:prints",
    "all-paper-wastes-no-secret-lairs-by-appearance.csv": "t:basic !\"Wastes\" game:paper -set:sld -set:slp unique:prints",
    "english-paper-basics-no-secret-lairs-by-appearance.csv": "t:basic game:paper lang:en -set:sld -set:slp unique:prints",
    "english-paper-forests-no-secret-lairs-by-appearance.csv": "t:basic t:forest game:paper lang:en -set:sld -set:slp unique:prints",
    "english-paper-plains-no-secret-lairs-by-appearance.csv": "t:basic t:plains game:paper lang:en -set:sld -set:slp unique:prints",
    "english-paper-islands-no-secret-lairs-by-appearance.csv": "t:basic t:island game:paper lang:en -set:sld -set:slp unique:prints",
    "english-paper-swamps-no-secret-lairs-by-appearance.csv": "t:basic t:swamp game:paper lang:en -set:sld -set:slp unique:prints",
    "english-paper-mountains-no-secret-lairs-by-appearance.csv": "t:basic t:mountain game:paper lang:en -set:sld -set:slp unique:prints",
    "english-paper-wastes-no-secret-lairs-by-appearance.csv": "t:basic !\"Wastes\" game:paper lang:en -set:sld -set:slp unique:prints",
}


def fetch_all_prints(query: str) -> List[dict]:
    return fetch_all_prints_since(query, None)


def fetch_all_prints_since(query: str, since_date: Optional[dt.date]) -> List[dict]:
    full_query = query
    if since_date is not None:
        # Include the boundary date and dedupe on merge so same-day additions are retained.
        full_query = f"{query} date>={since_date.isoformat()}"

    params = {
        "q": full_query,
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


def read_existing_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: List[Dict[str, str]] = []
        for row in reader:
            rows.append({col: row.get(col, "") for col in COLUMNS})
        return rows


def date_from_row(row: Dict[str, str]) -> Optional[dt.date]:
    raw = row.get("released_at", "")
    if not raw:
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        return None


def latest_release_date(rows: Sequence[Dict[str, str]]) -> Optional[dt.date]:
    dates = [d for d in (date_from_row(r) for r in rows) if d is not None]
    if not dates:
        return None
    return max(dates)


def row_key(row: Dict[str, str]) -> Tuple[str, str, str, str, str, str]:
    return (
        row.get("card", ""),
        row.get("released_at", ""),
        row.get("set", ""),
        row.get("set_name", ""),
        row.get("collector_number", ""),
        row.get("scryfall_uri", ""),
    )


def merge_rows(existing: Sequence[Dict[str, str]], incoming: Sequence[Dict[str, str]], cutoff: dt.date) -> List[Dict[str, str]]:
    merged: Dict[Tuple[str, str, str, str, str, str], Dict[str, str]] = {}
    for row in existing:
        row_date = date_from_row(row)
        if row_date is not None and row_date <= cutoff:
            merged[row_key(row)] = row

    for row in incoming:
        row_date = date_from_row(row)
        if row_date is not None and row_date <= cutoff:
            merged[row_key(row)] = row

    rows = list(merged.values())
    rows.sort(
        key=lambda r: (
            r.get("released_at", ""),
            r.get("set", ""),
            r.get("collector_number", ""),
            r.get("card", ""),
            r.get("scryfall_uri", ""),
        )
    )
    return rows


def count_new_rows(existing: Sequence[Dict[str, str]], incoming: Sequence[Dict[str, str]], cutoff: dt.date) -> int:
    existing_keys = {
        row_key(row)
        for row in existing
        if (date_from_row(row) is not None and date_from_row(row) <= cutoff)
    }
    incoming_keys = {
        row_key(row)
        for row in incoming
        if (date_from_row(row) is not None and date_from_row(row) <= cutoff)
    }
    return len(incoming_keys - existing_keys)


def parse_cutoff(argv: List[str]) -> dt.date:
    if len(argv) < 2:
        return DEFAULT_CUTOFF
    try:
        return dt.date.fromisoformat(argv[1])
    except ValueError as exc:
        raise SystemExit("Cutoff date must be YYYY-MM-DD") from exc


def update_readme_timestamp(path: Path, timestamp_utc: str) -> bool:
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")
    updated_line = f"Last updated @ {timestamp_utc} UTC"
    pattern = re.compile(r"^Last updated @ .*?$", re.MULTILINE)

    if pattern.search(content):
        new_content = pattern.sub(updated_line, content)
    else:
        lines = content.splitlines()
        if lines:
            insert_at = 1
            while insert_at < len(lines) and lines[insert_at] == "":
                insert_at += 1
            lines.insert(insert_at, updated_line)
            if insert_at + 1 < len(lines) and lines[insert_at + 1] != "":
                lines.insert(insert_at + 1, "")
        else:
            lines = [updated_line, ""]
        new_content = "\n".join(lines)
        if not new_content.endswith("\n"):
            new_content += "\n"

    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        return True
    return False


def main(argv: List[str]) -> int:
    cutoff = parse_cutoff(argv)
    run_timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    SHEETS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Updating sheets with cutoff date: {cutoff.isoformat()}")
    for filename, query in SHEETS.items():
        path = SHEETS_DIR / filename
        existing_rows = read_existing_rows(path)
        existing_effective = merge_rows(existing_rows, [], cutoff)
        since_date = latest_release_date(existing_rows)

        cards = fetch_all_prints_since(query, since_date)
        incoming_rows = [row_from_card(c) for c in cards if within_cutoff(c, cutoff)]
        merged_rows = merge_rows(existing_rows, incoming_rows, cutoff)
        new_rows = count_new_rows(existing_rows, incoming_rows, cutoff)

        if merged_rows != existing_effective:
            count = write_csv(path, merged_rows)
            updated_msg = "updated"
        else:
            count = len(existing_effective)
            updated_msg = "no changes"

        fetched_msg = f"fetched {len(incoming_rows)}"
        if since_date is not None:
            fetched_msg += f" since {since_date.isoformat()}"
        else:
            fetched_msg += " from full history"
        print(f"- {filename}: {count} rows ({fetched_msg}; {new_rows} new; {updated_msg})")

    readme_updated = update_readme_timestamp(README_PATH, run_timestamp)
    if readme_updated:
        print(f"- README.md timestamp updated: {run_timestamp}")
    else:
        print("- README.md not updated (missing file or no content change)")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
