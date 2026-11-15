"""Run with:  python -m pytest"""
import pandas as pd
import pytest

from rules import evaluate, needs_flight_surgeon, overall, status
from simulate import generate_mission


@pytest.mark.parametrize("ind, value, expected", [
    ("heart_rate", 100, "ok"), ("heart_rate", 101, "warn"), ("heart_rate", 121, "alert"),
    ("heart_rate", 55, "warn"), ("heart_rate", 49, "alert"),
    ("systolic", 119, "ok"), ("systolic", 120, "warn"), ("systolic", 140, "alert"), ("systolic", 85, "warn"),
    ("diastolic", 79, "ok"), ("diastolic", 80, "warn"), ("diastolic", 90, "alert"),
    ("glucose", 99, "ok"), ("glucose", 100, "warn"), ("glucose", 126, "alert"), ("glucose", 53, "alert"),
    ("temp_c", 37.2, "ok"), ("temp_c", 37.3, "warn"), ("temp_c", 38.0, "alert"), ("temp_c", 34.9, "alert"),
    ("sleep_hrs", 7, "ok"), ("sleep_hrs", 6.5, "warn"), ("sleep_hrs", 5.9, "alert"),
    ("mood", 3, "ok"), ("mood", 2, "warn"), ("mood", 1, "alert"),
    ("radiation_msv", 0.5, "ok"), ("radiation_msv", 0.6, "warn"), ("radiation_msv", 1.1, "alert"),
])
def test_status_matches_thresholds_md(ind, value, expected):
    assert status(ind, value) == expected


def _mission_with(day_values):
    df = generate_mission(days=30)
    for col, v in day_values.items():
        df.loc[df.index[-1], col] = v
    return df


def test_quiet_day_has_no_flags():
    df = generate_mission()
    assert evaluate(df, 10) == []


def test_bp_crisis_escalates():
    flags = evaluate(_mission_with({"systolic": 185, "diastolic": 95}))
    assert flags[0]["indicator"] == "bp_crisis"
    assert needs_flight_surgeon(flags)


def test_sleep_and_mood_patterns():
    df = generate_mission(days=30)
    df.loc[df.index[-3:], "sleep_hrs"] = 5.0
    df.loc[df.index[-3:], "mood"] = 2
    kinds = {f["indicator"] for f in evaluate(df)}
    assert {"pattern_sleep", "pattern_mood"} <= kinds


def test_baseline_shift_inside_safe_range():
    df = generate_mission(days=30)
    df["heart_rate"] = 62.0 + (df.index % 2)       # steady 62-63 bpm
    df.loc[df.index[-1], "heart_rate"] = 85        # safe range, but a big jump for this person
    f = [f for f in evaluate(df) if f["indicator"] == "heart_rate"]
    assert f and f[0]["level"] == "warn" and "YOUR" in f[0]["why"]


def test_demo_mission_catches_injected_events():
    df = generate_mission()
    levels = {d: overall(evaluate(df, d - 1)) for d in (41, 45, 78, 90)}
    assert all(lv == "alert" for lv in levels.values()), levels


def test_real_solar_particle_events_are_urgent():
    df = generate_mission()                        # default replay: Apr-Jun 2024
    may11 = df.index[df["date"] == "2024-05-11"][0]
    flags = evaluate(df, may11)
    sep = [f for f in flags if f["indicator"] == "sep_event"]
    assert sep and sep[0]["level"] == "alert" and "11 May 2024" in sep[0]["why"]


def test_far_side_only_events_are_ignored():
    from nasa import sep_events, sep_on
    ev = sep_events()
    far = ev[ev["severity"] == 0]
    assert len(far) and all(sep_on(d) is None for d in far["date"])
