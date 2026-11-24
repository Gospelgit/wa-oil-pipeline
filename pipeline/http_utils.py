"""Downloads with retries (networks blip; one failure shouldn't sink a run)."""
import time

import requests

from config import HEADERS


def get(url, retries=4, timeout=120, stream=False):
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, stream=stream)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            wait = 5 * attempt
            print(f"  attempt {attempt} failed ({e}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Could not download {url}: {last}")


def download(url, path, retries=4):
    """Stream a (possibly large) file to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    r = get(url, retries=retries, timeout=300, stream=True)
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    return path
