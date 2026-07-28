#!/usr/bin/env python3
"""
Lightweight validation of the TECHNICAL score.

Honest scope: Yahoo only gives point-in-time fundamentals, so we cannot backtest
the value/quality/ownership dimensions with this data source. We CAN backtest the
technical score, which is a pure function of price history: compute it as of ~1
year ago, then measure the realised forward return to today, and check whether a
higher technical score lined up with a better forward return.

This is a small-sample, single-period, price-only check — indicative, not proof.

Run:  python backtest.py
"""
from __future__ import annotations

import json
import yfinance as yf

import activist_screener as s

LOOKBACK = 252   # trading days ~ 1 year as-of point
MIN_HIST = 180   # need enough history before the as-of point to compute MAs


def tech_score_asof(hist_slice):
    co = s.Company(ticker="X")
    s.compute_technicals(co, hist_slice)
    return s.score_technical(co)


def main():
    rows = []
    for t in s.TICKERS:
        try:
            hist = yf.Ticker(t).history(period="2y", interval="1d", auto_adjust=True)
        except Exception:
            continue
        close = hist["Close"].dropna() if "Close" in hist else None
        if close is None or len(close) < MIN_HIST + LOOKBACK:
            continue
        cut = len(close) - LOOKBACK
        sc = tech_score_asof(hist.iloc[:cut])
        if sc is None:
            continue
        fwd = float(close.iloc[-1]) / float(close.iloc[cut - 1]) - 1
        rows.append({"ticker": t, "tech_score": round(sc, 2), "fwd_return": round(fwd, 4)})

    if len(rows) < 5:
        print(f"Not enough data to backtest ({len(rows)} names).")
        return 1

    # Correlation (Pearson) between score and forward return.
    n = len(rows)
    xs = [r["tech_score"] for r in rows]
    ys = [r["fwd_return"] for r in rows]
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    corr = cov / (vx * vy) if vx and vy else 0.0

    # Buckets.
    def bucket(sc):
        return (">=4.0" if sc >= 4 else "3.5-4.0" if sc >= 3.5 else
                "3.0-3.5" if sc >= 3 else "<3.0")
    order = ["<3.0", "3.0-3.5", "3.5-4.0", ">=4.0"]
    agg = {}
    for r in rows:
        agg.setdefault(bucket(r["tech_score"]), []).append(r["fwd_return"])

    print(f"\nTechnical-score backtest — {n} names, as-of ~{LOOKBACK} sessions ago\n")
    print(f"{'Score bucket':12} {'n':>3}  {'avg 1y fwd return':>18}")
    for b in order:
        if b in agg:
            v = agg[b]
            print(f"{b:12} {len(v):>3}  {sum(v)/len(v)*100:>16.1f}%")
    print(f"\nPearson correlation(score, forward return) = {corr:+.2f}")
    print("Positive => higher technical score tended to precede better returns.")
    print("Caveat: single period, price-only, small sample — indicative, not proof.\n")

    json.dump({"rows": rows, "correlation": round(corr, 3)},
              open("backtest_result.json", "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
