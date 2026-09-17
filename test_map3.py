"""Standalone harness for building/testing Map 3 before wiring it into the bot loop.

Run this directly (python test_map3.py) with BlueStacks already open and the
world map loaded. It connects ADB, then lets you fire individual game_actions
steps on demand so you can watch the instances and fix up tap coordinates
without going through the GUI's retry loops.
"""

import time

from bot_setup import connect_bluestacks_devices, check_adb_devices
from config import instances, RETRY_LIMIT
from adb_utils import hold_click_all_instances
from game_actions import (
    host_game_map3, run_map3_dungeon, loot, logout, joinback, invite, join_game,
    _battle_until_enemies_at_most, _battle_until_return_to_towne,
)
from ocr_utils import get_enemies_remaining_count, search_words_stacked

PARTY_NAMES = [instances[0]["name"], instances[1]["name"], instances[3]["name"], instances[2]["name"]]
PARTY_NAMES_REGION = (0, 449, 144, 611)


def wait_for_players_connected():
    for _ in range(RETRY_LIMIT):
        if search_words_stacked(PARTY_NAMES, *PARTY_NAMES_REGION):
            print("Everyone connected, starting run...")
            return True
        time.sleep(0.5)
    print("Not all players connected within retry limit.")
    return False

# Mirrors the exact step order inside game_actions.run_map3_dungeon so each
# move/battle segment can be fired and watched on its own.
STEPS = [
    ("Move: 48,639 (1000ms)", lambda: hold_click_all_instances(instances, 48, 639, 1000)),
    ("Move: 125,522 (1500ms)", lambda: hold_click_all_instances(instances, 125, 522, 1500)),
    ("Battle until enemies<=112 (First hallway cleared)", lambda: _battle_until_enemies_at_most(112, "First hallway cleared")),
    ("Move: 172,544 (1000ms)", lambda: hold_click_all_instances(instances, 172, 544, 1000)),
    ("Battle until enemies<=107 (Right hallway cleared)", lambda: _battle_until_enemies_at_most(107, "Right hallway cleared")),
    ("Move: 70,525 (1500ms)", lambda: hold_click_all_instances(instances, 70, 525, 1500)),
    ("Move: 173,632 (1500ms)", lambda: hold_click_all_instances(instances, 173, 632, 1500)),
    ("Battle until enemies<=71 (Right room cleared)", lambda: _battle_until_enemies_at_most(71, "Right room cleared")),
    ("Move: 147,650 (1000ms)", lambda: hold_click_all_instances(instances, 147, 650, 1000)),
    ("logout()", logout),
    ("joinback()", joinback),
    ("Move: 48,639 (1000ms)", lambda: hold_click_all_instances(instances, 48, 639, 1000)),
    ("Move: 125,522 (3000ms)", lambda: hold_click_all_instances(instances, 125, 522, 3000)),
    ("Move: 32,622 (1500ms)", lambda: hold_click_all_instances(instances, 32, 622, 1500)),
    ("Battle until enemies<=61 (Left hallway cleared)", lambda: _battle_until_enemies_at_most(61, "Left hallway cleared")),
    ("Move: 173,665 (1000ms)", lambda: hold_click_all_instances(instances, 173, 665, 1000)),
    ("Move: 45,589 (1000ms)", lambda: hold_click_all_instances(instances, 45, 589, 1000)),
    ("Battle until enemies<=25 (Left room cleared)", lambda: _battle_until_enemies_at_most(25, "Left room cleared")),
    ("logout()", logout),
    ("joinback()", joinback),
    ("Move: 48,639 (1000ms)", lambda: hold_click_all_instances(instances, 48, 639, 1000)),
    ("Move: 125,522 (7000ms)", lambda: hold_click_all_instances(instances, 125, 522, 7000)),
    ("Move: 80,569 (750ms)", lambda: hold_click_all_instances(instances, 80, 569, 750)),
    ("Battle until RETURN TO TOWNE", _battle_until_return_to_towne),
]

ACTIONS = {
    "1": lambda: (connect_bluestacks_devices(), check_adb_devices()),
    "2": host_game_map3,
    "3": run_map3_dungeon,
    "4": loot,
    "5": lambda: print(f"count = {get_enemies_remaining_count()}"),
    "6": invite,
    "7": join_game,
    "8": wait_for_players_connected,
}

STEP_OFFSET = 9
for i, (description, action) in enumerate(STEPS):
    ACTIONS[str(STEP_OFFSET + i)] = action

MENU = "\n".join([
    "1) Connect + check ADB devices",
    "2) Run host_game_map3()",
    "3) Run FULL run_map3_dungeon()  (runs the whole sequence below, ends on RETURN TO TOWNE)",
    "4) Run loot()",
    "5) Print get_enemies_remaining_count() once",
    "6) Run invite()",
    "7) Run join_game()",
    "8) Wait until everyone connected (name check, retries up to RETRY_LIMIT)",
    "--- individual run_map3_dungeon steps, in order ---",
] + [
    f"{STEP_OFFSET + i}) {description}" for i, (description, _) in enumerate(STEPS)
] + [
    "q) Quit",
])

if __name__ == "__main__":
    while True:
        print(MENU)
        choice = input("> ").strip().lower()
        if choice == "q":
            break
        action = ACTIONS.get(choice)
        if action is None:
            print("Unknown option.")
            continue
        try:
            action()
        except Exception as e:
            print(f"Step failed: {e}")
