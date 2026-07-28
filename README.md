# Innimmo Public Markets Activist Screener (T-AI-10)

Methodology & User Guide — **v4**

**New in v4:** data-**confidence** score, **liquidity** (avg daily value + days to
build a 5% stake), **peer-implied fair value / upside %**, **ownership
verified-dates** with staleness flags, a **rule-based auto-thesis** when no API
key is set, a wider **46-name** universe (adds Bucharest & Athens), and a
**technical-score backtest** (`backtest.py`).

Pulls **live** data for a universe of CEE / European listings from Yahoo Finance,
scores each name for activist attractiveness across **six dimensions**, reads the
**price chart** technically (with volume), checks whether an activist could
realistically **act** on the name, normalises sizes to **EUR**, tracks scores
**run-over-run**, and (with an API key) asks Claude for an activist thesis.

> **Disclaimer.** Internal **research-support** tool. Metrics are as-reported by
> Yahoo Finance and unaudited; theses are AI-generated drafts; the ownership and
> macro overlays are hand-written editorial context, **not** live feeds. Nothing
> here is investment advice or a recommendation to transact.

---

## Outputs

| File | Contents |
|---|---|
| `innimmo_activist_watchlist.csv` | Flat export — one row per passing name |
| `innimmo_watchlist_data.json` | Rich data — every field + price/volume series |
| `score_history.json` | One record per run, for Δ-vs-last-run tracking |
| `dashboard.html` | Self-contained interactive dashboard (open in any browser) |

---

## The six scoring dimensions

Each is scored **1–5**. The **overall score** is a weighted blend; dimensions
with no data drop out and the weights renormalise. Names scoring **≥ 3.0**
overall make the watchlist.

| Dimension | Weight | Built from |
|---|---|---|
| **Value** | 25% | P/B, P/E, P/S, EV/EBITDA, FCF yield — **blended with a sector-relative (peer) read** |
| **Quality** | 15% | ROE, operating margin, net margin |
| **Balance sheet** | 10% | Net cash / cap, Debt/Equity, current ratio *(skipped for financials)* |
| **Growth** | 10% | Revenue growth, earnings growth |
| **Technical** | 20% | The chart — trend, support/resistance, **volume-confirmed** breakouts, RSI |
| **Actionability** | 20% | **Can an activist actually act?** Ownership / control (see below) |

### Actionability — the activist reality check

An activist has to buy a stake and push for change. That only works if the
company is **not majority-controlled** by the state, a foreign parent, or a
family. `ownership.py` holds a **hand-maintained** control map (state / parent /
family / anchor / widely-held) scored 1–5; state-majority names score ~1
(activism blocked), widely-held names score ~5. Heavy insider ownership from
Yahoo further caps the score. Controlled names are also **flagged** on the
dashboard.

*Effect:* state-controlled names (e.g. PGE, Orlen, ČEZ, Verbund) are demoted;
widely-held quality names (e.g. OTP, BAWAG) rise to the top. This map is
editorial and **approximate — verify before relying on it** (last review 2026-07).

### Technical (the chart) — now with volume

Computed from one year of daily prices: trend (50/200-day MAs), prior-swing
support & resistance, breakout/breakdown, and RSI(14). **Breakouts are
confirmed by volume** — a breakout on above-average volume scores higher than one
on soft volume. The dashboard **draws the chart** (price, both MAs,
support/resistance lines, volume bars) so a human can judge it too.

### Sector-relative valuation

Absolute multiples can mislead across sectors, so Value also blends a
**peer read**: each name's P/B, P/E and EV/EBITDA are compared to the **median of
its sector** across the fetched universe (needs ≥3 peers, else skipped).

---

## Other features

- **EUR-normalised market caps** — sizes are comparable across PLN/HUF/CZK/RON/EUR
  (live FX with a hardcoded fallback if the FX fetch fails).
- **Data-confidence score** — each name gets a High/Medium/Low confidence from how
  complete its data is; thin names (e.g. missing fundamentals) are flagged so a
  score built on partial data isn't mistaken for a solid one.
- **Liquidity / tradability** — average daily traded value in EUR and an estimate
  of **how many sessions it would take to build a 5% stake** (assuming ~20% of
  daily volume); illiquid names are flagged.
- **Peer-implied fair value** — each name valued at its sector's median multiple
  to give an **upside/downside %**. Crude (quality names may deserve a premium) —
  a sanity check, not a target price.
- **Ownership verified-dates** — `ownership.py` carries a `LAST_VERIFIED` date;
  names are flagged if the map is older than 180 days at run time.
- **Rule-based auto-thesis** — with no `ANTHROPIC_API_KEY`, each passing name gets
  a deterministic summary composed from its metrics (so the dashboard is always
  populated); with a key, Claude writes the full thesis instead.
- **Data-sanity flags** — dividend yield > 15%, negative P/E, extreme ROE, sparse
  data, controlled ownership, illiquidity, stale ownership.
- **Run tracking** — each run appends to `score_history.json`; the dashboard shows
  **Δ vs the previous run**.
- **Macro overlay** — `macro.py`, editorial country/sector backdrop (not live).
- **Diversification / concentration** — a top-of-dashboard view of how the
  watchlist splits by sector and country, with a concentration verdict
  (Herfindahl-based) that warns when the list is really one bet (e.g. "54% are
  financials").
- **Catalyst calendar** — per name: next **earnings**, **ex-dividend** and
  **dividend-payment** dates (from Yahoo). Market-wide: next **MSCI / FTSE /
  STOXX index-review** windows (computed from their fixed schedules — potential
  passive-flow catalysts). Plus an **editorial AGM-season** hint per country.
  *Note: exact AGM dates and shareholder-proposal deadlines are not available
  from a free feed, so those are approximate and flagged "verify" — not invented.*

## Data validation (`validate.py`)

```bash
python validate.py         # validates the current watchlist
python validate.py 10      # top 10 names only
```

Tells you **how much to trust the inputs** before acting. Two kinds of check per
name: (A) internal consistency of Yahoo's summary fields (market cap = price ×
shares; P/B = price ÷ book; P/E = price ÷ EPS; dividend yield vs rate ÷ price),
and (B) summary ratios vs figures recomputed from Yahoo's **balance sheet /
income statement** (a different endpoint) — book value, net debt, ROE.
Mismatches beyond tolerance are listed as "verify against filings before acting",
and a pass-rate is reported. Results saved to `validate_result.json`.

The net-debt check is **skipped for financials** (meaningless there, already
excluded from scoring). **Honest scope:** this checks Yahoo against itself and
against arithmetic — it is not an independent third-party audit; filings or a
paid feed remain the gold standard. Latest run: **96% pass**, with a handful of
fields flagged (e.g. an ROE and a book-value discrepancy) to verify by hand.

## Backtest (validation)

```bash
python backtest.py     # -> prints a report, writes backtest_result.json
```

Because Yahoo only gives point-in-time fundamentals, only the **technical** score
can be backtested (it's a pure function of price history). `backtest.py` computes
it as of ~1 year ago and measures the realised forward return, bucketed by score.
It is a single-period, price-only, small-sample check — **indicative, not proof**.
A positive result means higher technical scores tended to precede better returns;
the value/quality/ownership dimensions remain unvalidated without a historical
fundamentals feed.

---

## Setup & run

```bash
pip install -r requirements.txt

# Optional — enables AI theses (screen + charts run without it):
setx ANTHROPIC_API_KEY sk-ant-...     # Windows; reopen the shell afterwards

python activist_screener.py
```

Then open **`dashboard.html`** (or double-click **`start.bat`**, which refreshes
the data and opens the dashboard in one step). Click any row to expand its price
chart, six-factor scorecard, full ratios, ownership read, flags, and thesis.

**Rebuild only the dashboard** (no re-fetch):

```bash
python build_dashboard.py                         # -> dashboard.html
python build_dashboard.py data.json out.html --fragment   # body-only (embedding)
```

**Run the tests:**

```bash
python test_screener.py     # exits non-zero on any failure
```

---

## Configuration

Top of `activist_screener.py`: `CLAUDE_MODEL` (default `claude-sonnet-5`),
`SCORE_THRESHOLD` (`3.0`), `DIMENSION_WEIGHTS`, `FX_FALLBACK`, `TICKERS`.
Ownership map: `ownership.py`. Macro map: `macro.py`.

> **Model note.** The spec named "Claude 3.5 Sonnet", which is retired and 404s;
> the tool targets the current `claude-sonnet-5`.

---

## Known limitations / next steps

- **Yahoo data is unaudited** and occasionally sparse/quirky (flags surface the
  worst cases). A paid feed (Refinitiv/Bloomberg) is the production path.
- **Ownership & macro are hand-maintained** — a live cap-table / macro feed would
  make them dynamic. Verify ownership before acting.
- **No auto-email / scheduling yet** — `start.bat` is manual; a scheduled task
  and email digest need your mail credentials.
- **AI theses need a key** — without `ANTHROPIC_API_KEY` the thesis field is a
  placeholder (the rest of the pipeline still runs).
- Technicals use **daily** data over one year (no intraday / multi-year swings).
