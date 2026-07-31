#!/usr/bin/env python3
"""
Additional news sources for the Innimmo screener, beyond Yahoo Finance.

Two sources, each used for what it is actually good at:

  GDELT  (api.gdeltproject.org) — free, open, permits commercial use, and
         crucially supports TOPIC search rather than only per-company lookups.
         This is what fixes Yahoo's "per-company only" limitation, so it
         supplies the readable, free-to-open articles.

  THE ECONOMIST (official RSS) — used for AGENDA only: which themes a serious
         business audience is discussing this week. We show the headline plus a
         link straight back to economist.com, which is exactly what a published
         RSS feed is for.

ON THE PAYWALL — deliberate boundary: The Economist is a paid publication, so we
take ONLY what its public feed offers (headline, date, link) and never attempt to
fetch or reconstruct article bodies. Readers click through to the publisher.
Full readable coverage of the same themes comes from GDELT instead.

Rate limiting: GDELT asks for no more than one request every 5 seconds and
returns HTTP 429 otherwise, so calls here are throttled and fail soft — every
function returns [] rather than raising, so a news outage never breaks the app.

Usage:
    python news_feeds.py                 # sample both sources
    python news_feeds.py gdelt "battery recycling"
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (compatible; InnimmoResearch/1.0; +internal research tool)"
GDELT_MIN_INTERVAL = 5.5      # seconds between GDELT calls (their stated limit)
_last_gdelt_call = 0.0

# Circuit breaker. Measured on 2026-07-31: from this IP a single topic query
# burned 187s across its retry ladder and still returned ZERO articles, because
# GDELT 429s shared/cloud addresses regardless of pacing. Retrying harder does
# not help — it only converts a fast empty result into a hung page. So once a
# call fails we stop asking for a while and let the Yahoo fallback carry the
# section, which is fast and actually returns articles.
GDELT_COOLDOWN = 30 * 60      # seconds to stay quiet after a failure
_gdelt_blocked_until = 0.0


def gdelt_available() -> bool:
    """False while the breaker is open (a recent call failed)."""
    return time.time() >= _gdelt_blocked_until

# Economist sections that map onto Innimmo's research verticals.
ECONOMIST_FEEDS = {
    "Business": "https://www.economist.com/business/rss.xml",
    "Finance & economics": "https://www.economist.com/finance-and-economics/rss.xml",
    "Science & technology": "https://www.economist.com/science-and-technology/rss.xml",
}

# Topic queries per research vertical (Workstream 2 of the 2026 intern plan).
# These are real keyword searches — GDELT indexes article text, so unlike Yahoo
# we can ask about a THEME instead of naming companies.
TOPIC_QUERIES = {
    "Data Centres & Cooling": '"data centre" OR "data center" cooling',
    "Energy & Battery Storage": '"battery storage" OR "battery recycling" energy Europe',
    "Fintech & Digital Lending": '"digital lending" OR fintech OR "credit technology" Europe',
}


def _fetch(url: str, timeout: int = 8) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read()


# --------------------------------------------------------------------------- #
# GDELT — free topic search, supplies the readable articles
# --------------------------------------------------------------------------- #
def gdelt_topic(query: str, max_records: int = 8, retries: int = 1,
                deadline: float | None = None) -> list[dict]:
    """Recent articles matching a topic query. Returns [] on any failure.

    NEVER blocks the caller for long. GDELT is a nice-to-have topic source, not
    the page's only news, so it is strictly time-boxed:

      * `deadline` is an absolute time.time() value the caller owns. We refuse to
        start an attempt we cannot finish inside it. This is what keeps the Home
        page bounded no matter how many themes are requested.
      * one cheap retry, not five. A 429 from a shared IP does not clear in
        seconds, so extra attempts buy nothing but latency.
      * on failure the module-level breaker opens for GDELT_COOLDOWN, so the
        other themes in the same page load skip the network entirely.
    """
    global _last_gdelt_call, _gdelt_blocked_until
    if not gdelt_available():
        return []
    params = urllib.parse.urlencode({
        "query": query, "mode": "artlist", "maxrecords": max_records,
        "format": "json", "sort": "datedesc",
    })
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"

    for attempt in range(retries + 1):
        wait = max(0.0, GDELT_MIN_INTERVAL - (time.time() - _last_gdelt_call))
        # Budget check: pacing wait + the request's own timeout must both fit.
        if deadline is not None and time.time() + wait + 8 > deadline:
            return []
        if wait > 0:
            time.sleep(wait)
        try:
            _last_gdelt_call = time.time()
            payload = json.loads(_fetch(url))
            out = []
            for a in payload.get("articles", []):
                title = (a.get("title") or "").strip()
                if not title:
                    continue
                out.append({
                    "title": title,
                    "url": a.get("url", ""),
                    "publisher": a.get("domain", ""),
                    "date": _gdelt_date(a.get("seendate", "")),
                    "image": a.get("socialimage", "") or "",
                    "source": "GDELT",
                })
            return out
        except Exception:
            if attempt >= retries:
                _gdelt_blocked_until = time.time() + GDELT_COOLDOWN
                return []
            time.sleep(1.0)
    return []


def _gdelt_date(seen: str) -> str:
    """GDELT stamps are '20260729T120000Z' -> 'YYYY-MM-DD'."""
    s = str(seen)
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}" if len(s) >= 8 else ""


# --------------------------------------------------------------------------- #
# The Economist — headlines only, always linked back to the publisher
# --------------------------------------------------------------------------- #
def economist_headlines(section: str | None = None, limit: int = 6) -> list[dict]:
    """Headline + date + link from The Economist's public RSS. No article bodies."""
    feeds = ({section: ECONOMIST_FEEDS[section]} if section in ECONOMIST_FEEDS
             else ECONOMIST_FEEDS)
    out, seen = [], set()
    for name, url in feeds.items():
        try:
            root = ET.fromstring(_fetch(url))
        except Exception:
            continue
        for item in root.findall(".//item"):
            # RSS titles arrive padded with newlines/indentation.
            title = " ".join((item.findtext("title") or "").split())
            if not title or title in seen:
                continue
            seen.add(title)
            out.append({
                "title": title,
                "url": item.findtext("link") or "",
                "publisher": "The Economist",
                "section": name,
                "date": _rss_date(item.findtext("pubDate") or ""),
                "paywalled": True,
                "source": "Economist",
            })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:limit]


_MONTHS = {m: f"{i:02d}" for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def _rss_date(raw: str) -> str:
    """'Wed, 29 Jul 2026 20:27:57 +0000' -> '2026-07-29'."""
    parts = raw.replace(",", "").split()
    if len(parts) >= 4 and parts[2] in _MONTHS:
        return f"{parts[3]}-{_MONTHS[parts[2]]}-{int(parts[1]):02d}"
    return ""


def topic_news(theme: str, max_records: int = 6,
               deadline: float | None = None) -> list[dict]:
    """Free, readable articles for one research vertical (GDELT).

    `deadline` is an absolute time.time() the caller must not overrun; pass the
    SAME value for every theme in a page load to cap the total, not each call.
    """
    q = TOPIC_QUERIES.get(theme)
    return gdelt_topic(q, max_records=max_records, deadline=deadline) if q else []


def _main(argv) -> int:
    if argv and argv[0] == "gdelt":
        q = argv[1] if len(argv) > 1 else "data centre cooling"
        items = gdelt_topic(q)
        print(f"GDELT '{q}': {len(items)} articles")
        for i in items[:6]:
            print(f"  [{i['date']}] {i['publisher']:22} {i['title'][:60]}")
        return 0

    print("=== The Economist (headlines only, linked back) ===")
    for h in economist_headlines(limit=6):
        print(f"  [{h['date']}] {h['section'][:20]:20} {h['title'][:60]}")
    print()
    for theme in TOPIC_QUERIES:
        items = topic_news(theme, max_records=4)
        print(f"=== {theme} — GDELT: {len(items)} articles ===")
        for i in items[:3]:
            print(f"  [{i['date']}] {i['publisher']:22} {i['title'][:58]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
