"""Load the tidy inputs the models need: production panel, Brent, oil rigs."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

RIG_NAMES = {
    "ALGERIA": "Algeria", "ANGOLA": "Angola", "BRAZIL": "Brazil", "CANADA": "Canada",
    "LIBYA": "Libya", "NIGERIA": "Nigeria", "NORWAY": "Norway",
    "KUWAIT": "Kuwait", "SAUDI ARABIA": "Saudi Arabia",
    "UNITED STATES": "United States of America",
    "VENEZUELA": "Venezuela",
}


def _to_period(s):
    return pd.PeriodIndex(pd.to_datetime(s), freq="M")


def production(path=None):
    """dict country -> monthly crude production Series (kb/d), PeriodIndex."""
    path = path or DATA / "clean" / "jodi.csv"
    if not Path(path).exists():
        path = DATA / "reference" / "jodi_hand_exports_2026-11.csv"
    d = pd.read_csv(path)
    d = d[(d["product"] == "Crude oil") & (d.flow == "Production")].dropna(subset=["value"])
    out = {}
    for c, g in d.groupby("country"):
        s = pd.Series(g.value.values, index=_to_period(g.month)).sort_index()
        out[c] = s.asfreq("M")
    return out


def brent(path=None):
    path = path or DATA / "clean" / "brent_monthly.csv"
    if not Path(path).exists():
        path = DATA / "reference" / "brent_monthly_fred.csv"
    d = pd.read_csv(path)
    return pd.Series(d.brent_usd_per_barrel.values, index=_to_period(d.month)).sort_index()


def oil_rigs(path=None):
    """dict country -> monthly oil-rig Series.

    Saudi Arabia's count method changed in Jan 2024. Its series is put on one
    basis by scaling the new-method counts down by the average new/old ratio
    over the months both versions exist.
    """
    path = path or DATA / "clean" / "oil_rigs.csv"
    if not Path(path).exists():
        path = DATA / "reference" / "baker_hughes_rigs_monthly_long.csv"
    d = pd.read_csv(path)
    d = d[d.drill_for == "Oil"]
    out = {}
    for c, g in d.groupby("country"):
        name = RIG_NAMES.get(c, c)
        by = g.groupby(["rig_status", "month"]).rigs.sum()
        statuses = set(g.rig_status)
        if "Operating Rigs" in statuses and "Active Rigs (old method, overlap)" in statuses:
            old = pd.concat([by["Active Rigs"], by["Active Rigs (old method, overlap)"]])
            new = by["Operating Rigs"]
            both = old.index.intersection(new.index)
            ratio = (new[both] / old[both].replace(0, np.nan)).mean()
            s = pd.concat([old, new[new.index > old.index.max()] / ratio])
        else:
            s = by.groupby(level="month").sum()
        s.index = _to_period(s.index)
        out[name] = s.sort_index().asfreq("M")
    return out
