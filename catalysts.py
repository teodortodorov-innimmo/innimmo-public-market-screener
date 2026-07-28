"""
Catalyst calendar for the Innimmo screener.

Three tiers, clearly separated by how trustworthy they are:

  REAL, per-company (from Yahoo, populated in the screener):
      - next earnings date
      - ex-dividend date, dividend payment date

  REAL, market-wide (fixed published schedules, computed here):
      - next MSCI / FTSE Russell / STOXX index-review windows

  EDITORIAL, approximate (hand-maintained here — NOT precise):
      - AGM season by country

IMPORTANT: exact AGM dates and shareholder-proposal deadlines are NOT available
from a free feed, so we do NOT invent them. `agm_season()` returns only a rough
window and must be verified against each company's investor-relations calendar.
"""
from datetime import date

# Index-review months (representative). MSCI: Feb/May/Aug/Nov (semi-annual +
# quarterly); FTSE Russell & STOXX: Mar/Jun/Sep/Dec.
_FAMILIES = [
    ("MSCI review", [2, 5, 8, 11]),
    ("FTSE Russell review", [3, 6, 9, 12]),
    ("STOXX review", [3, 6, 9, 12]),
]

_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_AGM = {
    "Poland":   "AGM season typically May–June",
    "Austria":  "AGM season typically April–May",
    "Czechia":  "AGM season typically April–June",
    "Hungary":  "AGM season typically April",
    "Slovenia": "AGM season typically May–June",
    "Romania":  "AGM season typically April",
    "Greece":   "AGM season typically June–July",
}


def _next_review_month(today: date, months):
    """Next review (month, year); roll over if we're past ~20th of that month."""
    for m in sorted(months):
        if m > today.month or (m == today.month and today.day < 20):
            return m, today.year
    return min(months), today.year + 1


def next_index_reviews(today: date):
    """Return [{'name','when'}] of the next review window per index family."""
    out = []
    for name, months in _FAMILIES:
        m, y = _next_review_month(today, months)
        out.append({"name": name, "when": f"{_MONTHS[m]} {y}"})
    return out


def agm_season(country: str) -> str:
    return _AGM.get(country, "AGM season varies — verify with the company")
