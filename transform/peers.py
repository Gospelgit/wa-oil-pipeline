"""Nigeria against the other 11 countries, grouped by region.

One row per country with the measures used on the website:
production now and in 2010, distance from peak, month-to-month swings,
export and refining shares, fuel self-sufficiency, net product trade,
oil rigs and output per rig. Writes data/clean/peers.csv.

Run from the project root:  python transform/peers.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import CLEAN, REGION, RIG_COUNTRIES, SHORT_NAME  # noqa: E402


def yearly(d, product, flow):
    x = d[(d["product"] == product) & (d.flow == flow)]
    return x.groupby(["country", x.month.str[:4]]).value.mean().unstack()


def main():
    j = pd.read_csv(CLEAN / "jodi.csv").dropna(subset=["value"])
    prod = j[(j["product"] == "Crude oil") & (j.flow == "Production")].sort_values("month")
    last_full_year = str(int(prod.month.max()[:4]) - 1)

    rows = []
    for c, g in prod.groupby("country"):
        s = g.set_index("month").value
        mom = s.pct_change().abs() * 100
        rows.append({
            "country": c, "short_name": SHORT_NAME.get(c, c), "region": REGION[c],
            "latest_month": s.index[-1], "latest_kbd": round(s.iloc[-1], 1),
            "avg_2010_kbd": round(s["2010-01":"2010-12"].mean(), 1) if s["2010-01":"2010-12"].size else None,
            "peak_kbd": round(s.max(), 1), "peak_month": s.idxmax(),
            "pct_of_peak": round(s.iloc[-1] / s.max() * 100, 1),
            "typical_monthly_swing_pct": round(mom["2015-01":].median(), 1),
        })
    t = pd.DataFrame(rows).set_index("country")
    t["change_since_2010_pct"] = ((t.latest_kbd / t.avg_2010_kbd - 1) * 100).round(1)

    py = yearly(j, "Crude oil", "Production").get(last_full_year)
    ex = yearly(j, "Crude oil", "Exports").get(last_full_year)
    rf = yearly(j, "Crude oil", "Refinery intake").get(last_full_year)
    t["share_basis_year"] = last_full_year
    t["export_share_pct"] = (ex / py * 100).round(1)
    t["refined_at_home_pct"] = (rf / py * 100).round(1)

    yr = prod.month.max()[:4]
    out_ = yearly(j, "Total oil products", "Refinery output").get(yr)
    dem = yearly(j, "Total oil products", "Demand").get(yr)
    imp = yearly(j, "Total oil products", "Imports").get(yr)
    exp = yearly(j, "Total oil products", "Exports").get(yr)
    t["fuel_basis_year"] = yr
    t["fuel_self_sufficiency_pct"] = (out_ / dem.replace(0, np.nan) * 100).round(1)
    t["net_product_exports_kbd"] = (exp - imp).round(1)

    # Rig counts as published for that year (Saudi on its current method).
    rg = pd.read_csv(CLEAN / "oil_rigs.csv")
    rg = rg[(rg.drill_for == "Oil") & (rg.month.str[:4] == last_full_year)
            & (rg.rig_status != "Active Rigs (old method, overlap)")]
    rg["country"] = rg.country.map(RIG_COUNTRIES)
    t["oil_rigs"] = rg.groupby(["country", "month"]).rigs.sum().groupby("country").mean().round(1)
    per_rig = (py / t.oil_rigs).round(0)
    t["kbd_per_rig"] = per_rig.where(t.oil_rigs >= 5)  # too few rigs to be meaningful

    CLEAN.mkdir(exist_ok=True)
    t.reset_index().to_csv(CLEAN / "peers.csv", index=False)
    print(t[["region", "latest_kbd", "pct_of_peak", "typical_monthly_swing_pct",
             "fuel_self_sufficiency_pct", "kbd_per_rig"]].sort_values("region").to_string())


if __name__ == "__main__":
    main()
