"""
Ownership / actionability overlay for the Innimmo screener.

WHY THIS EXISTS: an ACTIVIST needs to buy a stake and push for change. That is
only realistic when the company is NOT majority-controlled by the state, a
foreign parent, or a founding family. A deep-value, high-quality name that is
70% state-owned is un-actionable for an activist, and the screener must say so.

IMPORTANT: this is a HAND-MAINTAINED editorial map, not a live cap-table feed.
Control structures and free floats change — every entry is approximate and must
be VERIFIED before it is relied on. Last review: 2026-07.

Each entry: ticker -> (label, actionability_score 1-5, note)
  5 = widely held, an activist can build a position and be heard
  1 = state/parent majority, activism cannot force change
"""

# (label, score, note)  — score is the Actionability sub-score (1-5)
_MAP = {
    # --- Poland (Warsaw) ---
    "PKO.WA":  ("State-influenced", 2.0, "State Treasury is the largest holder (~29%); state sets policy."),
    "PKN.WA":  ("State-controlled", 1.5, "State ~49%; effectively state-directed."),
    "KGH.WA":  ("State-influenced", 2.0, "State Treasury largest holder (~32%)."),
    "PZU.WA":  ("State-controlled", 1.5, "State controls via ~34% stake."),
    "PGE.WA":  ("State majority", 1.0, "State ~57-60% — activism blocked."),
    "PEO.WA":  ("State-linked", 2.0, "Controlled by PZU / PFR (state-linked)."),
    "DNP.WA":  ("Founder-controlled", 2.5, "Founder holds ~51%."),
    "CDR.WA":  ("Widely held", 4.5, "Founders hold a minority; large free float."),
    "LPP.WA":  ("Family-controlled", 2.0, "Founding families control via foundations."),
    "ALE.WA":  ("Widely held", 5.0, "Large free float post-IPO."),
    "CPS.WA":  ("Family-controlled", 2.0, "Solorz family control."),
    "JSW.WA":  ("State majority", 1.0, "State ~55%."),
    "OPL.WA":  ("Foreign parent", 2.0, "Orange S.A. holds ~50%."),
    "KTY.WA":  ("Widely held", 5.0, "Institutional free float."),
    "BDX.WA":  ("Foreign parent", 2.0, "Ferrovial holds ~55%."),
    # --- Austria (Vienna) ---
    "EBS.VI":  ("Anchor shareholder", 3.5, "Erste Foundation + savings banks anchor ~30%; rest free float."),
    "OMV.VI":  ("State + strategic", 1.5, "OeBAG 31.5% + ADNOC ~25%."),
    "VOE.VI":  ("Widely held", 4.0, "Core holders exist but large free float."),
    "RBI.VI":  ("Group majority", 2.0, "Raiffeisen regional banks ~58%."),
    "VER.VI":  ("State majority", 1.0, "Republic of Austria ~51%."),
    "WIE.VI":  ("Widely held", 5.0, "Broad free float."),
    "ANDR.VI": ("Anchor shareholder", 3.5, "Custos / related anchor ~25-29%."),
    "BG.VI":   ("Widely held", 5.0, "Broad free float post-Cerberus exit."),
    "DOC.VI":  ("Founder-controlled", 2.0, "Attila Dogudan founder control."),
    "LNZ.VI":  ("Anchor majority", 2.0, "B&C Group majority."),
    "UQA.VI":  ("Anchor majority", 2.0, "Raiffeisen / UNIQA foundations control."),
    "POST.VI": ("State majority", 1.0, "OeBAG ~52.8%."),
    "MMK.VI":  ("Family-controlled", 2.0, "Mayr-Melnhof family control."),
    # --- Czechia (Prague) ---
    "CEZ.PR":  ("State majority", 1.0, "Czech state ~70%."),
    "KOMB.PR": ("Foreign parent", 2.0, "Societe Generale ~60%."),
    "MONET.PR":("Widely held", 5.0, "Broad free float."),
    # --- Hungary (Budapest) ---
    "OTP.BD":  ("Widely held", 5.0, "No single controlling owner; broad free float."),
    "MOL.BD":  ("State-influenced", 2.0, "Hungarian state + cross-holdings."),
    "RICHT.BD":("State-influenced", 3.0, "State (Maecenas) minority; otherwise free float."),
    "MTEL.BD": ("Foreign parent", 2.0, "Deutsche Telekom majority."),
    # --- Romania (Bucharest) ---
    "FP.RO":   ("Widely held (closed-end fund)", 4.0, "Investment fund with broad free float and a history of activist pressure to close its NAV discount; note it is a FUND, so its P/B is a discount-to-NAV, not an operating cheapness."),
    "TLV.RO":  ("Widely held", 4.0, "Largest Romanian bank; broad free float, no single controller (EBRD among holders)."),
    "SNP.RO":  ("Parent + state", 1.5, "OMV ~51% plus the Romanian state ~20%."),
    "SNG.RO":  ("State majority", 1.0, "Romanian state ~70% (Romgaz)."),
    "DIGI.RO": ("Founder-controlled", 2.0, "Founder (Zoltan Teszari) majority via RCS&RDS."),
    "EL.RO":   ("State-controlled", 1.5, "Romanian state is the largest holder (~48%) (Electrica)."),
    "TGN.RO":  ("State majority", 1.0, "Romanian state ~58% (Transgaz)."),
    # --- Greece (Athens) ---
    "ETE.AT":  ("Widely held", 3.5, "Largely widely held after the HFSF sell-down; verify residual state stake."),
    "EUROB.AT":("Anchor shareholder", 3.0, "Fairfax is a large (~30%+) anchor holder; otherwise free float."),
    "TPEIR.AT":("State fund + free float", 2.5, "HFSF (state fund) retains a stake; free float growing — verify."),
    "OPAP.AT": ("Parent-controlled", 2.0, "Allwyn / Sazka (Komarek) majority."),
    "OTE.AT":  ("Foreign parent", 2.0, "Deutsche Telekom majority."),
    "MYTIL.AT":("Founder anchor", 3.0, "Mytilineos family founder anchor (~25-30%)."),
    "PPC.AT":  ("State-influenced", 2.0, "Greek state ~34% is the largest holder (Public Power Corp)."),
}

_DEFAULT = ("Ownership unknown", 3.0, "Ownership not on file — verify before relying.")

# When this map was last reviewed. The screener flags names as stale if the run
# date is more than STALE_AFTER_DAYS beyond this. Bump it whenever you verify.
LAST_VERIFIED = "2026-07-24"
STALE_AFTER_DAYS = 180


def ownership(ticker: str):
    """Return (label, actionability_score, note) for a ticker."""
    return _MAP.get(ticker, _DEFAULT)


def verified_date() -> str:
    return LAST_VERIFIED


def is_actionable(score: float) -> bool:
    """Below ~2.5 an activist realistically cannot force change."""
    return score is not None and score >= 2.5
