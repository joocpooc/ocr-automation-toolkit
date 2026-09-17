# ocr-automation-toolkit

Python toolkit for screen-reading automation: OCR-based state detection (OpenCV/Tesseract), ADB device control, and a Tkinter GUI orchestrator for running the same workflow across multiple Android emulator instances in parallel.

## How it works

- **`ocr_utils.py`** — screen capture (`mss`) + preprocessing (OpenCV/Pillow) + text extraction (Tesseract via `pytesseract`) to detect on-screen state (labels, counters, fuzzy-matched text via `fuzzywuzzy`).
- **`adb_utils.py`** — sends taps/holds to one or more Android emulator instances over ADB.
- **`bot_setup.py`** — connects to emulator instances and auto-detects their ADB ports/serials.
- **`game_actions.py`** — higher-level action sequences built from the OCR + ADB primitives.
- **`gui.py`** / **`main.py`** — Tkinter desktop UI that ties it all together: an instance table, live console output, and start/stop control.

## Setup

### Prerequisites

- **Python 3.10+** (developed against 3.14)
- **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)** installed. By default the code expects it at:
  ```
  C:\Program Files\Tesseract-OCR\tesseract.exe
  ```
  If yours is installed elsewhere, update `TESSERACT_PATH` in [`config.py`](config.py).
- **ADB (Android Debug Bridge)** available on your `PATH`.
- An Android emulator (e.g. BlueStacks) with one or more instances running, each with ADB debugging enabled.

### Install

```powershell
pip install -r requirements.txt
```

### Configure

Edit [`config.py`](config.py) to match your setup:

- `MONITOR_INDEX` — which monitor (as reported by `screeninfo`) the emulator windows are on.
- `instances` — list of emulator instances (window title + display name). Their ADB IPs are auto-detected at runtime and persisted to `settings.json` (created next to the script/exe on first run), so you don't need to hardcode IPs here.
- `HOLD_MULTIPLIER` / `RETRY_LIMIT` — timing/retry tuning.

### Calibrate the OCR search boxes

All state detection (world map check, boss name, enemies-remaining counter, dialog buttons, party-member names, etc.) reads a **fixed pixel region** of the screen and OCRs whatever is inside it. Those regions are hardcoded as absolute `(top_left_x, top_left_y, bottom_right_x, bottom_right_y)` coordinates on the monitor selected by `MONITOR_INDEX`, so they only line up if your emulator windows are positioned/sized exactly like the original setup. **On a different resolution, monitor arrangement, or window layout, every box needs to be re-measured before the tool will detect anything correctly.**

Where they live:

- **`ocr_utils.py`** — `get_enemies_remaining()` (fixed region) and `get_enemies_remaining_count(top_left_x=..., top_left_y=..., bottom_right_x=..., bottom_right_y=...)` (defaults, overridable per call).
- **`gui.py`** — inline coordinates passed to `search_words(...)` / `search_words_stacked(...)` for things like the world-map load check, the "FORCE START" lobby check, and the connected-party-names check.
- **`game_actions.py`** — inline coordinates passed to `search_boss_name(...)`, `search_return_to_towne(...)`, and `search_words(["EXIT"], ...)` for boss identification and dialog/navigation buttons.

How to re-measure a box:

1. Take a full screenshot of the target monitor (or use `print_monitor_info()` from `bot_setup.py` to confirm the monitor's origin/resolution first).
2. Find the pixel coordinates of the top-left and bottom-right corners of the text/button you want detected, relative to that monitor's origin.
3. Update the corresponding call site above with the new `(top_left_x, top_left_y, bottom_right_x, bottom_right_y)` values.
4. Re-run and check the generated `debug_*.png` files (saved next to the script — gitignored) to confirm the crop actually contains the expected text before trusting the OCR result.
5. For the enemies-remaining counter specifically, `test_enemies.py` is a tight loop for iterating on the region/threshold without going through the full GUI flow.

## Usage

### Run from source

```powershell
python main.py
```

This launches the GUI:

1. **Instance table** — shows each configured emulator instance, its ADB IP (editable), a connection-status dot, and any tracked in-game counter.
2. **Connect BlueStacks** — runs `adb connect` against each configured IP.
3. **Auto-detect IPs** — scans local ADB ports, matches devices to instances by serial number, and saves the mapping so it survives restarts/rebuilds.
4. **Map dropdown** — selects which workflow/action sequence to run.
5. **▶ Start Bot** — runs the selected workflow in a background thread across all connected instances; button becomes **■ Stop Bot** to halt it (see [`stop_flag.py`](stop_flag.py)).
6. **Console** — live log output from the running workflow.
7. **Clear Inventory** — runs the standalone inventory-clearing action.

Debug screenshots taken during OCR steps are saved as `debug_*.png` in the working directory (gitignored) — useful for tuning capture regions/thresholds in `ocr_utils.py`.

### Build a standalone executable

```powershell
build.bat
```

This runs PyInstaller (`--onefile --windowed`) and produces `dist\lairbot.exe`. `settings.json` (saved IPs/serials) is written next to the executable so it persists across rebuilds.

### Standalone test/tuning scripts

- **`test_enemies.py`** — loops `get_enemies_remaining_count()` for tuning its OCR region/thresholds.
- **`test_map3.py`** — interactive playground for firing individual `game_actions` functions against connected instances without running the full GUI loop.
