"""Work out the Strait of Hormuz status from the data, with an optional manual override.

Saudi Arabia ships most of its crude through the strait, so its exports
compared with their pre-war level are a direct reading of whether the strait
is working:

    under 60% of pre-war               -> closed
    60% to 90%                         -> restricted
    90% or more for 2 months in a row  -> open

Pre-war level = average Saudi crude exports, Sep 2025 to Feb 2026.
JODI runs about two months behind, so config/hormuz_status.json can set the
status by hand when news moves faster than the data.

Writes public_data/hormuz_status.json.
Run from the project root:  python transform/hormuz.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import CLEAN, CONFIG, PUBLIC, REFERENCE  # noqa: E402

BASELINE = ("2025-09", "2026-02")
CLOSED_BELOW, OPEN_FROM, OPEN_MONTHS = 60, 90, 2


def status_from_ratio(ratios):
    last = ratios.iloc[-1]
    if len(ratios) >= OPEN_MONTHS and (ratios.iloc[-OPEN_MONTHS:] >= OPEN_FROM).all():
        return "open"
    return "closed" if last < CLOSED_BELOW else "restricted"


def main():
    path = CLEAN / "jodi.csv"
    jodi = pd.read_csv(path if path.exists() else REFERENCE / "jodi_hand_exports_2026-11.csv")
    s = (jodi[(jodi.country == "Saudi Arabia") & (jodi["product"] == "Crude oil") & (jodi.flow == "Exports")]
         .dropna(subset=["value"]).set_index("month").value.sort_index())
    base = s[BASELINE[0]:BASELINE[1]].mean()
    ratios = (s[BASELINE[0]:] / base * 100).round(1)
    data_status = status_from_ratio(ratios)

    cfg = json.loads((CONFIG / "hormuz_status.json").read_text())
    override = cfg.get("override")
    if override and override.get("status") not in {"closed", "restricted", "open"}:
        raise ValueError("config/hormuz_status.json: status must be closed, restricted or open")

    out = {
        "status": override["status"] if override else data_status,
        "decided_by": "manual override" if override else "data",
        "data_status": data_status,
        "latest_month": ratios.index[-1],
        "latest_pct_of_prewar": float(ratios.iloc[-1]),
        "lowest_pct_of_prewar": float(ratios.min()),
        "lowest_month": ratios.idxmin(),
        "prewar_exports_kbd": round(float(base), 0),
        "prewar_period": f"{BASELINE[0]} to {BASELINE[1]}",
        "rules": {"closed_below_pct": CLOSED_BELOW, "open_from_pct": OPEN_FROM,
                  "open_needs_consecutive_months": OPEN_MONTHS},
        "override": override,
        "saudi_forecast_warning": (override["status"] if override else data_status) != "open",
        "monthly_pct_of_prewar": [{"month": m, "pct": float(v)} for m, v in ratios.items()],
    }
    PUBLIC.mkdir(exist_ok=True)
    (PUBLIC / "hormuz_status.json").write_text(json.dumps(out, indent=2))
    print(f"Hormuz status: {out['status']} ({out['decided_by']}); Saudi exports at "
          f"{out['latest_pct_of_prewar']}% of pre-war in {out['latest_month']}")


if __name__ == "__main__":
    main()
