import json
import os
import time

import requests

from config import STATE_FILE
from ocr_utils import extract_text


def clean_number(text):
    text = text.strip()
    return int(text) if text.isdigit() else 0


def send_gold_update(webhook_url):
    boxes = [
        (108, 350, 193, 373),
        (748, 350, 850, 372),
        (1380, 350, 1470, 375),
        (1381, 728, 1470, 745),
        (210, 988, 355, 1020),
    ]

    current = []
    for box in boxes:
        text = extract_text(*box).strip()
        current.append(int(text) if text else 0)

    now = time.time()

    if not os.path.exists(STATE_FILE):
        state = {"previous": current, "lifetime_total": 0, "last_time": now}
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        return

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    previous = state["previous"]
    last_time = state.get("last_time", now)

    deltas = [max(0, current[i] - previous[i]) for i in range(5)]
    cycle_total = sum(deltas)

    elapsed = now - last_time
    avg_runtime = elapsed / 5
    state["lifetime_total"] += cycle_total
    state["previous"] = current
    state["last_time"] = now

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    mins, secs = int(avg_runtime // 60), int(avg_runtime % 60)
    avg_string = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    message = (
        "💰 **Gold Earnings (Last 5 runs)**\n\n"
        + "\n".join(f"{i+1}: +{d}" for i, d in enumerate(deltas))
        + f"\n\n⏱ Avg run time: {avg_string}"
    )

    requests.post(webhook_url, json={"content": message})
