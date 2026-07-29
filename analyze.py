#!/usr/bin/env python3
"""
On-demand single-ticker analysis for the Innimmo screener.

Type any Yahoo ticker and get the same six-factor score, price-chart technicals,
ownership read, ratios, and thesis the screener produces — even if the name is
not in the standard universe. Builds a one-name dashboard you can open.

If a prior full run left `innimmo_universe_data.json`, its names are used as
sector peers so the sector-relative value / fair-value work; otherwise value is
absolute only (noted on the card).

Usage:
    python analyze.py KGH.WA
    python analyze.py AAPL          # works for any Yahoo ticker
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import fields

import activist_screener as s

UNIVERSE_JSON = "innimmo_universe_data.json"


def _load_peers():
    """Rebuild lightweight Company peers from a prior universe run, if present."""
    if not os.path.exists(UNIVERSE_JSON):
        return []
    try:
        data = json.load(open(UNIVERSE_JSON, encoding="utf-8"))
    except Exception:
        return []
    valid = {f.name for f in fields(s.Company)}
    peers = []
    for d in data:
        peers.append(s.Company(**{k: v for k, v in d.items() if k in valid}))
    return peers


def main(argv):
    if not argv:
        print("Usage: python analyze.py <TICKER>   e.g. python analyze.py KGH.WA")
        return 1
    ticker = argv[0].strip().upper()
    peers = _load_peers()
    print(f"Analyzing {ticker}"
          + (f" with {len(peers)} sector-peer context names..." if peers
             else " (no peer context — value shown absolute only)..."))

    co = s.analyze_ticker(ticker, peers=peers)
    if co is None:
        print(f"Could not fetch {ticker} from Yahoo Finance — check the symbol "
              "(e.g. KGH.WA for Warsaw, EBS.VI for Vienna).")
        return 1

    ss = co.sub_scores
    print(f"\n{co.name} ({co.ticker}) — {co.sector or 'n/a'}, {co.country or 'n/a'}")
    print(f"OVERALL SCORE: {co.score}/5   confidence {co.confidence_label}")
    print("  " + "  ".join(f"{k}={v}" for k, v in ss.items() if v is not None))
    print(f"Control: {co.control_label}  |  P/B {s._f(co.pb)}  P/E {s._f(co.pe)}  "
          f"ROE {s._f(co.roe, True)}  trend {co.trend or 'n/a'}")
    if co.flags:
        print("Flags: " + " | ".join(co.flags))
    print(f"\n{co.thesis}\n")

    out_json = f"analysis_{ticker.replace('.', '_')}.json"
    out_html = f"analysis_{ticker.replace('.', '_')}.html"
    s.write_json([co], out_json)
    try:
        from build_dashboard import build_dashboard
        build_dashboard(out_json, out_html)
        print(f"Wrote {out_html} (open it for the full chart + scorecard).")
    except Exception as exc:
        print(f"Dashboard build skipped ({exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
