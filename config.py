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

def _load_ips():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f).get("ips", _DEFAULT_IPS)
        except Exception:
            pass
    return list(_DEFAULT_IPS)

instances = [
    {"ip": "", "window_title": "BlueStacks App Player 3", "name": "Minaamage"},
    {"ip": "", "window_title": "BlueStacks App Player 1", "name": "Religeous"},
    {"ip": "", "window_title": "BlueStacks App Player 2", "name": "Fierybride"},
    {"ip": "", "window_title": "BlueStacks App Player 4", "name": "Rafakillo"},
    {"ip": "", "window_title": "BlueStacks App Player 5", "name": "Iscataol"},
]

def _apply_ips(ips):
    for i, inst in enumerate(instances):
        inst["ip"] = ips[i] if i < len(ips) else ""

_apply_ips(_load_ips())


def save_ips(ips):
    """Persist IPs to settings.json and update instances in memory."""
    _apply_ips(ips)
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"ips": ips}, f, indent=2)
