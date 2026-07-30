#!/usr/bin/env python3
"""
Local store for the Innimmo screener — watchlist + analyst decisions/notes.

Replaces the old flat watchlist.json with a small SQLite database so that
entries are transactional, survive every Streamlit rerun, and can carry a
review status and free-text notes alongside the ticker.

HONEST LIMIT ON PERSISTENCE: Streamlit Community Cloud gives each app an
ephemeral filesystem. This database therefore survives reruns, navigation and
re-logins, but is wiped when the container restarts (a redeploy, or after a
period of inactivity). Truly durable storage would need either a hosted
database or a git write-back, and both require credentials — which are out of
scope here. To work around that without any credentials, use `export_json()` /
`import_json()` (wired to Download/Upload buttons in the Watchlist tab) to keep
your own copy and restore it in one click.

Usage (CLI):
    python store.py list
    python store.py add KGH.WA --price 250 --note "deep value"
    python store.py status KGH.WA reviewed
    python store.py remove KGH.WA
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_FILE = os.environ.get("INNIMMO_DB", "innimmo_store.db")

# Review states an analyst can move a name through. Kept deliberately short —
# this is a screening workflow, not a full CRM.
STATUSES = ["new", "reviewing", "shortlist", "to IC", "passed"]
DEFAULT_STATUS = "new"

# Seeded when the database is created for the first time, so a fresh container
# still shows a useful watchlist instead of an empty page.
SEED = [
    ("FP.RO", None, "Closed-end fund at a discount to NAV"),
    ("TLV.RO", None, "Largest Romanian bank, widely held"),
    ("OTP.BD", None, "High-ROE CEE bank, no controlling owner"),
    ("BG.VI", None, "BAWAG — efficient Austrian bank, broad free float"),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    """Create the schema if needed and seed a first-run watchlist."""
    fresh = not os.path.exists(DB_FILE)
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker      TEXT PRIMARY KEY,
                entry_price REAL,
                note        TEXT DEFAULT '',
                status      TEXT DEFAULT 'new',
                added       TEXT,
                updated     TEXT
            )""")
        # Append-only decision log, so the reasoning history is never overwritten.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker  TEXT NOT NULL,
                status  TEXT,
                note    TEXT,
                ts      TEXT
            )""")
        if fresh:
            for ticker, price, note in SEED:
                conn.execute(
                    "INSERT OR IGNORE INTO watchlist"
                    " (ticker, entry_price, note, status, added, updated)"
                    " VALUES (?,?,?,?,?,?)",
                    (ticker, price, note, DEFAULT_STATUS, _now(), _now()))


def load() -> list[dict]:
    """Watchlist rows, newest-updated last (stable ordering for the UI)."""
    init()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticker, entry_price, note, status, added, updated"
            " FROM watchlist ORDER BY added").fetchall()
    return [dict(r) for r in rows]


def add(ticker: str, entry_price=None, note: str = "", status: str | None = None) -> None:
    """Insert or update a watchlist entry (blank fields never overwrite existing)."""
    ticker = ticker.strip().upper()
    if not ticker:
        return
    init()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT ticker FROM watchlist WHERE ticker=?", (ticker,)).fetchone()
        if existing:
            if entry_price is not None:
                conn.execute("UPDATE watchlist SET entry_price=?, updated=?"
                             " WHERE ticker=?", (entry_price, _now(), ticker))
            if note:
                conn.execute("UPDATE watchlist SET note=?, updated=? WHERE ticker=?",
                             (note, _now(), ticker))
            if status:
                conn.execute("UPDATE watchlist SET status=?, updated=? WHERE ticker=?",
                             (status, _now(), ticker))
        else:
            conn.execute(
                "INSERT INTO watchlist (ticker, entry_price, note, status, added, updated)"
                " VALUES (?,?,?,?,?,?)",
                (ticker, entry_price, note, status or DEFAULT_STATUS, _now(), _now()))
        if status or note:
            conn.execute("INSERT INTO decisions (ticker, status, note, ts)"
                         " VALUES (?,?,?,?)", (ticker, status, note, _now()))


def set_status(ticker: str, status: str, note: str = "") -> None:
    """Move a name through the review workflow and log the change."""
    ticker = ticker.strip().upper()
    init()
    with _connect() as conn:
        conn.execute("UPDATE watchlist SET status=?, updated=? WHERE ticker=?",
                     (status, _now(), ticker))
        conn.execute("INSERT INTO decisions (ticker, status, note, ts) VALUES (?,?,?,?)",
                     (ticker, status, note, _now()))


def remove(ticker: str) -> None:
    ticker = ticker.strip().upper()
    init()
    with _connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker,))
        conn.execute("INSERT INTO decisions (ticker, status, note, ts) VALUES (?,?,?,?)",
                     (ticker, "removed", "", _now()))


def history(ticker: str | None = None, limit: int = 100) -> list[dict]:
    """Decision log, newest first — optionally for one ticker."""
    init()
    with _connect() as conn:
        if ticker:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE ticker=? ORDER BY id DESC LIMIT ?",
                (ticker.strip().upper(), limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Keyless durability: let the user keep and restore their own copy.
# --------------------------------------------------------------------------- #
def export_json() -> str:
    return json.dumps({"watchlist": load(), "decisions": history(limit=1000)},
                      ensure_ascii=False, indent=1)


def import_json(text: str) -> int:
    """Merge an exported file back in. Returns how many names were restored."""
    data = json.loads(text)
    items = data.get("watchlist", data if isinstance(data, list) else [])
    init()
    n = 0
    with _connect() as conn:
        for it in items:
            t = str(it.get("ticker", "")).strip().upper()
            if not t:
                continue
            conn.execute(
                "INSERT INTO watchlist (ticker, entry_price, note, status, added, updated)"
                " VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(ticker) DO UPDATE SET"
                " entry_price=excluded.entry_price, note=excluded.note,"
                " status=excluded.status, updated=excluded.updated",
                (t, it.get("entry_price"), it.get("note", ""),
                 it.get("status", DEFAULT_STATUS), it.get("added") or _now(), _now()))
            n += 1
    return n


def _main(argv) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "list":
        for r in load():
            print(r)
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
        print("added:", argv[1])
    elif cmd == "status" and len(argv) > 2:
        set_status(argv[1], argv[2])
        print(f"{argv[1]} -> {argv[2]}")
    elif cmd == "remove" and len(argv) > 1:
        remove(argv[1])
        print("removed:", argv[1])
    elif cmd == "history":
        for r in history(argv[1] if len(argv) > 1 else None):
            print(r)
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
