"""Standalone playground for tuning get_enemies_remaining_count().

Run this while a BlueStacks instance is visible on the configured monitor
(see config.MONITOR_INDEX) with the "Enemies Remaining" label on screen.
Watch the printed count and check debug_enemies_remaining*.png to tune
the crop box / preprocessing in ocr_utils.py.
"""

import time

from ocr_utils import get_enemies_remaining_count

if __name__ == "__main__":
    while True:
        count = get_enemies_remaining_count()
        print(f"count = {count}")
        time.sleep(1)
