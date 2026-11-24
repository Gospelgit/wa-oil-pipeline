"""Download the monthly Brent price from FRED (series MCOILBRENTEU, from the US EIA).

No account or key is needed. Writes data/clean/brent_monthly.csv.
Run from the project root:  python ingestion/fetch_brent.py
"""
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import CLEAN, FRED_BRENT_URL  # noqa: E402
from http_utils import get  # noqa: E402


def main():
    print("Downloading Brent from FRED...")
    d = pd.read_csv(io.StringIO(get(FRED_BRENT_URL).text))
    date_col = d.columns[0]  # "observation_date" (older files used "DATE")
    d = pd.DataFrame({
        "month": pd.to_datetime(d[date_col]).dt.strftime("%Y-%m"),
        "brent_usd_per_barrel": pd.to_numeric(d["MCOILBRENTEU"], errors="coerce"),
    }).dropna()
    d = d[d.month >= "2002-01"]
    d["source"] = "FRED MCOILBRENTEU (EIA Brent spot, monthly avg)"
    if len(d) < 250:
        raise RuntimeError(f"Only {len(d)} Brent months came back; expected 250+")
    CLEAN.mkdir(parents=True, exist_ok=True)
    d.to_csv(CLEAN / "brent_monthly.csv", index=False)
    print(f"  {len(d)} months, latest {d.month.max()} at ${d.brent_usd_per_barrel.iloc[-1]:.2f}")


if __name__ == "__main__":
    main()
