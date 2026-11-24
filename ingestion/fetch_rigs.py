"""Update oil rig counts from Baker Hughes' monthly Worldwide Rig Count report.

The report's download link changes every month, so this script reads the
international rig count page and takes the newest "Worldwide Rig Count" Excel
file. The report covers January 2024 onwards; older months (2013 to 2023)
come from the archive file saved in data/reference.

This is the most fragile step in the pipeline. If anything goes wrong
(page changed, download blocked, file layout changed), the script keeps the
previous rig data, writes a warning to data/quality/rig_warning.txt, and
exits without failing the run.

Run from the project root:  python ingestion/fetch_rigs.py
    python ingestion/fetch_rigs.py --file path/to/report.xlsx   (use a local file)
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import CLEAN, DATA, RAW, REFERENCE, RIG_BASE_URL, RIG_COUNTRIES, RIG_PAGE_URL  # noqa: E402
from http_utils import download, get  # noqa: E402

OUT = CLEAN / "oil_rigs.csv"
WARN = DATA / "quality" / "rig_warning.txt"
COLS = ["country", "region", "drill_for", "location", "rig_status", "month", "rigs", "source"]


def newest_report_url():
    html = get(RIG_PAGE_URL).text
    # Each file is listed as a link to /static-files/<id> near its title. The
    # newest report is listed first; the archive files mention "Archive" or a
    # year range, so skip those.
    found = list(re.finditer(r'(?:https://[^"\']*)?/static-files/[0-9a-f-]{36}', html))
    for i, m in enumerate(found):
        stop = found[i + 1].start() if i + 1 < len(found) else m.end() + 300
        context = re.sub(r"<[^>]+>", " ", html[m.end(): min(stop, m.end() + 300)]).lower()
        if "worldwide rig count" in context and "new report" in context and "2013" not in context:
            href = m.group(0)
            return href if href.startswith("http") else RIG_BASE_URL + href
    raise RuntimeError("No Worldwide Rig Count link found on the page")


def read_report(path):
    raw = pd.read_excel(path, sheet_name="WW Monthly", header=None)
    hdr = raw.index[raw[0] == "Region"][0]
    cols = [str(c) for c in raw.iloc[hdr]]
    n = cols.index("Rig Count Value") + 1
    d = raw.iloc[hdr + 1:, :n]
    d.columns = cols[:n]
    d = d.dropna(subset=["Country"])
    d = d[d.Country.isin(RIG_COUNTRIES)]
    if "Rig Status" not in d:
        d["Rig Status"] = "Active Rigs"
    out = pd.DataFrame({
        "country": d.Country.values, "region": d.Region.values, "drill_for": d.DrillFor.values,
        "location": d.Location.values, "rig_status": d["Rig Status"].values,
        "month": pd.to_datetime(dict(year=d.Year.astype(int), month=d.Month.astype(int), day=1)).dt.strftime("%Y-%m").values,
        "rigs": d["Rig Count Value"].astype(float).round(2).values,
    })
    out["source"] = f"Baker Hughes Worldwide Rig Count ({Path(path).name})"
    if out.empty or out.country.nunique() < 8:
        raise RuntimeError("Report has fewer than 8 of our countries; layout may have changed")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="local report .xlsx (skips the download)")
    args = ap.parse_args()

    current = pd.read_csv(OUT) if OUT.exists() else pd.read_csv(
        REFERENCE / "baker_hughes_rigs_monthly_10_countries_long.csv")
    WARN.parent.mkdir(parents=True, exist_ok=True)
    try:
        path = args.file
        if not path:
            url = newest_report_url()
            print(f"Downloading {url}")
            path = download(url, RAW / "worldwide_rig_count.xlsx")
        new = read_report(path)
    except Exception as e:  # keep last month's data rather than fail the run
        msg = f"Rig update skipped, previous data kept: {e}"
        print("WARNING:", msg)
        WARN.write_text(msg)
        current.to_csv(OUT, index=False)
        return

    start = new.month.min()
    # Keep the archive months before the report starts, plus the Saudi
    # old-method overlap rows (used to put Saudi on one basis).
    keep = current[(current.month < start) | (current.rig_status == "Active Rigs (old method, overlap)")]
    merged = pd.concat([keep, new])[COLS].sort_values(["country", "month", "rig_status", "drill_for", "location"])
    CLEAN.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT, index=False)
    WARN.unlink(missing_ok=True)
    print(f"  {len(merged):,} rows, {merged.month.min()} to {merged.month.max()}")


if __name__ == "__main__":
    main()
