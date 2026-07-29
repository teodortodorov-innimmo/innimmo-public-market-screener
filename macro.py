"""
Macro overlay for the Innimmo screener.

IMPORTANT: this is a hand-maintained EDITORIAL overlay, not a live data feed.
It gives the screener a short, human-written line of country / sector context
so the AI thesis is grounded in the operating backdrop. Review and refresh it
periodically (last review: 2026-07). It must not be read as current market data.

NOTE ON KEYS: these must match the country string Yahoo actually returns, which
is not always the modern short name — e.g. Yahoo says "Czech Republic", not
"Czechia". Aliases are included where the two differ.
"""

# Country-level backdrop (structural, slow-moving).
_COUNTRY = {
    # --- CEE ---
    "Poland": "Poland — large, resilient domestic economy; NBP policy rate "
              "elevated but easing; PLN broadly stable; State Treasury holds "
              "stakes in several large caps, which can both cap and catalyse "
              "activist change.",
    "Austria": "Austria — open, export-tilted economy with heavy CEE and "
               "German linkage; ECB policy applies; banks and industrials "
               "carry meaningful Central/Eastern European exposure.",
    "Czech Republic": "Czechia — stable, industry- and export-heavy economy; CNB "
                      "among the more hawkish CEE central banks; CZK firm; strong "
                      "auto-supply-chain and utility linkage to Germany.",
    "Hungary": "Hungary — higher-beta CEE market; historically elevated "
               "inflation and rates with a more volatile HUF; notable state "
               "influence and sector-specific windfall taxes to watch.",
    "Slovenia": "Slovenia — small, euro-zone economy; shallower equity market "
                "liquidity; pharma and insurance are the export-quality names.",
    "Romania": "Romania — fast-growing but twin-deficit economy; RON managed "
               "against the euro; heavy state ownership across energy and "
               "utilities, which limits outside influence on strategy.",
    "Greece": "Greece — post-crisis recovery story; banks recapitalised and "
              "largely re-privatised (HFSF sell-downs), leaving genuinely "
              "wider free floats; sovereign risk premium compressed but present.",
    # --- Western / Northern Europe ---
    "Germany": "Germany — Europe's largest economy, currently in an industrial "
               "soft patch; energy costs and China demand are the swing factors; "
               "co-determination and family/foundation blocks are common.",
    "France": "France — large domestic market with an interventionist state; "
              "founding families hold controlling blocks in several CAC 40 names, "
              "and the state retains golden-share style influence in strategics.",
    "Italy": "Italy — high public debt and modest growth; the state (via MEF/CDP) "
             "is the anchor shareholder in energy and telecom; strong export-led "
             "industrial and luxury niches.",
    "Spain": "Spain — above-EU-average growth led by services and tourism; "
             "SEPI (state holding) retains stakes in strategics; banks are "
             "geared to Latin American as well as domestic cycles.",
    "Netherlands": "Netherlands — small, highly open economy and a common "
                   "incorporation domicile (several 'French'/'Italian' listings "
                   "are Dutch-incorporated); strong governance standards.",
    "Belgium": "Belgium — open economy with concentrated family and cooperative "
               "reference shareholders; shallower mid-cap liquidity.",
    "Portugal": "Portugal — smaller euro-zone economy; several large caps have "
                "strategic foreign or state-linked anchor holders, limiting the "
                "practical free float.",
    "Sweden": "Sweden — export- and innovation-heavy; SEK volatile versus EUR; "
              "dominated by dual-class A/B share structures and the Wallenberg "
              "(Investor AB) sphere, which caps outside voting power.",
    "Denmark": "Denmark — small, high-income economy; DKK pegged to the euro; "
               "several bellwethers are controlled by charitable foundations, "
               "which prioritise long-term stability over activist demands.",
    "Finland": "Finland — export-geared, euro-zone; the state (Solidium) is a "
               "meaningful anchor holder in several large caps; heavy exposure "
               "to the paper, machinery and telecom-equipment cycles.",
    "United Kingdom": "United Kingdom — deep, liquid market outside the euro and "
                      "the EU single market; genuinely dispersed ownership makes "
                      "it the most activist-friendly market here. Note LSE prices "
                      "quote in pence (GBp).",
    "Ireland": "Ireland — small, FDI- and multinational-driven economy; "
               "euro-zone; residual state stakes remain in the post-bailout "
               "banks; several listings are dual-listed in London or New York.",
    "Luxembourg": "Luxembourg — holding-company and fund domicile rather than an "
                  "operating economy; a listing domiciled here usually operates "
                  "elsewhere, so read the underlying assets, not the domicile.",
}
# Yahoo's country string is the key above; add aliases for alternative spellings.
_COUNTRY["Czechia"] = _COUNTRY["Czech Republic"]
_COUNTRY["UK"] = _COUNTRY["United Kingdom"]

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
    "Technology": "Technology: valued on growth and recurring revenue rather "
                  "than book value, so low-P/B screens rarely apply; watch "
                  "customer concentration and AI-capex cycles.",
    "Consumer Defensive": "Consumer defensive: stable volumes with pricing power "
                          "the key margin lever; input costs and private-label "
                          "competition are the pressures.",
    "Real Estate": "Real estate: NAV- and rate-driven — a low P/B is a discount "
                   "to appraised asset value, so verify the valuation basis and "
                   "debt maturity profile before treating it as cheap.",
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
