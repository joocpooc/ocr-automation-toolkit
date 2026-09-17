import os
import sys
import json
import pytesseract

TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

HOLD_MULTIPLIER = 0.7  # scale all hold durations (1.0 = original, 0.5 = half)

MONITOR_INDEX = 2
RETRY_LIMIT = 20

# settings.json lives next to the exe (or script) so IPs survive rebuilds
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATE_FILE    = os.path.join(_BASE_DIR, "gold_state.json")
SETTINGS_FILE = os.path.join(_BASE_DIR, "settings.json")

_DEFAULT_IPS = [
    "127.0.0.1:5585",
    "127.0.0.1:5555",
    "127.0.0.1:5575",
    "127.0.0.1:5595",
    "127.0.0.1:5605",
]

_NUM_INSTANCES = 5
_DEFAULT_NAMES = [f"Instance {i + 1}" for i in range(_NUM_INSTANCES)]
_DEFAULT_WINDOW_TITLES = [f"BlueStacks App Player {i + 1}" for i in range(_NUM_INSTANCES)]

# Real IPs/names/window titles are personal to each setup, so they're never
# hardcoded here - they're read from settings.json (gitignored, lives next to
# the script/exe) if present, falling back to generic placeholders otherwise.
def _load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

_settings = _load_settings()

instances = [
    {
        "ip": "",
        "window_title": _settings.get("window_titles", _DEFAULT_WINDOW_TITLES)[i]
            if i < len(_settings.get("window_titles", _DEFAULT_WINDOW_TITLES)) else _DEFAULT_WINDOW_TITLES[i],
        "name": _settings.get("names", _DEFAULT_NAMES)[i]
            if i < len(_settings.get("names", _DEFAULT_NAMES)) else _DEFAULT_NAMES[i],
    }
    for i in range(_NUM_INSTANCES)
]

def _apply_ips(ips):
    for i, inst in enumerate(instances):
        inst["ip"] = ips[i] if i < len(ips) else ""

_apply_ips(_settings.get("ips", _DEFAULT_IPS))


def save_ips(ips):
    """Persist IPs to settings.json (merging with any existing keys) and update instances in memory."""
    _apply_ips(ips)
    existing = _load_settings()
    existing["ips"] = ips
    with open(SETTINGS_FILE, "w") as f:
        json.dump(existing, f, indent=2)
