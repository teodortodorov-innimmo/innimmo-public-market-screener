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
    # --- Slovenia (via Vienna cross-listing; Ljubljana has no Yahoo feed) ---
    "KRKG.VI": ("Widely held", 4.0, "Krka — broad free float with Slovenian institutional and retail holders; no single controlling shareholder."),
    # --- Romania (Bucharest) ---
    "FP.RO":   ("Widely held (closed-end fund)", 4.0, "Investment fund with broad free float and a history of activist pressure to close its NAV discount; note it is a FUND, so its P/B is a discount-to-NAV, not an operating cheapness."),
    "TLV.RO":  ("Widely held", 4.0, "Largest Romanian bank; broad free float, no single controller (EBRD among holders)."),
    "SNP.RO":  ("Parent + state", 1.5, "OMV ~51% plus the Romanian state ~20%."),
    "SNG.RO":  ("State majority", 1.0, "Romanian state ~70% (Romgaz)."),
    "DIGI.RO": ("Founder-controlled", 2.0, "Founder (Zoltan Teszari) majority via RCS&RDS."),
    "EL.RO":   ("State-controlled", 1.5, "Romanian state is the largest holder (~48%) (Electrica)."),
    "TGN.RO":  ("State majority", 1.0, "Romanian state ~58% (Transgaz)."),
    "SNN.RO":  ("State majority", 1.0, "Romanian state (Ministry of Energy) ~82% (Nuclearelectrica)."),
    "H2O.RO":  ("State majority", 1.0, "Romanian state ~80% (Hidroelectrica)."),
    "TEL.RO":  ("State majority", 1.0, "Romanian state ~59% (Transelectrica)."),
    "BRD.RO":  ("Foreign parent", 2.0, "Societe Generale ~60% (BRD)."),
    "CFH.RO":  ("Family-controlled", 2.0, "Cris-Tim family holding — founder-controlled."),
    # --- Greece (Athens) ---
    "ETE.AT":  ("Widely held", 3.5, "Largely widely held after the HFSF sell-down; verify residual state stake."),
    "EUROB.AT":("Anchor shareholder", 3.0, "Fairfax is a large (~30%+) anchor holder; otherwise free float."),
    "TPEIR.AT":("State fund + free float", 2.5, "HFSF (state fund) retains a stake; free float growing — verify."),
    "HTO.AT":  ("Foreign parent", 2.0, "Deutsche Telekom majority (OTE / Hellenic Telecom)."),
    "MTLN.AT": ("Founder anchor", 3.0, "Mytilineos family founder anchor (~25-30%) (Metlen, formerly Mytilineos)."),
    "PPC.AT":  ("State-influenced", 2.0, "Greek state ~34% is the largest holder (Public Power Corp)."),
    # --- Germany (Xetra) ---
    "SAP.DE":  ("Widely held", 4.5, "Founder families retain a minority; broad institutional free float."),
    "ALV.DE":  ("Widely held", 4.5, "No single controlling shareholder; broad free float (Allianz)."),
    "SIE.DE":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Siemens)."),
    "DTE.DE":  ("State-influenced", 2.0, "German state (via KfW) ~30% (Deutsche Telekom)."),
    "BAS.DE":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (BASF)."),
    "BMW.DE":  ("Family-controlled", 2.0, "Quandt/Klatten family ~47% control."),
    "VOW3.DE": ("Family + state", 1.5, "Porsche/Piech family + Lower Saxony state + Qatar; effectively controlled (Volkswagen)."),
    "MBG.DE":  ("Anchor shareholders", 3.0, "Kuwait Investment Authority + BAIC/Li Shufu anchors; otherwise free float (Mercedes-Benz)."),
    "DBK.DE":  ("Widely held", 4.0, "Broad free float; no controlling shareholder (Deutsche Bank)."),
    "MUV2.DE": ("Widely held", 4.5, "Broad free float; no controlling shareholder (Munich Re)."),
    # --- France (Paris) ---
    "MC.PA":   ("Family-controlled", 1.5, "Arnault family ~48% control (LVMH)."),
    "OR.PA":   ("Family-controlled", 2.0, "Bettencourt Meyers family ~35% anchor (L'Oreal)."),
    "SAN.PA":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Sanofi)."),
    "BNP.PA":  ("Widely held", 4.5, "Broad free float; Belgian state a minor legacy holder (BNP Paribas)."),
    "AIR.PA":  ("State + family", 1.5, "French/German/Spanish states + Lagardere family hold a coordinated stake (Airbus; incorporated in Netherlands)."),
    "TTE.PA":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (TotalEnergies)."),
    "SU.PA":   ("Widely held", 4.5, "Broad free float; no controlling shareholder (Schneider Electric)."),
    "DG.PA":   ("Widely held", 4.0, "Broad free float; no controlling shareholder (Vinci)."),
    "CS.PA":   ("Widely held", 4.5, "Broad free float; no controlling shareholder (AXA)."),
    "ENGI.PA": ("State-controlled", 1.5, "French state ~24% is the largest holder, with governance rights (Engie)."),
    # --- Italy (Milan) ---
    "ENEL.MI": ("State-influenced", 2.0, "Italian state (via MEF/CDP) ~24% is the largest holder."),
    "ENI.MI":  ("State-influenced", 2.0, "Italian state (via MEF/CDP) ~30% combined."),
    "ISP.MI":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Intesa Sanpaolo)."),
    "UCG.MI":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (UniCredit)."),
    "G.MI":    ("Widely held", 4.0, "Broad free float; Caltagirone/Del Vecchio are large minority holders (Generali)."),
    "STLAM.MI":("Family anchor", 2.0, "Agnelli family (Exor) + Peugeot family anchor stakes (Stellantis; incorporated in Netherlands)."),
    "TIT.MI":  ("Anchor shareholder", 2.5, "Vivendi + MEF (Italian state) large minority stakes (Telecom Italia)."),
    "RACE.MI": ("Family anchor", 2.0, "Agnelli family (Exor) anchor stake (Ferrari)."),
    # --- Spain (Madrid) ---
    "SAN.MC":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Banco Santander)."),
    "ITX.MC":  ("Family-controlled", 1.5, "Ortega family ~59% control (Inditex/Zara)."),
    "IBE.MC":  ("Widely held", 4.0, "Broad free float; Qatar Investment Authority a large minority holder (Iberdrola)."),
    "BBVA.MC": ("Widely held", 4.5, "Broad free float; no controlling shareholder."),
    "TEF.MC":  ("State-influenced", 2.5, "Spanish state (via SEPI) + Saudi STC large minority stakes (Telefonica)."),
    "REP.MC":  ("Widely held", 4.0, "Broad free float; Sacyr a large minority holder (Repsol)."),
    "AENA.MC": ("State majority", 1.0, "Spanish state ~51% (Aena)."),
    # --- Netherlands (Amsterdam) ---
    "ASML.AS": ("Widely held", 4.5, "Broad free float; no controlling shareholder."),
    "INGA.AS": ("Widely held", 4.5, "Broad free float; no controlling shareholder (ING)."),
    "AD.AS":   ("Widely held", 4.0, "Broad free float; no controlling shareholder (Ahold Delhaize)."),
    "PHIA.AS": ("Widely held", 4.5, "Broad free float; no controlling shareholder (Philips)."),
    "ADYEN.AS":("Founder anchor", 3.0, "Founders retain a meaningful anchor stake alongside broad free float."),
    "WKL.AS":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Wolters Kluwer)."),
    # --- Belgium (Brussels) ---
    "ABI.BR":  ("Family anchor", 2.0, "3G Capital + de Spoelberch/de Mevius/van Damme families anchor control (AB InBev)."),
    "KBC.BR":  ("Anchor shareholders", 3.0, "Cera + KBC Ancora cooperative shareholders anchor ~40%."),
    "UCB.BR":  ("Family anchor", 2.5, "Janssen family foundation anchor stake."),
    "SOLB.BR": ("Widely held", 4.0, "Broad free float; Solvay family retains a minority (Solvay)."),
    # --- Portugal (Lisbon) ---
    "EDP.LS":  ("Foreign parent", 2.0, "China Three Gorges ~20% + state-linked holders; no free majority (EDP)."),
    "GALP.LS": ("Anchor shareholders", 3.0, "Amorim family + Oman state fund anchor stakes (Galp)."),
    "JMT.LS":  ("Family-controlled", 2.0, "Soares dos Santos family control (Jeronimo Martins)."),
    # --- Sweden (Stockholm) ---
    "ERIC-B.ST":  ("Anchor shareholder", 3.0, "Investor AB (Wallenberg family) anchor stake (Ericsson)."),
    "VOLV-B.ST":  ("Anchor shareholder", 3.0, "Investor AB (Wallenberg family) anchor stake (Volvo)."),
    "ATCO-A.ST":  ("Anchor shareholder", 3.0, "Investor AB (Wallenberg family) anchor stake (Atlas Copco)."),
    "HM-B.ST":    ("Family-controlled", 1.5, "Persson family ~65% voting control (H&M)."),
    "SEB-A.ST":   ("Anchor shareholder", 3.0, "Wallenberg family anchor stake (SEB)."),
    "SWED-A.ST":  ("Widely held", 4.0, "Broad free float; Swedish savings-bank foundations are large minority holders (Swedbank)."),
    "SAND.ST":    ("Anchor shareholder", 3.0, "Investor AB (Wallenberg family) anchor stake (Sandvik)."),
    "INVE-B.ST":  ("Family-controlled", 1.5, "Wallenberg family control (Investor AB itself is the family's holding vehicle)."),
    # --- Denmark (Copenhagen) ---
    "NOVO-B.CO":  ("Foundation-controlled", 2.0, "Novo Nordisk Foundation majority voting control."),
    "DSV.CO":     ("Widely held", 4.5, "Broad free float; no controlling shareholder."),
    "ORSTED.CO":  ("State majority", 1.0, "Danish state ~50%+ (Orsted)."),
    "MAERSK-B.CO":("Family-controlled", 2.0, "Moller family ~50%+ voting control (Maersk)."),
    "CARL-B.CO":  ("Foundation-controlled", 2.0, "Carlsberg Foundation majority voting control."),
    "VWS.CO":     ("Widely held", 4.0, "Broad free float; no controlling shareholder (Vestas)."),
    # --- Finland (Helsinki) ---
    "NOKIA.HE":  ("Widely held", 4.5, "Broad free float; no controlling shareholder."),
    "NESTE.HE":  ("State majority", 1.0, "Finnish state ~36% is the largest holder (Neste)."),
    "KNEBV.HE":  ("Widely held", 4.0, "Broad free float; Herlin family a legacy minority holder (Kone)."),
    "SAMPO.HE":  ("Widely held", 4.5, "Broad free float; no controlling shareholder."),
    "UPM.HE":    ("Widely held", 4.0, "Broad free float; no controlling shareholder."),
    # --- United Kingdom (London) — prices in GBp/pence, see fetch() ---
    "SHEL.L":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Shell)."),
    "AZN.L":   ("Widely held", 4.5, "Broad free float; no controlling shareholder (AstraZeneca)."),
    "HSBA.L":  ("Widely held", 4.5, "Broad free float; Ping An a large minority holder (HSBC)."),
    "ULVR.L":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Unilever)."),
    "BP.L":    ("Widely held", 4.5, "Broad free float; no controlling shareholder."),
    "GSK.L":   ("Widely held", 4.5, "Broad free float; no controlling shareholder."),
    "DGE.L":   ("Widely held", 4.0, "Broad free float; no controlling shareholder (Diageo)."),
    "RIO.L":   ("Widely held", 4.5, "Broad free float; dual-listed with RIO.AX (Rio Tinto)."),
    "BATS.L":  ("Widely held", 4.0, "Broad free float; no controlling shareholder (British American Tobacco)."),
    "VOD.L":   ("Widely held", 4.5, "Broad free float; e& (Emirates Telecom) a large minority holder (Vodafone)."),
    "BARC.L":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Barclays)."),
    "LLOY.L":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Lloyds)."),
    "NWG.L":   ("Widely held", 4.0, "UK government retains a residual minority stake post-bailout (NatWest)."),
    "STAN.L":  ("Widely held", 4.5, "Broad free float; Temasek a large minority holder (Standard Chartered)."),
    # --- Ireland (Dublin) ---
    "RYA.IR":  ("Widely held", 4.5, "Broad free float; no controlling shareholder (Ryanair)."),
    "KRZ.IR":  ("Family anchor", 3.0, "Kerry Group founding family retains a minority anchor stake."),
    "BIRG.IR": ("Widely held", 4.0, "Broad free float; Irish state retains a small residual stake post-bailout (Bank of Ireland)."),
    "PTSB.IR": ("State-influenced", 2.0, "Irish state ~57% (PTSB)."),
}

_DEFAULT = ("Ownership unknown", 3.0, "Ownership not on file — verify before relying.")

# When this map was last reviewed. The screener flags names as stale if the run
# date is more than STALE_AFTER_DAYS beyond this. Bump it whenever you verify.
LAST_VERIFIED = "2026-07-29"
STALE_AFTER_DAYS = 180


def ownership(ticker: str):
    """Return (label, actionability_score, note) for a ticker."""
    return _MAP.get(ticker, _DEFAULT)


def verified_date() -> str:
    return LAST_VERIFIED


def is_actionable(score: float) -> bool:
    """Below ~2.5 an activist realistically cannot force change."""
    return score is not None and score >= 2.5
