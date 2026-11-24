"""Forecast crude production 12 months ahead for every country with recent data.

Model: blend (average of the last-3-month level and a damped Holt trend).
It had the lowest error in the selection period of the backtest.
80% ranges come from the blend's real backtest errors at each horizon:
the 10th and 90th percentiles of % error, per country when the country has
enough backtest points, otherwise pooled across all countries.

Run from the project root:  python ml/forecast.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import forecastable  # noqa: E402
from data import DATA, production  # noqa: E402
from models import H, blend  # noqa: E402

MODEL = "blend"
MAX_STALENESS = 3  # skip countries whose latest month is this far behind the newest
MIN_POINTS = 25    # backtest points per horizon needed for a country-specific range


def error_bands(errors):
    e = errors[errors.model == MODEL]
    pooled = e.groupby("h").pct_error.quantile([0.1, 0.9]).unstack()
    bands = {}
    for c, g in e.groupby("country"):
        q = g.groupby("h").pct_error.quantile([0.1, 0.9]).unstack()
        n = g.groupby("h").size()
        bands[c] = q.where(n.reindex(q.index) >= MIN_POINTS, pooled)
    # Ranges should only widen with horizon: smooth out sampling noise.
    widen = lambda q: pd.DataFrame({0.1: q[0.1].cummin(), 0.9: q[0.9].cummax()})
    return {c: widen(q) for c, q in bands.items()}, widen(pooled)


def run():
    panel = production()
    errors = pd.read_csv(DATA / "backtest" / "backtest_errors.csv")
    bands, pooled = error_bands(errors)
    newest = max(y.dropna().index.max() for y in panel.values())
    rows, skipped = [], {}
    for c, y in panel.items():
        y = y.dropna()
        t = y.index.max()
        if (newest - t).n >= MAX_STALENESS:
            skipped[c] = f"no data since {t}"
            continue
        yy = y.asfreq("M")
        if not forecastable(yy, t):
            skipped[c] = "fewer than 24 unbroken months of recent data"
            continue
        fc = blend(yy[yy.index <= t], H)
        b = bands.get(c, pooled)
        for k in range(1, H + 1):
            lo, hi = b.loc[k, 0.1], b.loc[k, 0.9]
            # forecast = actual*(1+e/100)  =>  actual = forecast/(1+e/100)
            rows.append({
                "country": c, "month": str(t + k), "horizon": k,
                "forecast": round(float(fc[k - 1]), 1),
                "low_80": round(float(fc[k - 1] / (1 + hi / 100)), 1),
                "high_80": round(float(fc[k - 1] / (1 + lo / 100)), 1),
                "last_actual_month": str(t), "last_actual": round(float(y[t]), 1),
            })
    out = pd.DataFrame(rows)
    (DATA / "forecast").mkdir(exist_ok=True)
    out.to_csv(DATA / "forecast" / "crude_production_forecast.csv", index=False)
    pd.Series(skipped, name="reason").to_csv(DATA / "forecast" / "skipped_countries.csv", index_label="country")
    return out, skipped


if __name__ == "__main__":
    out, skipped = run()
    end = out[out.horizon == H][["country", "last_actual_month", "last_actual", "month", "forecast", "low_80", "high_80"]]
    print(end.to_string(index=False))
    print("\nSkipped:", skipped)
