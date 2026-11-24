"""Download the JODI-Oil bulk files and keep only our countries and series.

The two bulk zips hold every country, product and flow since 2002
(the primary CSV alone is about 290 MB unzipped). We read them in chunks,
keep the 12 countries and the series listed in config.JODI_SERIES, and
write one tidy file: data/clean/jodi.csv.

Run from the project root:
    python ingestion/fetch_jodi.py
    python ingestion/fetch_jodi.py --primary path/to/primary.csv   (use a local file instead)
"""
import argparse
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import CLEAN, COUNTRIES, JODI_SERIES, JODI_URLS, RAW, REGION  # noqa: E402
from http_utils import download  # noqa: E402

COLS = ["REF_AREA", "TIME_PERIOD", "ENERGY_PRODUCT", "FLOW_BREAKDOWN", "UNIT_MEASURE", "OBS_VALUE"]


def open_csv(path):
    """Return a text stream for a .csv or for the single .csv inside a .zip."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        z = zipfile.ZipFile(path)
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        return io.TextIOWrapper(z.open(name), encoding="utf-8")
    return open(path, encoding="utf-8")


def extract(path, table):
    wanted = {(p, f, u): v for (t, p, f, u), v in JODI_SERIES.items() if t == table}
    keep = []
    with open_csv(path) as fh:
        for chunk in pd.read_csv(fh, usecols=COLS, dtype=str, chunksize=500_000):
            chunk = chunk[chunk.REF_AREA.isin(COUNTRIES)]
            key = list(zip(chunk.ENERGY_PRODUCT, chunk.FLOW_BREAKDOWN, chunk.UNIT_MEASURE))
            chunk = chunk[[k in wanted for k in key]]
            keep.append(chunk)
    d = pd.concat(keep, ignore_index=True)
    if d.empty:
        raise RuntimeError(f"No rows for our countries in the {table} file. Has the format changed?")
    mapped = [wanted[k] for k in zip(d.ENERGY_PRODUCT, d.FLOW_BREAKDOWN, d.UNIT_MEASURE)]
    out = pd.DataFrame({
        "country": d.REF_AREA.map(lambda c: COUNTRIES[c][0]),
        "product": [m[0] for m in mapped],
        "flow": [m[1] for m in mapped],
        "month": d.TIME_PERIOD,
        # JODI uses "-" (not reported) and "x" (confidential); both become empty
        "value": pd.to_numeric(d.OBS_VALUE, errors="coerce"),
        "unit": [m[2] for m in mapped],
    })
    out["region"] = out.country.map(REGION)
    out["table"] = table
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", help="local primary .csv or .zip (skips the download)")
    ap.add_argument("--secondary", help="local secondary .csv or .zip (skips the download)")
    args = ap.parse_args()

    parts = []
    for table in ("primary", "secondary"):
        path = getattr(args, table)
        if not path:
            path = RAW / f"world_{table}_csv.zip"
            print(f"Downloading JODI {table} file...")
            download(JODI_URLS[table], path)
            print(f"  {path.stat().st_size / 1e6:.0f} MB")
        print(f"Extracting our series from the {table} file...")
        part = extract(path, table)
        print(f"  {len(part):,} rows, {part.month.min()} to {part.month.max()}")
        parts.append(part)

    jodi = pd.concat(parts, ignore_index=True)
    jodi = jodi[["table", "country", "region", "product", "flow", "month", "value", "unit"]]
    jodi = jodi.sort_values(["table", "product", "flow", "country", "month"])
    CLEAN.mkdir(parents=True, exist_ok=True)
    jodi.to_csv(CLEAN / "jodi.csv", index=False)
    print(f"Saved {len(jodi):,} rows to data/clean/jodi.csv")


if __name__ == "__main__":
    main()
