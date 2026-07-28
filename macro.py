"""
Macro overlay for the Innimmo screener.

IMPORTANT: this is a hand-maintained EDITORIAL overlay, not a live data feed.
It gives the screener a short, human-written line of country / sector context
so the AI thesis is grounded in the operating backdrop. Review and refresh it
periodically (last review: 2026-07). It must not be read as current market data.
"""

# Country-level backdrop (structural, slow-moving).
_COUNTRY = {
    "Poland": "Poland — large, resilient domestic economy; NBP policy rate "
              "elevated but easing; PLN broadly stable; State Treasury holds "
              "stakes in several large caps, which can both cap and catalyse "
              "activist change.",
    "Austria": "Austria — open, export-tilted economy with heavy CEE and "
               "German linkage; ECB policy applies; banks and industrials "
               "carry meaningful Central/Eastern European exposure.",
    "Czechia": "Czechia — stable, industry- and export-heavy economy; CNB "
               "among the more hawkish CEE central banks; CZK firm; strong "
               "auto-supply-chain and utility linkage to Germany.",
    "Hungary": "Hungary — higher-beta CEE market; historically elevated "
               "inflation and rates with a more volatile HUF; notable state "
               "influence and sector-specific windfall taxes to watch.",
    "Slovenia": "Slovenia — small, euro-zone economy; shallower equity market "
                "liquidity; pharma and insurance are the export-quality names.",
}

# Sector-level cycle note (kept short and generic).
_SECTOR = {
    "Financial Services": "Banks/insurers: rate cycle and regulatory capital "
                          "rules drive earnings and how fast capital can be returned.",
    "Energy": "Energy: earnings swing with commodity prices; transition capex "
              "and any windfall levies weigh on free cash flow.",
    "Utilities": "Utilities: regulated returns plus large decarbonisation "
                 "capex; policy and tariff design dominate the story.",
    "Basic Materials": "Materials: deeply cyclical; margins track global "
                       "commodity prices and energy input costs.",
    "Consumer Cyclical": "Consumer cyclical: sensitive to real wages and "
                         "domestic demand; watch inventory and FX on sourcing.",
    "Healthcare": "Healthcare/pharma: defensive demand; pricing pressure and "
                  "export-market concentration are the key swing factors.",
    "Communication Services": "Telecom/media: cash-generative but capex-heavy; "
                              "regulation and competitive intensity cap growth.",
    "Industrials": "Industrials: order-book and PMI driven; leveraged to the "
                   "German/EU manufacturing cycle.",
}


def macro_note(country: str, sector: str) -> str:
    parts = []
    if country in _COUNTRY:
        parts.append(_COUNTRY[country])
    if sector in _SECTOR:
        parts.append(_SECTOR[sector])
    if not parts:
        return ("CEE/European backdrop — editorial overlay; refresh before "
                "relying on it. (No specific note on file for this "
                "country/sector.)")
    return " ".join(parts)
