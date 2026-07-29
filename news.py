#!/usr/bin/env python3
"""
News aggregation for the Innimmo screener.

Pulls recent headlines from Yahoo Finance (free) for a set of tickers, newest
first, with source and link. HONEST LIMIT: Yahoo's news coverage is good for
large / widely-followed names but thin or empty for small CEE listings — expect
gaps for the smaller companies. We only surface real headlines + links; we never
fabricate or summarise beyond what the feed provides.

Usage:
    python news.py OTP.BD KGH.WA EBS.VI
"""
from __future__ import annotations

import sys

import yfinance as yf


def _content(item):
    if not isinstance(item, dict):
        return {}
    return item.get("content", item)  # yfinance 1.x nests under 'content'


def get_news(tickers, per_ticker=6, total=30):
    """Return [{ticker,title,url,publisher,date}] newest-first."""
    out, seen = [], set()
    for t in tickers:
        try:
            raw = yf.Ticker(t).news or []
        except Exception:
            raw = []
        for it in raw[:per_ticker]:
            c = _content(it)
            title = (c.get("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            cu = c.get("canonicalUrl") or c.get("clickThroughUrl") or {}
            url = cu.get("url", "") if isinstance(cu, dict) else ""
            prov = c.get("provider") or {}
            publisher = prov.get("displayName", "") if isinstance(prov, dict) else ""
            date = str(c.get("pubDate") or c.get("displayTime") or "")[:10]
            out.append({"ticker": t, "title": title, "url": url,
                        "publisher": publisher, "date": date})
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:total]


def main(argv):
    tickers = argv or ["OTP.BD", "KGH.WA", "EBS.VI"]
    items = get_news(tickers)
    print(f"{len(items)} headlines for {', '.join(tickers)}:\n")
    for n in items:
        print(f"[{n['date']}] {n['ticker']:9} {n['title']}")
        print(f"           {n['publisher']} — {n['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
