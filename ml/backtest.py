"""Backtest the forecasting models on hidden months.

Rolling origins: at each origin the models only see data up to that month,
forecast 12 months ahead, and are scored against what actually happened.

Selection period: origins 2015-12 to 2022-09 (pick the model).
Test period:      origins 2022-12 to 2025-09 (check it on months it never saw).

Run from the project root:  python ml/backtest.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import brent, oil_rigs, production, DATA  # noqa: E402
from models import H, MODELS, fit_driver_coefs  # noqa: E402

MIN_HISTORY = 24  # months of unbroken history needed before an origin


def forecastable(y, t):
    """True if the country has the last MIN_HISTORY months up to t with no gaps."""
    w = y[(y.index > t - MIN_HISTORY) & (y.index <= t)]
    return len(w) == MIN_HISTORY and w.notna().all()


def run():
    panel, br, rigs = production(), brent(), oil_rigs()
    origins = pd.period_range("2015-12", "2025-09", freq="M")[::3]
    rows = []
    for t in origins:
        coefs = fit_driver_coefs(panel, br, rigs, cutoff=t)
        for c, y in panel.items():
            if not forecastable(y, t):
                continue
            hist = y[y.index <= t]
            for name, f in MODELS.items():
                if name == "drivers" and c not in rigs:
                    continue
                fc = f(hist, H, brent=br, rigs=rigs.get(c), coefs=coefs)
                for k in range(1, H + 1):
                    tk = t + k
                    if tk in y.index and np.isfinite(y[tk]):
                        rows.append((c, str(t), k, name, fc[k - 1], y[tk]))
    r = pd.DataFrame(rows, columns=["country", "origin", "h", "model", "forecast", "actual"])
    r["pct_error"] = (r.forecast - r.actual) / r.actual * 100
    r["period"] = np.where(r.origin <= "2022-09", "selection", "test")
    out = DATA / "backtest"
    out.mkdir(exist_ok=True)
    r.to_csv(out / "backtest_errors.csv", index=False)
    return r


def summarise(r):
    r = r.assign(ape=r.pct_error.abs())
    print("\nAverage absolute % error, all horizons 1-12 months")
    print(r.pivot_table(index="model", columns="period", values="ape", aggfunc="mean").round(2))
    print("\nBy country, test period")
    print(r[r.period == "test"].pivot_table(index="country", columns="model", values="ape", aggfunc="mean").round(1))
    print("\nBy horizon (test period)")
    print(r[r.period == "test"].pivot_table(index="h", columns="model", values="ape", aggfunc="mean").round(1).loc[[1, 3, 6, 12]])


if __name__ == "__main__":
    summarise(run())
