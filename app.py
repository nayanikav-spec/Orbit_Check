"""SECTION 3: The Streamlit app. Run with:  streamlit run app.py"""
from datetime import datetime, timezone
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import game
import routine
import storage
from environments import ENVIRONMENTS, env
from learn import GUIDE, quiz_for
from nasa import TIMEPOINTS, crew_glucose, crew_wbc, sep_events
from rules import (BASELINE_DAYS, CAREER_LIMIT_MSV, HAZARD, INDICATORS, LABELS, LIMITS,
                   MIN_BASELINE, UNITS, evaluate, fmt, limits, needs_flight_surgeon, overall, status)
from simulate import DEFAULT_START

st.set_page_config(page_title="Orbit Check", page_icon="🪐", layout="wide")

INK, PAPER, ACCENT, LEMON = "#0b1f3a", "#e3f0f7", "#3f8fd2", "#f6e75a"
COLORS = {"ok": "#1b7a4b", "warn": "#a96b00", "alert": "#c1272d"}
CREW_COLORS = ["#0b1f3a", "#3f8fd2", "#8c5ac8", "#5b6b7f"]
BANDS = {"ok": "rgba(27,122,75,.20)", "warn": "rgba(169,107,0,.28)", "alert": "rgba(193,39,45,.26)"}
WORDS = {"ok": "NORMAL", "warn": "CAUTION", "alert": "URGENT"}
OVERALL = {"ok": "ALL CLEAR", "warn": "CAUTION", "alert": "URGENT"}

# ---------------- LOOK AND FEEL: flight-log / paper-and-ink ----------------
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
#MainMenu, footer {visibility: hidden;}
.stApp {background: #e3f0f7;}
.block-container {max-width: 1500px; padding-top: 1rem;}
.stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp li, .stApp td, .stApp th,
div[data-testid="stMarkdownContainer"], .stTabs [data-baseweb="tab"] {
  font-family: 'Bricolage Grotesque', sans-serif; color: #0b1f3a;}
.mono {font-family: 'IBM Plex Mono', monospace;}

/* ---- banner ---- */
.banner {background: #0b1f3a; border-bottom: 6px solid #f6e75a;
  padding: 10px 28px 16px; margin-bottom: 18px;}
.banner-top {display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px;
  font-family: 'IBM Plex Mono', monospace; font-size: .72rem; letter-spacing: .08em; color: #bcd6e8;
  border-bottom: 1px solid rgba(188,214,232,.45); padding-bottom: 8px;}
.banner-top span:first-child {color: #f6e75a; font-weight: 600;}
.banner-title {font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800;
  font-size: clamp(2.4rem, 5vw, 4.2rem); line-height: 1; letter-spacing: -.03em;
  margin: 12px 0 4px -.03em; color: #f4fafd;}
.banner-sub {font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.05rem; font-weight: 600;
  line-height: 1.2; color: #bcd6e8;}

/* ---- tabs ---- */
.stTabs [data-baseweb="tab-list"] {gap: 28px; border-bottom: 2px solid #0b1f3a;}
.stTabs [data-baseweb="tab"] {font-size: 1.15rem; font-weight: 600; padding: 8px 0;}
.stTabs [data-baseweb="tab-highlight"] {background: #0b1f3a; height: 5px;}

/* ---- status strip ---- */
.strip {display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;
  border-top: 6px solid #0b1f3a; border-bottom: 2px solid #0b1f3a; padding: 10px 2px; margin: 10px 0 6px;
  font-family: 'IBM Plex Mono', monospace;}
.strip .d {font-size: 1.3rem; font-weight: 600; background: #f6e75a; padding: 2px 12px;}
.strip .s {font-size: clamp(2rem, 4vw, 3rem); font-weight: 600; letter-spacing: -.02em; line-height: 1;}
.strip .f {font-size: 1.3rem; font-weight: 600;}

/* ---- mission timeline ---- */
.tl {display: grid; gap: 2px; margin: 4px 0 2px;}
.tl span {height: 18px; min-width: 0; opacity: .85;}
.tl span.on {outline: 3px solid #0b1f3a; outline-offset: 1px; opacity: 1;}
.tl span.sep {box-shadow: inset 0 5px 0 #f6e75a;}
.envstrip {display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 2px; margin: 14px 0 6px;
  background: #0b1f3a;}
.envstrip div {background: #f4fafd; padding: 8px 12px;}
.envstrip .k {display: block; font-family: 'IBM Plex Mono', monospace; font-size: .68rem; letter-spacing: .1em; opacity: .65;}
.envstrip .v {font-weight: 600;}
.prompt {border-left: 6px solid #0b1f3a; background: #f4fafd; padding: 10px 14px; margin: 8px 0 4px;}
.prompt .pw {font-family: 'IBM Plex Mono', monospace; font-size: .75rem; font-weight: 600; color: #fff !important;
  padding: 2px 8px; margin-right: 8px;}
.prompt .px, .task .px {font-family: 'IBM Plex Mono', monospace; font-size: .75rem; background: #f6e75a; padding: 1px 6px;}
.prompt .pd {font-size: .92rem; margin-top: 4px; opacity: .85;}
.task {border-left: 6px solid #7b8fa3; background: #f4fafd; padding: 8px 12px;}
.task .tt {font-family: 'IBM Plex Mono', monospace; font-weight: 600; margin-right: 6px;}
.task .ts {float: right; font-family: 'IBM Plex Mono', monospace; font-size: .75rem; font-weight: 600; letter-spacing: .06em;}
.task .tw {font-size: .88rem; opacity: .8; margin-top: 2px;}
.tick {font-size: 1.5rem; font-weight: 700;}
.badges {display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px;}
.badge {border: 2px solid rgba(11,31,58,.25); padding: 8px 10px; background: #f4fafd; opacity: .7;}
.badge.on {border-color: #0b1f3a; background: #f6e75a; opacity: 1;}
.badge .bt {font-weight: 800;}
.badge .bd {font-size: .8rem; line-height: 1.25; margin: 2px 0 6px;}
.badge .bp {font-family: 'IBM Plex Mono', monospace; font-size: .7rem; margin-top: 3px;}
.legend {display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;}
.legend div {border-left: 6px solid; background: #f4fafd; padding: 8px 12px; font-size: .92rem;}
.legend b {display: block; font-family: 'IBM Plex Mono', monospace; font-size: .8rem; letter-spacing: .06em;}
.envcard {border-top: 4px solid #0b1f3a; padding-top: 8px; font-size: .88rem;}
.envcard.here {border-top-color: #f6e75a; background: #f4fafd; padding: 8px;}
.envcard .en {font-weight: 800; font-size: 1.05rem;}
.envcard .ef {font-family: 'IBM Plex Mono', monospace; font-size: .74rem; margin: 4px 0; opacity: .8;}
.envcard ul {padding-left: 18px; margin: 4px 0;}
.xpchip {font-family: 'IBM Plex Mono', monospace; font-size: .85rem; border: 2px solid #0b1f3a; padding: 8px 12px;
  background: #f4fafd;}
.xpchip .lv {background: #0b1f3a; color: #f6e75a !important; padding: 1px 6px; font-weight: 600;}
.note {border-left: 6px solid #3f8fd2; background: #f4fafd; padding: 10px 14px; margin: 14px 0 8px;}
.note b {font-family: 'IBM Plex Mono', monospace; font-size: .75rem; letter-spacing: .1em; margin-right: 8px;}
.nasa {border-left: 6px solid #f6e75a; background: #0b1f3a; color: #e3f0f7 !important; padding: 12px 16px;
  margin: 8px 0 14px; font-size: .95rem;}
.nasa b, .nasa span {color: #f6e75a !important;}
.tlcap {font-family: 'IBM Plex Mono', monospace; font-size: .72rem; opacity: .7; display: flex;
  justify-content: space-between;}

/* ---- ledger rows ---- */
.row {display: grid; grid-template-columns: 1fr auto 135px; align-items: baseline; gap: 14px;
  border-bottom: 1px solid rgba(11,31,58,.3); padding: 12px 2px;}
.row .rl {font-size: 1.1rem; font-weight: 600;}
.row .rl small {display: block; font-family: 'IBM Plex Mono', monospace; font-size: .72rem;
  font-weight: 400; opacity: .6;}
.row .rv {font-family: 'IBM Plex Mono', monospace; font-size: 2.1rem; font-weight: 600; text-align: right;}
.row .rv small {font-size: .9rem; font-weight: 400; opacity: .65;}
.row .rs {font-family: 'IBM Plex Mono', monospace; font-size: .8rem; font-weight: 600; letter-spacing: .06em;
  display: flex; align-items: center; gap: 9px;}
.dot {width: 11px; height: 11px; border-radius: 50%; display: inline-block; animation: blink 1.4s ease-in-out infinite;}
.dot.ok {animation: none;}
.dot.alert {animation-duration: .6s;}
.dot.warn {animation-duration: 1s;}
@keyframes blink {0%, 100% {opacity: 1; transform: scale(1);} 50% {opacity: .15; transform: scale(.7);}}
@media (prefers-reduced-motion: reduce) {.dot {animation: none;}}

.sec {font-family: 'IBM Plex Mono', monospace; font-size: .85rem; font-weight: 600;
  letter-spacing: .12em; margin: 26px 0 6px; padding-bottom: 6px; border-bottom: 2px solid #0b1f3a;}
.alertbar {background: #c1272d; color: #e3f0f7 !important; padding: 16px 20px; margin: 18px 0 4px;
  font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 1.05rem;}
.flag {border-left: 6px solid #b7791f; padding: 6px 0 6px 16px; margin: 16px 0;}
.flag .ft {font-size: 1.25rem; font-weight: 800;}
.flag .fm {font-family: 'IBM Plex Mono', monospace; font-size: .78rem; margin: 6px 0; opacity: .75;}
.flag .fa {font-weight: 600;}
.logtitle {font-weight: 800; font-size: 2.4rem; letter-spacing: -.03em; line-height: 1;}
.logsub {font-family: 'IBM Plex Mono', monospace; font-size: .8rem; margin: 6px 0 12px; opacity: .75;}
.hz {border-top: 4px solid #0b1f3a; padding-top: 8px; height: 100%;}
.hz .n {font-family: 'IBM Plex Mono', monospace; font-size: 1.4rem; font-weight: 600; background: #f6e75a; display: inline-block; padding: 0 10px; margin-bottom: 6px;}
.hz b {font-size: 1.1rem;}

/* ---- stat tiles ---- */
.stat {border-top: 4px solid #0b1f3a; padding-top: 6px;}
.stat .k {font-family: 'IBM Plex Mono', monospace; font-size: .72rem; letter-spacing: .1em; opacity: .7;}
.stat .v {font-family: 'IBM Plex Mono', monospace; font-size: 1.9rem; font-weight: 600; line-height: 1.1;}
.stat .v small {font-size: .85rem; font-weight: 400; opacity: .65;}
.bar {height: 8px; background: rgba(11,31,58,.12); margin-top: 6px;}
.bar span {display: block; height: 100%; background: #0b1f3a;}

/* ---- ranges table ---- */
table.rng {width: 100%; border-collapse: collapse; font-size: .95rem;}
table.rng th {text-align: left; font-family: 'IBM Plex Mono', monospace; font-size: .75rem;
  letter-spacing: .08em; border-bottom: 2px solid #0b1f3a; padding: 6px 8px;}
table.rng td {border-bottom: 1px solid rgba(11,31,58,.25); padding: 8px; vertical-align: top;}
table.rng td.m {font-family: 'IBM Plex Mono', monospace; font-weight: 600; white-space: nowrap;}

/* ---- inputs + buttons: square, no rounded cards ---- */
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 0 !important; border: 2px solid #0b1f3a !important;
  background: #f4fafd;}
.stNumberInput input {background: #e3f0f7 !important; color: #0b1f3a !important; border-radius: 0 !important;
  font-family: 'IBM Plex Mono', monospace !important;}
.stButton button, .stDownloadButton button {border-radius: 0 !important; border: 2px solid #0b1f3a !important;
  background: #e3f0f7 !important; font-weight: 600;}
.stButton button p, .stDownloadButton button p {color: #0b1f3a !important;}
div[data-testid="stPopover"] button {border-radius: 0 !important; border: 2px solid #0b1f3a !important;
  background: #e3f0f7 !important; font-weight: 600;}
div[data-testid="stPopoverBody"] {border-radius: 0 !important; border: 2px solid #0b1f3a;}
.stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {background: #0b1f3a !important;}
.stButton button[kind="primary"] p, .stButton button[data-testid="stBaseButton-primary"] p {color: #f6e75a !important;}
@media (max-width: 640px) {
  .row {grid-template-columns: 1fr auto; }
  .row .rs {grid-column: 1 / -1;}
  .row .rv {font-size: 1.6rem;}
}
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)

# ---------------- DATA: every crew member's days are saved in SQLite ----------------
storage.init()
crew_names = storage.list_crew()
if st.session_state.get("crew") not in crew_names:
    st.session_state.crew = crew_names[0]
crew = st.session_state.crew
df = storage.load(crew)
tasks_df = storage.load_tasks(crew)
start = storage.start_date(crew)
env_key = storage.environment(crew)
E = env(env_key)
now = datetime.now(timezone.utc).replace(tzinfo=None)          # mission clock runs on UTC, like the ISS
today_tasks = routine.tasks_for(env_key)
done_today = set(tasks_df.loc[(tasks_df["day"] == len(df) + 1) & (tasks_df["done"] == 1), "task_id"])
next_day = len(df) + 1                      # days are numbered 1..n with no gaps
mission_lo = pd.Timestamp(start)
mission_hi = mission_lo + pd.Timedelta(days=max(len(df), 90) - 1)
st.session_state.setdefault("mission_start", start)
st.session_state.setdefault("mission_env", env_key)

TYPICAL = dict(in_hr=66, in_sys=110, in_dia=70, in_glu=87, in_temp=36.7,
               in_sleep=7.5, in_rad=0.35, in_mood=4, in_note="")
TYPICAL["in_rad"] = round(E.expected_msv, 2)
ROUGH = dict(in_hr=112, in_sys=146, in_dia=92, in_glu=118, in_temp=37.6,
             in_sleep=4.5, in_rad=round(E.expected_msv * 1.15, 2), in_mood=2, in_note="Headache, slept badly after a loud night in the module.")
for k, v in TYPICAL.items():
    st.session_state.setdefault(k, v)
st.session_state.setdefault("edit_day", None)


def flags_for(data, i):
    """evaluate() for day i, cached: a day's flags only depend on that day and the days before it."""
    key = (env_key, i, int(pd.util.hash_pandas_object(data.iloc[:i + 1], index=False).sum()))
    cache = st.session_state.setdefault("flag_cache", {})
    if key not in cache:
        cache[key] = evaluate(data, i, env_key)
    return cache[key]


# Flags that aren't a single measurement point to the closest guide topic
LEARN_TOPIC = {"bp_crisis": "systolic", "pattern_sleep": "sleep_hrs", "pattern_mood": "mood",
               "sep_event": "radiation_msv"}


def notify(msg):
    st.session_state.toast = msg


def load_values(vals):
    st.session_state.update(vals)


def save_checkin(name, day):
    s = st.session_state
    vitals = dict(heart_rate=s.in_hr, systolic=s.in_sys, diastolic=s.in_dia, glucose=s.in_glu,
                  temp_c=round(s.in_temp, 1), sleep_hrs=s.in_sleep, mood=int(s.in_mood),
                  radiation_msv=round(s.in_rad, 2))
    storage.save_day(name, day, vitals, s.in_note)
    notify(f"Day {day} {'updated' if s.edit_day else 'saved'} for {name}.")
    s.update(TYPICAL, view_day=day, edit_day=None)


def start_edit(row):
    st.session_state.update(
        in_hr=int(row["heart_rate"]), in_sys=int(row["systolic"]), in_dia=int(row["diastolic"]),
        in_glu=int(row["glucose"]), in_temp=float(row["temp_c"]), in_sleep=float(row["sleep_hrs"]),
        in_rad=float(row["radiation_msv"]), in_mood=int(row["mood"]), in_note=row["note"],
        edit_day=int(row["day"]))


def cancel_edit():
    st.session_state.update(TYPICAL, edit_day=None)


def delete_day(name, day):
    storage.delete_day(name, day)
    st.session_state.update(view_day=None, edit_day=None)
    notify(f"Day {day} deleted.")


def switch_crew():
    name = st.session_state.crew
    st.session_state.update(view_day=None, edit_day=None, mission_start=storage.start_date(name),
                            mission_env=storage.environment(name))


def tick_task(name, day, task_id):
    done = st.session_state[f"task_{task_id}_{day}"]
    storage.set_task(name, day, task_id, True if done else None)
    if done:
        notify(f"+{next(t.xp for t in routine.tasks_for(storage.environment(name)) if t.id == task_id)} XP")


def answer_quiz(name, day, correct_index):
    picked = st.session_state.get(f"quiz_{day}")
    if picked is None:
        return
    storage.set_task(name, day, "quiz", picked == correct_index)
    notify(f"Correct! +{game.XP_QUIZ} XP" if picked == correct_index else "Not quite. See the explanation.")


def add_crew():
    s = st.session_state
    try:
        storage.add_crew(s.new_name, s.new_start, demo=s.new_demo, env_key=s.new_env)
    except ValueError as e:
        s.crew_error = str(e)
        return
    s.update(crew=s.new_name.strip(), view_day=None, edit_day=None,
             mission_start=s.new_start, mission_env=s.new_env, new_name="", crew_error="")
    notify(f"{s.crew} added to the crew.")


def restart(name, demo):
    storage.restart(name, st.session_state.mission_start, demo=demo, env_key=st.session_state.mission_env)
    st.session_state.update(view_day=None, edit_day=None)
    notify(f"New mission started for {name}.")


def remove_crew(name):
    storage.delete_crew(name)
    storage.init()                                 # re-seeds the demo astronaut if nobody is left
    first = storage.list_crew()[0]
    st.session_state.update(crew=first, view_day=None, edit_day=None,
                            mission_start=storage.start_date(first), mission_env=storage.environment(first))
    notify(f"{name} removed.")


def stat(label, value, unit="", bar=None):
    b = f'<div class="bar"><span style="width:{min(bar, 1) * 100:.1f}%"></span></div>' if bar is not None else ""
    return f'<div class="stat"><div class="k">{label}</div><div class="v">{value}<small> {unit}</small></div>{b}</div>'


def chart_layout(fig, height, ytitle=""):
    fig.update_layout(template="simple_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=INK, family="IBM Plex Mono, monospace"), height=height,
                      xaxis_title="Mission day", yaxis_title=ytitle, hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                      margin=dict(l=10, r=10, t=30, b=10))
    return fig


all_flags = [flags_for(df, i) for i in range(len(df))]
is_sep = (df["sep_event"].fillna("") != "").tolist()
day_level = [overall(f) for f in all_flags]

if st.session_state.get("toast"):
    st.toast(st.session_state.pop("toast"))

# Celebrate level-ups and new badges
score = game.summary(df, tasks_df, env_key)
earned = sum(b.earned for b in score["badges"])
prev = st.session_state.get("score_seen", {}).get(crew)
if prev and (score["level"][0] > prev[0] or earned > prev[1]):
    st.balloons()
    st.toast(f"Level up: {score['level'][1]}!" if score["level"][0] > prev[0] else "New badge earned!")
st.session_state.setdefault("score_seen", {})[crew] = (score["level"][0], earned)

# ---------------- BANNER ----------------
st.markdown(f"""
<div class="banner">
  <div class="banner-top"><span>CREW HEALTH LOG / {escape(crew.upper())} / {E.short.upper()} / MISSION FROM {mission_lo:%d %b %Y}</span>
  <span>MISSION CLOCK {now:%H:%M} UTC / REAL NASA SPACE WEATHER / NOT MEDICAL ADVICE</span></div>
  <div class="banner-title">ORBIT CHECK</div>
  <div class="banner-sub">Know what your body is telling you, and why, when help is far away.</div>
</div>
""", unsafe_allow_html=True)

# ---------------- CREW BAR ----------------
cb1, cb2, cb3, cb4 = st.columns([1.4, 1, 1, 2.2], vertical_alignment="bottom")
cb1.selectbox("Crew member", crew_names, key="crew", on_change=switch_crew)
with cb2.popover("Add crew member", width="stretch"):
    st.text_input("Name", key="new_name", placeholder="e.g. Cmdr. Rivera")
    st.date_input("Mission start date", key="new_start", value=DEFAULT_START,
                  help="Days are matched to these calendar dates, so real NASA solar particle "
                       "events on those dates show up as radiation alerts.")
    st.selectbox("Where is the mission?", list(ENVIRONMENTS), format_func=lambda k: ENVIRONMENTS[k].name, key="new_env")
    st.checkbox("Fill with a simulated 90-day demo mission", key="new_demo")
    st.button("Add", type="primary", on_click=add_crew, width="stretch")
    if st.session_state.get("crew_error"):
        st.error(st.session_state.crew_error)
with cb3.popover("Manage mission", width="stretch"):
    st.markdown(f"**{crew}**: {len(df)} day{'s' if len(df) != 1 else ''} saved.")
    st.date_input("Mission start date", key="mission_start",
                  help="Used when you start a new mission below.")
    st.selectbox("Mission environment", list(ENVIRONMENTS), format_func=lambda k: ENVIRONMENTS[k].name, key="mission_env",
                 help="Changes radiation levels and limits, the daily routine and the risks shown.")
    sure = st.checkbox(f"Yes, replace {crew}'s saved days")
    st.button("Start new mission with demo data", on_click=restart, args=(crew, True),
              disabled=not sure, width="stretch")
    st.button("Start new empty mission", on_click=restart, args=(crew, False),
              disabled=not sure, width="stretch")
    st.button(f"Remove {crew}", on_click=remove_crew, args=(crew,), disabled=not sure, width="stretch")

lvl_no, lvl_name, lvl_lo, lvl_hi = score["level"]
cb4.markdown(f'<div class="xpchip"><span class="lv">LV {lvl_no}</span> {lvl_name} / '
             f'<b>{score["xp"]:,} XP</b> / streak {score["streak"]} day{"s" if score["streak"] != 1 else ""}</div>',
             unsafe_allow_html=True)

# ---------------- ENVIRONMENT STRIP ----------------
st.markdown(
    '<div class="envstrip">'
    f'<div><span class="k">ENVIRONMENT</span><span class="v">{E.name}</span></div>'
    f'<div><span class="k">GRAVITY</span><span class="v">{E.gravity_text}</span></div>'
    f'<div><span class="k">SIGNAL TO EARTH</span><span class="v">{E.delay_text}</span></div>'
    f'<div><span class="k">TYPICAL RADIATION</span><span class="v">{E.expected_msv} mSv/day</span></div>'
    '</div>', unsafe_allow_html=True)

# ---------------- PROMPT: what to do next ----------------
up = routine.next_up(today_tasks, done_today, now)
if up:
    st_ = routine.state(up, False, now)
    word = {"overdue": "OVERDUE", "due": "DUE NOW", "later": "NEXT UP"}[st_]
    color = {"overdue": COLORS["alert"], "due": COLORS["warn"], "later": INK}[st_]
    where = "Log it in today's check-in." if up.kind == "measure" else "Tick it off in the Routine tab."
    st.markdown(f'<div class="prompt" style="border-left-color:{color}"><span class="pw" style="background:{color}">'
                f'{word} {up.at:%H:%M}</span> <b>{up.title}</b> <span class="px">+{up.xp} XP</span>'
                f'<div class="pd">{up.why} {where}</div></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="prompt" style="border-left-color:#1b7a4b"><span class="pw" style="background:#1b7a4b">'
                'ALL DONE</span> <b>Today\'s routine is complete.</b> Nice work.</div>', unsafe_allow_html=True)

tab_dash, tab_routine, tab_trends, tab_nasa, tab_guide, tab_about = st.tabs(
    ["Dashboard", "Routine & Rewards", "Trends", "NASA Data", "Guide", "About"])

# ---------------- DASHBOARD ----------------
with tab_dash:
    left, right = st.columns([1, 2.2], gap="large")

    # ----- left: the day to fill in (or edit) -----
    with left:
        editing = st.session_state.edit_day
        form_day = editing or next_day
        with st.container(border=True):
            st.markdown(f'<div class="logtitle">{"Edit" if editing else "Log"} day {form_day}</div>'
                        f'<div class="logsub">{storage.date_for(crew, form_day):%a %d %b %Y} / '
                        f'{"EDITING A SAVED DAY" if editing else "NOT LOGGED YET"}</div>', unsafe_allow_html=True)
            a, b = st.columns(2)
            a.number_input("Heart rate (bpm)", 30, 220, key="in_hr")
            b.number_input("Sleep (hrs)", 0.0, 14.0, step=0.5, format="%.1f", key="in_sleep")
            a.number_input("Systolic BP (mmHg)", 60, 250, key="in_sys")
            b.number_input("Diastolic BP (mmHg)", 30, 150, key="in_dia")
            a.number_input("Blood sugar (mg/dL)", 30, 400, key="in_glu",
                           help="Fasting reading: ranges assume you haven't eaten for 8 hours.")
            b.number_input("Body temp (°C)", 33.0, 42.0, step=0.1, format="%.1f", key="in_temp")
            a.number_input("Radiation (mSv)", 0.0, 10.0, step=0.05, format="%.2f", key="in_rad",
                           help="Today's dose from your personal dosimeter.")
            b.slider("Mood (1-5)", 1, 5, key="in_mood", help="1 = very low, 5 = great")
            st.text_area("Notes (optional)", key="in_note", height=80, max_chars=500,
                         placeholder="Symptoms, workouts, anything unusual today")
            st.button(f"{'Update' if editing else 'Save'} day {form_day}", type="primary",
                      on_click=save_checkin, args=(crew, form_day), width="stretch")
            with st.expander("Not sure how to measure something?"):
                pick = st.selectbox("Measurement", list(GUIDE), format_func=lambda k: LABELS[k],
                                    key="help_pick", label_visibility="collapsed")
                g = GUIDE[pick]
                st.markdown(f"**What it is:** {g['what']}")
                st.markdown("**How to measure:**\n" + "\n".join(f"{i}. {step}" for i, step in enumerate(g["how"], 1)))
                st.caption(g["tip"])
            if editing:
                st.button("Cancel edit", on_click=cancel_edit, width="stretch")
            else:
                p1, p2 = st.columns(2)
                p1.button("Typical day", on_click=load_values, args=(TYPICAL,), width="stretch")
                p2.button("Rough day (demo)", on_click=load_values, args=(ROUGH,), width="stretch")

        cum = df["radiation_msv"].sum()
        rate = df["radiation_msv"].tail(14).mean() if len(df) else E.expected_msv
        left_days = (CAREER_LIMIT_MSV - cum) / rate if rate > 0 else float("inf")
        horizon = (f"limit reached in ~{left_days / 365:.1f} years at this rate" if left_days > 365
                   else f"limit reached in ~{left_days:.0f} days at this rate")
        s1, s2 = st.columns(2)
        s1.markdown(stat("MISSION DOSE", f"{cum:.1f}", "mSv", cum / CAREER_LIMIT_MSV)
                    + f'<div class="tlcap"><span>{cum / CAREER_LIMIT_MSV:.1%} of {CAREER_LIMIT_MSV} mSv career limit; '
                      f'{horizon}</span></div>',
                    unsafe_allow_html=True)
        s2.markdown(stat("DAYS FLAGGED", f"{sum(lv != 'ok' for lv in day_level)}", f"/ {len(df)}"),
                    unsafe_allow_html=True)

    # ----- right: readout for the selected day -----
    with right:
        if df.empty:
            st.markdown('<div class="strip"><span class="d">NO DAYS YET</span>'
                        '<span class="s">READY</span><span class="f">0 FLAGS</span></div>', unsafe_allow_html=True)
            st.markdown(f"**{escape(crew)} hasn't logged any days yet.** Fill in the form and save day 1. "
                        f"Personal-baseline checks start after {MIN_BASELINE} days.")
        else:
            if not isinstance(st.session_state.get("view_day"), int) or not 1 <= st.session_state.view_day <= len(df):
                st.session_state.view_day = len(df)
            if len(df) > 1:
                day = st.slider("Viewing mission day", 1, len(df), key="view_day")
            else:
                day = 1
            idx = day - 1
            row = df.iloc[idx]
            flags = all_flags[idx]
            lvl = day_level[idx]

            cells = "".join(f'<span class="{"on" if i == idx else ""} {"sep" if is_sep[i] else ""}" '
                            f'title="Day {i + 1}: {WORDS[lv]}{" / solar particle event" if is_sep[i] else ""}" '
                            f'style="background:{COLORS[lv]}"></span>' for i, lv in enumerate(day_level))
            st.markdown(f'<div class="tl" style="grid-template-columns:repeat({len(df)},1fr)">{cells}</div>'
                        f'<div class="tlcap"><span>DAY 1</span><span>MISSION TIMELINE / YELLOW TOP = REAL SOLAR '
                        f'PARTICLE EVENT</span><span>DAY {len(df)}</span></div>', unsafe_allow_html=True)

            st.markdown(
                f'<div class="strip"><span class="d">DAY {day} / {row["date"]:%d %b %Y}</span>'
                f'<span class="s" style="color:{COLORS[lvl]}">{OVERALL[lvl]}</span>'
                f'<span class="f">{len(flags)} FLAG{"" if len(flags) == 1 else "S"}</span></div>',
                unsafe_allow_html=True)

            flagged = {f["indicator"]: f["level"] for f in flags}
            c1, c2 = st.columns(2, gap="large")
            for col, group in ((c1, INDICATORS[:4]), (c2, INDICATORS[4:])):
                html = ""
                for ind in group:
                    s = flagged.get(ind, status(ind, row[ind], env_key))
                    prev = df[ind].iloc[max(0, idx - BASELINE_DAYS):idx]
                    base = (f"your normal {fmt(ind, prev.mean())}" if len(prev) >= MIN_BASELINE
                            else "building baseline")
                    html += (f'<div class="row"><span class="rl">{LABELS[ind]}<small>{base}</small></span>'
                             f'<span class="rv">{fmt(ind, row[ind])}<small> {UNITS[ind]}</small></span>'
                             f'<span class="rs" style="color:{COLORS[s]}"><span class="dot {s}" '
                             f'style="background:{COLORS[s]};box-shadow:0 0 8px {COLORS[s]}"></span>{WORDS[s]}</span></div>')
                col.markdown(html, unsafe_allow_html=True)

            if row["note"]:
                st.markdown(f'<div class="note"><b>NOTE</b> {escape(row["note"])}</div>', unsafe_allow_html=True)

            e1, e2, _ = st.columns([1, 1, 2])
            e1.button(f"Edit day {day}", on_click=start_edit, args=(row.to_dict(),), width="stretch")
            if day == len(df):
                with e2.popover(f"Delete day {day}", width="stretch"):
                    st.markdown(f"Delete day {day} ({row['date']:%d %b %Y}) for {escape(crew)}? This can't be undone.")
                    st.button("Delete", type="primary", on_click=delete_day, args=(crew, day), width="stretch")

            if needs_flight_surgeon(flags):
                st.markdown(f'<div class="alertbar">CONTACT YOUR FLIGHT SURGEON. {E.help_text} '
                            f'Signal to Earth: {E.delay_text.lower()}.</div>', unsafe_allow_html=True)

            st.markdown('<div class="sec">WHY FLAGGED</div>', unsafe_allow_html=True)
            if not flags:
                st.markdown("**Nothing flagged.** Every reading is inside its safe range and close to your own normal.")
            for n, f in enumerate(sorted(flags, key=lambda f: f["level"] != "alert")):
                st.markdown(
                    f'<div class="flag" style="border-left-color:{COLORS[f["level"]]}">'
                    f'<div class="ft">{f["title"]}</div><div>{f["why"]}</div>'
                    f'<div class="fm">HAZARD: {f["hazard"]} / RISK: {f["risk"]}</div>'
                    f'<div class="fa">&rarr; {f["action"]}</div></div>', unsafe_allow_html=True)
                topic = LEARN_TOPIC.get(f["indicator"], f["indicator"])
                if topic in GUIDE:
                    with st.expander(f"Learn more: {LABELS[topic].lower()} and why it matters in space"):
                        g = GUIDE[topic]
                        st.markdown(f"**What it is.** {g['what']}\n\n**In space.** {g['space']}\n\n**Tip.** {g['tip']}")

# ---------------- ROUTINE & REWARDS ----------------
TASK_COLORS = {"done": COLORS["ok"], "due": COLORS["warn"], "overdue": COLORS["alert"], "later": "#7b8fa3"}
TASK_WORDS = {"done": "DONE", "due": "DUE NOW", "overdue": "OVERDUE", "later": "LATER"}

with tab_routine:
    xp_into = score["xp"] - lvl_lo
    xp_span = (lvl_hi - lvl_lo) if lvl_hi else None
    r1, r2, r3, r4 = st.columns(4)
    to_next = f"{lvl_hi - score['xp']:,} XP to next level" if lvl_hi else "Top level reached"
    r1.markdown(stat("LEVEL", f"{lvl_no}", lvl_name, xp_into / xp_span if xp_span else 1)
                + f'<div class="tlcap"><span>{to_next}</span></div>', unsafe_allow_html=True)
    r2.markdown(stat("TOTAL XP", f"{score['xp']:,}"), unsafe_allow_html=True)
    r3.markdown(stat("ROUTINE STREAK", f"{score['streak']}", f"day{'s' if score['streak'] != 1 else ''}")
                + f'<div class="tlcap"><span>best: {score["best_streak"]} days</span></div>', unsafe_allow_html=True)
    r4.markdown(stat("FULL ROUTINE DAYS", f"{score['full_days']}", f"/ {len(df)}"), unsafe_allow_html=True)

    left_r, right_r = st.columns([1.5, 1], gap="large")
    with left_r:
        n_done = sum(t.id in done_today for t in today_tasks)
        st.markdown(f'<div class="sec">DAY {next_day} ROUTINE / {storage.date_for(crew, next_day):%a %d %b %Y} / '
                    f'{n_done} OF {len(today_tasks)} DONE / MISSION CLOCK {now:%H:%M} UTC</div>',
                    unsafe_allow_html=True)
        st.caption("Measurements tick themselves off when you save today's check-in on the Dashboard. "
                   "Tick off actions here as you do them. Finishing every task earns a "
                   f"+{game.XP_FULL_DAY} XP bonus and keeps your streak going.")
        for t in today_tasks:
            done = t.id in done_today
            stt = routine.state(t, done, now)
            c_chk, c_body = st.columns([0.08, 0.92], vertical_alignment="center")
            if t.kind == "action":
                c_chk.checkbox(t.title, value=done, key=f"task_{t.id}_{next_day}", label_visibility="collapsed",
                               on_change=tick_task, args=(crew, next_day, t.id))
            else:
                c_chk.markdown(f'<span class="tick" style="color:{TASK_COLORS[stt]}">{"✓" if done else "○"}</span>',
                               unsafe_allow_html=True)
            c_body.markdown(
                f'<div class="task" style="border-left-color:{TASK_COLORS[stt]}">'
                f'<span class="tt">{t.at:%H:%M}</span> <b>{t.title}</b> <span class="px">+{t.xp} XP</span>'
                f'<span class="ts" style="color:{TASK_COLORS[stt]}">{TASK_WORDS[stt]}</span>'
                f'<div class="tw">{"Measurement: log it in the daily check-in. " if t.kind == "measure" else ""}{t.why}</div></div>',
                unsafe_allow_html=True)
            steps = [s for ind in t.indicators[:1] for s in GUIDE[ind]["how"]] if t.indicators else t.how
            with c_body.expander("How to do it"):
                st.markdown("\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1)))

    with right_r:
        st.markdown('<div class="sec">DAILY QUESTION</div>', unsafe_allow_html=True)
        q = quiz_for(next_day)
        answered = tasks_df[(tasks_df["day"] == next_day) & (tasks_df["task_id"] == "quiz")]
        with st.container(border=True):
            st.markdown(f"**{q['q']}**")
            if answered.empty:
                st.radio("Your answer", range(len(q["options"])), format_func=lambda i: q["options"][i],
                         key=f"quiz_{next_day}", index=None, label_visibility="collapsed")
                st.button(f"Check answer (+{game.XP_QUIZ} XP if right)", on_click=answer_quiz,
                          args=(crew, next_day, q["answer"]), width="stretch",
                          disabled=st.session_state.get(f"quiz_{next_day}") is None)
            else:
                right_answer = bool(answered["done"].iloc[0])
                (st.success if right_answer else st.info)(
                    ("Correct! " if right_answer else f"The answer: {q['options'][q['answer']]}. ") + q["explain"])
                st.caption("A new question comes with the next mission day.")

        st.markdown('<div class="sec">BADGES</div>', unsafe_allow_html=True)
        html = ""
        for b in score["badges"]:
            pct = min(b.have / b.need, 1)
            html += (f'<div class="badge {"on" if b.earned else ""}"><div class="bt">{"★" if b.earned else "☆"} {b.title}</div>'
                     f'<div class="bd">{b.desc}</div><div class="bar"><span style="width:{pct * 100:.0f}%"></span></div>'
                     f'<div class="bp">{min(b.have, b.need)} / {b.need}</div></div>')
        st.markdown(f'<div class="badges">{html}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sec">CREW LEADERBOARD</div>', unsafe_allow_html=True)
        board = []
        for name in crew_names:
            sm = game.summary(storage.load(name), storage.load_tasks(name), storage.environment(name))
            board.append(dict(Crew=name, Level=f"{sm['level'][0]} {sm['level'][1]}", XP=sm["xp"],
                              Streak=sm["streak"], Badges=sum(b.earned for b in sm["badges"])))
        st.dataframe(pd.DataFrame(board).sort_values("XP", ascending=False), hide_index=True, width="stretch")
        st.caption("XP comes from habits (logging, routine, learning), never from your health numbers, "
                   "so there's no reason to fudge a reading.")

# ---------------- TRENDS ----------------
WINDOWS = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "Whole mission": None}
CODE = {"ok": 0, "warn": 1, "alert": 2}

with tab_trends:
    if df.empty:
        st.info(f"No days saved for {crew} yet. Log a day on the Dashboard to see trends.")
    else:
        # ----- whole mission at a glance: every reading, color coded -----
        st.markdown('<div class="sec">MISSION AT A GLANCE</div>', unsafe_allow_html=True)
        grid, words = [], []
        for ind in INDICATORS:
            per_day = [next((f["level"] for f in fl if f["indicator"] == ind), status(ind, v, env_key))
                       for fl, v in zip(all_flags, df[ind])]
            grid.append([CODE[x] for x in per_day])
            words.append([f"{LABELS[ind]}: {fmt(ind, v)} {UNITS[ind]} ({WORDS[x].lower()})"
                          for x, v in zip(per_day, df[ind])])
        heat = go.Figure(go.Heatmap(
            z=grid, x=df["day"], y=[LABELS[i] for i in INDICATORS], customdata=words, zmin=0, zmax=2,
            colorscale=[[0, COLORS["ok"]], [0.33, COLORS["ok"]], [0.34, "#d9a400"], [0.66, "#d9a400"],
                        [0.67, COLORS["alert"]], [1, COLORS["alert"]]],
            showscale=False, xgap=1, ygap=2, hovertemplate="Day %{x}<br>%{customdata}<extra></extra>"))
        chart_layout(heat, 290).update_layout(hovermode="closest")
        heat.update_yaxes(autorange="reversed", showline=False, ticks="")
        st.plotly_chart(heat, width="stretch", config={"displayModeBar": False})
        st.caption("Each square is one reading: green normal, amber caution, red urgent. Look for columns that "
                   "light up together, like sleep, mood and heart rate dipping at the same time.")

        # ----- one indicator in detail -----
        st.markdown('<div class="sec">ONE INDICATOR IN DETAIL</div>', unsafe_allow_html=True)
        l, r = st.columns([1, 3], gap="large")
        ind = l.selectbox("Indicator", INDICATORS, format_func=lambda k: LABELS[k])
        others = [None] + [i for i in INDICATORS if i != ind]
        cmp_ind = l.selectbox("Compare with", others, format_func=lambda k: "Nothing" if k is None else LABELS[k],
                              help="Overlay a second indicator on its own axis to see if they move together.")
        window = l.segmented_control("Time window", list(WINDOWS), default="Whole mission") or "Whole mission"
        l.caption("Navy line: your readings, with flagged days marked in amber (caution) and red (urgent). "
                  f"Dotted blue: your own {BASELINE_DAYS}-day baseline. Background bands: safe, caution and "
                  "urgent zones. Drag the slider under the chart to zoom.")
        l.markdown(f"**Hazard:** {HAZARD[ind][0]}  \n**Risk:** {HAZARD[ind][1]}")
        with l.expander(f"What does {LABELS[ind].lower()} tell me?"):
            st.markdown(f"{GUIDE[ind]['what']}\n\n**In space.** {GUIDE[ind]['space']}")
        l.download_button(f"Download {crew}'s log (CSV)", df.to_csv(index=False),
                          f"orbit_check_{crew.lower().replace(' ', '_')}.csv", "text/csv", width="stretch")

        n = WINDOWS[window]
        view = df.tail(n) if n else df
        view_flags = all_flags[-len(view):]
        lim = limits(ind, env_key)
        cuts = [v for v in (lim.alert_lo, lim.warn_lo, lim.warn_hi, lim.alert_hi) if v is not None]
        pad = (max(cuts + [view[ind].max()]) - min(cuts + [view[ind].min()])) * 0.12 or 1
        y0, y1 = min(cuts + [view[ind].min()]) - pad, max(cuts + [view[ind].max()]) + pad
        if ind in ("mood", "radiation_msv", "sleep_hrs"):
            y0 = max(y0, 0)
        edges = [y0, lim.alert_lo, lim.warn_lo, lim.warn_hi, lim.alert_hi, y1]
        zones = ["alert", "warn", "ok", "warn", "alert"]

        fig = go.Figure()
        lo = y0
        for z, hi in zip(zones, edges[1:]):
            if hi is None:
                continue
            hi = min(max(hi, y0), y1)
            if hi > lo:
                fig.add_hrect(y0=lo, y1=hi, fillcolor=BANDS[z], line_width=0, layer="below")
            lo = hi

        levels = [next((f["level"] for f in fl if f["indicator"] == ind), "ok") for fl in view_flags]
        fig.add_scatter(x=view["day"], y=view[ind], mode="lines", name=LABELS[ind],
                        line=dict(color=INK, width=2.5), hovertemplate="%{y}")
        fig.add_scatter(x=df["day"], y=df[ind].rolling(BASELINE_DAYS, min_periods=MIN_BASELINE).mean(),
                        mode="lines", name=f"Your {BASELINE_DAYS}-day baseline",
                        line=dict(dash="dot", color=ACCENT, width=3), hovertemplate="%{y:.1f}")
        for lv in ("warn", "alert"):
            m = [x == lv for x in levels]
            if any(m):
                fig.add_scatter(x=view["day"][m], y=view[ind][m], mode="markers",
                                name=f"Flagged: {WORDS[lv].lower()}",
                                marker=dict(color=COLORS[lv], size=10, line=dict(color="white", width=1.5)),
                                hoverinfo="skip")
        if cmp_ind:
            fig.add_scatter(x=view["day"], y=view[cmp_ind], mode="lines", name=f"{LABELS[cmp_ind]} (right axis)",
                            yaxis="y2", line=dict(color="#8c5ac8", width=2, dash="dash"), hovertemplate="%{y}")
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", title=UNITS[cmp_ind], showgrid=False))
        fig.update_yaxes(range=[y0, y1], selector=dict(overlaying=None))
        chart_layout(fig, 460, UNITS[ind])
        fig.update_xaxes(range=[view["day"].min() - 0.5, view["day"].max() + 0.5],
                         rangeslider=dict(visible=True, thickness=0.07))
        r.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        st.markdown('<div class="sec">CUMULATIVE RADIATION DOSE (mSv)</div>', unsafe_allow_html=True)
        cumfig = go.Figure(go.Scatter(x=df["day"], y=df["radiation_msv"].cumsum(), fill="tozeroy", name="Mission dose",
                                      line=dict(color=INK, width=2), fillcolor="rgba(246,231,90,.75)",
                                      hovertemplate="%{y:.1f} mSv"))
        cumfig.add_scatter(x=df["day"], y=df["day"] * E.expected_msv, mode="lines", name=f"Typical for {E.short.lower()}",
                           line=dict(color="#7b8fa3", dash="dot"), hovertemplate="%{y:.1f} mSv")
        for d, when in df.loc[df["sep_event"] != "", ["day", "date"]].itertuples(index=False):
            cumfig.add_vline(x=d, line_dash="dot", line_color=COLORS["alert"],
                             annotation_text=f"{when:%d %b}", annotation_position="top left")
        st.plotly_chart(chart_layout(cumfig, 280, "mSv"), width="stretch", config={"displayModeBar": False})
        st.caption("Dotted red lines: real solar particle events (NASA DONKI). Grey dotted line: what a typical "
                   f"day in the {E.short.lower()} adds up to. Career limit: {CAREER_LIMIT_MSV} mSv. This mission so far: "
                   f"{df['radiation_msv'].sum():.1f} mSv ({df['radiation_msv'].sum() / CAREER_LIMIT_MSV:.1%}).")


# ---------------- NASA DATA ----------------
with tab_nasa:
    ev = sep_events()
    st.markdown('<div class="sec">SOLAR PARTICLE EVENTS, 2021-2025 (NASA DONKI)</div>', unsafe_allow_html=True)
    if ev.empty:
        st.info("No NASA files found. Run `python nasa_data.py` to download them.")
    else:
        near = ev[ev["severity"] > 0]
        st.markdown(
            f'<div class="nasa"><b>{len(near)}</b> days with a solar particle event that reached near-Earth space, '
            f'from <b>{len(ev)}</b> days NASA recorded in total. Events grow more common through Solar Cycle 25, '
            'which reached its maximum in late 2024. Your mission replays these real dates.</div>', unsafe_allow_html=True)
        monthly = (ev.assign(month=ev["date"].dt.to_period("M").dt.to_timestamp(),
                             kind=ev["severity"].map({2: "Strong (>100 MeV)", 1: "Moderate (>10 MeV)",
                                                      0: "Far side only (no effect near Earth)"}))
                     .groupby(["month", "kind"]).size().unstack(fill_value=0))
        evfig = go.Figure()
        for kind, color in (("Strong (>100 MeV)", COLORS["alert"]), ("Moderate (>10 MeV)", "#d9a400"),
                            ("Far side only (no effect near Earth)", "#9fb4c7")):
            if kind in monthly:
                evfig.add_bar(x=monthly.index, y=monthly[kind], name=kind, marker_color=color,
                              hovertemplate="%{y} day(s)")
        evfig.add_vrect(x0=mission_lo, x1=mission_hi, fillcolor="rgba(11,31,58,.10)",
                        line_width=0, annotation_text="your mission", annotation_position="top left")
        chart_layout(evfig, 300, "days with an event").update_layout(barmode="stack", xaxis_title="")
        st.plotly_chart(evfig, width="stretch", config={"displayModeBar": False})

        mine = df.loc[df["sep_event"] != "", ["day", "date", "sep_event", "radiation_msv"]]
        if len(mine):
            st.dataframe(mine.rename(columns={"day": "Mission day", "date": "Date", "sep_event": "Strength",
                                              "radiation_msv": "Your dose (mSv)"}),
                         hide_index=True, width="stretch",
                         column_config={"Date": st.column_config.DateColumn(format="D MMM YYYY")})
        else:
            st.caption("No near-Earth solar particle events during this mission window.")
        st.caption("Event dates and strengths are real. The extra dose added on those days is illustrative: "
                   "a real dose depends on shielding and where the spacecraft is.")

    st.markdown('<div class="sec">INSPIRATION4 CREW BLOODWORK (NASA OSDR)</div>', unsafe_allow_html=True)
    glu, wbc = crew_glucose(), crew_wbc()
    if glu.empty:
        st.info("No NASA files found. Run `python nasa_data.py` to download them.")
    else:
        glu = glu.assign(status=[status("glucose", v) for v in glu["value"]])
        n_flag = int((glu["status"] != "ok").sum())
        st.markdown(
            '<div class="nasa">Real blood tests from the four crew of SpaceX <b>Inspiration4</b> (3 days in orbit, '
            'September 2021), taken from 92 days before launch to 194 days after landing. Run through Orbit Check, '
            f'<b>{n_flag} of {len(glu)}</b> blood sugar readings would be flagged.</div>', unsafe_allow_html=True)

        def crew_chart(data, ytitle, bands, hover):
            fig = go.Figure()
            for (lo, hi, color) in bands:
                fig.add_hrect(y0=lo, y1=hi, fillcolor=color, line_width=0, layer="below")
            for (name, g), color in zip(data.groupby("crew"), CREW_COLORS):
                fig.add_scatter(x=g["timepoint"], y=g["value"], mode="lines+markers", name=name,
                                line=dict(color=color, width=2.5), marker=dict(size=8), hovertemplate=hover)
            fig.add_vrect(x0=2.3, x1=2.7, fillcolor="rgba(246,231,90,.8)", line_width=0,
                          annotation_text="flight", annotation_position="top")
            chart_layout(fig, 340, ytitle).update_layout(hovermode="closest")
            return fig.update_xaxes(categoryorder="array", categoryarray=TIMEPOINTS,
                                    title="Sample time (L = days before launch, R = days after return)")

        g1, g2 = st.columns(2, gap="large")
        lim = LIMITS["glucose"]
        g1.markdown("**Blood sugar** against Orbit Check's ranges")
        g1.plotly_chart(crew_chart(glu, "mg/dL", [
            (20, lim.alert_lo, BANDS["alert"]), (lim.alert_lo, lim.warn_lo, BANDS["warn"]),
            (lim.warn_lo, lim.warn_hi, BANDS["ok"]), (lim.warn_hi, lim.alert_hi, BANDS["warn"])],
            "%{y} mg/dL"), width="stretch", config={"displayModeBar": False})
        if not wbc.empty:
            g2.markdown("**White blood cells** against the lab's normal range")
            g2.plotly_chart(crew_chart(wbc, "thousand cells/µL", [
                (wbc["lo"].iloc[0], wbc["hi"].iloc[0], BANDS["ok"])], "%{y} k/µL"),
                width="stretch", config={"displayModeBar": False})
        st.caption("Source: NASA Open Science Data Repository, studies OSD-575 (metabolic panel) and OSD-569 "
                   "(blood count). Whether each sample was taken fasting isn't recorded, so the blood sugar "
                   "ranges are a guide here, not a diagnosis. Crew are anonymized as in the original data.")

# ---------------- GUIDE ----------------


def describe(lim):
    """Plain-text green / caution / urgent ranges for the Guide table."""
    hi_op, hi_not = ("≥", "<") if lim.hi_inclusive else (">", "≤")
    lo = lim.warn_lo if lim.warn_lo is not None else lim.alert_lo
    hi = lim.warn_hi if lim.warn_hi is not None else lim.alert_hi
    green = " and ".join(p for p in (f"≥ {lo}" if lo is not None else "",
                                     f"{hi_not} {hi}" if hi is not None else "") if p)
    caution = " or ".join(p for p in (f"< {lim.warn_lo}" if lim.warn_lo is not None else "",
                                      f"{hi_op} {lim.warn_hi}" if lim.warn_hi is not None else "") if p)
    urgent = " or ".join(p for p in (f"< {lim.alert_lo}" if lim.alert_lo is not None else "",
                                     f"{hi_op} {lim.alert_hi}" if lim.alert_hi is not None else "") if p)
    return green, caution or "–", urgent or "–"


with tab_guide:
    st.markdown('<div class="sec">THE FIVE HAZARDS OF SPACEFLIGHT</div>', unsafe_allow_html=True)
    hazards = [
        ("Space radiation", "Invisible, and one of the most hazardous parts of spaceflight."),
        ("Isolation and confinement", "Long stretches in a small space, far from home, affect behavior and mood."),
        ("Distance from Earth", "Medical care and supplies get harder to receive the farther you go."),
        ("Gravity fields", "Muscles, bones, inner ear and organs must adjust to new gravity."),
        ("Hostile/closed environments", "The spacecraft itself: temperature, pressure, noise, microbes."),
    ]
    for i, (col, (name, text)) in enumerate(zip(st.columns(5, gap="large"), hazards), 1):
        col.markdown(f'<div class="hz"><div class="n">0{i}</div><b>{name}</b><br>{text}</div>',
                     unsafe_allow_html=True)

    st.markdown('<div class="sec">COLOR CODES AT A GLANCE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="legend">'
        f'<div style="border-color:{COLORS["ok"]}"><b style="color:{COLORS["ok"]}">● NORMAL / GREEN</b>'
        'Inside the safe range and close to your own normal. Keep going.</div>'
        f'<div style="border-color:{COLORS["warn"]}"><b style="color:{COLORS["warn"]}">● CAUTION / AMBER</b>'
        'Worth a second look: retake the reading and follow the tip.</div>'
        f'<div style="border-color:{COLORS["alert"]}"><b style="color:{COLORS["alert"]}">● URGENT / RED</b>'
        'Act now: follow the action shown and contact your flight surgeon.</div>'
        '<div style="border-color:#f6e75a"><b>▀ YELLOW TOP</b>A day with a real solar particle event recorded by NASA.</div>'
        '</div>', unsafe_allow_html=True)
    st.caption("Every color also comes with a word (NORMAL, CAUTION, URGENT), so the status is clear even "
               "without seeing color.")

    st.markdown('<div class="sec">HOW TO TAKE EACH MEASUREMENT</div>', unsafe_allow_html=True)
    gcols = st.columns(2, gap="large")
    for i, ind in enumerate(GUIDE):
        g = GUIDE[ind]
        with gcols[i % 2].expander(f"{LABELS[ind]} ({UNITS[ind]})"):
            st.markdown(f"**What it is.** {g['what']}")
            st.markdown("**How to measure**\n" + "\n".join(f"{n}. {step}" for n, step in enumerate(g["how"], 1)))
            st.markdown(f"**Why it matters in space.** {g['space']}\n\n**Tip.** {g['tip']}")

    st.markdown('<div class="sec">WHERE YOU ARE CHANGES THE RISKS</div>', unsafe_allow_html=True)
    ecols = st.columns(len(ENVIRONMENTS), gap="medium")
    for col, e_ in zip(ecols, ENVIRONMENTS.values()):
        here = " here" if e_.key == env_key else ""
        risks = "".join(f"<li><b>{t}.</b> {d}</li>" for t, d in e_.risks)
        col.markdown(f'<div class="envcard{here}"><div class="en">{e_.short}{" (you)" if here else ""}</div>'
                     f'<div class="ef">{e_.gravity_text}<br>Signal: {e_.delay_text}<br>'
                     f'Radiation: ~{e_.expected_msv} mSv/day</div><ul>{risks}</ul></div>', unsafe_allow_html=True)
    st.caption("Typical radiation doses are published measurements: Curiosity's RAD in deep space (1.84 mSv/day) "
               "and on Mars (0.64), and the Chang'e 4 lander on the Moon (1.37). Switch environments under "
               "Manage mission.")

    st.markdown(f'<div class="sec">SAFE RANGES WE USE ({E.short.upper()})</div>', unsafe_allow_html=True)
    rows = ""
    for ind in INDICATORS:
        g, c, u = describe(limits(ind, env_key))
        rows += (f'<tr><td><b>{LABELS[ind]}</b> <span class="mono">({UNITS[ind]})</span></td>'
                 f'<td class="m" style="color:{COLORS["ok"]}">{g}</td>'
                 f'<td class="m" style="color:{COLORS["warn"]}">{c}</td>'
                 f'<td class="m" style="color:{COLORS["alert"]}">{u}</td>'
                 f'<td>{limits(ind, env_key).source}</td><td>{HAZARD[ind][0]}</td></tr>')
    st.markdown('<div style="overflow-x:auto"><table class="rng"><tr><th>MEASUREMENT</th><th>NORMAL</th>'
                f'<th>CAUTION</th><th>URGENT</th><th>SOURCE</th><th>HAZARD</th></tr>{rows}</table></div>',
                unsafe_allow_html=True)
    st.caption("Also urgent: blood pressure of 180/120 or higher, 3 nights in a row under 6 hours of sleep, "
               "and 3 days in a row with mood at 2 or lower.")

    a, b = st.columns([1.3, 1], gap="large")
    a.markdown('<div class="sec">HOW THE APP THINKS</div>', unsafe_allow_html=True)
    a.write("Every reading goes through three checks:\n"
            "1. **Safe range.** Is it inside the medical range above?\n"
            f"2. **Your own normal.** Is it far (3+ standard deviations) from your last {BASELINE_DAYS} days? "
            "A change can matter even inside the safe range.\n"
            "3. **The whole picture.** An Isolation Forest model compares today's full set of readings with "
            "every earlier day of the mission and flags unusual combinations.\n\n"
            "Each flag is explained and linked to a NASA hazard. Because you are far from Earth, "
            "any urgent flag (or 3+ cautions) tells you to contact your flight surgeon.")
    b.markdown('<div class="sec">HOW THE ROUTINE AND REWARDS WORK</div>', unsafe_allow_html=True)
    b.write("- **Routine:** measurements and healthy actions are scheduled on the mission clock (UTC). "
            "The banner tells you what's due now or overdue.\n"
            f"- **XP:** +{game.XP_CHECKIN} for a daily check-in, +10 to +15 per routine task, "
            f"+{game.XP_FULL_DAY} bonus for a full routine day, +{game.XP_QUIZ} for a correct quiz answer.\n"
            "- **Levels and badges** show your habits building up. Your streak counts days in a row with "
            "every routine task done.\n"
            "- **Fair play:** XP never depends on your health numbers, only on looking after yourself.")

# ---------------- ABOUT ----------------
with tab_about:
    st.markdown('<div class="sec">ABOUT THIS PROTOTYPE</div>', unsafe_allow_html=True)
    st.write("**Simulated vitals.** The 90-day mission's health readings are generated by our own script, with "
             "problems injected on purpose (a sleep-loss stretch, rising blood pressure, a blood sugar bump) "
             "so every kind of flag can be demonstrated.")
    st.write("**Real NASA data.** Radiation days replay real solar particle events from NASA's DONKI "
             "space-weather database on the mission's calendar dates. The NASA Data tab also shows real "
             "Inspiration4 crew blood tests from NASA's Open Science Data Repository (OSD-575, OSD-569).")
    st.write("**Safe ranges** come from the American Heart Association, CDC and American Diabetes Association, "
             "with some caution/urgent bands set by our team. See the Guide tab for the full table.")
    st.write("**Sources:** NASA DONKI; NASA Open Science Data Repository; "
             "NASA Human Research Program (5 Hazards, Risks of Human Spaceflight); "
             "CSA article on monitoring radiation for astronaut health.")
    st.write("**Five environments.** Space station, deep-space spacecraft, lunar rover, Moon base and Mars base, "
             "each with its own gravity, signal delay, radiation level and limits, routine and risks. Typical "
             "radiation levels come from Curiosity's RAD instrument (deep space and Mars) and the Chang'e 4 "
             "lander (Moon).")
    st.write("**Routine and rewards.** A daily routine on the mission clock prompts each measurement and "
             "healthy habit. XP, levels, streaks, badges and a daily quiz reward the habits, never the numbers.")
    st.write("**Not medical advice.** This is a hackathon prototype for the 2026 NASA Space Apps Challenge.")
