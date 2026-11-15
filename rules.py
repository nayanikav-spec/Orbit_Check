"""SECTION 2: The rules. Compares readings to safe ranges AND the person's own baseline,
then explains every flag in plain English and ties it to a NASA hazard/risk.

The ranges below follow thresholds.md (AHA, CDC and ADA categories plus team-set bands).
Keep the two in sync: the Guide tab renders its table straight from LIMITS.
"""
from dataclasses import dataclass

from environments import DEFAULT_ENV, env

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Limits:
    """Caution/urgent cut-offs for one indicator. None = no limit on that side.

    Low side: below warn_lo is caution, below alert_lo is urgent.
    High side: above warn_hi is caution, above alert_hi is urgent
    (or "at or above" when hi_inclusive=True, as in the AHA/ADA categories).
    """
    warn_lo: float | None = None
    warn_hi: float | None = None
    alert_lo: float | None = None
    alert_hi: float | None = None
    hi_inclusive: bool = False
    source: str = ""

    def _over(self, v, limit):
        return limit is not None and (v >= limit if self.hi_inclusive else v > limit)

    def status(self, v):
        if (self.alert_lo is not None and v < self.alert_lo) or self._over(v, self.alert_hi):
            return "alert"
        if (self.warn_lo is not None and v < self.warn_lo) or self._over(v, self.warn_hi):
            return "warn"
        return "ok"


LIMITS = {
    "heart_rate":    Limits(warn_lo=60, warn_hi=100, alert_lo=50, alert_hi=120,
                            source="Green: AHA. Caution/urgent: team-set"),
    "systolic":      Limits(warn_lo=90, warn_hi=120, alert_hi=140, hi_inclusive=True,
                            source="AHA categories. Low cut-off: team-set"),
    "diastolic":     Limits(warn_lo=60, warn_hi=80, alert_hi=90, hi_inclusive=True,
                            source="AHA categories. Low cut-off: team-set"),
    "glucose":       Limits(warn_lo=70, warn_hi=100, alert_lo=54, alert_hi=126, hi_inclusive=True,
                            source="American Diabetes Association (fasting)"),
    "temp_c":        Limits(warn_lo=36.1, warn_hi=37.3, alert_lo=35.0, alert_hi=38.0, hi_inclusive=True,
                            source="CDC (fever 38.0 C, hypothermia 35 C). Caution: team-set"),
    "sleep_hrs":     Limits(warn_lo=7, alert_lo=6, source="Green: CDC. Caution/urgent: team-set"),
    "mood":          Limits(warn_lo=3, alert_lo=2, source="Team-set (our own 1-5 scale)"),
    "radiation_msv": Limits(warn_hi=0.5, alert_hi=1.0, source="Reference: NASA. Cut-offs: team-set"),
}
INDICATORS = list(LIMITS)

# Hypertensive crisis (AHA): contact the flight surgeon immediately.
BP_CRISIS = (180, 120)
# NASA career effective-dose limit for astronauts.
CAREER_LIMIT_MSV = 600

LABELS = {"heart_rate": "Heart rate", "systolic": "Systolic BP", "diastolic": "Diastolic BP",
          "glucose": "Blood sugar", "temp_c": "Body temp", "sleep_hrs": "Sleep",
          "mood": "Mood", "radiation_msv": "Radiation (daily)"}

UNITS = {"heart_rate": "bpm", "systolic": "mmHg", "diastolic": "mmHg", "glucose": "mg/dL",
         "temp_c": "°C", "sleep_hrs": "hrs", "mood": "/5", "radiation_msv": "mSv"}

# Decimal places used when showing each indicator.
DECIMALS = {"heart_rate": 0, "systolic": 0, "diastolic": 0, "glucose": 0,
            "temp_c": 1, "sleep_hrs": 1, "mood": 0, "radiation_msv": 2}

# indicator -> (NASA hazard, NASA risk). Risk names come from NASA's Risks page;
# the hazard assignment is our own mapping.
HAZARD = {
    "heart_rate":    ("Gravity fields", "Risk of Cardiovascular Adaptations"),
    "systolic":      ("Gravity fields", "Risk of Cardiovascular Adaptations"),
    "diastolic":     ("Gravity fields", "Risk of Cardiovascular Adaptations"),
    "glucose":       ("Hostile/closed environments", "Risk of Inadequate Food and Nutrition"),
    "temp_c":        ("Hostile/closed environments", "Risk of Altered Immune System Responses"),
    "sleep_hrs":     ("Isolation and confinement", "Risk of Inadequate Sleep and Irregular Schedules"),
    "mood":          ("Isolation and confinement", "Risk of Behavioral Changes and Psychiatric Disorders"),
    "radiation_msv": ("Space radiation", "Risk of Radiation-Induced Cancers"),
}

ACTIONS = {
    "heart_rate": "Rest, hydrate, and retake the reading in 30 minutes. Keep up your exercise routine.",
    "systolic": "Sit quietly for 5 minutes, then retake it. Log it again tomorrow.",
    "diastolic": "Sit quietly for 5 minutes, then retake it. Log it again tomorrow.",
    "glucose": "Think about your last meal, then retest. Log what you ate.",
    "temp_c": "Retake after 15 minutes and watch for other symptoms.",
    "sleep_hrs": "Protect your sleep window and wind down before bed.",
    "mood": "Talk with a crewmate or schedule a private call with ground support.",
    "radiation_msv": "Follow your mission radiation protocol and check in with ground control.",
}

SURGEON = "Contact your flight surgeon. "
Z_LIMIT = 3.0        # how many "standard deviations from your own normal" counts as a shift
BASELINE_DAYS = 14   # length of the personal-baseline window
MIN_BASELINE = 7     # need at least this many earlier days before comparing to baseline
ANOMALY_MIN_DAYS = 21


def fmt(ind, v):
    return f"{v:.{DECIMALS[ind]}f}"


def limits(ind, env_key=DEFAULT_ENV):
    """Limits for one indicator. Radiation depends on where the mission is."""
    if ind != "radiation_msv" or env_key == DEFAULT_ENV:
        return LIMITS[ind]
    e = env(env_key)
    return Limits(warn_hi=e.rad_warn, alert_hi=e.rad_alert,
                  source=f"Typical here: {e.expected_msv} mSv/day (published measurement). Cut-offs: team-set")


def status(ind, v, env_key=DEFAULT_ENV):
    return limits(ind, env_key).status(v)


def baseline(df, ind, idx, window=BASELINE_DAYS):
    """The person's own recent normal: mean and spread of the previous `window` days."""
    prev = df[ind].iloc[max(0, idx - window):idx]
    if len(prev) < MIN_BASELINE:
        return None
    return prev.mean(), prev.std()


def _flag(indicator, level, title, why, hazard, risk, action):
    return dict(indicator=indicator, level=level, title=title, why=why,
                hazard=hazard, risk=risk, action=action)


def _anomaly_flag(df, idx):
    """Isolation Forest over all indicators: is today an unusual *combination* of readings
    compared with the earlier days of this mission? Catches drifts no single range would."""
    if idx < ANOMALY_MIN_DAYS:
        return None
    from sklearn.ensemble import IsolationForest

    hist = df[INDICATORS].iloc[:idx].to_numpy(dtype=float)
    mu, sd = hist.mean(axis=0), hist.std(axis=0)
    sd[sd == 0] = 1.0
    model = IsolationForest(n_estimators=100, random_state=0).fit((hist - mu) / sd)
    today = (df[INDICATORS].iloc[idx].to_numpy(dtype=float) - mu) / sd
    if model.decision_function(today.reshape(1, -1))[0] >= -0.05:
        return None
    top = [INDICATORS[i] for i in np.argsort(-np.abs(today))[:2]]
    names = " and ".join(LABELS[i].lower() for i in top)
    return _flag("anomaly", "warn", "Unusual combination of readings",
                 f"Each reading may look fine on its own, but together they are unlike any "
                 f"earlier day of your mission. The biggest shifts are in {names}.",
                 HAZARD[top[0]][0], HAZARD[top[0]][1],
                 "Retake today's readings. If they hold, mention it at your next medical conference.")


def evaluate(df, idx=None, env_key=DEFAULT_ENV):
    """Return a list of flags for one mission day (0-based row index)."""
    idx = len(df) - 1 if idx is None else idx
    row = df.iloc[idx]
    flags = []

    for ind in INDICATORS:
        v = row[ind]
        s, b = status(ind, v, env_key), baseline(df, ind, idx)
        hazard, risk = HAZARD[ind]
        reading = f"{LABELS[ind]} is {fmt(ind, v)} {UNITS[ind]}"
        if s != "ok":
            level = s
            why = f"{reading}, outside the {'urgent' if s == 'alert' else 'caution'} limit."
            if ind == "radiation_msv":
                why += f" A typical day in the {env(env_key).short.lower()} is about {env(env_key).expected_msv} mSv."
            if b:
                why += f" Your own {BASELINE_DAYS}-day average is {fmt(ind, b[0])}."
        elif b and b[1] > 0 and abs(v - b[0]) / b[1] >= Z_LIMIT:
            level = "warn"
            why = (f"{reading}. That's inside the safe range, but far from YOUR "
                   f"{BASELINE_DAYS}-day average of {fmt(ind, b[0])}, so it's a real change for you.")
        else:
            continue
        action = ACTIONS[ind] if level == "warn" else SURGEON + ACTIONS[ind]
        flags.append(_flag(ind, level, f"{LABELS[ind]}: {fmt(ind, v)} {UNITS[ind]}",
                           why, hazard, risk, action))

    # Real solar particle event on this calendar day (NASA DONKI). thresholds.md: always urgent.
    sep = row.get("sep_event", "")
    if isinstance(sep, str) and sep:
        when = f" on {row['date']:%d %b %Y}" if "date" in row and pd.notna(row["date"]) else ""
        flags.append(_flag(
            "sep_event", "alert", "Solar particle event alert",
            f"NASA's DONKI space-weather database recorded a {sep} solar particle event{when}. "
            "Bursts of fast protons from the Sun can raise your dose within hours.",
            *HAZARD["radiation_msv"],
            SURGEON + f"Go to {env(env_key).shelter} until the all-clear."))

    # Hypertensive crisis
    if row["systolic"] >= BP_CRISIS[0] or row["diastolic"] >= BP_CRISIS[1]:
        flags.insert(0, _flag(
            "bp_crisis", "alert", f"Blood pressure crisis: {row['systolic']:.0f}/{row['diastolic']:.0f}",
            f"Readings of {BP_CRISIS[0]}/{BP_CRISIS[1]} or higher are a hypertensive crisis.",
            *HAZARD["systolic"], "Contact your flight surgeon NOW. Rest and retake in 5 minutes."))

    # Multi-day patterns (thresholds.md: 3 in a row)
    recent = df.iloc[max(0, idx - 2):idx + 1]
    if len(recent) == 3 and (recent["sleep_hrs"] < 6).all():
        low_mood = row["mood"] < 3
        flags.append(_flag(
            "pattern_sleep", "alert", "Sleep-loss pattern (3 nights in a row)",
            "You've slept under 6 hours three nights running"
            + (" and your mood is low" if low_mood else "")
            + ". Hazards feed off each other: isolation and chronic sleep loss make each other worse.",
            "Isolation and confinement", "Risk of Inadequate Sleep and Irregular Schedules",
            SURGEON + ACTIONS["sleep_hrs"]))
    if len(recent) == 3 and (recent["mood"] <= 2).all():
        flags.append(_flag(
            "pattern_mood", "alert", "Low-mood pattern (3 days in a row)",
            "Your mood has been 2 or lower for three days running. "
            "A low mood is a signal, not a weakness.",
            *HAZARD["mood"], SURGEON + ACTIONS["mood"]))

    # Whole-picture check, only when nothing else already explains the day
    if not flags:
        a = _anomaly_flag(df, idx)
        if a:
            flags.append(a)
    return flags


def overall(flags):
    levels = {f["level"] for f in flags}
    return "alert" if "alert" in levels else "warn" if "warn" in levels else "ok"


def needs_flight_surgeon(flags):
    """Far from Earth, help is delayed: escalate on any urgent flag or 3+ cautions."""
    return any(f["level"] == "alert" for f in flags) or sum(f["level"] == "warn" for f in flags) >= 3
