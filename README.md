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

### Recommended specs

Running several Android emulator instances at once (5 by default) is the main resource cost here — the OCR/ADB overhead on top of that is comparatively light.

| | Minimum (1–2 instances) | Recommended (5 instances) |
|---|---|---|
| CPU | Quad-core, VT-x/AMD-V virtualization enabled | 8+ cores / threads (modern desktop CPU) |
| RAM | 8 GB | 32 GB |
| Storage | Any (SSD preferred) | SSD — multiple emulator instances are disk-heavy on boot |
| GPU | Integrated is fine | Dedicated GPU improves per-instance render smoothness |

Scale roughly linearly if you configure more or fewer instances in [`config.py`](config.py). Make sure hardware virtualization (Intel VT-x / AMD-V) is enabled in BIOS — BlueStacks needs it and performance degrades badly without it.

### Install

```powershell
pip install -r requirements.txt
```

### Configure

Edit [`config.py`](config.py) to match your setup:

- `MONITOR_INDEX` — which monitor (as reported by `screeninfo`) the emulator windows are on.
- `HOLD_MULTIPLIER` / `RETRY_LIMIT` — timing/retry tuning.

Per-instance details (IPs, window titles, display names) are personal to your setup and are **not** hardcoded in `config.py` — they're loaded at runtime from `settings.json`, which lives next to the script/exe and is gitignored. Without one, generic placeholders (`Instance 1`, `Instance 2`, ...) and loopback defaults are used, and IPs get filled in automatically the first time you use **Auto-detect IPs** in the GUI.

To pre-set your own instance names/window titles (not editable from the GUI), create `settings.json` in the project root:

```json
{
  "ips": ["127.0.0.1:5585", "127.0.0.1:5555", "127.0.0.1:5575", "127.0.0.1:5595", "127.0.0.1:5605"],
  "window_titles": ["BlueStacks App Player 1", "BlueStacks App Player 2", "BlueStacks App Player 3", "BlueStacks App Player 4", "BlueStacks App Player 5"],
  "names": ["Alice", "Bob", "Carol", "Dave", "Eve"]
}
```

`ips` is also rewritten automatically by **Connect BlueStacks** / **Auto-detect IPs**, and `serials` (used for auto-detection) is added there too — none of it should ever be committed.

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
