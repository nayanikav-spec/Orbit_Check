"""SECTION 1: Simulated mission data.

The health readings are simulated (no real astronaut data), but the radiation days
replay REAL solar particle events recorded by NASA DONKI on the mission's calendar dates.
"""
from datetime import date

import numpy as np
import pandas as pd

from environments import DEFAULT_ENV, env
from nasa import SEVERITY_WORDS, sep_events

# Default replay window: covers the May 2024 solar storms.
DEFAULT_START = date(2024, 4, 1)
# Extra daily dose on a solar particle event day, by severity (illustrative values, mSv).
SEP_DOSE = {2: 1.4, 1: 0.45}


def generate_mission(days=90, seed=42, start=DEFAULT_START, env_key=DEFAULT_ENV):
    rng = np.random.default_rng(seed)
    d = np.arange(1, days + 1)
    df = pd.DataFrame({"day": d, "date": pd.date_range(start, periods=days)})

    # Normal "healthy astronaut" values with small daily noise
    df["heart_rate"] = rng.normal(66, 3, days)
    df["systolic"] = rng.normal(110, 3.5, days)
    df["diastolic"] = rng.normal(70, 2.5, days)
    df["glucose"] = rng.normal(87, 3.5, days)
    df["temp_c"] = rng.normal(36.7, 0.12, days)
    df["sleep_hrs"] = rng.normal(7.7, 0.3, days)
    df["mood"] = rng.normal(4.2, 0.4, days)
    e = env(env_key)
    df["radiation_msv"] = rng.normal(e.expected_msv, e.expected_msv * 0.08, days)   # typical dose here

    # Injected health problems so the demo has something to catch
    dip = (d >= 40) & (d <= 55)                      # sleep loss + low mood + higher HR
    df.loc[dip, "sleep_hrs"] -= 2.3
    df.loc[dip, "mood"] -= 1.6
    df.loc[dip, "heart_rate"] += 14

    late = d >= 65                                   # blood pressure slowly climbs
    df.loc[late, "systolic"] += np.linspace(0, 34, late.sum())
    df.loc[late, "diastolic"] += np.linspace(0, 16, late.sum())

    df.loc[(d >= 75) & (d <= 80), "glucose"] += 45   # blood sugar bump

    # Real space weather: NASA DONKI solar particle events on these calendar dates
    df["sep_event"] = ""
    ev = sep_events()
    ev = ev[(ev["severity"] > 0) & ev["date"].between(df["date"].iloc[0], df["date"].iloc[-1])]
    if len(ev):
        for _, ev_row in ev.iterrows():
            i = df.index[df["date"] == ev_row["date"]][0]
            df.loc[i, "radiation_msv"] += SEP_DOSE[ev_row["severity"]] * e.sep_multiplier
            df.loc[i, "sep_event"] = SEVERITY_WORDS[ev_row["severity"]]
    elif sep_events().empty:                         # no NASA file: keep a demo spike
        df.loc[d == 60, "radiation_msv"] += 1.4 * e.sep_multiplier

    df["mood"] = df["mood"].round().clip(1, 5).astype(int)
    df["radiation_msv"] = df["radiation_msv"].clip(lower=0)
    return df.round({"heart_rate": 0, "systolic": 0, "diastolic": 0, "glucose": 0,
                     "temp_c": 1, "sleep_hrs": 1, "radiation_msv": 2})
