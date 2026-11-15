"""Saves every crew member's daily check-ins in a small SQLite database (data/orbit_check.db).

The file is created on first run and seeded with one demo astronaut. On a laptop or in a
Codespace it persists between runs. On free Streamlit Cloud it lasts while the app is running
but is reset whenever the app restarts or is redeployed.
"""
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from environments import DEFAULT_ENV
from nasa import SEVERITY_WORDS, sep_on
from routine import MEASURE_TASKS, tasks_for
from simulate import DEFAULT_START, generate_mission

DB = Path(__file__).parent / "data" / "orbit_check.db"
DEMO_CREW = "Demo astronaut"
VITALS = ["heart_rate", "systolic", "diastolic", "glucose", "temp_c", "sleep_hrs", "mood", "radiation_msv"]
COLUMNS = ["day", "date", *VITALS, "sep_event", "note"]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS crew (
    name        TEXT PRIMARY KEY,
    start_date  TEXT NOT NULL,
    environment TEXT NOT NULL DEFAULT 'station'
);
CREATE TABLE IF NOT EXISTS tasks (
    crew     TEXT NOT NULL,
    day      INTEGER NOT NULL,
    task_id  TEXT NOT NULL,
    done     INTEGER NOT NULL DEFAULT 1,      -- for the quiz: 1 = answered correctly, 0 = not
    saved_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (crew, day, task_id)
);
CREATE TABLE IF NOT EXISTS checkins (
    crew       TEXT NOT NULL REFERENCES crew(name) ON DELETE CASCADE,
    day        INTEGER NOT NULL,
    date       TEXT NOT NULL,
    {", ".join(f"{v} REAL NOT NULL" for v in VITALS)},
    sep_event  TEXT NOT NULL DEFAULT '',
    note       TEXT NOT NULL DEFAULT '',
    saved_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (crew, day)
);
"""


def _connect(path=None):
    path = Path(path or DB)
    path.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init(path=None):
    """Create the tables, and a demo astronaut with a full 90-day mission if nobody exists yet."""
    with _connect(path) as con:
        con.executescript(SCHEMA)
        cols = [r[1] for r in con.execute("PRAGMA table_info(crew)")]
        if "environment" not in cols:          # databases made by an older version
            con.execute("ALTER TABLE crew ADD COLUMN environment TEXT NOT NULL DEFAULT 'station'")
        empty = con.execute("SELECT COUNT(*) FROM crew").fetchone()[0] == 0
    if empty:
        add_crew(DEMO_CREW, DEFAULT_START, demo=True, path=path)


def list_crew(path=None):
    with _connect(path) as con:
        return [r[0] for r in con.execute("SELECT name FROM crew ORDER BY rowid")]


def start_date(name, path=None):
    with _connect(path) as con:
        row = con.execute("SELECT start_date FROM crew WHERE name = ?", (name,)).fetchone()
    return date.fromisoformat(row[0]) if row else DEFAULT_START


def environment(name, path=None):
    with _connect(path) as con:
        row = con.execute("SELECT environment FROM crew WHERE name = ?", (name,)).fetchone()
    return row[0] if row else DEFAULT_ENV


def add_crew(name, start, demo=False, env_key=DEFAULT_ENV, path=None):
    """Add a crew member. demo=True fills their log with a simulated 90-day mission."""
    name = name.strip()
    if not name:
        raise ValueError("Please enter a name.")
    with _connect(path) as con:
        if con.execute("SELECT 1 FROM crew WHERE name = ?", (name,)).fetchone():
            raise ValueError(f"{name} is already on the crew list.")
        con.execute("INSERT INTO crew (name, start_date, environment) VALUES (?, ?, ?)",
                    (name, start.isoformat(), env_key))
    if demo:
        restart(name, start, demo=True, env_key=env_key, path=path)


def delete_crew(name, path=None):
    with _connect(path) as con:
        con.execute("DELETE FROM checkins WHERE crew = ?", (name,))
        con.execute("DELETE FROM tasks WHERE crew = ?", (name,))
        con.execute("DELETE FROM crew WHERE name = ?", (name,))


def restart(name, start, demo, env_key=None, path=None):
    """Wipe a crew member's log and start a new mission (empty, or with demo data),
    optionally in a different environment."""
    env_key = env_key or environment(name, path)
    with _connect(path) as con:
        con.execute("DELETE FROM checkins WHERE crew = ?", (name,))
        con.execute("DELETE FROM tasks WHERE crew = ?", (name,))
        con.execute("UPDATE crew SET start_date = ?, environment = ? WHERE name = ?",
                    (start.isoformat(), env_key, name))
    if demo:
        df = generate_mission(start=start, env_key=env_key).assign(note="")
        rows = [_row(name, r) for r in df.to_dict("records")]
        with _connect(path) as con:
            con.executemany(_INSERT, rows)
            con.executemany("INSERT OR REPLACE INTO tasks (crew, day, task_id, done) VALUES (?, ?, ?, ?)",
                            _demo_tasks(name, df, env_key))


def _demo_tasks(name, df, env_key, seed=7):
    """Simulated routine history: most actions done, fewer during the rough patch (days 40-55)."""
    rng = np.random.default_rng(seed)
    out = []
    for day in df["day"]:
        rough = 40 <= day <= 55
        for t in tasks_for(env_key):
            if t.kind == "measure" or rng.random() < (0.45 if rough else 0.9):
                out.append((name, int(day), t.id, 1))
        if rng.random() < 0.8:
            out.append((name, int(day), "quiz", int(rng.random() < 0.75)))
    return out


def load(name, path=None):
    """All of a crew member's saved days, oldest first."""
    with _connect(path) as con:
        df = pd.read_sql_query(f"SELECT {', '.join(COLUMNS)} FROM checkins WHERE crew = ? ORDER BY day",
                               con, params=(name,))
    df["date"] = pd.to_datetime(df["date"])
    df["mood"] = df["mood"].astype(int)
    return df


def date_for(name, day, path=None):
    return pd.Timestamp(start_date(name, path)) + pd.Timedelta(days=day - 1)


def save_day(name, day, vitals, note="", path=None):
    """Insert or overwrite one day. The calendar date and any real NASA solar
    particle event on that date are filled in automatically."""
    when = date_for(name, day, path)
    ev = sep_on(when)
    rec = dict(day=day, date=when, **{v: vitals[v] for v in VITALS}, note=note.strip(),
               sep_event=SEVERITY_WORDS[ev["severity"]] if ev is not None else "")
    with _connect(path) as con:
        con.execute(_INSERT, _row(name, rec))
        # logging the day covers every measurement task in the routine
        con.executemany("INSERT OR REPLACE INTO tasks (crew, day, task_id, done) VALUES (?, ?, ?, 1)",
                        [(name, day, t.id) for t in MEASURE_TASKS])


def delete_day(name, day, path=None):
    with _connect(path) as con:
        con.execute("DELETE FROM checkins WHERE crew = ? AND day = ?", (name, day))
        con.execute("DELETE FROM tasks WHERE crew = ? AND day = ?", (name, day))


def set_task(name, day, task_id, done=True, path=None):
    """Tick (or untick) a routine task. For the quiz, done = answered correctly."""
    with _connect(path) as con:
        if done is None:
            con.execute("DELETE FROM tasks WHERE crew = ? AND day = ? AND task_id = ?", (name, day, task_id))
        else:
            con.execute("INSERT OR REPLACE INTO tasks (crew, day, task_id, done) VALUES (?, ?, ?, ?)",
                        (name, day, task_id, int(done)))


def load_tasks(name, path=None):
    with _connect(path) as con:
        return pd.read_sql_query("SELECT day, task_id, done FROM tasks WHERE crew = ? ORDER BY day",
                                 con, params=(name,))


_INSERT = (f"INSERT OR REPLACE INTO checkins (crew, {', '.join(COLUMNS)}) "
           f"VALUES ({', '.join('?' * (len(COLUMNS) + 1))})")


def _row(name, rec):
    when = pd.Timestamp(rec["date"]).date().isoformat()
    return (name, int(rec["day"]), when, *(float(rec[v]) for v in VITALS),
            rec.get("sep_event") or "", rec.get("note") or "")
