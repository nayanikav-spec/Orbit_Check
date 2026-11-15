"""Download the real NASA datasets Orbit Check uses and save them as small CSVs in data/.

Run once (the CSVs are committed, so the app works offline):
    NASA_API_KEY=your_key python nasa_data.py

1. NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information):
   solar energetic particle (SEP) events observed 2021-2025 (one row per day, with the
   instruments that detected it). https://ccmc.gsfc.nasa.gov/tools/DONKI/
2. NASA Open Science Data Repository (OSDR): SpaceX Inspiration4 crew blood tests
   before and after their 2021 flight.
   OSD-575 (Comprehensive Metabolic Panel), OSD-569 (Complete Blood Count).
"""
import io
import json
import os
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"
DONKI = "https://api.nasa.gov/DONKI"
OSDR = "https://osdr.nasa.gov/geode-py/ws/studies/{osd}/download?source=datamanager&file={file}"
START, END = date(2021, 1, 1), date(2025, 12, 31)


def _get(url, key=None):
    req = urllib.request.Request(url, headers={"X-Api-Key": key} if key else {})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def _donki(kind, key):
    """DONKI only allows ~60-day windows per request, so walk the range in chunks."""
    out, s = [], START
    while s <= END:
        e = min(s + timedelta(days=59), END)
        body = _get(f"{DONKI}/{kind}?startDate={s}&endDate={e}", key)
        out += json.loads(body) if body.strip() else []
        s = e + timedelta(days=1)
    return out


def fetch_sep_events(key):
    rows = []
    for ev in _donki("SEP", key):
        observed = [i["displayName"] for i in ev.get("instruments", [])
                    if not i["displayName"].upper().startswith("MODEL")]
        if not observed:                      # skip forecast-only entries
            continue
        rows.append(dict(time=ev["eventTime"], instruments="; ".join(observed),
                         link=ev.get("link", "")))
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["time"]).dt.date
    # one row per day: the same storm is logged once per instrument
    daily = (df.sort_values("time")
               .groupby("date")
               .agg(first_time=("time", "first"),
                    detections=("time", "size"),
                    instruments=("instruments", lambda s: "; ".join(sorted(set("; ".join(s).split("; "))))),
                    link=("link", "first"))
               .reset_index())
    daily.to_csv(DATA / "donki_sep_events.csv", index=False)
    return daily


def fetch_inspiration4():
    cmp_raw = _get(OSDR.format(osd="OSD-575", file="LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv"))
    cmp_df = pd.read_csv(io.BytesIO(cmp_raw), encoding="utf-8-sig")
    cmp_df.to_csv(DATA / "inspiration4_cmp.csv", index=False)

    cbc_raw = _get(OSDR.format(osd="OSD-569", file="LSDS-7_Complete_Blood_Count_CBC_TRANSFORMED.csv"))
    cbc_df = pd.read_csv(io.BytesIO(cbc_raw), encoding="utf-8-sig")
    cbc_df.to_csv(DATA / "inspiration4_cbc.csv", index=False)
    return cmp_df, cbc_df


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    key = os.environ.get("NASA_API_KEY")
    if not key:
        print("No NASA_API_KEY set: DONKI requests may hit the shared rate limit.")
    sep = fetch_sep_events(key)
    print(f"DONKI: {len(sep)} days with observed solar particle events -> data/donki_sep_events.csv")
    cmp_df, cbc_df = fetch_inspiration4()
    print(f"OSDR: {len(cmp_df)} metabolic-panel rows, {len(cbc_df)} blood-count samples -> data/inspiration4_*.csv")
