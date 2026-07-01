#!/usr/bin/env python3
"""Fetch Tour de France stage results from letour.fr rankings pages.

Updates tour-de-france-2026.json with stage_winner/stage_result/gc_leader for completed stages.
Prints nothing when no update.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, date, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
JSON_PATH = BASE / 'tour-de-france-2026.json'

UA = {'User-Agent': 'Mozilla/5.0'}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode('utf-8', 'replace')


def stage_number(row: dict) -> int | None:
    try:
        return int(str(row.get('stage', '')).strip())
    except Exception:
        return None


def stage_date_iso(row: dict) -> str | None:
    v = row.get('date_iso')
    if isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        return v
    return None


def extract_first_rider_name(html: str) -> str | None:
    # On letour rankings pages, first row on the page is the winner / GC leader.
    m = re.search(r'rankingTables__row__profile--name"[^>]*>([^<]+)</a>', html)
    if not m:
        return None
    name = re.sub(r'\s+', ' ', m.group(1)).strip()
    return name or None


def extract_stage_winner(stage: int) -> str | None:
    html = fetch(f'https://www.letour.fr/en/rankings/stage-{stage}')
    return extract_first_rider_name(html)


def extract_gc_leader() -> str | None:
    html = fetch('https://www.letour.fr/en/rankings/stage-21')
    return extract_first_rider_name(html)


def main() -> int:
    rows = json.loads(JSON_PATH.read_text())
    today = datetime.now(timezone.utc).date()
    changed = False
    gc_leader = None

    for row in rows:
        n = stage_number(row)
        ds = stage_date_iso(row)
        if not n or not ds:
            continue
        d = date.fromisoformat(ds)
        if d > today:
            continue
        try:
            winner = extract_stage_winner(n)
        except Exception:
            continue
        if not winner:
            continue
        if row.get('stage_winner') != winner:
            row['stage_winner'] = winner
            row['status'] = 'completed'
            changed = True
        if gc_leader is None:
            try:
                gc_leader = extract_gc_leader()
            except Exception:
                gc_leader = None
        if gc_leader and row.get('gc_leader') != gc_leader:
            row['gc_leader'] = gc_leader
            changed = True

    if changed:
        JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    return 0 if changed else 0


if __name__ == '__main__':
    raise SystemExit(main())
