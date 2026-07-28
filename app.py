#!/usr/bin/env python3
"""
Streamlit Cloud entry point for the Innimmo Activist Screener (T-AI-10).

Runs the existing screener pipeline (activist_screener.main) and embeds the
existing dashboard.html output — no scoring/rendering logic is duplicated here.
"""

import os
import time

import streamlit as st

st.set_page_config(page_title="Innimmo Activist Screener", layout="wide")


# --------------------------------------------------------------------------- #
# Password gate. The repo is public, so anyone with the URL can reach this
# app — the password is what keeps the actual watchlist/scores private.
# Set APP_PASSWORD in Streamlit Cloud -> App settings -> Secrets. Never commit
# a real password to the repo; there is no hardcoded fallback on purpose.
# --------------------------------------------------------------------------- #
def _check_password() -> bool:
    try:
        real_password = st.secrets["APP_PASSWORD"]
    except Exception:
        st.error(
            "APP_PASSWORD is not set. Add it under App settings → Secrets "
            "in Streamlit Cloud before sharing this app's URL."
        )
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
# height with internal scrolling is the only workable option here.
st.iframe(html, height=3600)
