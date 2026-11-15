# Orbit Check

Orbit Check is a daily health check-in for astronauts, built for the 2026 NASA Space Apps Challenge.

> This is a hackathon prototype. The demo astronaut's health readings are simulated. The space weather, astronaut blood tests and radiation levels come from NASA data and published studies. Orbit Check is not a medical device and does not give medical advice.

## Why we built this

Picture yourself on Mars. You've slept badly three nights running, your head hurts, and you can't tell if it's a rough week or the start of something serious. The doctor is on Earth, and a message takes up to 24 minutes to get there and the same again to come back.

Astronauts are trained in first aid, but most of them are not doctors, and far from Earth they have to spot problems early on their own. Orbit Check keeps track of the daily readings, explains each number in plain words, and says when it's time to contact the flight surgeon.

The challenge was: *Create Health Monitoring Software for Astronauts on Space Missions.*

## What it does

Every day, the astronaut logs heart rate, blood pressure, blood sugar, temperature, hours slept, mood and the day's radiation dose. Each reading then gets a color and a label. Green means "All good": the reading is in the safe range and close to the astronaut's usual. Amber means "Heads up": it's worth a second look. Red means "Act now": follow the advice shown and contact the flight surgeon.

Every flag has a short explanation, the NASA hazard it relates to, and a next step.

## How it fits the challenge

| The challenge asked for | What Orbit Check does |
|---|---|
| Insights for different environments | Pick a space station, a deep-space spacecraft, a lunar rover, a Moon base or a Mars base. Each one changes the gravity, the message delay to Earth, the normal radiation level, the radiation limits, the daily routine and the risks shown. |
| Prompts to measure or act | A daily routine runs on the mission clock (UTC, as on the space station). A banner shows what's due now, what's overdue and what's next, with how-to steps for each task. |
| Gamification | XP, levels from Cadet to Mission Legend, a routine streak, 10 badges, a daily space-health question and a crew leaderboard. Points come only from habits, never from health numbers, so there's no reason to change a reading. |
| Dynamic charts | A grid with one colored square per reading for the whole mission, and a detailed chart for any measurement with zoom, time windows, a personal average line and a second measurement to compare. |
| Color coding | Green, amber and red on readings, the mission timeline, the routine and the charts. Each color always comes with a word, for people who find colors hard to tell apart. |
| Simple instructions | Step-by-step guides for each measurement, a "learn more" note under every flag, a "why it matters in space" note for every measurement, and a daily quiz. |

## The tabs

The Dashboard is where you log today's check-in, add a note, and look at any day. You can edit a saved day or delete the latest one.

Routine & Rewards has today's checklist on the mission clock, your level, streak and badges, the question of the day, and the crew leaderboard.

Trends shows the whole mission on one grid, a closer chart for any measurement, and your running radiation total against the 600 mSv career limit.

NASA Data shows every solar particle event NASA's DONKI service recorded from 2021 to 2025. The demo mission replays them on their calendar dates, so a real storm becomes an alert. The tab also has blood tests from the four Inspiration4 crew members.

The Guide explains the colors, how to take each measurement, how the five environments differ, and the safe ranges the app uses.

Each crew member has their own log, baseline, mission setting and profile photo, taken with the camera or uploaded. Check-ins are saved in a SQLite database, so they are still there next time.

### What each environment watches

Each environment has three top-priority measurements, based on NASA's list of human spaceflight risks:

| Where | Watch closely | Why |
|---|---|---|
| Space station | Blood pressure, heart rate, sleep | Fluids shift toward the head, the heart loses fitness, and the Sun rises 16 times a day |
| Deep-space spacecraft | Radiation, mood, sleep | No magnetic field for shielding, Earth shrinks to a dot, and there's no day or night |
| Lunar rover | Radiation, sleep, temperature | Thin walls, sleeping in a seat, and a fever spreads fast in a small cabin |
| Moon base | Radiation, sleep, blood pressure | No atmosphere, two-week nights, and one-sixth gravity |
| Mars base | Mood, blood sugar, blood pressure | Messages take up to 24 minutes, years of packaged food, and readjusting to gravity after landing |

Top-priority measurements are listed first with a star, are flagged at smaller changes from your usual, and come with a note on why they matter in that place. The farther you are from help, the sooner Orbit Check tells you to call the flight surgeon: in deep space, on a rover or on Mars, two "Heads up" flags in a day are enough instead of three. The medical safe ranges are the same everywhere except for radiation.

Each environment's demo mission has its own events: a low-mood stretch in deep space, a fever in the rover, disrupted sleep on the Moon, and dizziness after landing on Mars.

### Sleep tracker

NASA's equipment list shows no sleep tracker in use on the space station since about 2020. Orbit Check's tracker needs only two taps. Tap "Going to sleep" at bedtime and "I'm awake" when you get up. Orbit Check records both times on the mission clock (UTC), works out how long you slept, adds it to today's check-in and ticks off "Log last night's sleep" in the routine.

You can also rate how well you slept from 1 to 5 and add minutes spent awake in the night, which are taken off the total. Naps count too. If you forgot to tap, you can add a night by hand, and the app rejects impossible times, overlapping nights and nights longer than 24 hours. The Trends tab shows a bar for each night from bedtime to waking, your average sleep, how regular your bedtime is, and the full sleep log.

### Typo check, symptoms, flight surgeon summary and PIN

If a reading looks like a slip, such as a heart rate of 660, swapped blood pressure numbers, or a value far from your own usual, Orbit Check asks "Did you mean that?" before saving. One tap saves it if it's right.

The check-in has eight symptom options: headache, changes in vision, a stuffy nose or puffy face, back or joint aches, nausea or dizziness, a cough or sore throat, itchy eyes or skin, and trouble concentrating. Each one has an explanation tied to a NASA spaceflight risk and to the environment. For example, itchy eyes on the Moon or Mars points to dust, and dizziness after landing points to readjusting to gravity. The same symptom three days in a row, or a cough with a fever, is flagged "Act now".

The flight surgeon summary is a short plain-text summary of the day, with readings against your usual, flags, symptoms, sleep and notes. You can copy it or download it.

A crew member can lock their log with a 4 to 8 digit PIN, which the app asks for on every new visit. Only a salted hash of the PIN is stored. Saved days are not encrypted yet.

### Voice mood check

NASA's ISS research equipment list has no device that measures mood. Under the mood slider, the astronaut can record 5 to 10 seconds about their day. Orbit Check takes about 100 measurements of the sound of the voice (pitch, loudness, pace and voice quality) and does not work out the words. A small neural network sorts the recording into upbeat, calm, low or stressed and suggests a mood score, which the astronaut can accept or ignore.

The model was trained on 1,248 recordings of 24 professional actors from the [RAVDESS](https://zenodo.org/records/1188976) dataset, with extra copies that add fan-like cabin noise and shift voices higher and lower. Tested only on actors it never trained on, it picks the right mood 63% of the time, or 58% with background noise. Random guessing would get 25%. Everyday voices are harder to read than actors' voices, so accuracy will be lower in real use.

Recordings are analysed in memory and never saved. The model runs with numpy and scipy and is stored as a 53 KB JSON file (`data/voice_mood_model.json`). To retrain it, download the RAVDESS speech audio and run `python voice_train.py path/to/folder`.

### ISS equipment for each measurement

We used NASA's list of the human-research equipment flown on the International Space Station (36 items) and the human-research experiments (about 370), from the [Space Station Research Explorer](https://www.nasa.gov/iss-science), and matched them to Orbit Check's measurements:

| Measurement | ISS research equipment | Examples (agency, years used) |
|---|---|---|
| Heart rate | In use today | Bio-Monitor (Canada, 2018 to today), European Physiology Module (Europe) |
| Blood pressure | In use today | Bio-Monitor, Mobil-O-Graph (Canada, 2023 to today) |
| Body temperature | In use today | Bio-Monitor (skin temperature) |
| Blood sugar | Only older equipment | i-STAT blood analyzer (NASA, 2001 to 2002) |
| Sleep | Only older equipment | Actiwatch Spectrum (NASA, 2010 to 2020) |
| Radiation | Only older research equipment | ALTEA, TEPC, Radiation Area Monitors |
| Mood | No device | Studied with questionnaires and computer tests |

Two of the Mars base's three priorities, mood and blood sugar, have no research equipment in use on the station today. Deep space has the same gap for mood.

This is NASA's list of research equipment, so it leaves out the everyday medical kit and the radiation monitors and dosimeters crews wear. NASA's open data also doesn't say which module each item is in, so the app shows the agency that provided it.

### How it decides something is wrong

Each reading gets three checks:

1. Is it outside a medical safe range? The ranges come from the American Heart Association, the CDC and the American Diabetes Association, plus a few bands our team set (see [thresholds.md](thresholds.md)).
2. Is it unusual for you? A heart rate of 85 is normal for many people, but if yours is usually 62, it's worth noticing. Each reading is compared with your own last 14 days.
3. Does today look odd overall? An Isolation Forest model flags days when the readings together look unlike the rest of the mission.

It also looks for patterns over several days: three short nights in a row, three low-mood days in a row, a blood pressure of 180/120 or higher, or a NASA-recorded solar particle event on that date.

## Try it yourself

You need Python 3.11 or newer.

```bash
git clone https://github.com/nayanikav-spec/Orbit_Check.git
cd Orbit_Check
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens with a demo astronaut who already has 90 days of data. Try logging day 91.

To run the tests, use `pip install pytest && python -m pytest`. To start fresh, delete `data/orbit_check.db`, and the demo astronaut is created again on the next run. The NASA data is already saved in `data/`. To download it again, get a free key at [api.nasa.gov](https://api.nasa.gov) and run `NASA_API_KEY=your_key python nasa_data.py`.

### Putting it online

[Streamlit Community Cloud](https://share.streamlit.io) hosts Streamlit apps for free:

1. Sign in with GitHub and click Create app.
2. Pick this repo, the `main` branch and `app.py`, and choose Python 3.11 or newer.
3. Click Deploy. After a few minutes you get a public link.

On the free plan, saved check-ins and photos are deleted whenever the site restarts or updates. A real mission would need a permanent database.

## What's inside

| File | What it does |
|---|---|
| `app.py` | The web app: every tab, chart and button |
| `rules.py` | The health checks and their plain-English explanations |
| `environments.py` | The five mission settings: gravity, signal delay, radiation, risks and photos |
| `routine.py` | The daily routine and what's due next |
| `game.py` | XP, levels, streaks and badges |
| `learn.py` | The how-to guides and quiz questions |
| `storage.py` | Saves each crew member's days, routine, sleep log and photo |
| `simulate.py` | Makes the demo astronaut's 90-day mission |
| `voice.py` and `voice_train.py` | The voice mood check and the script that trained it |
| `equipment.py` | Matches the station's health equipment and experiments to each measurement |
| `nasa.py` and `nasa_data.py` | Load and download the NASA data |
| `data/` | The saved NASA datasets |
| `thresholds.md` | Our research notes for every safe range |
| `tests/` | 75 automated tests |

Orbit Check is built with Python, Streamlit, Plotly, pandas, NumPy, scikit-learn, SciPy and Pillow.

## Sources

### NASA data

- NASA DONKI (Space Weather Database Of Notifications, Knowledge, Information): solar energetic particle events from 2021 to 2025. https://ccmc.gsfc.nasa.gov/tools/DONKI/
- NASA Open APIs, used to download DONKI data with a free key: https://api.nasa.gov
- NASA Open Science Data Repository: https://osdr.nasa.gov
  - Inspiration4 crew blood tests, study OSD-575 (comprehensive metabolic panel): https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
  - Inspiration4 crew blood tests, study OSD-569 (complete blood count): https://osdr.nasa.gov/bio/repo/data/studies/OSD-569
- NASA Space Station Research Explorer, human-research facilities and experiments on the ISS, downloaded November 2026: https://www.nasa.gov/iss-science
  - All Facilities report: https://www.nasa.gov/mission_pages/station/research/experiments/explorer/All_Facilities_Report.xlsx
  - All Experiments report: https://www.nasa.gov/mission_pages/station/research/experiments/explorer/All_Experiments_Report.xlsx
- NASA Human Research Program, the five hazards of human spaceflight: https://www.nasa.gov/hrp/hazards/
- NASA Human Research Roadmap, the named spaceflight health risks used in `rules.py`: https://humanresearchroadmap.nasa.gov

### Normal radiation in each place

- Deep space: 1.84 mSv a day, measured by Curiosity's RAD instrument on the way to Mars. Zeitlin et al., *Science*, 2013. https://doi.org/10.1126/science.1235989
- Mars surface: 0.64 mSv a day, also measured by Curiosity's RAD. Hassler et al., *Science*, 2014. https://doi.org/10.1126/science.1244797
- Moon surface: 1.37 mSv a day, measured by the Chang'e 4 lander. Zhang et al., *Science Advances*, 2020. https://doi.org/10.1126/sciadv.aaz1334

### Voice mood model

Livingstone SR and Russo FA (2018), *The Ryerson Audio-Visual Database of Emotional Speech and Song (RAVDESS)*, PLoS ONE 13(5): e0196391. https://doi.org/10.1371/journal.pone.0196391

The dataset is at https://zenodo.org/records/1188976. It is licensed CC BY-NC-SA 4.0, so the voice model can only be used non-commercially.

### Safe ranges

All the ranges and team-set bands are in [thresholds.md](thresholds.md).

- American Heart Association, blood pressure categories: https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings
- CDC, fever at 38.0 °C: https://www.cdc.gov
- American Diabetes Association, fasting blood sugar: https://diabetes.org

### Photos

All photos are from the NASA Image and Video Library (https://images.nasa.gov) and are public domain. Their use does not imply NASA endorsement.

- The space station over Earth, seen from Space Shuttle Endeavour (2000): https://images.nasa.gov/details/s97e5104
- Orion with the Moon and Earth on Artemis I (2022): https://images.nasa.gov/details/orion_earth_moon_20221121
- The Apollo 15 Lunar Roving Vehicle (1971): https://images.nasa.gov/details/as15-86-11603
- Earth setting over the Moon on Artemis II (2026): https://images.nasa.gov/details/art002e021278
- A sunset in Gale Crater on Mars, seen by Curiosity (2015), NASA/JPL-Caltech/MSSS: https://images.nasa.gov/details/PIA19400
- A spacewalk outside the space station (2019): https://images.nasa.gov/details/iss059e002710

### What's simulated

The demo astronaut's daily health readings, the extra radiation added on solar storm days, and the demo routine history are simulated.

## The team

## The team

SaiNayanika Vakkalanka set up the repo, wrote the simulated mission generator, worked with Shoury on the first dashboard and 
health checks, and gave the presentation.

Shoury Vasishta built most of the website: the five environments, the routine and rewards, daily storage and crew photos, 
the NASA data, the charts, the Guide, the sleep tracker, the voice mood check, the typo check, symptoms, flight surgeon summary 
and PIN. Shoury also did the research and the documentation.

The team used Claude, an AI assistant made by Anthropic, to help write and improve the code for these features.

Thanks to our parents for supporting us and helping with the coding and installation.