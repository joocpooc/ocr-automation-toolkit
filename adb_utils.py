import subprocess
import threading

from config import HOLD_MULTIPLIER


def tap_on_instance(instance, x, y):
    subprocess.run(f"adb -s {instance} shell input tap {x} {y}", shell=True)


def send_text(instance, text):
    subprocess.run(f"adb -s {instance} shell input text {text}", shell=True)


def send_keystroke(instance, key_code):
    subprocess.run(f"adb -s {instance} shell input keyevent {key_code}", shell=True)


def hold_left_click(instance, x, y, duration=3000):
    scaled = int(duration * HOLD_MULTIPLIER)
    subprocess.run(f"adb -s {instance} shell input swipe {x} {y} {x} {y} {scaled}", shell=True)


def tap_all_instances(instances, x, y):
    def tap(ip, x, y):
        try:
            subprocess.run(f"adb -s {ip} shell input tap {x} {y}", shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error tapping on instance {ip}: {e}")

    threads = [threading.Thread(target=tap, args=(inst["ip"], x, y)) for inst in instances]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def hold_click_all_instances(instances, x, y, duration=3000):
    threads = [
        threading.Thread(target=hold_left_click, args=(inst["ip"], x, y, duration))
        for inst in instances
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def batch_tap_instance(ip, *coords_list):
    cmd = "; ".join(f"input swipe {x} {y} {x} {y} 0" for x, y in coords_list)
    subprocess.run(f'adb -s {ip} shell "{cmd}"', shell=True)


def batch_tap_all_instances(instances, *coords_list):
    """Fire multiple taps in a single ADB shell call per instance (no round-trip overhead between taps)."""
    cmd = "; ".join(f"input swipe {x} {y} {x} {y} 0" for x, y in coords_list)
    def run(ip):
        subprocess.run(f'adb -s {ip} shell "{cmd}"', shell=True)
    threads = [threading.Thread(target=run, args=(inst["ip"],)) for inst in instances]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def batch_swipe_all_instances(instances, *swipe_list):
    """Fire multiple swipes in a single ADB shell call per instance.
    Each entry is either (x, y, duration) for an in-place hold, or
    (x1, y1, x2, y2, duration) for a directional swipe."""
    parts = []
    for swipe in swipe_list:
        if len(swipe) == 3:
            x, y, d = swipe
            parts.append(f"input swipe {x} {y} {x} {y} {int(d * HOLD_MULTIPLIER)}")
        else:
            x1, y1, x2, y2, d = swipe
            parts.append(f"input swipe {x1} {y1} {x2} {y2} {int(d * HOLD_MULTIPLIER)}")
    cmd = "; ".join(parts)
    def run(ip):
        subprocess.run(f'adb -s {ip} shell "{cmd}"', shell=True)
    threads = [threading.Thread(target=run, args=(inst["ip"],)) for inst in instances]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
