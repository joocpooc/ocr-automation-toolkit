import subprocess
import socket
import json
import os
import threading

from screeninfo import get_monitors

from config import instances, SETTINGS_FILE, save_ips


def print_monitor_info():
    for m in get_monitors():
        print(f"Monitor: {m.name}, Width: {m.width}, Height: {m.height}, Left: {m.x}, Top: {m.y}")


def disconnect_all_devices():
    print("Disconnecting all ADB devices...")
    subprocess.run("adb disconnect", shell=True, capture_output=True)
    print("All devices disconnected.\n")


def connect_bluestacks_devices():
    print("Connecting BlueStacks devices...")
    for instance in instances:
        ip = instance["ip"]
        try:
            subprocess.run(f"adb connect {ip}", shell=True, check=True)
            print(f"Connected to {ip}")
        except subprocess.CalledProcessError:
            print(f"Failed to connect to {ip}")
    print("Finished connecting devices.\n")


def check_adb_devices():
    print("Checking connected ADB devices...\n")
    subprocess.run("adb devices", shell=True)


def wait_for_user_confirmation():
    input("Press Enter to start the script after verifying connections...")


def _scan_open_ports(start=5550, end=5616, timeout=0.05):
    """Return list of open TCP ports in range using parallel socket checks."""
    open_ports = []
    lock = threading.Lock()

    def check(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                with lock:
                    open_ports.append(port)
            s.close()
        except Exception:
            pass

    threads = [threading.Thread(target=check, args=(p,)) for p in range(start, end)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return sorted(open_ports)


def _get_serial(ip, timeout=3):
    """Return the serial number of an ADB device, or None."""
    try:
        r = subprocess.run(
            f"adb -s {ip} shell getprop ro.serialno",
            shell=True, capture_output=True, text=True, timeout=timeout,
        )
        serial = r.stdout.strip()
        return serial if serial else None
    except Exception:
        return None


def auto_detect_devices():
    """
    Scan BlueStacks ADB ports, identify instances by serial number,
    update IPs in memory and settings.json.
    Returns (new_ips, matched_count).
    """
    print("Scanning for BlueStacks ADB ports...")
    open_ports = _scan_open_ports()
    print(f"Open ports found: {[f'127.0.0.1:{p}' for p in open_ports]}")

    if not open_ports:
        print("No open ports found. Is BlueStacks running?")
        return None, 0

    # Connect to each open port and collect serial → ip
    found = {}  # serial -> ip
    for port in open_ports:
        ip = f"127.0.0.1:{port}"
        try:
            r = subprocess.run(
                f"adb connect {ip}", shell=True, capture_output=True, text=True, timeout=5
            )
            if "connected" in r.stdout or "already connected" in r.stdout:
                serial = _get_serial(ip)
                if serial and serial not in found:
                    found[serial] = ip
                    print(f"  {ip}  →  serial: {serial}")
        except Exception:
            pass

    print(f"Detected {len(found)} device(s).")

    # Load stored serial → instance-index mapping
    serial_to_idx = {}
    try:
        with open(SETTINGS_FILE) as f:
            serial_to_idx = json.load(f).get("serials", {})
    except Exception:
        pass

    new_ips = [inst["ip"] for inst in instances]
    matched = 0

    if serial_to_idx:
        # Match discovered devices to known instances by stored serial
        for serial, ip in found.items():
            if serial in serial_to_idx:
                idx = serial_to_idx[serial]
                new_ips[idx] = ip
                matched += 1
                print(f"  Matched {ip} → {instances[idx]['name']}")
        if matched == 0:
            print("No serial matches found — clearing stored serials and re-learning.")
            serial_to_idx = {}

    if not serial_to_idx:
        print("Learning serial → instance mapping from current session...")
        current_ip_to_idx = {inst["ip"]: i for i, inst in enumerate(instances)}
        unmatched_found = {}

        for serial, ip in found.items():
            if ip in current_ip_to_idx:
                idx = current_ip_to_idx[ip]
                serial_to_idx[serial] = idx
                matched += 1
                print(f"  Learned: {ip} → {instances[idx]['name']} (serial {serial})")
            else:
                unmatched_found[serial] = ip

        # Pair any leftover devices with leftover instances (handles changed ports on first learn)
        matched_indices = set(serial_to_idx.values())
        unmatched_instances = [i for i in range(len(instances)) if i not in matched_indices]

        for (serial, ip), idx in zip(unmatched_found.items(), unmatched_instances):
            serial_to_idx[serial] = idx
            new_ips[idx] = ip
            matched += 1
            print(f"  Learned (port changed): {ip} → {instances[idx]['name']} (serial {serial})")

    # Persist
    existing = {}
    try:
        with open(SETTINGS_FILE) as f:
            existing = json.load(f)
    except Exception:
        pass

    existing["ips"] = new_ips
    existing["serials"] = serial_to_idx
    with open(SETTINGS_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    save_ips(new_ips)
    return new_ips, matched
