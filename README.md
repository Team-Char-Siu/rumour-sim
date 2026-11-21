# Rumour simulation - Team Char Siu

Serial mobile-agent rumour model. Python, NumPy, SciPy, Arcade.
Parallel implementation and benchmarks: pending.

## Setup

```powershell
python -m pip install -r requirements.txt
python -m pip install --no-deps arcade
```

Arcade is installed separately in the current dependency workflow. Versions are
not fully pinned; record the environment when comparing runs.

## Run

```powershell
python main.py "A rumour about the subject"
python main.py "A rumour about the subject" --n=500 --steps=400 --seed=42
python main.py "A rumour about the subject" --seed=7
python main.py "A rumour about the subject" --headless
python -m unittest discover -s tests -v
```

Omit the rumour argument for an input prompt. Defaults: 500 agents, 400 steps,
seed 42. R replays the same seed. Same code, settings and numerical environment
are required for repeatable results.

Headless outputs: `results/curve.png`, `group_spreaders.png`,
`near_subject.png`, `tree.png`. The printed elapsed time includes plotting;
it is not a model-only benchmark.

## Controls

| Key | Action |
|---|---|
| Space | Pause/resume |
| Up / Down | Speed |
| Enter | Skip intro |
| R | Replay |
| S | Size by direct rumour transmissions |
| T | Retain/fade transmission arrows |
| G | Hop colours |
| F | Follow newest rumour chain |
| H | Group outlines |
| Click agent | Inspect its rumour chain |
| Hover agent / graph | Inspect traits / state counts |
| Esc / Q | Quit |

## Display

- Pale: unaware. Red: active rumour spreader. Green: active corrector.
- Grey: inactive. Orange: inactive agent credited with previous transmissions.
- Pink centre: subject/current friend. Violet centre: ex-friend.
- Red outer ring: avoiding the subject. Friendship nodes retain active-state outlines.
- White marker: patient zero. Pink marker/radius: subject/avoidance boundary.
- Gold chain: patient zero to newest rumour recipient. White chain: selected agent.
- T arrows: red rumour, green correction, grey explicit rejection.
- Size and leaderboard use direct attributed recipients, not downstream reach.
  Counts can tie. No transmission-count cap or guaranteed leading spreader.
- Chart: 400x220. Panel: three spreader rows and three recent-pass rows.

## Code

| File | Responsibility |
|---|---|
| `agent.py` | States, timers, belief and friendship transitions |
| `movement.py` | Random walk, group visits, avoidance routing |
| `simulation.py` | Population setup, snapshot transmission, statistics |
| `main.py` | CLI, defaults, live/headless entry points |
| `viewer_arcade.py` | Base viewer, panels, graph, controls |
| `viewer_friendships.py` | Friendship and avoidance overlays |
| `viewer_effects.py` | Thin arrows and avoidance indicator helpers |
| `plots.py` | Headless plots |
| `tests/` | Regression tests |

Model rules, equations, methods, defaults and implementation record:
[notes.md](notes.md). Attribution and source links: [references.md](references.md).
