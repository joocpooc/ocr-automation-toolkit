"""Daily blessing scheduler.

Rolling window: the blessing unlocks 24h after the last claim and must be
claimed within 5h of unlocking. Missing the window resets the streak, after
which it can be claimed any time (and that claim becomes the new anchor).
Either way the rule for the bot is the same: claim as soon as it's unlocked.
"""
import json
import os
from datetime import datetime, timedelta

from config import BLESSING_FILE

UNLOCK_AFTER = timedelta(hours=24)
WINDOW = timedelta(hours=5)
# Buffer after unlock so a slightly fast PC clock doesn't tap before the game unlocks it.
SAFETY_DELAY = timedelta(minutes=5)


def _now():
    return datetime.now().astimezone()


def last_claim():
    try:
        with open(BLESSING_FILE) as f:
            return datetime.fromisoformat(json.load(f)["last_claim"])
    except (OSError, ValueError, KeyError):
        return None


def _record_claim(when):
    with open(BLESSING_FILE, "w") as f:
        json.dump({"last_claim": when.isoformat(timespec="seconds")}, f, indent=2)


def status():
    """Human-readable line about the next blessing, for logging."""
    last = last_claim()
    if last is None:
        return "Blessing: no claim recorded yet, will claim now."
    unlock = last + UNLOCK_AFTER
    return (f"Blessing: last claimed {last:%a %H:%M}, "
            f"window {unlock:%a %H:%M} - {unlock + WINDOW:%H:%M}.")


def is_due():
    last = last_claim()
    if last is None:
        return True
    return _now() >= last + UNLOCK_AFTER + SAFETY_DELAY


def maybe_claim(claim_fn):
    """Claim the blessing via claim_fn() if it's unlocked. claim_fn must return
    True only if the claim actually happened; only then is the new time saved."""
    if not is_due():
        return False

    last = last_claim()
    if last is not None and _now() > last + UNLOCK_AFTER + WINDOW:
        print(f"Blessing window missed (last claim {last:%a %H:%M}); streak reset, claiming now.")
    else:
        print("Blessing unlocked, claiming...")

    claimed_at = _now()
    if not claim_fn():
        print("Blessing claim failed or not implemented; will retry next run.")
        return False

    _record_claim(claimed_at)
    print(f"Blessing claimed at {claimed_at:%a %H:%M}. "
          f"Next window: {claimed_at + UNLOCK_AFTER:%a %H:%M} - {claimed_at + UNLOCK_AFTER + WINDOW:%H:%M}.")
    return True
