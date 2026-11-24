"""Check whether any source has published something new since the last run.

  JODI:   Last-Modified / ETag / size of the two bulk zips (a cheap HEAD request)
  FRED:   the newest Brent month
  Rigs:   the link of the newest Baker Hughes report (it changes each month)

Prints the result, and in GitHub Actions sets the step output changed=true/false
so the workflow can skip the full run when nothing is new.

    python ingestion/check_updates.py          # compare with state/last_updated.json
    python ingestion/check_updates.py --save   # record the current fingerprints
"""
import argparse
import io
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from config import FRED_BRENT_URL, HEADERS, JODI_URLS, STATE  # noqa: E402
from http_utils import get  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_rigs import newest_report_url  # noqa: E402

STATE_FILE = STATE / "last_updated.json"


def fingerprints():
    fp = {}
    for name, url in JODI_URLS.items():
        try:
            h = requests.head(url, headers=HEADERS, timeout=60, allow_redirects=True).headers
            fp[f"jodi_{name}"] = "|".join(h.get(k, "") for k in ("Last-Modified", "ETag", "Content-Length"))
        except requests.RequestException as e:
            fp[f"jodi_{name}"] = f"unreachable: {e.__class__.__name__}"
    try:
        d = pd.read_csv(io.StringIO(get(FRED_BRENT_URL, retries=2).text))
        fp["brent_latest_month"] = str(d.iloc[-1, 0])[:7]
    except Exception as e:
        fp["brent_latest_month"] = f"unreachable: {e.__class__.__name__}"
    try:
        fp["rig_report_url"] = newest_report_url()
    except Exception as e:
        fp["rig_report_url"] = f"unreachable: {e.__class__.__name__}"
    return fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    now = fingerprints()
    if args.save:
        STATE.mkdir(exist_ok=True)
        STATE_FILE.write_text(json.dumps(now, indent=2))
        print("Saved fingerprints:", json.dumps(now, indent=2))
        return

    before = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    new = [k for k, v in now.items() if not v.startswith("unreachable") and before.get(k) != v]
    changed = bool(new) or not before
    for k, v in now.items():
        print(f"{k:20} {'NEW' if k in new else 'same':5} {v}")
    print("changed =", changed)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()
