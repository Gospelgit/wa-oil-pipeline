"""Write the JSON files the website reads (public_data/).

The website fetches these straight from GitHub, e.g.
https://raw.githubusercontent.com/Gospelgit/wa-oil-pipeline/main/public_data/meta.json

Series are stored compactly as [month, value] pairs.
Run from the project root (after the transform and ml steps):
    python publish/export_json.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import CLEAN, COUNTRIES, DATA, PUBLIC, RIG_COUNTRIES, SHORT_NAME  # noqa: E402

HISTORY_FROM = "2005-01"


def clean(v):
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else round(float(v), 2)
    if isinstance(v, np.integer):
        return int(v)
    return v


def pairs(s):
    return [[m, clean(v)] for m, v in s.items() if v is not None and not pd.isna(v)]


def scrub(o):
    """Replace NaN with null everywhere (NaN is not valid JSON)."""
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [scrub(v) for v in o]
    return clean(o)


def write(name, obj):
    (PUBLIC / f"{name}.json").write_text(json.dumps(scrub(obj), separators=(",", ":"), allow_nan=False))
    return name


def nested(d):
    """{country: {product|flow: [[month, value], ...]}}"""
    out = {}
    for (c, p, f), g in d.groupby(["country", "product", "flow"]):
        key = f if p == "Crude oil" else f"{p} | {f}"
        out.setdefault(c, {})[key] = pairs(g.set_index("month").value)
    return out


def main():
    PUBLIC.mkdir(exist_ok=True)
    j = pd.read_csv(CLEAN / "jodi.csv").dropna(subset=["value"])
    j = j[j.month >= HISTORY_FROM].sort_values("month")
    written = []

    crude = j[j["product"] == "Crude oil"]
    written.append(write("crude", {"unit": {"Closing stocks": "thousand barrels", "other": "thousand barrels per day"},
                                   "series": nested(crude)}))
    products = j[j["product"] != "Crude oil"]
    written.append(write("products", {"unit": "thousand barrels per day", "series": nested(products)}))

    # Nigeria's fuel story, yearly
    ng = products[(products.country == "Nigeria") & (products["product"] == "Total oil products")]
    ny = ng.groupby([ng.month.str[:4], "flow"]).value.mean().unstack()
    ny = ny[ny.index >= "2015"]
    written.append(write("nigeria_fuel", [{
        "year": y, "refinery_output": r.get("Refinery output"), "demand": r.get("Demand"),
        "imports": r.get("Imports"), "exports": r.get("Exports"),
        "self_sufficiency_pct": clean(r.get("Refinery output") / r.get("Demand") * 100) if r.get("Demand") else None,
        "net_exports": clean(r.get("Exports") - r.get("Imports")),
    } for y, r in ny.iterrows()]))

    peers = pd.read_csv(CLEAN / "peers.csv")
    written.append(write("peers", peers.to_dict("records")))

    brent = pd.read_csv(CLEAN / "brent_monthly.csv")
    written.append(write("brent", {"unit": "US$ per barrel", "source": brent.source.iloc[0],
                                   "series": pairs(brent[brent.month >= HISTORY_FROM].set_index("month").brent_usd_per_barrel)}))

    rg = pd.read_csv(CLEAN / "oil_rigs.csv")
    rg = rg[(rg.drill_for == "Oil") & (rg.rig_status != "Active Rigs (old method, overlap)")]
    rg["country"] = rg.country.map(RIG_COUNTRIES)
    rs = rg.groupby(["country", "month"]).rigs.sum()
    written.append(write("rigs", {
        "unit": "active oil rigs (monthly average)",
        "note": "Saudi Arabia counts operating rigs from Jan 2024 (method change), so its series jumps then.",
        "series": {c: pairs(rs[c]) for c in rs.index.get_level_values(0).unique()},
    }))

    hormuz = json.loads((PUBLIC / "hormuz_status.json").read_text())
    fc = pd.read_csv(DATA / "forecast" / "crude_production_forecast.csv")
    skipped = pd.read_csv(DATA / "forecast" / "skipped_countries.csv")
    bt = pd.read_csv(DATA / "backtest" / "backtest_errors.csv")
    bt["ape"] = bt.pct_error.abs()
    by_country = bt[(bt.model == "blend") & (bt.period == "test")].groupby("country").ape.mean().round(1)
    prod = crude[crude.flow == "Production"]
    fcs = {}
    for c, g in fc.groupby("country"):
        hist = prod[prod.country == c].set_index("month").value
        warning = None
        if c == "Saudi Arabia" and hormuz["saudi_forecast_warning"]:
            warning = (f"Strait of Hormuz {hormuz['status']}: Saudi output depends on shipping through the "
                       f"strait, which past data can't predict. Treat this forecast with caution.")
        fcs[c] = {
            "history": pairs(hist.iloc[-36:]),
            "forecast": g[["month", "forecast", "low_80", "high_80"]].values.tolist(),
            "model": "blend", "test_error_pct": clean(by_country.get(c)),
            "warning": warning,
        }
    written.append(write("forecast", {
        "unit": "thousand barrels per day", "range": "80% range from backtest errors",
        "countries": fcs, "skipped": skipped.to_dict("records"),
    }))

    summary = bt.pivot_table(index="model", columns="period", values="ape", aggfunc="mean").round(2)
    written.append(write("backtest", {
        "metric": "average absolute % error, 1 to 12 months ahead",
        "selection_period": "origins Dec 2015 to Sep 2022", "test_period": "origins Dec 2022 to Sep 2025",
        "models": summary.reset_index().to_dict("records"),
        "chosen_model": "blend",
        "blend_test_error_by_country": by_country.to_dict(),
    }))

    written.append(write("meta", {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "newest_month": j.month.max(),
        "countries": [{"name": n, "short_name": SHORT_NAME.get(n, n), "iso2": k, "region": r}
                      for k, (n, r) in COUNTRIES.items()],
        "sources": {
            "jodi": "JODI-Oil World Database (jodidata.org), primary and secondary tables",
            "brent": "FRED series MCOILBRENTEU (US EIA)",
            "rigs": "Baker Hughes Worldwide Rig Count",
        },
        "files": sorted(written + ["hormuz_status", "quality"]),
    }))
    print("Wrote", ", ".join(f"{w}.json" for w in written))


if __name__ == "__main__":
    main()
