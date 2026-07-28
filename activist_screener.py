#!/usr/bin/env python3
"""
Innimmo Investment Capital Group — Public Markets Activist Screener (T-AI-10)
============================================================================

Pulls LIVE data for a universe of CEE / European listings from Yahoo Finance
and scores each name for activist attractiveness across SIX dimensions:

    Value · Quality · Balance sheet · Growth · Technical · Actionability

- Value blends absolute multiples with a SECTOR-RELATIVE (peer) read.
- Technical reads the price chart (trend, support/resistance, breakouts with
  VOLUME confirmation, RSI) from one year of daily prices.
- Actionability asks the question an activist must answer first: can a 3-10%
  holder actually force change, or is the company state / parent / family
  controlled? (see ownership.py)

Market caps are normalised to EUR so sizes are comparable. Each run is tracked
so scores can be compared to the previous run.

Outputs:
    innimmo_activist_watchlist.csv   flat export
    innimmo_watchlist_data.json      rich data (all fields + price series)
    score_history.json               one record per run (for Δ tracking)
    dashboard.html                   interactive dashboard with price charts

Internal RESEARCH SUPPORT tool — NOT investment advice.

Run:  pip install -r requirements.txt ; python activist_screener.py
"""

from __future__ import annotations

import csv
import json
import logging
import math
import os
import statistics
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

from macro import macro_note
from ownership import ownership, verified_date
from catalysts import agm_season

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass


# --------------------------------------------------------------------------- #
CLAUDE_MODEL = "claude-sonnet-5"
SCORE_THRESHOLD = 3.0
OUTPUT_CSV = "innimmo_activist_watchlist.csv"
OUTPUT_JSON = "innimmo_watchlist_data.json"
HISTORY_JSON = "score_history.json"

DIMENSION_WEIGHTS = {
    "value": 0.25, "quality": 0.15, "balance": 0.10,
    "growth": 0.10, "technical": 0.20, "actionability": 0.20,
}

# Fallback EUR FX rates (units of local currency per 1 EUR) if live fetch fails.
# Approximate, 2026-07 — used only as a backstop; refresh periodically.
FX_FALLBACK = {"EUR": 1.0, "PLN": 4.30, "HUF": 395.0, "CZK": 25.0, "RON": 4.97,
               "GBP": 0.84, "USD": 1.08, "BGN": 1.96}

TICKERS: list[str] = [
    "PKO.WA", "PKN.WA", "KGH.WA", "PZU.WA", "PGE.WA", "PEO.WA", "DNP.WA",
    "CDR.WA", "LPP.WA", "ALE.WA", "CPS.WA", "JSW.WA", "OPL.WA", "KTY.WA",
    "BDX.WA",
    "EBS.VI", "OMV.VI", "VOE.VI", "RBI.VI", "VER.VI", "WIE.VI", "ANDR.VI",
    "BG.VI", "DOC.VI", "LNZ.VI", "UQA.VI", "POST.VI", "MMK.VI",
    "CEZ.PR", "KOMB.PR", "MONET.PR",
    "OTP.BD", "MOL.BD", "RICHT.BD", "MTEL.BD",
    "KRKG.LJ", "POSR.LJ", "ZVTG.LJ",
    # Romania — Bucharest
    "TLV.RO", "SNP.RO", "SNG.RO", "DIGI.RO", "EL.RO", "FP.RO", "TGN.RO",
    # Greece — Athens
    "ETE.AT", "EUROB.AT", "TPEIR.AT", "OPAP.AT", "OTE.AT", "MYTIL.AT", "PPC.AT",
]

FINANCIAL_SECTORS = {"Financial Services", "Financial", "Insurance"}

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("screener")


# --------------------------------------------------------------------------- #
@dataclass
class Company:
    ticker: str
    name: str = ""
    currency: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    is_financial: bool = False
    business: str = ""

    price: Optional[float] = None
    market_cap: Optional[float] = None
    market_cap_eur: Optional[float] = None

    pb: Optional[float] = None
    pe: Optional[float] = None
    fwd_pe: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ps: Optional[float] = None
    div_yield: Optional[float] = None
    roe: Optional[float] = None
    oper_margin: Optional[float] = None
    profit_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    rev_growth: Optional[float] = None
    earn_growth: Optional[float] = None
    fcf_yield: Optional[float] = None
    net_cash: Optional[float] = None
    net_cash_to_mktcap: Optional[float] = None

    # ownership / actionability
    control_label: str = ""
    control_note: str = ""
    control_verified: str = ""
    insider_pct: Optional[float] = None

    # liquidity / tradability
    adv_eur: Optional[float] = None          # avg daily traded value, EUR
    days_to_5pct: Optional[float] = None     # sessions to build a 5% stake

    # valuation vs peers
    fv_upside: Optional[float] = None        # peer-implied upside/downside (fraction)
    fair_value: Optional[float] = None       # peer-implied fair price

    # data confidence + catalysts
    confidence: Optional[float] = None       # 0-1 data completeness
    confidence_label: str = ""
    next_earnings: str = ""
    ex_div_date: str = ""
    div_pay_date: str = ""
    agm_season: str = ""

    # technicals
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    rsi14: Optional[float] = None
    high52: Optional[float] = None
    low52: Optional[float] = None
    pct_from_high: Optional[float] = None
    pct_from_low: Optional[float] = None
    ret_3m: Optional[float] = None
    ret_12m: Optional[float] = None
    resistance: Optional[float] = None
    support: Optional[float] = None
    trend: str = ""
    breakout: str = ""
    vol_avg: Optional[float] = None
    vol_ratio: Optional[float] = None
    vol_confirm: bool = False
    tech_read: str = ""

    chart_dates: list = field(default_factory=list)
    chart_close: list = field(default_factory=list)
    chart_sma50: list = field(default_factory=list)
    chart_sma200: list = field(default_factory=list)
    chart_volume: list = field(default_factory=list)

    rel_value: Optional[float] = None      # sector-relative value score 1-5
    sub_scores: dict = field(default_factory=dict)
    score: float = 0.0
    score_delta: Optional[float] = None
    flags: list = field(default_factory=list)
    macro: str = ""
    thesis: str = ""
    warnings: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
def num(*vals):
    for v in vals:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            return f
    return None


def band(value, thresholds, scores):
    if value is None:
        return None
    for t, s in zip(thresholds, scores):
        if value < t:
            return s
    return scores[-1]


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _ts_date(ts):
    """Yahoo epoch-seconds timestamp -> 'YYYY-MM-DD', or '' if unavailable."""
    t = num(ts)
    if t and t > 0:
        try:
            return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
        except (OverflowError, OSError, ValueError):
            return ""
    return ""


# --------------------------------------------------------------------------- #
# FX — normalise market caps to EUR
# --------------------------------------------------------------------------- #
def fetch_fx(currencies) -> dict:
    rates = {"EUR": 1.0}
    for cur in currencies:
        if cur in ("EUR", "") or cur in rates:
            continue
        try:
            h = yf.Ticker(f"EUR{cur}=X").history(period="5d")
            r = num(h["Close"].dropna().iloc[-1]) if not h.empty else None
        except Exception:
            r = None
        rates[cur] = r or FX_FALLBACK.get(cur)
        if r is None:
            log.warning("  FX %s: using fallback rate %s", cur, rates[cur])
    return rates


# --------------------------------------------------------------------------- #
# Technicals
# --------------------------------------------------------------------------- #
def compute_technicals(co: Company, hist) -> None:
    if hist is None or hist.empty or "Close" not in hist:
        co.warnings.append("no price history")
        return
    close = hist["Close"].dropna()
    if len(close) < 60:
        co.warnings.append("thin price history")
        return
    vol = hist["Volume"].reindex(close.index) if "Volume" in hist else None

    last = float(close.iloc[-1])
    sma50_s = close.rolling(50).mean()
    sma200_s = close.rolling(min(200, len(close))).mean()
    co.sma50 = num(sma50_s.iloc[-1])
    co.sma200 = num(sma200_s.iloc[-1])
    co.high52 = float(close.max())
    co.low52 = float(close.min())
    co.pct_from_high = last / co.high52 - 1 if co.high52 else None
    co.pct_from_low = last / co.low52 - 1 if co.low52 else None
    co.ret_12m = last / float(close.iloc[0]) - 1
    if len(close) > 63:
        co.ret_3m = last / float(close.iloc[-63]) - 1

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    co.rsi14 = num((100 - 100 / (1 + rs)).iloc[-1])

    window = close.iloc[-160:-5] if len(close) > 165 else close.iloc[:-5]
    if len(window):
        co.resistance = float(window.max())
        co.support = float(window.min())
        if co.resistance and last >= co.resistance * 0.995:
            co.breakout = "up"
        elif co.support and last <= co.support * 1.005:
            co.breakout = "down"

    # Volume: confirm a breakout only if recent volume runs above its average.
    if vol is not None and vol.notna().sum() > 50:
        co.vol_avg = num(vol.rolling(50).mean().iloc[-1])
        recent = num(vol.iloc[-5:].mean())
        if co.vol_avg and recent:
            co.vol_ratio = recent / co.vol_avg
            co.vol_confirm = co.vol_ratio >= 1.2

    if co.sma50 and co.sma200:
        if last > co.sma50 > co.sma200:
            co.trend = "Uptrend"
        elif last < co.sma50 < co.sma200:
            co.trend = "Downtrend"
        else:
            co.trend = "Range / mixed"
    elif co.sma50:
        co.trend = "Uptrend" if last > co.sma50 else "Downtrend"

    co.tech_read = _narrative(co)

    n = len(close)
    step = max(1, n // 140)
    idx = list(range(0, n, step))
    co.chart_dates = [close.index[i].strftime("%Y-%m-%d") for i in idx]
    co.chart_close = [round(float(close.iloc[i]), 4) for i in idx]
    co.chart_sma50 = [num(sma50_s.iloc[i]) for i in idx]
    co.chart_sma200 = [num(sma200_s.iloc[i]) for i in idx]
    if vol is not None:
        co.chart_volume = [num(vol.iloc[i]) or 0 for i in idx]


def _narrative(co: Company) -> str:
    bits = []
    if co.trend:
        bits.append(co.trend.lower())
    if co.breakout == "up" and co.resistance:
        conf = "on strong volume" if co.vol_confirm else "on soft volume"
        bits.append(f"breaking resistance ~{co.resistance:,.2f} {conf}")
    elif co.breakout == "down" and co.support:
        bits.append(f"breaking support ~{co.support:,.2f}")
    elif co.resistance and co.support:
        bits.append(f"ranging {co.support:,.2f}-{co.resistance:,.2f}")
    if co.pct_from_high is not None:
        bits.append(f"{co.pct_from_high * 100:+.0f}% vs 52w high")
    if co.rsi14 is not None:
        state = ("overbought" if co.rsi14 > 70 else
                 "oversold" if co.rsi14 < 30 else "neutral")
        bits.append(f"RSI {co.rsi14:.0f} ({state})")
    return "; ".join(bits)


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
def fetch(ticker: str, fx: dict) -> Optional[Company]:
    co = Company(ticker=ticker)
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
    except Exception as exc:
        log.warning("  %-9s fetch failed (%s)", ticker, exc)
        return None
    if not info or not isinstance(info, dict) or not (
            info.get("regularMarketPrice") or info.get("currentPrice")
            or info.get("previousClose")):
        log.warning("  %-9s no data on Yahoo Finance", ticker)
        return None

    co.name = info.get("longName") or info.get("shortName") or ticker
    co.currency = info.get("currency") or ""
    co.sector = info.get("sector") or ""
    co.industry = info.get("industry") or ""
    co.country = info.get("country") or ""
    co.is_financial = co.sector in FINANCIAL_SECTORS
    co.business = (info.get("longBusinessSummary") or "")[:600]

    co.price = num(info.get("currentPrice"), info.get("regularMarketPrice"),
                   info.get("previousClose"))
    co.market_cap = num(info.get("marketCap"))
    rate = fx.get(co.currency) or FX_FALLBACK.get(co.currency)
    if co.market_cap and rate:
        co.market_cap_eur = co.market_cap / rate

    co.pb = num(info.get("priceToBook"))
    if co.pb is None:
        bv = num(info.get("bookValue"))
        if co.price and bv and bv > 0:
            co.pb = co.price / bv
    co.pe = num(info.get("trailingPE"))
    co.fwd_pe = num(info.get("forwardPE"))
    co.ev_ebitda = num(info.get("enterpriseToEbitda"))
    co.ps = num(info.get("priceToSalesTrailing12Months"))
    dy = num(info.get("dividendYield"))                 # Yahoo returns percent
    co.div_yield = dy / 100.0 if dy is not None else num(info.get("trailingAnnualDividendYield"))
    co.roe = num(info.get("returnOnEquity"))
    co.oper_margin = num(info.get("operatingMargins"))
    co.profit_margin = num(info.get("profitMargins"))
    dte = num(info.get("debtToEquity"))     # Yahoo reports this in percent (e.g. 60.9 = 0.61x)
    co.debt_to_equity = dte / 100.0 if dte is not None else None
    co.current_ratio = num(info.get("currentRatio"))
    co.rev_growth = num(info.get("revenueGrowth"))
    co.earn_growth = num(info.get("earningsGrowth"))
    fcf = num(info.get("freeCashflow"))
    if fcf is not None and co.market_cap:
        co.fcf_yield = fcf / co.market_cap

    tc, td = num(info.get("totalCash")), num(info.get("totalDebt"))
    if tc is not None and td is not None:
        co.net_cash = tc - td
        if co.market_cap:
            co.net_cash_to_mktcap = co.net_cash / co.market_cap

    co.control_label, _, co.control_note = ownership(ticker)
    co.control_verified = verified_date()
    co.insider_pct = num(info.get("heldPercentInsiders"))

    try:
        hist = tk.history(period="1y", interval="1d", auto_adjust=True)
        compute_technicals(co, hist)
    except Exception as exc:
        co.warnings.append(f"technicals failed: {exc}")

    # Liquidity: average daily traded value in EUR, and sessions to build a 5%
    # stake assuming you can be ~20% of daily volume without moving the price.
    if co.vol_avg and co.price and rate:
        co.adv_eur = co.vol_avg * co.price / rate
        if co.market_cap_eur and co.adv_eur > 0:
            co.days_to_5pct = (0.05 * co.market_cap_eur) / (0.20 * co.adv_eur)

    # Catalysts — next earnings, ex-dividend, dividend payment (best-effort).
    try:
        cal = tk.calendar
        ed = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if ed:
            co.next_earnings = str(ed[0] if isinstance(ed, (list, tuple)) else ed)[:10]
    except Exception:
        pass
    co.ex_div_date = _ts_date(info.get("exDividendDate"))
    co.div_pay_date = _ts_date(info.get("dividendDate"))
    co.agm_season = agm_season(co.country)

    _confidence(co)
    co.macro = macro_note(co.country, co.sector)
    _flag(co)
    return co


# Fields that should normally be present; confidence = fraction available.
def _confidence(co: Company) -> None:
    fields = [co.pb, co.pe, co.roe, co.oper_margin, co.profit_margin,
              co.rev_growth, co.earn_growth, co.ps, co.fcf_yield,
              co.div_yield, co.market_cap, co.rsi14]
    if not co.is_financial:                 # these are meaningless for banks
        fields += [co.ev_ebitda, co.net_cash_to_mktcap]
    fields.append(1 if co.trend else None)  # a computed trend counts as present
    present = sum(1 for f in fields if f is not None)
    co.confidence = round(present / len(fields), 2)
    co.confidence_label = ("High" if co.confidence >= 0.75 else
                           "Medium" if co.confidence >= 0.5 else "Low")


def _flag(co: Company) -> None:
    """Data-sanity flags surfaced to the analyst."""
    if co.div_yield is not None and co.div_yield > 0.15:
        co.flags.append("Dividend yield >15% — verify (possible data error)")
    if co.pe is not None and co.pe < 0:
        co.flags.append("Negative P/E (loss-making)")
    if co.roe is not None and abs(co.roe) > 0.80:
        co.flags.append("Extreme ROE — verify")
    if co.market_cap is None:
        co.flags.append("Market cap missing")
    if "fund" in (co.control_label or "").lower():
        co.flags.append("Closed-end fund — P/B is a discount-to-NAV; peer upside % is misleading")
    if co.confidence_label == "Low":
        co.flags.append("Low data confidence — score is unreliable, verify")
    elif co.confidence_label == "Medium":
        co.flags.append("Partial data — treat score with some caution")
    if co.days_to_5pct is not None and co.days_to_5pct > 60:
        co.flags.append(f"Illiquid — ~{co.days_to_5pct:.0f} sessions to build a 5% stake")
    from ownership import is_actionable, STALE_AFTER_DAYS
    _, act_score, _ = ownership(co.ticker)
    if not is_actionable(act_score):
        co.flags.append("Controlled ownership — activist stake unlikely to force change")
    try:
        age = (datetime.now() - datetime.strptime(co.control_verified, "%Y-%m-%d")).days
        if age > STALE_AFTER_DAYS:
            co.flags.append(f"Ownership last verified {co.control_verified} — re-verify")
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Sector-relative (peer) valuation — computed across the whole fetched universe
# --------------------------------------------------------------------------- #
def compute_relative_value(companies) -> None:
    by_sector = {}
    for c in companies:
        by_sector.setdefault(c.sector, []).append(c)

    def rel(value, peers_vals):
        """Lower multiple than peers = cheaper = higher score (1-5)."""
        peers_vals = [v for v in peers_vals if v is not None and v > 0]
        if value is None or value <= 0 or len(peers_vals) < 3:
            return None
        med = statistics.median(peers_vals)
        if med <= 0:
            return None
        r = value / med
        return band(r, [0.6, 0.8, 1.0, 1.3], [5, 4, 3, 2, 1])

    def med(vals):
        vals = [v for v in vals if v is not None and v > 0]
        return statistics.median(vals) if len(vals) >= 3 else None

    for sector, peers in by_sector.items():
        m_pb = med([p.pb for p in peers])
        m_pe = med([p.pe for p in peers])
        m_ev = med([p.ev_ebitda for p in peers])
        for c in peers:
            c.rel_value = _mean([
                rel(c.pb, [p.pb for p in peers]),
                rel(c.pe, [p.pe for p in peers]),
                rel(c.ev_ebitda, [p.ev_ebitda for p in peers]) if not c.is_financial else None,
            ])
            # Peer-implied fair value: where each multiple would sit at the
            # sector median. Crude — quality names may deserve a premium.
            ups = []
            if m_pb and c.pb and c.pb > 0:
                ups.append(m_pb / c.pb - 1)
            if m_pe and c.pe and c.pe > 0:
                ups.append(m_pe / c.pe - 1)
            if not c.is_financial and m_ev and c.ev_ebitda and c.ev_ebitda > 0:
                ups.append(m_ev / c.ev_ebitda - 1)
            if ups:
                c.fv_upside = max(-0.9, min(3.0, sum(ups) / len(ups)))
                if c.price is not None:
                    c.fair_value = c.price * (1 + c.fv_upside)


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def score_value(co):
    absol = _mean([
        band(co.pb, [0.75, 1.0, 1.5, 2.5], [5, 4, 3, 2, 1]),
        band(co.pe, [8, 12, 16, 22], [5, 4, 3, 2, 1]) if (co.pe and co.pe > 0) else None,
        band(co.ps, [0.8, 1.5, 3, 5], [5, 4, 3, 2, 1]),
        band(co.ev_ebitda, [5, 7, 10, 14], [5, 4, 3, 2, 1])
        if (co.ev_ebitda and co.ev_ebitda > 0 and not co.is_financial) else None,
        band(co.fcf_yield, [0, 0.04, 0.07, 0.10], [1, 2, 3, 4, 5])
        if co.fcf_yield is not None else None,
    ])
    # blend absolute with sector-relative (peer) valuation when available
    return _mean([absol, co.rel_value])


def score_quality(co):
    return _mean([
        band(co.roe, [0.05, 0.10, 0.15, 0.20], [1, 2, 3, 4, 5]) if co.roe is not None else None,
        band(co.oper_margin, [0, 0.08, 0.15, 0.25], [1, 2, 3, 4, 5]) if co.oper_margin is not None else None,
        band(co.profit_margin, [0, 0.05, 0.10, 0.18], [1, 2, 3, 4, 5]) if co.profit_margin is not None else None,
    ])


def score_balance(co):
    if co.is_financial:
        return None
    return _mean([
        band(co.net_cash_to_mktcap, [-0.25, 0.0, 0.15, 0.30], [1, 2, 3, 4, 5]) if co.net_cash_to_mktcap is not None else None,
        band(co.debt_to_equity, [0.3, 0.6, 1.0, 2.0], [5, 4, 3, 2, 1]) if co.debt_to_equity is not None else None,
        band(co.current_ratio, [0.8, 1.0, 1.5, 2.0], [1, 2, 3, 4, 5]) if co.current_ratio is not None else None,
    ])


def score_growth(co):
    return _mean([
        band(co.rev_growth, [0, 0.03, 0.10, 0.20], [1, 2, 3, 4, 5]) if co.rev_growth is not None else None,
        band(co.earn_growth, [0, 0.03, 0.10, 0.20], [1, 2, 3, 4, 5]) if co.earn_growth is not None else None,
    ])


def score_technical(co):
    if not co.trend and co.ret_12m is None:
        return None
    s = 3.0
    if co.trend == "Uptrend":
        s += 1.0
    elif co.trend == "Downtrend":
        s -= 1.0
    if co.breakout == "up":
        s += 0.5 if co.vol_confirm else 0.25   # volume-confirmed breakout counts more
    elif co.breakout == "down":
        s -= 0.5
    if co.ret_12m is not None:
        if co.ret_12m > 0.10:
            s += 0.5
        elif co.ret_12m < -0.10:
            s -= 0.5
    if co.rsi14 is not None:
        if co.rsi14 > 75:
            s -= 0.5
        elif co.rsi14 < 30:
            s += 0.25
    return max(1.0, min(5.0, s))


def score_actionability(co):
    label, s, _ = ownership(co.ticker)
    # Yahoo's insider % is unreliable for CEE names, so only let it lower the
    # score when we have NO curated ownership on file — otherwise the hand-checked
    # label (e.g. "Widely held") wins over a noisy feed.
    if "unknown" in label.lower() and co.insider_pct is not None and co.insider_pct > 0.5:
        s = min(s, 2.0)
    return s


def score(co: Company) -> None:
    co.sub_scores = {
        "value": score_value(co),
        "quality": score_quality(co),
        "balance": score_balance(co),
        "growth": score_growth(co),
        "technical": score_technical(co),
        "actionability": score_actionability(co),
    }
    w = {k: DIMENSION_WEIGHTS[k] for k, v in co.sub_scores.items() if v is not None}
    tw = sum(w.values())
    co.score = round(sum(co.sub_scores[k] * wt for k, wt in w.items()) / tw, 2) if tw else 0.0
    co.sub_scores = {k: (round(v, 1) if v is not None else None) for k, v in co.sub_scores.items()}


# --------------------------------------------------------------------------- #
# History (Δ vs previous run)
# --------------------------------------------------------------------------- #
def apply_history(companies) -> None:
    prev = {}
    if os.path.exists(HISTORY_JSON):
        try:
            hist = json.load(open(HISTORY_JSON, encoding="utf-8"))
            if hist:
                prev = hist[-1].get("scores", {})
        except Exception:
            hist = []
    else:
        hist = []
    for c in companies:
        if c.ticker in prev and prev[c.ticker] is not None:
            c.score_delta = round(c.score - prev[c.ticker], 2)
    hist.append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "scores": {c.ticker: c.score for c in companies}})
    json.dump(hist[-60:], open(HISTORY_JSON, "w", encoding="utf-8"), indent=1)


# --------------------------------------------------------------------------- #
# AI thesis
# --------------------------------------------------------------------------- #
def _f(v, p=False, money=False):
    if v is None:
        return "n/a"
    if p:
        return f"{v * 100:.1f}%"
    if money:
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def brief(co: Company) -> str:
    ss = co.sub_scores
    return (
        f"{co.name} ({co.ticker}) — {co.sector or 'n/a'}, {co.country or 'n/a'}\n"
        f"Overall {co.score}/5 [" + ", ".join(f"{k} {v}" for k, v in ss.items() if v is not None) + "]\n"
        f"OWNERSHIP: {co.control_label} — {co.control_note}\n"
        f"VALUATION: P/B {_f(co.pb)}, P/E {_f(co.pe)}, EV/EBITDA {_f(co.ev_ebitda)}, "
        f"P/S {_f(co.ps)}, FCF yield {_f(co.fcf_yield, True)}, sector-relative value {_f(co.rel_value)}/5\n"
        f"QUALITY: ROE {_f(co.roe, True)}, oper margin {_f(co.oper_margin, True)}, net margin {_f(co.profit_margin, True)}\n"
        f"BALANCE: net cash {_f(co.net_cash, money=True)} ({_f(co.net_cash_to_mktcap, True)} of cap), "
        f"D/E {_f(co.debt_to_equity)}\n"
        f"GROWTH: revenue {_f(co.rev_growth, True)}, earnings {_f(co.earn_growth, True)}\n"
        f"TECHNICAL: {co.tech_read or 'n/a'}; price {_f(co.price)}, 50d {_f(co.sma50)}, 200d {_f(co.sma200)}\n"
        f"MARKET CAP: {_f(co.market_cap_eur, money=True)} EUR\n"
        f"MACRO: {co.macro}\nBUSINESS: {co.business or 'n/a'}"
    )


def rule_based_thesis(co: Company) -> str:
    """Deterministic activist summary composed from the computed fields.
    Used when no ANTHROPIC_API_KEY is set, so the dashboard is always populated."""
    from ownership import is_actionable
    _, act, _ = ownership(co.ticker)
    s = []

    # Valuation
    val = []
    if co.pb is not None:
        val.append(f"{co.pb:.2f}x book")
    if co.pe is not None and co.pe > 0:
        val.append(f"{co.pe:.1f}x earnings")
    vtxt = " and ".join(val) if val else "limited valuation data"
    if co.fv_upside is not None:
        vtxt += f", implying ~{co.fv_upside*100:+.0f}% vs its sector-median multiple (crude)"
    s.append(f"{co.name} trades at {vtxt}.")

    # Quality
    if co.roe is not None:
        q = "strong" if co.roe > 0.15 else "modest" if co.roe > 0.05 else "weak"
        s.append(f"Quality is {q} (ROE {co.roe*100:.0f}%).")

    # Actionability — the activist verdict
    if "unknown" in (co.control_label or "").lower():
        s.append("Ownership isn't mapped for this name yet — verify the cap table "
                 "before assuming an activist could act.")
    elif is_actionable(act):
        s.append(f"Ownership is favourable ({co.control_label}), so an activist "
                 "stake could realistically press for capital return or change.")
        if "fund" in co.control_label.lower():
            s.append("Note: as a closed-end fund its book value is its NAV, so the "
                     "P/B is a discount-to-NAV and the peer-implied upside overstates it; "
                     "the real angle is closing that discount via buybacks.")
    else:
        s.append(f"But it is {co.control_label.lower()} — an activist stake is "
                 "unlikely to force change, which caps the thesis.")

    # Technical timing
    if co.trend:
        t = co.trend.lower()
        extra = ""
        if co.rsi14 is not None and co.rsi14 > 70:
            extra = " but overbought (RSI %.0f) — wait for a pullback" % co.rsi14
        elif co.rsi14 is not None and co.rsi14 < 30:
            extra = " and oversold (RSI %.0f) — a possible entry" % co.rsi14
        elif co.breakout == "up":
            extra = " and breaking resistance" + (" on strong volume" if co.vol_confirm else " on soft volume")
        s.append(f"The chart is in a {t}{extra}.")

    # Liquidity
    if co.days_to_5pct is not None:
        liq = ("liquid enough to build a stake" if co.days_to_5pct <= 30
               else f"relatively illiquid (~{co.days_to_5pct:.0f} sessions to build 5%)")
        s.append(f"It is {liq}.")

    # Confidence caveat
    if co.confidence_label != "High":
        s.append(f"Data confidence is {co.confidence_label.lower()} — verify before acting.")

    s.append("[Rule-based summary — set ANTHROPIC_API_KEY for a full AI thesis.]")
    return " ".join(s)


def generate_thesis(client, co: Company) -> str:
    system = (
        "You are an activist equity analyst at Innimmo Investment Capital Group, "
        "covering CEE and European public markets. Ground every claim in the data "
        "provided; never invent figures. Internal research, not investment advice."
    )
    prompt = (
        "Write a focused activist thesis (~150-200 words, no bullets). Integrate "
        "valuation (absolute AND sector-relative), quality, balance sheet, growth, "
        "the technical/chart setup, and macro. CRITICALLY assess ACTIONABILITY: if "
        "the company is state/parent/family controlled, say plainly that an activist "
        "stake is unlikely to force change and temper the thesis accordingly. State "
        "the catalyst, whether the chart supports timing an entry now, and end with "
        "the single biggest risk.\n\n" + brief(co)
    )
    msg = client.messages.create(
        model=CLAUDE_MODEL, max_tokens=1200, thinking={"type": "disabled"},
        system=system, messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if b.type == "text").strip()


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
CSV_COLUMNS = [
    "Ticker", "Company", "Sector", "Country", "Control", "OwnershipVerified",
    "MarketCapEUR", "Score", "ScoreDelta", "Confidence", "ValueScore",
    "QualityScore", "BalanceScore", "GrowthScore", "TechnicalScore",
    "ActionabilityScore", "UpsidePct", "PB", "PE", "EV_EBITDA", "PS",
    "DivYield", "ROE", "NetMargin", "DebtToEquity", "RevGrowth", "FCFYield",
    "NetCashToMktCap", "RelValue", "Trend", "RSI14", "VolConfirm",
    "ADV_EUR", "DaysTo5pct", "NextEarnings", "PctFromHigh", "Ret12m",
    "Support", "Resistance", "Flags", "TechRead", "Thesis",
]


def write_csv(rows, path):
    def g(v, p=False):
        return "n/a" if v is None else (f"{v*100:.1f}%" if p else f"{v:,.2f}")
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLUMNS)
        for c in rows:
            s = c.sub_scores
            w.writerow([
                c.ticker, c.name, c.sector, c.country, c.control_label,
                c.control_verified, g(c.market_cap_eur), c.score,
                "" if c.score_delta is None else c.score_delta,
                c.confidence_label, s.get("value"), s.get("quality"),
                s.get("balance"), s.get("growth"), s.get("technical"),
                s.get("actionability"), g(c.fv_upside, True),
                g(c.pb), g(c.pe), g(c.ev_ebitda), g(c.ps), g(c.div_yield, True),
                g(c.roe, True), g(c.profit_margin, True), g(c.debt_to_equity),
                g(c.rev_growth, True), g(c.fcf_yield, True),
                g(c.net_cash_to_mktcap, True), g(c.rel_value), c.trend,
                g(c.rsi14), "yes" if c.vol_confirm else "no",
                g(c.adv_eur), g(c.days_to_5pct), c.next_earnings,
                g(c.pct_from_high, True), g(c.ret_12m, True), g(c.support),
                g(c.resistance), " | ".join(c.flags), c.tech_read, c.thesis,
            ])


def write_json(rows, path):
    json.dump([asdict(c) for c in rows], open(path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


# --------------------------------------------------------------------------- #
def main() -> int:
    log.info("Innimmo Activist Screener — universe of %d tickers", len(TICKERS))

    # Pass 1: fetch FX, then every name.
    fx = fetch_fx(["PLN", "HUF", "CZK", "RON", "GBP", "USD", "BGN"])
    companies = []
    for t in TICKERS:
        co = fetch(t, fx)
        if co:
            companies.append(co)
    if not companies:
        log.error("Nothing could be screened — check network / tickers.")
        return 1

    # Pass 2: sector-relative valuation, then score everything.
    compute_relative_value(companies)
    for co in companies:
        score(co)
        log.info("  %-9s score=%.2f  act=%s  %-13s  P/B=%s",
                 co.ticker, co.score, co.sub_scores.get("actionability"),
                 co.trend or "-", _f(co.pb))
    apply_history(companies)

    watch = sorted((c for c in companies if c.score >= SCORE_THRESHOLD),
                   key=lambda c: c.score, reverse=True)
    log.info("%d of %d names scored >= %.1f", len(watch), len(companies), SCORE_THRESHOLD)

    if watch:
        if os.environ.get("ANTHROPIC_API_KEY"):
            import anthropic
            client = anthropic.Anthropic()
            for c in watch:
                log.info("  thesis: %s", c.ticker)
                try:
                    c.thesis = generate_thesis(client, c)
                except Exception as exc:
                    c.thesis = f"[thesis failed: {exc}]"
        else:
            log.warning("ANTHROPIC_API_KEY not set — using rule-based auto-summaries.")
            for c in watch:
                c.thesis = rule_based_thesis(c)

    write_csv(watch, OUTPUT_CSV)
    write_json(watch, OUTPUT_JSON)
    log.info("Wrote %s + %s (%d names)", OUTPUT_CSV, OUTPUT_JSON, len(watch))
    try:
        from build_dashboard import build_dashboard
        build_dashboard(OUTPUT_JSON, "dashboard.html")
        log.info("Wrote dashboard.html")
    except Exception as exc:
        log.warning("Dashboard build skipped (%s)", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
