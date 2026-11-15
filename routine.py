"""The daily mission routine: measurements and healthy actions at set times on the
mission clock (UTC, as on the International Space Station). The app prompts the
astronaut when each one is due."""
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from environments import env

DUE_WINDOW = timedelta(minutes=60)     # a task is "due" for an hour, then "overdue"


@dataclass(frozen=True)
class Task:
    id: str
    at: time
    title: str
    kind: str                     # "measure" (part of the daily check-in) or "action"
    xp: int
    why: str
    how: list = field(default_factory=list)
    indicators: tuple = ()        # measurements this task covers


MEASURE_TASKS = [
    Task("sleep", time(6, 45), "Log last night's sleep", "measure", 10,
         "Sleep loss builds up quietly and affects mood, reaction time and immunity.", indicators=("sleep_hrs",)),
    Task("vitals", time(7, 0), "Resting heart rate and blood pressure", "measure", 10,
         "Your heart and blood vessels adapt to low gravity. Daily readings show the trend.",
         indicators=("heart_rate", "systolic", "diastolic")),
    Task("glucose", time(7, 15), "Fasting blood sugar (before breakfast)", "measure", 10,
         "Stress and a changed diet can shift blood sugar. It's only comparable when fasting.",
         indicators=("glucose",)),
    Task("temp", time(7, 20), "Body temperature", "measure", 10,
         "A fever in a closed cabin can spread to the whole crew, so catch it early.", indicators=("temp_c",)),
    Task("dosimeter", time(8, 0), "Read your dosimeter", "measure", 10,
         "Your running radiation total is capped over a career, so every day counts.",
         indicators=("radiation_msv",)),
    Task("mood", time(20, 0), "Mood check-in", "measure", 10,
         "Isolation wears on everyone. Noticing a low patch early makes it easier to fix.", indicators=("mood",)),
]

COMMON_ACTIONS = [
    Task("hydrate", time(12, 0), "Hydration check: about 1 litre by midday", "action", 10,
         "In low gravity you feel less thirsty, but your body still needs water, including to prevent kidney stones.",
         ["Check your water log or bag.", "If you're behind, drink a glass now."]),
    Task("exercise", time(14, 0), "Exercise session", "action", 15,
         "Exercise is the main defense against bone and muscle loss.",
         ["Follow today's plan from your trainer.", "Log the session when you're done."]),
    Task("connect", time(19, 0), "Connect with someone", "action", 10,
         "Talking to crewmates, family or friends protects mood on long missions.",
         ["Share a meal, a call or a message with someone.", "Even 10 minutes counts."]),
    Task("winddown", time(21, 30), "Screen-free wind-down", "action", 10,
         "Dimming screens 30 minutes before sleep helps your body clock, which space light cycles confuse.",
         ["Switch the cabin lights to the evening setting.", "Put screens away and read, stretch or journal."]),
]

ENV_ACTIONS = {
    "station": [Task("window", time(10, 30), "Five minutes at the window", "action", 10,
                     "Looking at Earth lifts mood and helps against feeling closed in.",
                     ["Float to the Cupola or a window.", "Take five slow breaths and enjoy the view."])],
    "spacecraft": [Task("shelter_drill", time(9, 0), "Storm shelter route check", "action", 15,
                        "If a solar storm hits, you have minutes to get behind the water walls.",
                        ["Walk your route to the storm shelter.", "Check its supplies and lights."])],
    "rover": [Task("stretch", time(11, 0), "Get out of the seat and stretch", "action", 10,
                   "Long drives in a small cabin cause back pain and poor circulation.",
                   ["Stand or kneel in the cabin.", "Stretch your back, hips and legs for 5 minutes."]),
              Task("shelter_dist", time(16, 0), "Check distance to the nearest shelter", "action", 15,
                   "The rover has thin walls. Know how fast you can reach shelter in a solar storm.",
                   ["Check the map for the nearest shelter.", "Confirm the drive time with base."])],
    "moon": [Task("dust", time(17, 0), "Dust check after suit time", "action", 10,
                  "Lunar dust is sharp and irritates eyes and lungs.",
                  ["Vacuum suit seals and gloves in the airlock.", "Rinse eyes if gritty. Report coughing."])],
    "mars": [Task("dust", time(17, 0), "Airlock dust hygiene", "action", 10,
                  "Martian dust contains perchlorates that can harm the thyroid.",
                  ["Brush and vacuum suits in the airlock.", "Wipe surfaces near the suit port."]),
             Task("greenhouse", time(10, 30), "Ten minutes in the greenhouse", "action", 10,
                  "Green plants and tending something alive help mood far from Earth.",
                  ["Check on the plants.", "Spend ten unhurried minutes there."])],
}


def tasks_for(env_key):
    """Today's routine for an environment, in time order."""
    e = env(env_key)
    actions = [t if t.id != "exercise" else Task(t.id, t.at, f"Exercise: {e.exercise}", t.kind, t.xp, t.why, t.how)
               for t in COMMON_ACTIONS]
    return sorted(MEASURE_TASKS + actions + ENV_ACTIONS.get(env_key, []), key=lambda t: t.at)


def state(task, done, now):
    """'done', 'due' (in its hour), 'overdue', or 'later' for a task at mission-clock time `now`."""
    if done:
        return "done"
    start = datetime.combine(now.date(), task.at)
    if now < start:
        return "later"
    return "due" if now < start + DUE_WINDOW else "overdue"


def next_up(tasks, done_ids, now):
    """The most pressing unfinished task: overdue first, then due, then the next one later."""
    order = {"overdue": 0, "due": 1, "later": 2}
    open_tasks = [(order[state(t, False, now)], t.at, t) for t in tasks if t.id not in done_ids]
    return min(open_tasks)[2] if open_tasks else None
