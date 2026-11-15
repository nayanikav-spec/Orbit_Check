"""Run with:  python -m pytest"""
from datetime import date

import pytest

import storage

VITALS = dict(heart_rate=66, systolic=110, diastolic=70, glucose=87, temp_c=36.7,
              sleep_hrs=7.5, mood=4, radiation_msv=0.35)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    storage.init(path)
    return path


def test_first_run_seeds_demo_astronaut(db):
    assert storage.list_crew(db) == [storage.DEMO_CREW]
    assert len(storage.load(storage.DEMO_CREW, db)) == 90


def test_days_are_saved_edited_and_deleted(db):
    storage.add_crew("Rivera", date(2024, 5, 9), path=db)
    storage.save_day("Rivera", 1, VITALS, "felt fine", path=db)
    storage.save_day("Rivera", 2, VITALS, path=db)
    storage.save_day("Rivera", 2, {**VITALS, "heart_rate": 99}, "edited", path=db)   # overwrite
    df = storage.load("Rivera", db)
    assert list(df["day"]) == [1, 2]
    assert df.iloc[1]["heart_rate"] == 99 and df.iloc[1]["note"] == "edited"
    storage.delete_day("Rivera", 2, path=db)
    assert list(storage.load("Rivera", db)["day"]) == [1]


def test_dates_and_real_solar_events_fill_in(db):
    storage.add_crew("Rivera", date(2024, 5, 10), path=db)
    storage.save_day("Rivera", 2, VITALS, path=db)          # 11 May 2024: strong NASA DONKI event
    row = storage.load("Rivera", db).iloc[0]
    assert str(row["date"].date()) == "2024-05-11"
    assert "strong" in row["sep_event"]


def test_crew_logs_are_separate_and_names_unique(db):
    storage.add_crew("A", date(2024, 1, 1), path=db)
    storage.add_crew("B", date(2024, 1, 1), demo=True, path=db)
    storage.save_day("A", 1, VITALS, path=db)
    assert len(storage.load("A", db)) == 1 and len(storage.load("B", db)) == 90
    with pytest.raises(ValueError):
        storage.add_crew("A", date(2024, 1, 1), path=db)
    storage.delete_crew("B", path=db)
    assert "B" not in storage.list_crew(db) and storage.load("B", db).empty


def test_restart_replaces_log(db):
    storage.restart(storage.DEMO_CREW, date(2023, 1, 1), demo=False, path=db)
    assert storage.load(storage.DEMO_CREW, db).empty
    assert storage.start_date(storage.DEMO_CREW, db) == date(2023, 1, 1)
