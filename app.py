#!/usr/bin/env python3
"""
Streamlit app for the Innimmo Activist Screener (T-AI-10).

Tabs:
  - Home       : personal front page — your watchlist, EU/US/Crypto/Commodities/
                 Currencies market strip, CEE movers, and research-vertical news
  - Screener   : the full CEE/European six-factor watchlist (cached, ~6h),
                 with a quick ticker-lookup box at the top
  - Discover   : find NEW local companies via Yahoo's free screener
  - Watchlist  : track names with an optional entry price
  - News       : recent Yahoo headlines for your watchlist

Reuses the existing pipeline in activist_screener.py — no scoring/rendering
logic is duplicated here. Internal research tool, NOT investment advice.
"""
import os
import time

import streamlit as st
import streamlit.components.v1 as components

import activist_screener as s

st.set_page_config(page_title="Innimmo Activist Screener", layout="wide")

# Streamlit reserves a large default top margin above the page content. On
# Streamlit Community Cloud there is an additional floating viewer toolbar
# (Share/star/edit/GitHub icons) stacked on top of the normal header, so trimming
# too far makes the tabs overlap that toolbar instead of sitting below it. 3.5rem
# clears both while still cutting most of the default blank gap.
st.markdown(
    "<style>.block-container{padding-top:3.5rem;padding-bottom:1rem}</style>",
    unsafe_allow_html=True,
)

# App-wide font. Calibri is a Microsoft-licensed font (can't be bundled/embedded
# legally), so it's the preferred choice with graceful fallbacks: Carlito is a
# free, metric-compatible lookalike; then Segoe UI / system sans-serif. On
# Windows/Office machines this renders as true Calibri; elsewhere it falls back.
st.markdown(
    "<style>html, body, [class*='st-'], [class*='css-'] {"
    "font-family: Calibri, Carlito, 'Segoe UI', -apple-system, "
    "BlinkMacSystemFont, Helvetica, Arial, sans-serif !important;}</style>",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Password gate. The repo is public, so the password is what keeps the actual
# watchlist private. Set APP_PASSWORD in Streamlit Cloud → App settings → Secrets.
# --------------------------------------------------------------------------- #
def _check_password() -> bool:
    try:
        real_password = st.secrets["APP_PASSWORD"]
    except Exception:
        st.error("APP_PASSWORD is not set. Add it under App settings → Secrets "
                 "in Streamlit Cloud before sharing this app's URL.")
        st.stop()

    def _submit():
        if st.session_state.get("pw_input") == real_password:
            st.session_state["authed"] = True
            del st.session_state["pw_input"]
        else:
            st.session_state["authed"] = False

    if st.session_state.get("authed"):
        return True
    st.text_input("Password", type="password", key="pw_input", on_change=_submit)
    if st.session_state.get("authed") is False:
        st.error("Incorrect password.")
    return False


if not _check_password():
    st.stop()

# Wire the Streamlit secret into the env var the pipeline already reads.
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

REFRESH_SECONDS = 6 * 60 * 60


def _embed(html: str, height: int = 3200):
    """Embed a self-contained dashboard HTML string in the page."""
    components.html(html, height=height, scrolling=True)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Cached workers
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def run_full_screen(_bust: int) -> str:
    s.main()
    return _read("dashboard.html")


@st.cache_data(ttl=60 * 60, show_spinner=False)
def analyze_one(ticker: str) -> tuple:
    from build_dashboard import build_dashboard
    peers = _load_universe_peers()
    co = s.analyze_ticker(ticker, peers=peers)
    if co is None:
        return None, None
    base = "analysis_" + ticker.replace(".", "_")
    s.write_json([co], base + ".json")
    build_dashboard(base + ".json", base + ".html")
    return _read(base + ".html"), co.score


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def discover_screen(regions: tuple, per_region: int) -> tuple:
    from build_dashboard import build_dashboard
    import discover
    candidates = discover.discover_tickers(list(regions), per_region=per_region,
                                            exclude=s.TICKERS)
    companies = s.run_pipeline(candidates, do_history=False)
    allowed = discover._allowed_countries(list(regions))
    companies = [c for c in companies if c.country in allowed]
    passed = sorted((c for c in companies if c.score >= s.SCORE_THRESHOLD),
                    key=lambda c: c.score, reverse=True)
    s.write_thesis(passed)
    s.write_json(passed, "innimmo_discovered_data.json")
    build_dashboard("innimmo_discovered_data.json", "dashboard_discovered.html")
    return _read("dashboard_discovered.html"), len(passed), len(companies)


def _load_universe_peers():
    """Rebuild peer Company objects from the last full run, if present."""
    import json
    from dataclasses import fields
    path = "innimmo_universe_data.json"
    if not os.path.exists(path):
        return []
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    valid = {f.name for f in fields(s.Company)}
    return [s.Company(**{k: v for k, v in d.items() if k in valid}) for d in data]


@st.cache_data(ttl=60 * 60, show_spinner=False)
def watch_metrics(ticker: str):
    """Small live snapshot for one watchlist name."""
    co = s.analyze_ticker(ticker, peers=_load_universe_peers())
    if co is None:
        return None
    return {"name": co.name, "score": co.score, "control": co.control_label,
            "price": co.price, "currency": co.currency, "trend": co.trend,
            "confidence": co.confidence_label, "flags": co.flags}


@st.cache_data(ttl=30 * 60, show_spinner=False)
def news_for(tickers: tuple):
    import news
    return news.get_news(list(tickers))


@st.cache_data(ttl=15 * 60, show_spinner=False)
def home_markets():
    import home
    return {g: home.market_snapshot(g) for g in home.MARKET_GROUPS}


@st.cache_data(ttl=60 * 60, show_spinner=False)
def home_movers_and_picks():
    """Movers use the full fetched universe if a prior full run left one;
    top picks come from the passing watchlist."""
    import json
    picks = []
    if os.path.exists("innimmo_watchlist_data.json"):
        try:
            picks = json.load(open("innimmo_watchlist_data.json", encoding="utf-8"))
        except Exception:
            picks = []
    uni_path = ("innimmo_universe_data.json" if os.path.exists("innimmo_universe_data.json")
               else "innimmo_watchlist_data.json")
    uni = []
    if os.path.exists(uni_path):
        try:
            uni = json.load(open(uni_path, encoding="utf-8"))
        except Exception:
            uni = []
    import home
    # Resolve the function defensively: a hot-reloaded app.py can still be paired
    # with a stale cached `home` module, where only the old name exists.
    movers_fn = getattr(home, "movers", None) or getattr(home, "cee_movers")
    movers = movers_fn([c["ticker"] for c in uni], top_n=5)
    top_picks = sorted(picks, key=lambda c: c["score"], reverse=True)[:5]
    return movers, top_picks


@st.cache_data(ttl=30 * 60, show_spinner=False)
def home_research_news():
    import home
    # Fetch a larger pool than we display so there's a good chance at least one
    # item per theme has a thumbnail image (not every article carries one).
    return {t: home.news_for_theme(t, per_ticker=4, total=10) for t in home.NEWS_THEMES}


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### Innimmo Activist Screener")
    st.caption("Live CEE/European activist screen — internal research tool, "
               "not investment advice.")
    if st.button("Refresh screener data now"):
        run_full_screen.clear()
    st.caption(f"Screener auto-refreshes every {REFRESH_SECONDS // 3600}h.")
    if not (st.secrets.get("ANTHROPIC_API_KEY") if hasattr(st, "secrets") else None):
        st.caption("No AI key set → theses are rule-based summaries.")

tab_home, tab_screen, tab_discover, tab_watch, tab_news = st.tabs(
    ["🏠 Home", "📊 Screener", "🧭 Discover", "⭐ Watchlist", "📰 News"])

with tab_home:
    import home
    import watchlist as wl

    with st.spinner("Loading your home page..."):
        markets = home_markets()
        movers, top_picks = home_movers_and_picks()
        news_by_theme = home_research_news()

        watch_items = wl.load()
        watch_rows = []
        for it in watch_items:
            m = watch_metrics(it["ticker"])
            if m is None:
                continue
            ret = None
            if it.get("entry_price") and m.get("price"):
                ret = m["price"] / it["entry_price"] - 1
            watch_rows.append({"ticker": it["ticker"], "name": m["name"],
                               "score": m["score"], "control": m["control"],
                               "price": m["price"], "ret_pct": ret})

        html = home.render_home(markets, watch_rows, top_picks, movers,
                                top_picks, news_by_theme)

    # A company card on the Home page is an <a href="?analyze=TICKER">. The page
    # is inside a sandboxed iframe and cannot call back into Streamlit directly,
    # so the click navigates the top-level app with a query param, which we read
    # here. Some sandboxes block target="_top", so the buttons below are a
    # guaranteed second path to the same handler.
    _requested = st.query_params.get("analyze")
    if _requested:
        st.session_state["home_analyze"] = _requested.strip().upper()
        st.query_params.clear()   # keep the URL clean; state carries the choice

    _cards = watch_rows or top_picks
    if _cards:
        st.caption("Open a company's full analysis — click its card below, or use these:")
        _btn_cols = st.columns(min(len(_cards), home.WATCHLIST_MAX))
        for _col, _row in zip(_btn_cols, _cards[:home.WATCHLIST_MAX]):
            if _col.button(_row["ticker"], key=f"home_open_{_row['ticker']}",
                           use_container_width=True):
                st.session_state["home_analyze"] = _row["ticker"]

    _selected = st.session_state.get("home_analyze")
    if _selected:
        _c1, _c2 = st.columns([5, 1])
        _c1.markdown(f"#### Analysis — {_selected}")
        if _c2.button("Close", key="home_close_analysis", use_container_width=True):
            del st.session_state["home_analyze"]
            st.rerun()
        with st.spinner(f"Analysing {_selected}..."):
            _ahtml, _ = analyze_one(_selected)
        if _ahtml is None:
            st.error(f"Could not fetch {_selected} from Yahoo Finance — check the symbol.")
        else:
            _embed(_ahtml, height=1500)
        st.markdown("---")

    components.html(html, height=2000, scrolling=True)

with tab_screen:
    st.markdown("#### Quick ticker lookup")
    st.caption("Jump to any Yahoo ticker, e.g. `KGH.WA` (Warsaw), `EBS.VI` "
               "(Vienna), `SNN.RO` (Bucharest) — works for any listed company, "
               "even outside the standard universe below.")
    lookup = st.text_input("Ticker", value="", placeholder="KGH.WA",
                           key="screener_lookup").strip().upper()
    if lookup:
        with st.spinner(f"Analysing {lookup}..."):
            lhtml, _ = analyze_one(lookup)
        if lhtml is None:
            st.error(f"Could not fetch {lookup} from Yahoo Finance — check the symbol.")
        else:
            _embed(lhtml, height=1500)
        st.markdown("---")

    st.markdown("#### Full watchlist screen")
    with st.spinner("Fetching live data and scoring the universe — first load ~1-2 min..."):
        html = run_full_screen(int(time.time() // REFRESH_SECONDS))
    _embed(html, height=3400)

with tab_discover:
    st.markdown("#### Discover new local companies")
    st.caption("Pulls the universe from Yahoo's free screener, drops foreign "
               "cross-listings, and scores newcomers. Coverage of small markets "
               "is best-effort; discovered names have no curated ownership yet.")
    _market_labels = {
        "pl": "Poland", "at": "Austria", "cz": "Czechia", "hu": "Hungary",
        "ro": "Romania", "gr": "Greece", "de": "Germany", "fr": "France",
        "it": "Italy", "es": "Spain", "nl": "Netherlands", "be": "Belgium",
        "pt": "Portugal", "se": "Sweden", "dk": "Denmark", "fi": "Finland",
        "gb": "United Kingdom", "ie": "Ireland",
    }
    regions = st.multiselect(
        "Markets", options=list(_market_labels), default=["pl", "ro"],
        format_func=lambda c: _market_labels[c])
    per_region = st.slider("Candidates per market", 5, 40, 15)
    if st.button("Run discovery") and regions:
        with st.spinner("Discovering and scoring — this can take a few minutes..."):
            html, n_pass, n_total = discover_screen(tuple(regions), per_region)
        st.success(f"{n_pass} of {n_total} discovered names scored ≥ {s.SCORE_THRESHOLD}.")
        _embed(html, height=2600)

with tab_watch:
    import watchlist as wl
    st.markdown("#### Your watchlist / portfolio")
    st.caption("Track names with an optional entry price to see live score and "
               "return-since-entry. Stored in a local file — on Streamlit Cloud "
               "this resets on restart (use a database for permanent storage).")

    with st.form("add_wl", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 3])
        wt = c1.text_input("Ticker", placeholder="KGH.WA")
        wp = c2.number_input("Entry price (optional)", min_value=0.0, value=0.0, step=0.01)
        wn = c3.text_input("Note (optional)")
        if st.form_submit_button("Add / update") and wt.strip():
            wl.add(wt, entry_price=(wp or None), note=wn)
            st.rerun()

    items = wl.load()
    if not items:
        st.info("Watchlist is empty — add a ticker above.")
    else:
        rows = []
        for it in items:
            m = watch_metrics(it["ticker"])
            ret = None
            if m and it.get("entry_price") and m["price"]:
                ret = m["price"] / it["entry_price"] - 1
            rows.append({
                "Ticker": it["ticker"],
                "Name": (m["name"][:26] if m else "—"),
                "Score": (m["score"] if m else "—"),
                "Control": (m["control"] if m else "—"),
                "Price": (round(m["price"], 2) if m and m["price"] else "—"),
                "Entry": it.get("entry_price") or "—",
                "Return": (f"{ret * 100:+.1f}%" if ret is not None else "—"),
                "Trend": (m["trend"] if m else "—"),
                "Note": it.get("note", ""),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
        rem = st.selectbox("Remove a name", [""] + [i["ticker"] for i in items])
        if rem and st.button("Remove selected"):
            wl.remove(rem)
            st.rerun()

with tab_news:
    import json
    import watchlist as wl
    st.markdown("#### News")
    st.caption("Recent Yahoo headlines for your watchlist (or the top screener "
               "names if it's empty). Coverage of small CEE names is thin, and "
               "some items only *mention* the company — read the source.")

    tickers = [i["ticker"] for i in wl.load()]
    if not tickers and os.path.exists("innimmo_watchlist_data.json"):
        try:
            d = json.load(open("innimmo_watchlist_data.json", encoding="utf-8"))
            tickers = [c["ticker"] for c in d[:6]]
        except Exception:
            tickers = []
    if not tickers:
        st.info("No tickers yet — add names to your watchlist or run the screener.")
    else:
        with st.spinner("Fetching headlines..."):
            items = news_for(tuple(tickers))
        if not items:
            st.info("No headlines found (Yahoo coverage may be thin for these names).")
        for n in items:
            st.markdown(f"**[{n['title']}]({n['url']})**" if n["url"]
                        else f"**{n['title']}**")
            st.caption(f"{n['date']} · {n['ticker']} · {n['publisher']}")
