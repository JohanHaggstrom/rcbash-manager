# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

RC-racing timing/results manager (Swedish: "bash"-class, scale 1/5) for a full race day: Kval → Åttondelsfinal → Kvartsfinal → Semifinal → Final across three classes (2WD, SC, 4WD) with up to three skill groups (A/B/C). Reads HTML exports from RaceLogic timing hardware on a USB drive, matches against start lists, stores JSON per day, and computes points.

User-facing language is **Swedish**. Code identifiers are English, but printed strings, round names (`"Kval"`, `"Åttondelsfinal"`, …), class/group labels, and prompts are Swedish — keep them that way.

The main reference is [DOKUMENTATION.md](DOKUMENTATION.md) (Swedish, ~370 lines). It's authoritative for domain rules (point tables, start-list algorithms, race flow) — consult it before changing scoring or start-list logic.

## Running the app

Batch files in [scripts/](scripts/) are thin wrappers that `cd` to their own directory and invoke `py ../racelogic/resultcalculation.py <flag>`. That working directory matters: `resultcalculation.py` reads `./settings.json` relative to CWD, and `filelocation.py` reads `../racelogic/settings.json`. Invoking from other CWDs silently falls back to hard-coded defaults.

Direct CLI equivalents (run from the `scripts/` folder or replicate its CWD):

| Flag | Action |
|---|---|
| `-s` | Start a new race day, prompts for participants per class/group |
| `-g` | Show the next heat + start list |
| `-r` | Read latest HTML from USB and register result |
| `-r -m` | Manual result entry (fallback when USB/parse fails) |
| `-n` | Generate next round's start lists |
| `-l` | Show current round's start lists |
| `-d` | Show latest result |
| `-d -p` | Pick a specific heat to display |
| `-o` | Show current standings |
| `-o -v` | Standings with per-round breakdown |
| `-e <num>` | Exclude driver (DNS) from a result |

GUI alternative: [scripts/RCBashGUI.pyw](scripts/RCBashGUI.pyw) is a Tk launcher that spawns `resultcalculation.py` as a subprocess and routes stdin/stdout to a window. Launch via `scripts/StartaGUI.bat`. It does not replace the CLI — it wraps it.

First-time setup installs pip deps (`numpy`, `clipboard`) via `scripts/KörDettaInnanFörstaStart.bat`.

## Tests

Tests live in [racelogic/tests/](racelogic/tests/) but **import from `server.racelogic.*`** — they assume a parent `server/` package that does not exist in this repo. They cannot be run as-is from this checkout; they belong to a sibling web-server deployment. When editing test-covered logic, verify behavior manually or mirror the change in the server repo. Do not rewrite the imports to the flat paths — that breaks the server deployment.

Test data (reference JSON race days, sample RaceLogic HTML) lives in `racelogic/tests/testdata/` and is still useful as a fixture source when reasoning about the data model.

## Architecture

### Dual import paths (important)

Every module under [racelogic/](racelogic/) starts with a `try: from server.racelogic.X ... except ImportError: from X ...` block. The project ships as a standalone CLI (flat imports win) but the same files are consumed by a separate web server where they live under `server/racelogic/`. **Preserve this pattern in any new module** and in any cross-module import — breaking it breaks the server deployment invisibly.

`raceday.py` additionally swaps its driver-name lookup based on import context: server path uses `server.models.get_driver_name`; flat path falls back to the static `NAMES` dict in [racelogic/names.py](racelogic/names.py).

### Module responsibilities

- [racelogic/resultcalculation.py](racelogic/resultcalculation.py) — CLI entry point + workflow orchestration + start-list algorithms + points math. The big file (~34 KB). All batch-file flags dispatch here via argparse.
- [racelogic/raceday.py](racelogic/raceday.py) — Data model (`Driver`, `HeatStartLists`, `RaceResult`, `Raceday`) and JSON persistence. Owns round-name and class-order constants.
- [racelogic/htmlparsing.py](racelogic/htmlparsing.py) — `RCMHtmlParser` state machine for RaceLogic HTML + extraction helpers (positions, lap counts, best/avg laps).
- [racelogic/filelocation.py](racelogic/filelocation.py) — Polls the USB drive (default `E:`) and reads the newest numerically-named `.html`. Encoding is hard-coded `utf-16-le`.
- [racelogic/duration.py](racelogic/duration.py) — Value object for lap times (internal ms, prints `M:SS:mmm`).
- [racelogic/textmessages.py](racelogic/textmessages.py) — User-facing string builders (Swedish, with medal emojis for top-3).
- [racelogic/names.py](racelogic/names.py) — Static `NAMES = {number: "Firstname Lastname"}` — edit by hand before each race day. Empty slots use the number as a string. [racelogic/__names.py](racelogic/__names.py) is a legacy backup, unused.
- [racelogic/constants.py](racelogic/constants.py) — `RESULT_FOLDER_PATH` (`~/RCBashResults`), point-table caps (40 non-finals, 80 finals).

### Data storage

One JSON file per race day at `%USERPROFILE%\RCBashResults\YYMMDD.json` (Windows) or `/home/malcolm/RCBashResults/YYMMDD.json` (Linux fallback, legacy). Schema is documented in DOKUMENTATION.md §7. The `current_heat` field is an index into `RACE_ORDER` in `raceday.py`.

### Configuration

[racelogic/settings.json](racelogic/settings.json) holds `drive` (USB mount) and `max_participants` (cap per Final group). Driver roster lives in [racelogic/names.py](racelogic/names.py), not settings.

## Gotchas

- **CWD-sensitive config**: `settings.json` is read relative to the caller's CWD. Always launch via the batch files or mirror their `cd scripts/` behavior.
- **Duplicate drivers across groups**: detected but not prevented — the system warns and continues. Don't add automatic correction without checking intent.
- **`py` launcher required**: batch files call `py`, not `python`. Don't swap them — `py` picks the system-appropriate Python on Windows.
- **UTF-16-LE only**: HTML parser assumes RaceLogic's native encoding. Other encodings need explicit handling.
- **Finals scoring is separate**: Final points (80/-2 per place) add to the total; they don't replace prior-round points. See DOKUMENTATION.md §8.
- **Season drop-worst-race uses `numpy.argmin`**: per-driver, not global. Changes to season aggregation should keep this per-driver semantic.
