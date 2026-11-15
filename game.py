"""Gamification: XP, levels, streaks and badges.

Points reward healthy HABITS (logging, routine tasks, learning), never the health
values themselves, so nobody is tempted to fudge a reading to score better.
"""
from dataclasses import dataclass

from routine import tasks_for

XP_CHECKIN = 50          # a saved daily check-in
XP_FULL_DAY = 30         # bonus: every routine task done that day
XP_QUIZ = 20             # quiz answered correctly

LEVELS = [(0, "Cadet"), (500, "Flight Engineer"), (2000, "Mission Specialist"),
          (5000, "Science Officer"), (10000, "Commander"), (18000, "Mission Legend")]


@dataclass
class Badge:
    title: str
    desc: str
    have: int
    need: int

    @property
    def earned(self):
        return self.have >= self.need


def level_for(xp):
    """(level number, name, xp at this level, xp for next level or None)."""
    idx = max(i for i, (lo, _) in enumerate(LEVELS) if xp >= lo)
    nxt = LEVELS[idx + 1][0] if idx + 1 < len(LEVELS) else None
    return idx + 1, LEVELS[idx][1], LEVELS[idx][0], nxt


def _longest_run(flags):
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def _current_run(flags):
    n = 0
    for f in reversed(flags):
        if not f:
            break
        n += 1
    return n


def summary(checkins, tasks, env_key):
    """Everything the Routine tab needs: XP, level, streaks and badges."""
    routine = tasks_for(env_key)
    xp_of = {t.id: t.xp for t in routine}
    ids = set(xp_of)
    days = list(checkins["day"])
    done = tasks[(tasks["task_id"] != "quiz") & (tasks["done"] == 1)]
    by_day = done.groupby("day")["task_id"].apply(set).to_dict()
    full = [ids <= by_day.get(d, set()) for d in days]
    quiz = tasks[tasks["task_id"] == "quiz"]
    count = done["task_id"].value_counts().to_dict()

    xp = (XP_CHECKIN * len(days) + sum(xp_of.get(t, 10) for t in done["task_id"])
          + XP_FULL_DAY * sum(full) + XP_QUIZ * int(quiz["done"].sum()))
    good_sleep = list(checkins["sleep_hrs"] >= 7)
    badges = [
        Badge("First Log", "Save your first daily check-in", len(days), 1),
        Badge("Habit Streak", "Finish every routine task 14 days in a row", _longest_run(full), 14),
        Badge("Sleep Guardian", "Get 7+ hours of sleep 7 nights in a row", _longest_run(good_sleep), 7),
        Badge("Dose Keeper", "Read your dosimeter on 30 days", count.get("dosimeter", 0), 30),
        Badge("Iron Crew", "Complete 20 exercise sessions", count.get("exercise", 0), 20),
        Badge("Hydration Hero", "Hit your midday water goal 14 times", count.get("hydrate", 0), 14),
        Badge("Social Orbit", "Connect with someone on 14 days", count.get("connect", 0), 14),
        Badge("Space Scholar", "Answer 10 quiz questions correctly", int(quiz["done"].sum()), 10),
        Badge("Storm Ready", "Keep logging through a real solar particle event",
              int((checkins["sep_event"] != "").sum()), 1),
        Badge("Mission Veteran", "Log 90 days", len(days), 90),
    ]
    return dict(xp=xp, level=level_for(xp), streak=_current_run(full), best_streak=_longest_run(full),
                full_days=sum(full), badges=badges)
