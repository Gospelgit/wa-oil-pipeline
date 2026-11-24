"""Data quality checks on the cleaned data. Hard failures stop the run;
everything else is recorded in public_data/quality.json for the website.

Hard checks (the run stops):
  - every one of the 13 countries is present
  - crude production exists and its newest month is no more than 4 months old
  - no negative flows (stocks can't be negative either)
  - at least 90% of the values in the November 2026 hand exports are still there
    (for the countries still tracked)

Soft checks (recorded, run continues):
  - revisions: values that changed since the hand exports (JODI revises data)
  - unusual month-on-month jumps in the last 6 months, using a robust z-score:
        score = (change - median change) / (1.4826 x MAD)
    with the spread floored at the 25th percentile spread for that series type
    (so near-flat series do not flag tiny wobbles), similar to the
    same method used in the World Bank project. |score| > 5 is flagged.
  - countries that have stopped reporting

Run from the project root:  python transform/checks.py
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import CLEAN, COUNTRIES, DATA, PUBLIC, REFERENCE  # noqa: E402

JUMP_CUTOFF = 5
RECENT_MONTHS = 6


def fail(msg):
    print("CHECK FAILED:", msg)
    sys.exit(1)


def jumps(jodi, newest):
    d = jodi.dropna(subset=["value"]).sort_values("month").copy()
    d["prev"] = d.groupby(["country", "product", "flow"]).value.shift()
    d["prev_month"] = d.groupby(["country", "product", "flow"]).month.shift()
    d = d.dropna(subset=["prev"])
    # only compare back-to-back months (a country returning after a gap is not a jump)
    d = d[pd.PeriodIndex(d.month, freq="M") - pd.PeriodIndex(d.prev_month, freq="M") == pd.offsets.MonthEnd(1)]
    d = d[(d.prev > 0) & (d.flow != "Closing stocks")]
    d["change_pct"] = (d.value / d.prev - 1) * 100
    g = d.groupby(["country", "product", "flow"]).change_pct
    d["med"] = g.transform("median")
    d["mad"] = g.transform(lambda x: (x - x.median()).abs().median() * 1.4826)
    floor = d.groupby(["product", "flow"]).mad.transform(lambda x: x.quantile(0.25))
    d["spread"] = np.maximum(d.mad, floor)
    d["score"] = (d.change_pct - d.med) / d.spread
    cutoff = str(pd.Period(newest, "M") - RECENT_MONTHS)
    flagged = d[(d.month > cutoff) & (d.score.abs() > JUMP_CUTOFF)]
    return flagged.assign(change_pct=flagged.change_pct.round(1), score=flagged.score.round(1))[
        ["country", "product", "flow", "prev_month", "prev", "month", "value", "change_pct", "score"]
    ].sort_values("score", key=abs, ascending=False)


def main():
    jodi = pd.read_csv(CLEAN / "jodi.csv")
    ref = pd.read_csv(REFERENCE / "jodi_hand_exports_2026-11.csv")
    # Compare only countries that were in the hand exports and are still tracked.
    ref = ref[ref.country.isin([c for c, _ in COUNTRIES.values()])]

    missing = set(c for c, _ in COUNTRIES.values()) - set(jodi.country)
    if missing:
        fail(f"countries missing from JODI: {sorted(missing)}")

    prod = jodi[(jodi["product"] == "Crude oil") & (jodi.flow == "Production")].dropna(subset=["value"])
    if prod.empty:
        fail("no crude production rows")
    newest = prod.month.max()
    age = (pd.Period(date.today(), "M") - pd.Period(newest, "M")).n
    if age > 4:
        fail(f"newest production month is {newest}, {age} months old")

    if (jodi.value < 0).any():
        bad = jodi[jodi.value < 0].head(5)
        fail(f"negative values found:\n{bad}")

    key = ["table", "country", "product", "flow", "month"]
    m = ref.merge(jodi.dropna(subset=["value"]), on=key, how="left", suffixes=("_ref", ""))
    kept = m.value.notna().mean()
    if kept < 0.9:
        fail(f"only {kept:.0%} of reference values are still present; the source may have changed")
    changed = m[m.value.notna() & ((m.value - m.value_ref).abs() > 0.5)]

    latest = jodi.dropna(subset=["value"]).groupby("country").month.max()
    stale = latest[latest.map(lambda x: (pd.Period(newest, "M") - pd.Period(x, "M")).n >= 3)]

    flagged = jumps(jodi, newest)
    rig_warning = (DATA / "quality" / "rig_warning.txt")

    out = {
        "checked_on": date.today().isoformat(),
        "newest_month": newest,
        "rows": int(len(jodi)),
        "reference_values_present_pct": round(kept * 100, 1),
        "revised_since_reference": int(len(changed)),
        "revised_examples": changed.assign(change=(changed.value - changed.value_ref).round(1))
            [key + ["value_ref", "value", "change"]].head(20).to_dict("records"),
        "stopped_reporting": [{"country": c, "last_month": m} for c, m in stale.items()],
        "unusual_jumps": flagged.to_dict("records"),
        "rig_warning": rig_warning.read_text() if rig_warning.exists() else None,
    }
    PUBLIC.mkdir(exist_ok=True)
    (PUBLIC / "quality.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"Checks passed. Newest month {newest}; {len(changed)} revised values; "
          f"{len(flagged)} unusual recent jumps; {len(stale)} countries not reporting.")
    if len(flagged):
        print(flagged.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
