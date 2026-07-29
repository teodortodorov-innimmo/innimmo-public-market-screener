#!/usr/bin/env python3
"""
Watchlist / portfolio persistence for the Innimmo screener.

Stores the names you're tracking in a local JSON file, with an optional entry
price and note, so the app can show live scores and return-since-entry.

STORAGE NOTE: this is a simple local file. On Streamlit Cloud the filesystem is
ephemeral, so the watchlist resets when the app restarts/redeploys — fine for a
running session or local use, but for permanent multi-user storage you'd point
this at a small database or cloud bucket instead.

Usage (CLI):
    python watchlist.py add KGH.WA --price 142.30 --note "deep value"
    python watchlist.py list
    python watchlist.py remove KGH.WA
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

WATCHLIST_FILE = "watchlist.json"

# Names the watchlist starts with when there is no saved file yet. Because
# Streamlit Cloud's filesystem is ephemeral, committing a watchlist.json would
# not survive a restart — seeding here does, and the entries stay fully
# removable from the Watchlist tab.
DEFAULT_WATCHLIST = [
    {"ticker": "FP.RO", "entry_price": None, "note": "Closed-end fund at a discount to NAV", "added": "seeded"},
    {"ticker": "TLV.RO", "entry_price": None, "note": "Largest Romanian bank, widely held", "added": "seeded"},
    {"ticker": "OTP.BD", "entry_price": None, "note": "High-ROE CEE bank, no controlling owner", "added": "seeded"},
    {"ticker": "BG.VI", "entry_price": None, "note": "BAWAG — efficient Austrian bank, broad free float", "added": "seeded"},
]


def load() -> list:
    if not os.path.exists(WATCHLIST_FILE):
        # Copy so callers can never mutate the module-level default in place.
        return [dict(item) for item in DEFAULT_WATCHLIST]
    try:
        return json.load(open(WATCHLIST_FILE, encoding="utf-8"))
    except Exception:
        return []


def save(items) -> None:
    json.dump(items, open(WATCHLIST_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def add(ticker, entry_price=None, note="") -> list:
    ticker = ticker.strip().upper()
    items = load()
    if any(i["ticker"] == ticker for i in items):
        # update existing entry rather than duplicate
        for i in items:
            if i["ticker"] == ticker:
                if entry_price is not None:
                    i["entry_price"] = entry_price
                if note:
                    i["note"] = note
    else:
        items.append({
            "ticker": ticker,
            "entry_price": entry_price,
            "note": note,
            "added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        })
    save(items)
    return items


def remove(ticker) -> list:
    ticker = ticker.strip().upper()
    items = [i for i in load() if i["ticker"] != ticker]
    save(items)
    return items


def _main(argv):
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "list":
        for i in load():
            print(i)
    elif cmd == "add" and len(argv) > 1:
        price = None
        note = ""
        if "--price" in argv:
            try:
                price = float(argv[argv.index("--price") + 1])
            except (ValueError, IndexError):
                pass
        if "--note" in argv:
            try:
                note = argv[argv.index("--note") + 1]
            except IndexError:
                pass
        add(argv[1], entry_price=price, note=note)
        print("Added.", load())
    elif cmd == "remove" and len(argv) > 1:
        remove(argv[1])
        print("Removed.", load())
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
