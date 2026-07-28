#!/usr/bin/env python3
"""
Streamlit Cloud entry point for the Innimmo Activist Screener (T-AI-10).

Runs the existing screener pipeline (activist_screener.main) and embeds the
existing dashboard.html output — no scoring/rendering logic is duplicated here.
"""

import os
import time

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Innimmo Activist Screener", layout="wide")

# Streamlit Cloud secrets -> env var the existing pipeline already reads.
# st.secrets raises if no secrets file exists at all (e.g. running locally),
# in which case the screener falls back to rule-based theses.
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

REFRESH_SECONDS = 6 * 60 * 60  # re-fetch Yahoo data at most every 6 hours


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def run_screen(_cache_bust: int) -> str:
    import activist_screener
    activist_screener.main()
    with open("dashboard.html", encoding="utf-8") as fh:
        return fh.read()


with st.sidebar:
    st.markdown("### Innimmo Activist Screener")
    st.caption("Live CEE/European activist screen — internal research tool, not investment advice.")
    if st.button("Refresh data now"):
        run_screen.clear()
    st.caption(f"Data auto-refreshes every {REFRESH_SECONDS // 3600}h.")

with st.spinner("Fetching live data and scoring the universe — first load takes ~1-2 min..."):
    html = run_screen(int(time.time() // REFRESH_SECONDS))

# Rows expand on click, so the content height is dynamic — a generous fixed
# height with internal scrolling is the only workable option for st.components.
components.html(html, height=3600, scrolling=True)
