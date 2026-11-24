"""Forecasting models for monthly crude oil production.

Every model takes a monthly series (pandas Series, indexed by month, no gaps
at the end) and returns forecasts for the next `h` months.
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

H = 12  # forecast horizon in months


def naive(y, h=H, **_):
    """Last value carried forward."""
    return np.repeat(y.iloc[-1], h)


def mean3(y, h=H, **_):
    """Average of the last 3 months carried forward (smooths out one-off outages)."""
    return np.repeat(y.iloc[-3:].mean(), h)


def damped_holt(y, h=H, **_):
    """Exponential smoothing with a damped trend, fitted on the last 10 years."""
    y = y.iloc[-120:].astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(y.values, trend="add", damped_trend=True).fit()
    return fit.forecast(h)


def blend(y, h=H, **_):
    """Average of mean3 and damped Holt."""
    return (mean3(y, h) + damped_holt(y, h)) / 2


def drivers(y, h=H, brent=None, rigs=None, coefs=None, **_):
    """mean3 adjusted by last year's change in Brent and oil rigs.

    coefs: dict horizon -> (a, b_brent, b_rigs), fitted on past data only.
    Change in log production from now to now+k = a + b1*dlog(Brent, past 12m)
    + b2*dlog(rigs, past 12m).
    """
    base = y.iloc[-3:].mean()
    t = y.index[-1]
    xb = _dlog12(brent, t)
    xr = _dlog12(rigs, t) if rigs is not None else 0.0
    out = []
    for k in range(1, h + 1):
        a, b1, b2 = coefs[k]
        out.append(base * np.exp(a + b1 * xb + b2 * (xr if np.isfinite(xr) else 0.0)))
    return np.array(out)


def _dlog12(s, t):
    if s is None:
        return np.nan
    s = s.dropna()
    s = s[s.index <= t]
    if len(s) < 13 or s.iloc[-13] <= 0 or s.iloc[-1] <= 0:
        return np.nan
    return float(np.log(s.iloc[-1]) - np.log(s.iloc[-13]))


def fit_driver_coefs(panel, brent, rigs_by_country, cutoff, h=H):
    """Pooled least squares across countries, using only data up to `cutoff`."""
    rows = {k: [] for k in range(1, h + 1)}
    for c, y in panel.items():
        y = y.dropna()
        rg = rigs_by_country.get(c)
        months = y.index[(y.index <= cutoff)]
        for t in months[24:]:
            hist = y[y.index <= t]
            if len(hist) < 3 or (hist.index[-1] != t):
                continue
            base = hist.iloc[-3:].mean()
            xb = _dlog12(brent, t)
            xr = _dlog12(rg, t) if rg is not None else 0.0
            if not (np.isfinite(xb) and np.isfinite(xr)):
                continue
            for k in range(1, h + 1):
                tk = t + k
                if tk > cutoff or tk not in y.index or not np.isfinite(y[tk]) or y[tk] <= 0:
                    continue
                rows[k].append((np.log(y[tk] / base), xb, xr))
    coefs = {}
    for k, r in rows.items():
        a = np.array(r)
        if len(a) < 50:
            coefs[k] = (0.0, 0.0, 0.0)
            continue
        X = np.column_stack([np.ones(len(a)), a[:, 1], a[:, 2]])
        beta, *_ = np.linalg.lstsq(X, a[:, 0], rcond=None)
        coefs[k] = tuple(beta)
    return coefs


MODELS = {
    "naive": naive,
    "mean3": mean3,
    "damped_holt": damped_holt,
    "blend": blend,
    "drivers": drivers,
}
