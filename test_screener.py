#!/usr/bin/env python3
"""
Unit tests for the Innimmo screener's pure logic (no network).

Run:  python test_screener.py     (prints PASS/FAIL, exits non-zero on failure)
"""
import math
import pandas as pd

import activist_screener as s
from ownership import ownership, is_actionable

FAILS = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


def synth(trend, n=250, base=100.0, amp=3.0):
    """Deterministic price+volume frame: linear trend plus a sine wobble."""
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    close = [base + trend * i + amp * math.sin(i / 5.0) for i in range(n)]
    vol = [1_000_000 + 50_000 * math.sin(i / 7.0) for i in range(n)]
    return pd.DataFrame({"Close": close, "Volume": vol}, index=idx)


# --- helpers -------------------------------------------------------------
check("band below first threshold", s.band(0.5, [0.75, 1.0], [5, 3, 1]) == 5)
check("band middle", s.band(0.9, [0.75, 1.0], [5, 3, 1]) == 3)
check("band above last", s.band(2.0, [0.75, 1.0], [5, 3, 1]) == 1)
check("band None -> None", s.band(None, [1], [1, 2]) is None)

check("dividend normalisation", abs((6.76 / 100.0) - 0.0676) < 1e-9)   # Yahoo % -> fraction
check("debt/equity normalisation", abs((60.972 / 100.0) - 0.60972) < 1e-9)  # Yahoo % -> ratio

# --- technicals ----------------------------------------------------------
up = s.Company(ticker="UP")
s.compute_technicals(up, synth(+0.4))
check("uptrend classified", up.trend == "Uptrend")
check("RSI in range", up.rsi14 is None or 0 <= up.rsi14 <= 100)
check("support < resistance", up.support < up.resistance)
check("12m return positive in uptrend", up.ret_12m > 0)
check("chart series populated", len(up.chart_close) > 10 and len(up.chart_volume) == len(up.chart_close))

dn = s.Company(ticker="DN")
s.compute_technicals(dn, synth(-0.4, base=200.0))
check("downtrend classified", dn.trend == "Downtrend")
check("12m return negative in downtrend", dn.ret_12m < 0)
check("technical score up>down", s.score_technical(up) > s.score_technical(dn))

# --- FX ------------------------------------------------------------------
co = s.Company(ticker="X", currency="PLN", market_cap=4300.0)
rate = 4.30
co.market_cap_eur = co.market_cap / rate
check("FX to EUR", abs(co.market_cap_eur - 1000.0) < 1e-6)

# --- actionability -------------------------------------------------------
_, pge_score, _ = ownership("PGE.WA")      # state majority
_, otp_score, _ = ownership("OTP.BD")      # widely held
check("state < widely-held actionability", pge_score < otp_score)
check("state not actionable", not is_actionable(pge_score))
check("widely-held actionable", is_actionable(otp_score))
sa = s.Company(ticker="OTP.BD"); sb = s.Company(ticker="PGE.WA")
check("score_actionability reflects ownership",
      s.score_actionability(sa) > s.score_actionability(sb))

# --- sector-relative value ----------------------------------------------
cheap = s.Company(ticker="C", sector="X", pb=0.5, pe=6, ev_ebitda=4)
mid = s.Company(ticker="M", sector="X", pb=1.0, pe=12, ev_ebitda=8)
rich = s.Company(ticker="R", sector="X", pb=2.0, pe=24, ev_ebitda=16)
s.compute_relative_value([cheap, mid, rich])
check("cheaper peer scores higher rel_value", cheap.rel_value > rich.rel_value)

# --- overall score bounds -----------------------------------------------
for c in (up, dn, cheap, mid, rich):
    c.control_label, _, c.control_note = ownership(c.ticker)
    s.score(c)
    check(f"score in [0,5] for {c.ticker}", 0 <= c.score <= 5)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED:", ", ".join(FAILS))
    raise SystemExit(1)
print("ALL TESTS PASSED")
