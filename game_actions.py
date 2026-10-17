import random
import string
import time
import threading

from config import instances
from adb_utils import tap_on_instance, send_text, send_keystroke, tap_all_instances, hold_click_all_instances, batch_tap_all_instances, batch_swipe_all_instances, batch_tap_instance
from ocr_utils import (
    search_words, search_boss_name, search_return_to_towne, get_enemies_remaining_count,
)
import stop_flag
from watcher import Watcher


BOSS_NAME_REGION = (375, 431, 852, 459)
TOWNE_REGION = (409, 823, 725, 866)
ZORI_GRACE_SECONDS = 10  # first boss ends if Zori isn't seen for this long


def _read_boss():
    """One quick read for the watcher thread: boss name or None (no TOWNE check, cheaper)."""
    return search_boss_name(*BOSS_NAME_REGION, attempts=1)


def _read_boss_or_towne():
    """One quick read for the watcher thread: boss name, else 'towne', else None."""
    boss = search_boss_name(*BOSS_NAME_REGION, attempts=1)
    if boss:
        return boss
    if search_return_to_towne(*TOWNE_REGION):
        return "towne"
    return None


def _read_towne():
    return "towne" if search_return_to_towne(*TOWNE_REGION) else None


def _random_room_password(length=3):
    """Generate a fresh random lobby password so none is hardcoded/static."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def host_game():
    tap_on_instance(instances[0]["ip"], 773, 60)
    time.sleep(0.1) #2
    tap_on_instance(instances[0]["ip"], 324, 663)
    time.sleep(0.2) #1
    tap_on_instance(instances[0]["ip"], 444, 147)
    tap_on_instance(instances[0]["ip"], 1107, 413)
    tap_on_instance(instances[0]["ip"], 144, 645)
    send_text(instances[0]["ip"], _random_room_password())
    send_keystroke(instances[0]["ip"], 66)
    time.sleep(0.2) #1
    tap_on_instance(instances[0]["ip"], 597, 649)


def host_game_map2():
    tap_on_instance(instances[0]["ip"], 773, 60)
    time.sleep(2)
    tap_on_instance(instances[0]["ip"], 324, 663)
    time.sleep(1)
    for _ in range(4):
        tap_on_instance(instances[0]["ip"], 444, 147)
    tap_on_instance(instances[0]["ip"], 913, 413)
    tap_on_instance(instances[0]["ip"], 144, 645)
    send_text(instances[0]["ip"], _random_room_password())
    send_keystroke(instances[0]["ip"], 66)
    time.sleep(1)
    tap_on_instance(instances[0]["ip"], 597, 649)


def host_game_map3():
    # TODO: replace with real lobby-creation taps for Map 3
    tap_on_instance(instances[0]["ip"], 773, 60)
    time.sleep(2)
    tap_on_instance(instances[0]["ip"], 324, 663)
    time.sleep(1)
    for i in range(3):
            tap_on_instance(instances[0]["ip"], 444, 147)
    tap_on_instance(instances[0]["ip"], 913, 512)
    tap_on_instance(instances[0]["ip"], 144, 645)
    send_text(instances[0]["ip"], _random_room_password())
    send_keystroke(instances[0]["ip"], 66)
    time.sleep(1)
    tap_on_instance(instances[0]["ip"], 597, 649)


def join_game():
    def tap_and_send(instance, x1, y1, x2, y2, key_code):
        tap_on_instance(instance["ip"], x1, y1)
        time.sleep(0.5)
        tap_on_instance(instance["ip"], x2, y2)
        time.sleep(0.5)
        send_keystroke(instance["ip"], key_code)

    threads = [
        threading.Thread(target=tap_and_send, args=(inst, 635, 55, 869, 281, 66))
        for inst in instances[1:]
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def invite():
    tap_on_instance(instances[0]["ip"], 36, 37)
    time.sleep(0.5)
    tap_on_instance(instances[0]["ip"], 849, 48)
    time.sleep(0.2)
    batch_tap_instance(instances[0]["ip"], (407, 275), (407, 396), (407, 516), (407, 605), (47, 44))


def use_buffs():
    batch_tap_all_instances(instances,
        (1107, 334),
        (1107, 407),
        (1107, 477),
    )


def potspam(reps):
    for _ in range(reps):
        batch_tap_all_instances(instances, (907, 657), (907, 657))


def use_skills():
    batch_tap_all_instances(instances,
        (1250, 333),
        (1233, 403),
        (1233, 478),
        (1233, 548),
        (1175, 545),
        (1175, 478),
    )


def use_skills2():
    batch_tap_all_instances(instances,
        (1176, 643), (1176, 643),
        (1233, 187), (1176, 643),
        (1176, 643), (1176, 643),
        (1233, 293), (1176, 643),
        (1176, 643), (1176, 643),
        (1233, 393), (1176, 643),
        (1176, 643), (1176, 643),
        (1233, 493), (1176, 643),
        (1176, 643), (1176, 643),
        (1129, 497), (1176, 643),
        (1129, 393), (1176, 643),
        (1176, 643), (1176, 643),
        (1176, 643),
    )


def run_map2_dungeon():
    tap_on_instance(instances[0]["ip"], 636, 593)
    read_exit = lambda: "exit" if search_words(["EXIT"], 437, 800, 602, 860, 70) else None
    with Watcher(read_exit, name="map2 exit"):
        while True:
            stop_flag.check()
            use_buffs()
            use_skills2()
    print("EXIT found, dungeon complete.")
    hold_click_all_instances(instances, 141, 535, 800)
    loot()
    hold_click_all_instances(instances, 95, 681, 1600)
    loot()
    hold_click_all_instances(instances, 39, 599, 1000)
    loot()
    loot2()



def logout():
    # TODO: replace with the real mid-dungeon logout tap sequence for Map 3
    pass


def joinback():
    # TODO: replace with the real mid-dungeon rejoin tap sequence for Map 3
    pass


def _battle_until_enemies_at_most(threshold, label):
    def read_cleared():
        count = get_enemies_remaining_count()
        return "cleared" if count is not None and count <= threshold else None

    with Watcher(read_cleared, confirmations=3, name=label):
        while True:
            stop_flag.check()
            use_buffs()
            use_skills2()
    print(f"{label} confirmed.")


def _battle_until_return_to_towne():
    with Watcher(_read_towne, confirmations=3, name="return to towne"):
        while True:
            stop_flag.check()
            use_buffs()
            use_skills2()
    print("RETURN TO TOWNE confirmed, dungeon complete.")


def run_map3_dungeon():
    # TODO: replace with the real start-run tap for Map 3
    tap_on_instance(instances[0]["ip"], 636, 593)
    print("Starting Map 3 dungeon (122 enemies).")

    hold_click_all_instances(instances, 48, 639, 1000)
    hold_click_all_instances(instances, 125, 522, 1500)
    _battle_until_enemies_at_most(112, "First hallway cleared")

    hold_click_all_instances(instances, 172, 544, 1000)
    _battle_until_enemies_at_most(107, "Right hallway cleared")

    hold_click_all_instances(instances, 70, 525, 1500)
    hold_click_all_instances(instances, 173, 632, 1500)
    _battle_until_enemies_at_most(71, "Right room cleared")

    hold_click_all_instances(instances, 147, 650, 1000)
    logout()
    joinback()
    hold_click_all_instances(instances, 48, 639, 1000)
    hold_click_all_instances(instances, 125, 522, 3000)
    hold_click_all_instances(instances, 32, 622, 1500)
    _battle_until_enemies_at_most(61, "Left hallway cleared")

    hold_click_all_instances(instances, 173, 665, 1000)
    hold_click_all_instances(instances, 45, 589, 1000)
    _battle_until_enemies_at_most(25, "Left room cleared")

    logout()
    joinback()
    hold_click_all_instances(instances, 48, 639, 1000)
    hold_click_all_instances(instances, 125, 522, 7000)
    hold_click_all_instances(instances, 80, 569, 750)
    _battle_until_return_to_towne()


def respawn():
    tap_all_instances(instances, 506, 488)


def battle(repetitions):
    for _ in range(repetitions):
        stop_flag.check()
        use_buffs()
        use_skills()


# Route walked each mob-clear loop: (x, y, hold ms)
_MOB_ROUTE = [(23, 595, 1000), (152, 553, 3300), (187, 647, 2800), (35, 587, 1800)]


def mob_clear():
    stop_flag.check()
    print("Starting mob clearing...")
    total_fail_count = 0

    # Zori is trusted on one read; Platonius/Auros need two in a row to rule out misreads.
    with Watcher(_read_boss, confirmations={"platonius": 2, "auros": 2}, name="mob clear") as w:
        while True:
            for i, (x, y, ms) in enumerate(_MOB_ROUTE):
                if i:
                    respawn()
                hold_click_all_instances(instances, x, y, ms)
                battle(1)
                respawn()
            print("'Zori Kurn' NOT found. Restarting loop.")

            total_fail_count += 1
            if total_fail_count == 5:
                hold_click_all_instances(instances, 93, 519, 3800)
            if total_fail_count >= 15:
                break

    if w.result == "zori":
        print("Found 'Zori Kurn'. Stopping mob clearing.")
        respawn()


def first_boss_battle():
    stop_flag.check()
    print("Fighting First Boss")
    # Time-based grace so a dead reader character has time to respawn and rejoin;
    # the clock resets every time Zori is seen.
    last_zori = time.monotonic()

    with Watcher(_read_boss, stop_on={"auros", "platonius"}, name="first boss") as w:
        while True:
            stop_flag.check()
            battle(1)
            respawn()
            tap_all_instances(instances, 696, 87)

            if "zori" in w.drain():
                last_zori = time.monotonic()
                continue
            unseen = time.monotonic() - last_zori
            print(f"'Zori Kurn' NOT seen for {unseen:.1f}s.")
            if unseen >= ZORI_GRACE_SECONDS:
                print(f"'Zori Kurn' not seen for {ZORI_GRACE_SECONDS}s. Ending battle.")
                break


def second_boss_battle():
    stop_flag.check()
    print("Fighting Second Boss")
    fail_count = 0
    tapped_once = False

    with Watcher(_read_boss_or_towne, stop_on={"platonius", "towne"}, name="second boss") as w:
        while True:
            stop_flag.check()
            tap_all_instances(instances, 640, 413)
            hold_click_all_instances(instances, 107, 675, 1000)
            battle(1)
            respawn()

            reads = w.drain()
            if "auros" in reads:
                fail_count = 0
                print("'Auros Kurn' found. Continuing the battle.")
            elif reads:
                fail_count += 1
                print(f"'Auros Kurn' NOT found. Failure count: {fail_count}")

            if fail_count >= 3:
                if not tapped_once:
                    print("Performing reset actions...")
                    use_buffs()
                    hold_click_all_instances(instances, 112, 523, 3000)
                    battle(1)
                    hold_click_all_instances(instances, 112, 657, 3000)
                    tapped_once = True
                    fail_count = 0
                    w.drain()
                else:
                    print("Exiting loop after second set of failures.")
                    break


def final_boss_battle():
    stop_flag.check()
    print("Fighting Final Boss")
    with Watcher(_read_towne, name="final boss"):
        for _ in range(20):
            stop_flag.check()
            battle(1)
            respawn()


def log_out():
    tap_all_instances(instances, 37, 36)
    time.sleep(0.4)
    tap_all_instances(instances, 1104, 668)
    time.sleep(0.4)


def loot():
    batch_swipe_all_instances(instances,
        (52, 548, 1000),
        (187, 600, 800),
        (52, 649, 800),
        (187, 600, 800),
    )

def loot2():
    batch_swipe_all_instances(instances,
        (52, 548, 1000),
        (187, 600, 1000),
        (52, 649, 1000),
        (187, 600, 1000),
        (433, 353, 760, 360, 300),
    )


def go_to_inv():
    tap_all_instances(instances, 640, 59)
    time.sleep(0.5)
    tap_all_instances(instances, 368, 44)


def sell_all():
    tap_all_instances(instances, 1037, 671)
    time.sleep(0.1)
    for y in [247, 333, 420, 507, 593]:
        tap_all_instances(instances, 1107, y)
        time.sleep(0.1)
        tap_all_instances(instances, 629, 491)
        time.sleep(0.1)
    tap_all_instances(instances, 1233, 41)


def clean_rare_loot():
    tap_all_instances(instances, 933, 323)
    for _ in range(12):        
        #time.sleep(0.1)
        tap_all_instances(instances, 924, 673)
        #time.sleep(0.1)
        tap_all_instances(instances, 645, 548)


def navigate_to_top():
    for _ in range(2):
        batch_swipe_all_instances(instances, (67, 547, 1800), (160, 547, 1800))


def clear_inv():
    go_to_inv()
    time.sleep(0.3)
    clean_rare_loot()
    time.sleep(0.1)
    for x in [804, 867, 924, 987, 1043]:
        tap_all_instances(instances, x, 135)
        sell_all()
        clean_rare_loot()
        time.sleep(0.1)


def exit_program():
    print("Retry limit reached. Exiting program.")
    log_out()
    exit()
