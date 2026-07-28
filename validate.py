#!/usr/bin/env python3
"""
Data-validation harness for the Innimmo screener.

Purpose: tell us how much to TRUST the screener's inputs before acting on them.
For each watchlist name it runs two kinds of check:

  A) INTERNAL CONSISTENCY — do Yahoo's own summary fields agree with each other?
       - market cap  vs  price x shares outstanding
       - P/B         vs  price / book-value-per-share
       - P/E         vs  price / trailing EPS
       - dividend yield  vs  dividend rate / price
  B) SUMMARY vs STATEMENTS — do the summary ratios agree with the figures
     recomputed from Yahoo's balance sheet / income statement (a DIFFERENT
     endpoint, so disagreement flags stale or wrong summary data)?
       - book value per share  vs  equity / shares
       - net debt              vs  total debt - cash
       - ROE                   vs  net income / equity

HONEST SCOPE: this cross-checks Yahoo against itself and against arithmetic. It
is NOT an independent third-party audit — a paid feed (Refinitiv/Bloomberg) or
the companies' filings would be the real gold standard. But it reliably catches
unit errors, stale fields, and internal contradictions.

Run:  python validate.py            (validates the current watchlist)
      python validate.py 10         (limit to the top 10 names)
"""
from __future__ import annotations

import json
import os
import sys

import yfinance as yf

TOL = 0.05          # 5% relative tolerance for ratio/consistency checks
TOL_STMT = 0.15     # 15% for balance-sheet items (definitions vary a bit)


def num(x):
    try:
        f = float(x)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def row(df, *names):
    """First matching line item's most-recent value from a statement frame."""
    if df is None or getattr(df, "empty", True):
        return None
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna()
            if len(s):
                return num(s.iloc[0])
    return None


def cmp(name, summary, recomputed, tol=TOL, abs_pp=None):
    """Return a check dict. abs_pp: absolute tolerance in decimal (for yields)."""
    if summary is None or recomputed is None:
        return {"check": name, "summary": summary, "calc": recomputed, "status": "n/a"}
    if abs_pp is not None:
        ok = abs(summary - recomputed) <= abs_pp
    else:
        base = max(abs(summary), abs(recomputed), 1e-9)
        ok = abs(summary - recomputed) / base <= tol
    return {"check": name, "summary": round(summary, 4),
            "calc": round(recomputed, 4), "status": "OK" if ok else "MISMATCH"}


def validate_ticker(ticker):
    tk = yf.Ticker(ticker)
    try:
        info = tk.info
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc), "checks": []}
    price = num(info.get("currentPrice")) or num(info.get("regularMarketPrice")) or num(info.get("previousClose"))
    shares = num(info.get("sharesOutstanding"))
    checks = []

    # --- A) internal consistency (summary vs summary/arithmetic) ---
    if price and shares:
        checks.append(cmp("market cap = price x shares", num(info.get("marketCap")), price * shares))
    bvps = num(info.get("bookValue"))
    if price and bvps:
        checks.append(cmp("P/B = price / book", num(info.get("priceToBook")), price / bvps))
    eps = num(info.get("trailingEps"))
    if price and eps and eps > 0:
        checks.append(cmp("P/E = price / EPS", num(info.get("trailingPE")), price / eps))
    drate = num(info.get("dividendRate"))
    dy = num(info.get("dividendYield"))
    if price and drate is not None and dy is not None:
        checks.append(cmp("dividend yield", dy / 100.0, drate / price, abs_pp=0.005))

    # --- B) summary vs financial statements (different endpoint) ---
    try:
        bs = tk.balance_sheet
    except Exception:
        bs = None
    try:
        inc = tk.income_stmt
    except Exception:
        inc = None

    equity = row(bs, "Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity")
    if equity and shares and bvps:
        checks.append(cmp("book value/share vs equity/shares", bvps, equity / shares, tol=TOL_STMT))

    # Net-debt cross-check is meaningless for banks/insurers (their debt & cash
    # ARE the business), and the screener already excludes it there — so skip it
    # to avoid crying wolf and keep the report focused on real issues.
    sector = info.get("sector") or ""
    is_financial = sector in ("Financial Services", "Financial", "Insurance")
    tdebt = row(bs, "Total Debt")
    cash = row(bs, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    if not is_financial and tdebt is not None and cash is not None:
        nd_stmt = tdebt - cash
        nd_info = (num(info.get("totalDebt")) or 0) - (num(info.get("totalCash")) or 0)
        checks.append(cmp("net debt: summary vs statements", nd_info, nd_stmt, tol=TOL_STMT))

    net_income = row(inc, "Net Income", "Net Income Common Stockholders")
    roe_info = num(info.get("returnOnEquity"))
    if net_income and equity and roe_info is not None:
        checks.append(cmp("ROE vs net income / equity", roe_info, net_income / equity, abs_pp=0.03))

    return {"ticker": ticker, "name": info.get("shortName") or ticker, "checks": checks}


def main(argv):
    limit = int(argv[0]) if argv and argv[0].isdigit() else None
    if os.path.exists("innimmo_watchlist_data.json"):
        data = json.load(open("innimmo_watchlist_data.json", encoding="utf-8"))
        tickers = [c["ticker"] for c in data]
    else:
        import activist_screener as s
        tickers = s.TICKERS
    if limit:
        tickers = tickers[:limit]

    print(f"\nData validation — {len(tickers)} names")
    print("Cross-check: Yahoo summary vs Yahoo statements + internal arithmetic.")
    print("NOT an independent audit; a paid feed / filings would be the gold standard.\n")

    results = []
    total = mism = 0
    for t in tickers:
        r = validate_ticker(t)
        results.append(r)
        if r.get("error"):
            print(f"{t:9} ERROR: {r['error']}")
            continue
        bad = [c for c in r["checks"] if c["status"] == "MISMATCH"]
        na = [c for c in r["checks"] if c["status"] == "n/a"]
        ok = [c for c in r["checks"] if c["status"] == "OK"]
        total += len(r["checks"]); mism += len(bad)
        tag = "OK" if not bad else f"{len(bad)} MISMATCH"
        print(f"{t:9} {tag:14} ({len(ok)} ok, {len(na)} n/a)")
        for c in bad:
            print(f"           - {c['check']}: summary={c['summary']} vs calc={c['calc']}")

    print(f"\nSummary: {total} checks across {len(tickers)} names, {mism} mismatches.")
    if total:
        print(f"Pass rate: {100*(1-mism/total):.0f}%  "
              "(mismatches = fields to verify against filings before acting).")
    json.dump(results, open("validate_result.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("Wrote validate_result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
