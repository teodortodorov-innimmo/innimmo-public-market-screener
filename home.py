#!/usr/bin/env python3
"""
Home page for the Innimmo screener app.

A Yahoo-Finance-style landing page, but built around the tool's own data
instead of generic market media:

  - Market strip: Europe / US / Crypto / Commodities / Currencies, switchable.
  - Hero: YOUR watchlist (falls back to top screener picks if empty).
  - Right rail: today's CEE movers (from the universe) + top screener picks.
  - News: three columns themed to Innimmo's actual research verticals, per
    Workstream 2 (Market & Competitive Research) in the 2026 intern plan —
    Data Centres & Cooling (T-RES-23), Energy & Battery Storage (T-RES-2,
    T-RES-18, T-RES-11), Fintech & Digital Lending (T-RES-3, T-RES-21).

HONEST SCOPE: Yahoo's free news is per-company, not per-topic, so each column
is built from headlines about a representative set of real companies in that
vertical — not a true topic search. Market quotes are live Yahoo data; "movers"
use a simple 2-day close-to-close change, not full intraday ticks.
"""
from __future__ import annotations

import yfinance as yf

MARKET_GROUPS = {
    # WIG20 (Warsaw) intentionally omitted — Yahoo has almost no history for it.
    "Europe": [
        ("^GDAXI", "DAX"), ("^FCHI", "CAC 40"), ("^FTSE", "FTSE 100"),
        ("^STOXX50E", "Euro Stoxx 50"), ("^ATX", "ATX (Vienna)"),
    ],
    "US": [
        ("^GSPC", "S&P 500"), ("^DJI", "Dow Jones"),
        ("^IXIC", "Nasdaq"), ("^RUT", "Russell 2000"),
    ],
    "Crypto": [
        ("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"),
        ("SOL-USD", "Solana"), ("BNB-USD", "BNB"),
    ],
    "Commodities": [
        ("GC=F", "Gold"), ("CL=F", "Crude Oil"),
        ("SI=F", "Silver"), ("NG=F", "Nat Gas"),
    ],
    "Currencies": [
        ("EURUSD=X", "EUR/USD"), ("GBPUSD=X", "GBP/USD"),
        ("EURGBP=X", "EUR/GBP"), ("USDJPY=X", "USD/JPY"),
    ],
}

# Representative real companies per research vertical (Yahoo news is
# per-company; there is no free topic search, so this is the honest proxy).
NEWS_THEMES = {
    "Data Centres & Cooling": {
        "note": "T-RES-23 — European data centres, incl. cooling infrastructure",
        "tickers": ["EQIX", "DLR", "VRT", "SU.PA", "NVT"],
    },
    "Energy & Battery Storage": {
        "note": "T-RES-2, T-RES-18, T-RES-11 — CEE energy market & battery recycling",
        "tickers": ["OMV.VI", "PGE.WA", "CEZ.PR", "UMI.BR"],
    },
    "Fintech & Digital Lending": {
        "note": "T-RES-3, T-RES-21 — Financial Services & Digital Lending for SMBs",
        "tickers": ["ADYEN.AS", "WISE.L", "OTP.BD", "XTB.WA"],
    },
}


def market_snapshot(group: str) -> list[dict]:
    """Live price + % change for one market group. Empty entries are skipped."""
    out = []
    for sym, label in MARKET_GROUPS.get(group, []):
        try:
            h = yf.Ticker(sym).history(period="5d")
            close = h["Close"].dropna()
            if len(close) < 2:
                continue
            last, prev = float(close.iloc[-1]), float(close.iloc[-2])
            out.append({"symbol": sym, "label": label, "price": last,
                       "chg_pct": (last / prev - 1) if prev else None})
        except Exception:
            continue
    return out


def cee_movers(tickers: list[str], top_n: int = 5) -> dict:
    """Today's best/worst movers among a ticker list (2-day close-to-close)."""
    if not tickers:
        return {"gainers": [], "losers": []}
    try:
        df = yf.download(tickers, period="5d", progress=False, group_by="ticker",
                         threads=True)
    except Exception:
        return {"gainers": [], "losers": []}
    moves = []
    for t in tickers:
        try:
            close = df[t]["Close"].dropna() if len(tickers) > 1 else df["Close"].dropna()
            if len(close) < 2:
                continue
            pct = float(close.iloc[-1]) / float(close.iloc[-2]) - 1
            moves.append({"ticker": t, "chg_pct": pct})
        except Exception:
            continue
    moves.sort(key=lambda x: x["chg_pct"], reverse=True)
    return {"gainers": moves[:top_n], "losers": moves[-top_n:][::-1] if moves else []}


def news_for_theme(theme: str, per_ticker: int = 3, total: int = 6) -> list[dict]:
    import news
    cfg = NEWS_THEMES.get(theme)
    if not cfg:
        return []
    return news.get_news(cfg["tickers"], per_ticker=per_ticker, total=total)


# --------------------------------------------------------------------------- #
# Rendering — self-contained HTML/CSS/JS, same pattern as build_dashboard.py.
# All data is fetched server-side and embedded; the JS below only switches
# between the pre-fetched market groups and expands/collapses sections.
# --------------------------------------------------------------------------- #
CSS = r"""
*{box-sizing:border-box}
body{margin:0}
.ihome{
  --paper:#f4f6f8;--card:#fff;--ink:#191d23;--muted:#5f6a76;--line:#e3e7eb;
  --line2:#d3d9df;--accent:#7d2b3a;--accent2:#7d2b3a;--pos:#2f7d55;--neg:#9c3a48;
  --track:#eceef1;--s-mid:#2f7d55;--s-lo:#9a6a15;
  --shadow:0 1px 2px rgba(20,30,45,.05),0 4px 14px rgba(20,30,45,.05);
  --serif:Calibri,Carlito,"Segoe UI",-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;
  --sans:Calibri,Carlito,"Segoe UI",-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"Cascadia Code","SF Mono",Menlo,Consolas,monospace;
  background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.5;padding:4px 2px 32px;
}
@media (prefers-color-scheme:dark){.ihome{
  --paper:#13171c;--card:#1b2027;--ink:#e7eaee;--muted:#98a2ae;--line:#2a313a;
  --line2:#39424d;--accent:#cf6478;--accent2:#e08596;--pos:#3f9d6c;--neg:#cf6478;
  --track:#252c34;--s-mid:#3f9d6c;--s-lo:#b8842a;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 18px rgba(0,0,0,.28);}}

.ihome .strip{display:flex;align-items:center;gap:14px;background:var(--card);
  border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin-bottom:16px;
  overflow-x:auto;box-shadow:var(--shadow)}
.ihome select{font-family:var(--sans);font-size:12.5px;background:transparent;
  color:var(--ink);border:1px solid var(--line2);border-radius:7px;padding:5px 8px;
  flex:none}
.ihome .tick{display:flex;flex-direction:column;gap:1px;flex:none;min-width:88px}
.ihome .tick .lb{font-size:10.5px;color:var(--muted);white-space:nowrap}
.ihome .tick .pv{font-family:var(--mono);font-size:13px;font-weight:600;white-space:nowrap}
.ihome .tick .pv .chg{font-size:11px;margin-left:5px}
.ihome .pos{color:var(--pos)}.ihome .neg{color:var(--neg)}

.ihome .grid{display:grid;grid-template-columns:1.7fr 1fr;gap:16px;align-items:start}
@media (max-width:820px){.ihome .grid{grid-template-columns:1fr}}
.ihome .col-main{display:flex;flex-direction:column;gap:16px}

.ihome .panel{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;box-shadow:var(--shadow)}
.ihome h2{font-family:var(--serif);font-size:16px;margin:0 0 4px}
.ihome .sub{font-size:11.5px;color:var(--muted);margin:0 0 12px}

.ihome .wcard{border:1px solid var(--line);border-radius:10px;padding:10px 12px;
  margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;gap:10px}
.ihome .wcard .nm{font-weight:600;font-size:13.5px}
.ihome .wcard .tk{font-family:var(--mono);font-size:11px;color:var(--muted)}
.ihome .chip{display:inline-block;padding:2px 8px;border-radius:6px;color:#fff;
  font-weight:700;font-family:var(--mono);font-size:12px}
.ihome .empty{font-size:13px;color:var(--muted);padding:8px 0}

.ihome .moverow{display:flex;justify-content:space-between;font-size:13px;padding:5px 0;
  border-bottom:1px solid var(--line)}
.ihome .moverow:last-child{border-bottom:none}
.ihome .moverow .tk{font-family:var(--mono)}

.ihome .newscols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px}
@media (max-width:900px){.ihome .newscols{grid-template-columns:1fr}}
.ihome .newscol h3{font-size:13.5px;margin:0 0 2px;font-family:var(--serif)}
.ihome .newscol .sub{margin-bottom:10px}
.ihome .hero-item{display:block;text-decoration:none;color:inherit;margin-bottom:12px}
.ihome .hero-item img{width:100%;height:110px;object-fit:cover;border-radius:8px;
  display:block;margin-bottom:7px;background:var(--track)}
.ihome .hero-item .title{font-weight:700;font-size:13.5px;color:var(--ink);line-height:1.3}
.ihome .hero-item:hover .title{color:var(--accent)}
.ihome .newsitem{margin-bottom:10px;font-size:12.5px;padding-top:9px;border-top:1px solid var(--line)}
.ihome .newsitem:first-of-type{border-top:none;padding-top:0}
.ihome .newsitem a{color:var(--ink);text-decoration:none;font-weight:600}
.ihome .newsitem a:hover{color:var(--accent)}
.ihome .newsitem .meta{font-size:11px;color:var(--muted);margin-top:2px}
"""

JS = r"""
(function(){
  var DATA = __HOME_DATA__;
  function fmt(v,d){return v==null?'n/a':Number(v).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});}
  function pct(v){return v==null?'':(v>=0?'+':'')+(v*100).toFixed(2)+'%';}
  function renderStrip(group){
    var el=document.getElementById('mkt-strip');
    var items=DATA.markets[group]||[];
    el.innerHTML=items.map(function(x){
      var cls=x.chg_pct==null?'':(x.chg_pct>=0?'pos':'neg');
      return '<div class="tick"><span class="lb">'+x.label+'</span>'+
        '<span class="pv">'+fmt(x.price,2)+'<span class="chg '+cls+'">'+pct(x.chg_pct)+'</span></span></div>';
    }).join('');
  }
  document.getElementById('mkt-select').addEventListener('change', function(e){
    renderStrip(e.target.value);
  });
  renderStrip('Europe');
})();
"""


def _fmt(v, d=2):
    return "n/a" if v is None else f"{v:,.{d}f}"


def _pct(v):
    if v is None:
        return ""
    return f"{'+' if v >= 0 else ''}{v * 100:.2f}%"


def _score_color(s):
    if s is None:
        return "var(--s-lo)"
    return "var(--s-mid)" if s >= 3.5 else "var(--s-lo)"


WATCHLIST_MAX = 4


def _watchlist_html(watch_rows: list[dict]) -> str:
    if not watch_rows:
        return '<div class="empty">Your watchlist is empty — add a ticker in the Watchlist tab and it will show up here.</div>'
    extra = len(watch_rows) - WATCHLIST_MAX
    out = []
    for r in watch_rows[:WATCHLIST_MAX]:
        ret = r.get("ret_pct")
        ret_html = (f'<span class="{"pos" if ret >= 0 else "neg"}">{_pct(ret)} since entry</span>'
                   if ret is not None else '<span class="tk">no entry price set</span>')
        out.append(
            f'<div class="wcard"><div><div class="nm">{r["name"]}</div>'
            f'<div class="tk">{r["ticker"]} · {r.get("control","")}</div></div>'
            f'<div style="text-align:right"><span class="chip" style="background:{_score_color(r.get("score"))}">{_fmt(r.get("score"),1)}</span><br>'
            f'<span style="font-family:var(--mono);font-size:12.5px">{_fmt(r.get("price"))}</span> {ret_html}</div></div>'
        )
    if extra > 0:
        out.append(f'<div class="empty">+{extra} more on your Watchlist tab</div>')
    return "".join(out)


def _fallback_picks_html(picks: list[dict]) -> str:
    if not picks:
        return '<div class="empty">No screener data yet — run the Screener tab first.</div>'
    out = ['<div class="empty" style="margin-bottom:8px">Nothing on your watchlist yet — here are today\'s top screener picks to consider adding:</div>']
    for r in picks[:WATCHLIST_MAX]:
        out.append(
            f'<div class="wcard"><div><div class="nm">{r["name"]}</div>'
            f'<div class="tk">{r["ticker"]}</div></div>'
            f'<span class="chip" style="background:{_score_color(r.get("score"))}">{_fmt(r.get("score"),1)}</span></div>'
        )
    return "".join(out)


def _movers_html(movers: dict) -> str:
    def row(m):
        cls = "pos" if m["chg_pct"] >= 0 else "neg"
        return f'<div class="moverow"><span class="tk">{m["ticker"]}</span><span class="{cls}">{_pct(m["chg_pct"])}</span></div>'
    g = "".join(row(m) for m in movers.get("gainers", [])) or '<div class="empty">n/a</div>'
    l = "".join(row(m) for m in movers.get("losers", [])) or '<div class="empty">n/a</div>'
    return (f'<div style="margin-bottom:14px"><div class="sub" style="margin-bottom:6px">Top gainers today</div>{g}</div>'
           f'<div><div class="sub" style="margin-bottom:6px">Top losers today</div>{l}</div>')


def _news_col_html(theme: str, items: list[dict]) -> str:
    note = NEWS_THEMES.get(theme, {}).get("note", "")
    if not items:
        body = '<div class="empty">No recent headlines found.</div>'
    else:
        # Prefer the most recent item that actually HAS an image for the hero
        # slot — not every article carries a thumbnail, so pinning to items[0]
        # meant the picture was often missing even when a later item had one.
        img_idx = next((i for i, it in enumerate(items) if it.get("image")), None)
        if img_idx is not None:
            head = items[img_idx]
            rest = items[:img_idx] + items[img_idx + 1:]
        else:
            head, rest = items[0], items[1:]
        rest = rest[:3]   # keep the column to 1 hero + 3 text rows, Yahoo-style
        if head.get("image"):
            body = (f'<a class="hero-item" href="{head["url"]}" target="_blank" rel="noopener">'
                    f'<img src="{head["image"]}" alt="" loading="lazy">'
                    f'<div class="title">{head["title"]}</div>'
                    f'<div class="meta">{head["date"]} · {head["ticker"]} · {head["publisher"]}</div></a>')
        else:
            body = (f'<div class="newsitem" style="border-top:none;padding-top:0">'
                    f'<a href="{head["url"]}" target="_blank" rel="noopener">{head["title"]}</a>'
                    f'<div class="meta">{head["date"]} · {head["ticker"]} · {head["publisher"]}</div></div>')
        body += "".join(
            f'<div class="newsitem">'
            f'<a href="{n["url"]}" target="_blank" rel="noopener">{n["title"]}</a>'
            f'<div class="meta">{n["date"]} · {n["ticker"]} · {n["publisher"]}</div></div>'
            for n in rest
        )
    return f'<div class="newscol"><h3>{theme}</h3><div class="sub">{note}</div>{body}</div>'


def render_home(markets: dict, watch_rows: list[dict], fallback_picks: list[dict],
                movers: dict, top_picks: list[dict], news_by_theme: dict) -> str:
    import json as _json
    hero = (_watchlist_html(watch_rows) if watch_rows
           else _fallback_picks_html(fallback_picks))
    top_picks_html = "".join(
        f'<div class="wcard"><div><div class="nm">{p["name"][:26]}</div>'
        f'<div class="tk">{p["ticker"]}</div></div>'
        f'<span class="chip" style="background:{_score_color(p.get("score"))}">{_fmt(p.get("score"),1)}</span></div>'
        for p in top_picks
    ) or '<div class="empty">Run the Screener tab first.</div>'

    news_html = "".join(_news_col_html(t, news_by_theme.get(t, [])) for t in NEWS_THEMES)

    data_json = _json.dumps({"markets": markets}, ensure_ascii=False)
    js = JS.replace("__HOME_DATA__", data_json)

    return f"""<meta charset="utf-8">
<style>{CSS}</style>
<div class="ihome">
  <div class="strip">
    <select id="mkt-select">
      <option>Europe</option><option>US</option><option>Crypto</option>
      <option>Commodities</option><option>Currencies</option>
    </select>
    <div id="mkt-strip" style="display:flex;gap:16px;overflow-x:auto"></div>
  </div>

  <div class="grid">
    <div class="col-main">
      <div class="panel">
        <h2>Your Watchlist</h2>
        <div class="sub">Whatever you add in the Watchlist tab appears here first (max {WATCHLIST_MAX} shown).</div>
        {hero}
      </div>
      <div class="panel">
        <h2>Research-vertical news</h2>
        <div class="sub">Themed to Innimmo's active research verticals (Workstream 2, 2026
          intern plan) — Yahoo news is per-company, not per-topic, so each column uses real
          headlines from representative companies in that space.</div>
        <div class="newscols">{news_html}</div>
      </div>
    </div>
    <div class="panel">
      <h2>CEE movers &amp; top picks</h2>
      <div class="sub">From today's universe — not investment advice.</div>
      {_movers_html(movers)}
      <div class="sub" style="margin-top:14px;margin-bottom:6px">Top screener picks</div>
      {top_picks_html}
    </div>
  </div>
</div>
<script>{js}</script>"""

