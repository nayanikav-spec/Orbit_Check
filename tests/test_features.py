"""Run with:  python -m pytest"""
from datetime import date, datetime

import pandas as pd

import game
import routine
import storage
from environments import ENVIRONMENTS
from learn import GUIDE, QUIZ, quiz_for
from rules import INDICATORS, evaluate, status
from simulate import generate_mission


def test_radiation_limits_follow_the_environment():
    assert status("radiation_msv", 0.6, "station") == "warn"          # thresholds.md
    assert status("radiation_msv", 0.6, "mars") == "ok"               # typical on Mars
    assert status("radiation_msv", 1.84, "spacecraft") == "ok"        # typical in deep space
    assert status("radiation_msv", 4.5, "spacecraft") == "alert"
    for e in ENVIRONMENTS.values():
        assert status("radiation_msv", e.expected_msv, e.key) == "ok"


def test_solar_event_advice_names_the_right_shelter():
    df = generate_mission(env_key="rover")
    i = df.index[df["date"] == "2024-05-11"][0]
    sep = [f for f in evaluate(df, i, "rover") if f["indicator"] == "sep_event"][0]
    assert "rover" in sep["action"]


def test_routine_prompts_by_mission_clock():
    tasks = routine.tasks_for("station")
    vitals = next(t for t in tasks if t.id == "vitals")                 # due 07:00
    day = date(2026, 1, 1)
    assert routine.state(vitals, False, datetime.combine(day, datetime.min.time()).replace(hour=6)) == "later"
    assert routine.state(vitals, False, datetime(2026, 1, 1, 7, 30)) == "due"
    assert routine.state(vitals, False, datetime(2026, 1, 1, 9, 0)) == "overdue"
    assert routine.state(vitals, True, datetime(2026, 1, 1, 9, 0)) == "done"
    first = routine.next_up(tasks, set(), datetime(2026, 1, 1, 9, 0))
    assert first.id == "sleep"                                          # the earliest overdue task


def test_every_environment_has_its_own_tasks():
    ids = {k: {t.id for t in routine.tasks_for(k)} for k in ENVIRONMENTS}
    assert ids["rover"] != ids["station"] and "dust" in ids["mars"] and "shelter_drill" in ids["spacecraft"]


def test_xp_rewards_habits_not_health_values():
    df = generate_mission(days=10)
    tasks = pd.DataFrame(columns=["day", "task_id", "done"])
    healthy = game.summary(df, tasks, "station")["xp"]
    sick = game.summary(df.assign(heart_rate=130, systolic=170), tasks, "station")["xp"]
    assert healthy == sick == 10 * game.XP_CHECKIN


def test_levels_and_badges_progress(tmp_path):
    db = tmp_path / "t.db"
    storage.init(db)
    s = game.summary(storage.load(storage.DEMO_CREW, db), storage.load_tasks(storage.DEMO_CREW, db), "station")
    assert s["level"][0] >= 4 and any(b.earned for b in s["badges"])
    assert game.level_for(0)[1] == "Cadet"


def test_saving_a_day_completes_its_measurement_tasks(tmp_path):
    db = tmp_path / "t.db"
    storage.init(db)
    storage.add_crew("New", date(2024, 1, 1), path=db)
    storage.save_day("New", 1, dict(heart_rate=66, systolic=110, diastolic=70, glucose=87, temp_c=36.7,
                                    sleep_hrs=7.5, mood=4, radiation_msv=0.35), path=db)
    done = set(storage.load_tasks("New", db)["task_id"])
    assert {t.id for t in routine.MEASURE_TASKS} == done


def test_every_measurement_has_plain_language_help():
    assert set(GUIDE) == set(INDICATORS)
    assert all(g["how"] and g["what"] and g["space"] for g in GUIDE.values())
    assert all(0 <= q["answer"] < len(q["options"]) for q in QUIZ)
    assert quiz_for(1) is QUIZ[0] and quiz_for(len(QUIZ) + 1) is QUIZ[0]
