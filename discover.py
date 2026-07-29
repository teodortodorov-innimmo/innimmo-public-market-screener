#!/usr/bin/env python3
"""
Discovery for the Innimmo screener — find NEW companies, not just re-check a list.

Uses Yahoo Finance's free equity screener (via yfinance's EquityQuery) to pull
the universe of listed companies per CEE market, filters to genuine local
listings, drops names already covered, and (optionally) runs them through the
normal six-factor pipeline so undervalued newcomers surface automatically.

HONEST SCOPE: Yahoo's screener is free but (a) caps results, (b) can be patchy
for small markets, and (c) may include cross-listings — we filter by exchange
suffix and a market-cap floor to keep it clean. It is a discovery aid, not a
complete market registry.

Usage:
    python discover.py                       # discover + screen default regions
    python discover.py pl at --per 20        # only Poland+Austria, 20 each
    python discover.py --list                # just list candidates, don't screen
"""
from __future__ import annotations

import json
import sys

import yfinance as yf
from yfinance import EquityQuery as EQ

import activist_screener as s

# Yahoo region code -> expected local exchange suffix.
REGION_SUFFIX = {
    "pl": ".WA", "at": ".VI", "cz": ".PR", "hu": ".BD", "ro": ".RO", "gr": ".AT",
    "de": ".DE", "fr": ".PA", "it": ".MI", "es": ".MC", "nl": ".AS", "be": ".BR",
    "pt": ".LS", "se": ".ST", "dk": ".CO", "fi": ".HE", "gb": ".L", "ie": ".IR",
}
# ...and the country the listing should actually be in — to drop US/foreign
# mega-caps that are merely cross-listed locally (e.g. NVDA.WA, VISA.WA).
# NOTE: Airbus (AIR.PA) and Stellantis (STLAM.MI) are genuinely incorporated in
# the Netherlands despite trading in Paris/Milan — that's correct, not a bug;
# they just won't show up under a Netherlands-region discovery scan.
REGION_COUNTRY = {
    "pl": {"Poland"}, "at": {"Austria"}, "cz": {"Czechia", "Czech Republic"},
    "hu": {"Hungary"}, "ro": {"Romania"}, "gr": {"Greece"},
    "de": {"Germany"}, "fr": {"France"}, "it": {"Italy"}, "es": {"Spain"},
    "nl": {"Netherlands"}, "be": {"Belgium"}, "pt": {"Portugal"},
    "se": {"Sweden"}, "dk": {"Denmark"}, "fi": {"Finland"},
    "gb": {"United Kingdom"}, "ie": {"Ireland"},
}
# The original CEE markets, where FOREIGN_DENY below was tuned against real
# cross-listing noise (see discover_tickers). Applying that same denylist to
# the newer markets would wrongly strip their OWN home-market blue chips —
# e.g. "SAP" is denied because it showed up cross-listed on Budapest, but SAP.DE
# is SAP's real home listing. For markets outside this set we rely solely on
# the post-fetch country check (REGION_COUNTRY), which is the reliable backstop.
CEE_LEGACY_REGIONS = {"pl", "at", "cz", "hu", "ro", "gr"}
DEFAULT_REGIONS = ["pl", "at", "cz", "hu", "ro", "gr"]
MCAP_FLOOR = 3e8          # skip micro-caps (local currency)


# Yahoo tags many US/EU mega-caps cross-listed on CEE exchanges with the local
# suffix, local currency, AND region=US — so no screener field distinguishes them.
# They also dwarf real local names by market cap and crowd them out. We strip the
# common offenders cheaply here (CEE_LEGACY_REGIONS only); the post-fetch country
# filter is the real backstop everywhere else.
FOREIGN_DENY = {
    "AAPL", "MSFT", "NVDA", "GOOG", "GOOGL", "AMZN", "META", "TSLA", "ORCL",
    "ADBE", "INTC", "AMD", "NFLX", "PYPL", "VISA", "V", "MA", "PG", "PCGL",
    "KO", "PEP", "JNJ", "PFE", "MRK", "DIS", "BA", "JPM", "BAC", "WMT", "MCD",
    "NKE", "CSCO", "IBM", "QCOM", "TXN", "CRM", "UBER", "COIN", "SBUX", "GE",
    "XOM", "CVX", "T", "VZ", "ABNB", "AVGO", "COST", "LLY", "UNH",
    "SAP", "BMW", "BASF", "BAYER", "BAYN", "EON", "EOAN", "SIE", "ALV", "DTE",
    "VOW", "VOW3", "MBG", "DBK", "ADS", "DPW", "MUV2", "IFX", "VNA", "RWE",
    "AIR", "MC", "OR", "SU", "BN", "STLA", "ENEL", "ISP", "UCG",
}


def _allowed_countries(regions):
    out = set()
    for r in regions:
        out |= REGION_COUNTRY.get(r, set())
    return out


def discover_tickers(regions=None, per_region=30, mcap_floor=MCAP_FLOOR, exclude=None):
    """Return a deduped list of local-listed tickers per region, largest first."""
    regions = regions or DEFAULT_REGIONS
    exclude = set(exclude or [])
    found = []
    for code in regions:
        suffix = REGION_SUFFIX.get(code)
        if not suffix:
            continue
        try:
            q = EQ("and", [EQ("gt", ["intradaymarketcap", mcap_floor]),
                           EQ("eq", ["region", code])])
            res = yf.screen(q, size=100)
            quotes = res.get("quotes", []) if isinstance(res, dict) else []
        except Exception as exc:
            print(f"  {code}: screener failed ({exc})")
            continue
        # local suffix, not an obvious foreign cross-listing, largest first.
        # FOREIGN_DENY only applies to the legacy CEE markets it was tuned for —
        # elsewhere it would wrongly strip genuine home-market blue chips.
        apply_deny = code in CEE_LEGACY_REGIONS
        local = [x for x in quotes
                 if str(x.get("symbol", "")).endswith(suffix)
                 and (not apply_deny or x.get("symbol", "").split(".")[0].upper() not in FOREIGN_DENY)]
        local.sort(key=lambda x: x.get("marketCap") or 0, reverse=True)
        picks = [x["symbol"] for x in local
                 if x["symbol"] not in exclude][:per_region]
        found.extend(picks)
        print(f"  {code}: {len(local)} local names, took {len(picks)} new")
    # dedupe, preserve order
    seen, out = set(), []
    for t in found:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def main(argv):
    regions = [a for a in argv if a in REGION_SUFFIX] or DEFAULT_REGIONS
    per_region = 30
    if "--per" in argv:
        try:
            per_region = int(argv[argv.index("--per") + 1])
        except (ValueError, IndexError):
            pass
    list_only = "--list" in argv

    print(f"Discovering candidates in {regions} (up to {per_region} each)...")
    candidates = discover_tickers(regions, per_region=per_region,
                                  exclude=s.TICKERS)
    print(f"\n{len(candidates)} new candidate tickers found.")
    if list_only or not candidates:
        print(", ".join(candidates))
        return 0

    print("Screening candidates through the six-factor pipeline (may take a while)...")
    companies = s.run_pipeline(candidates, do_history=False)

    # Drop foreign cross-listings (e.g. NVDA.WA) — keep only genuine local names.
    allowed = _allowed_countries(regions)
    local = [c for c in companies if c.country in allowed]
    dropped = len(companies) - len(local)
    if dropped:
        foreign = [c.ticker for c in companies if c.country not in allowed]
        print(f"Dropped {dropped} foreign cross-listings: {', '.join(foreign)}")
    companies = local

    passed = sorted((c for c in companies if c.score >= s.SCORE_THRESHOLD),
                    key=lambda c: c.score, reverse=True)
    print(f"\n{len(passed)} of {len(companies)} discovered names scored >= {s.SCORE_THRESHOLD}:")
    for c in passed:
        print(f"  {c.ticker:10} {c.score:.2f}  {c.control_label:22} {c.name[:34]}")

    s.write_thesis(passed)
    s.write_json(passed, "innimmo_discovered_data.json")
    s.write_csv(passed, "innimmo_discovered.csv")
    try:
        from build_dashboard import build_dashboard
        build_dashboard("innimmo_discovered_data.json", "dashboard_discovered.html")
        print("\nWrote innimmo_discovered.csv, innimmo_discovered_data.json, dashboard_discovered.html")
    except Exception as exc:
        print(f"Dashboard build skipped ({exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
