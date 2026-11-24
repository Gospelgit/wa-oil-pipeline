"""Shared settings: countries, regions, JODI codes, file locations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
CLEAN = DATA / "clean"
REFERENCE = DATA / "reference"
PUBLIC = ROOT / "public_data"
STATE = ROOT / "state"
CONFIG = ROOT / "config"

# ISO2 code used by JODI -> (display name, region)
COUNTRIES = {
    "NG": ("Nigeria", "Africa"),
    "DZ": ("Algeria", "Africa"),
    "AO": ("Angola", "Africa"),
    "LY": ("Libya", "Africa"),
    "SA": ("Saudi Arabia", "Middle East"),
    "IR": ("Iran (Islamic Rep.)", "Middle East"),
    "NO": ("Norway", "Europe"),
    "RU": ("Russian Federation", "Europe"),
    "US": ("United States of America", "North America"),
    "CA": ("Canada", "North America"),
    "BR": ("Brazil", "South America"),
    "VE": ("Venezuela", "South America"),
}
NAME_TO_ISO2 = {v[0]: k for k, v in COUNTRIES.items()}
REGION = {v[0]: v[1] for v in COUNTRIES.values()}
SHORT_NAME = {
    "Iran (Islamic Rep.)": "Iran",
    "Russian Federation": "Russia",
    "United States of America": "United States",
}

JODI_URLS = {
    "primary": "https://www.jodidata.org/_resources/files/downloads/oil-data/world_primary_csv.zip",
    "secondary": "https://www.jodidata.org/_resources/files/downloads/oil-data/world_secondary_csv.zip",
}

# (table, JODI product code, JODI flow code, JODI unit) -> (product, flow, unit)
JODI_SERIES = {
    ("primary", "CRUDEOIL", "INDPROD", "KBD"): ("Crude oil", "Production", "kb/d"),
    ("primary", "CRUDEOIL", "TOTIMPSB", "KBD"): ("Crude oil", "Imports", "kb/d"),
    ("primary", "CRUDEOIL", "TOTEXPSB", "KBD"): ("Crude oil", "Exports", "kb/d"),
    ("primary", "CRUDEOIL", "REFINOBS", "KBD"): ("Crude oil", "Refinery intake", "kb/d"),
    ("primary", "CRUDEOIL", "CLOSTLV", "KBBL"): ("Crude oil", "Closing stocks", "kbbl"),
}
for code, name in [("GASOLINE", "Motor and aviation gasoline"),
                   ("GASDIES", "Gas/diesel oil"),
                   ("TOTPRODS", "Total oil products")]:
    for flow_code, flow in [("REFGROUT", "Refinery output"), ("TOTDEMO", "Demand"),
                            ("TOTIMPSB", "Imports"), ("TOTEXPSB", "Exports")]:
        JODI_SERIES[("secondary", code, flow_code, "KBD")] = (name, flow, "kb/d")

FRED_BRENT_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MCOILBRENTEU"
RIG_PAGE_URL = "https://bakerhughesrigcount.gcs-web.com/intl-rig-count"
RIG_BASE_URL = "https://bakerhughesrigcount.gcs-web.com"

# Baker Hughes country names -> our names
RIG_COUNTRIES = {
    "ALGERIA": "Algeria", "ANGOLA": "Angola", "BRAZIL": "Brazil", "CANADA": "Canada",
    "LIBYA": "Libya", "NIGERIA": "Nigeria", "NORWAY": "Norway",
    "SAUDI ARABIA": "Saudi Arabia", "UNITED STATES": "United States of America",
    "VENEZUELA": "Venezuela",
}

HEADERS = {"User-Agent": "wa-oil-pipeline/1.0 (portfolio data project; github.com/Gospelgit)"}
