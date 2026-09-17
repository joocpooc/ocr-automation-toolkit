import tkinter as tk
from tkinter import scrolledtext
import threading
import json
import os
import sys
import time
import queue
import subprocess
import shutil

from config import instances, STATE_FILE, RETRY_LIMIT, save_ips
import stop_flag


class _ConsoleRedirect:
    def __init__(self, q):
        self._q = q

    def write(self, text):
        self._q.put(text)

    def flush(self):
        pass


class LairbotApp:
    BG       = "#1a1a1a"
    FRAME_BG = "#252525"
    FG       = "#e0e0e0"
    ACCENT   = "#4fc3f7"
    GOLD_CLR = "#ffd700"
    HDR_FG   = "#888888"
    FONT     = ("Consolas", 9)
    FONT_B   = ("Consolas", 9, "bold")

    def __init__(self, root):
        self.root = root
        self.root.title("Lairbot")
        self.root.geometry("820x640")
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)

        self._bot_running = False
        self._bot_thread  = None
        self._console_q   = queue.Queue()
        self._map_var     = tk.StringVar(value="Map 1 (Lair)")
        self._start_time  = None

        self._build_ui()
        self._redirect_stdout()
        self._poll_console()
        self._refresh_gold()
        self._check_connections()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        self._build_instance_table()
        self._build_console()
        self._build_buttons()

    def _build_instance_table(self):
        outer = tk.Frame(self.root, bg=self.BG)
        outer.pack(fill="x", padx=12, pady=(10, 4))

        tk.Label(outer, text="INSTANCES", bg=self.BG, fg=self.HDR_FG,
                 font=self.FONT_B).pack(anchor="w")

        frame = tk.Frame(outer, bg=self.FRAME_BG, padx=8, pady=6)
        frame.pack(fill="x")

        for c, (text, w) in enumerate([("", 2), ("Instance", 32), ("Character", 14), ("IP", 20), ("Gold", 14)]):
            tk.Label(frame, text=text, bg=self.FRAME_BG, fg=self.HDR_FG,
                     font=self.FONT_B, width=w, anchor="w").grid(row=0, column=c, padx=4)

        self._gold_labels   = []
        self._status_labels = []
        self._ip_vars       = []
        for r, inst in enumerate(instances, start=1):
            status_lbl = tk.Label(frame, text="●", bg=self.FRAME_BG, fg="#888888",
                                  font=self.FONT_B, width=2, anchor="w")
            status_lbl.grid(row=r, column=0, padx=4)
            self._status_labels.append(status_lbl)

            tk.Label(frame, text=inst["window_title"], bg=self.FRAME_BG, fg=self.FG,
                     font=self.FONT, width=32, anchor="w").grid(row=r, column=1, padx=4)
            tk.Label(frame, text=inst["name"], bg=self.FRAME_BG, fg="#c792ea",
                     font=self.FONT, width=14, anchor="w").grid(row=r, column=2, padx=4)

            ip_var = tk.StringVar(value=inst["ip"])
            self._ip_vars.append(ip_var)
            ip_entry = tk.Entry(frame, textvariable=ip_var, bg="#1e1e1e", fg=self.ACCENT,
                                insertbackground=self.ACCENT, font=self.FONT, width=20,
                                relief="flat", bd=2)
            ip_entry.grid(row=r, column=3, padx=4, pady=1)

            lbl = tk.Label(frame, text="—", bg=self.FRAME_BG, fg=self.GOLD_CLR,
                           font=self.FONT, width=14, anchor="w")
            lbl.grid(row=r, column=4, padx=4)
            self._gold_labels.append(lbl)

    def _build_console(self):
        outer = tk.Frame(self.root, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=12, pady=4)

        tk.Label(outer, text="CONSOLE", bg=self.BG, fg=self.HDR_FG,
                 font=self.FONT_B).pack(anchor="w")

        self._console = scrolledtext.ScrolledText(
            outer, bg="#0d0d0d", fg="#cccccc",
            font=self.FONT, state="disabled", wrap="word",
        )
        self._console.pack(fill="both", expand=True)

    def _build_buttons(self):
        frame = tk.Frame(self.root, bg=self.BG)
        frame.pack(fill="x", padx=12, pady=8)

        self._start_btn = tk.Button(
            frame, text="▶  Start Bot",
            bg="#2e6b2e", fg="white", activebackground="#3d8c3d",
            font=("Consolas", 10, "bold"), width=14, relief="flat",
            command=self._toggle_bot,
        )
        self._start_btn.pack(side="left", padx=(0, 6))

        self._inv_btn = tk.Button(
            frame, text="Clear Inventory",
            bg="#3a3a3a", fg="white", activebackground="#4a4a4a",
            font=("Consolas", 10), width=16, relief="flat",
            command=self._run_clear_inv,
        )
        self._inv_btn.pack(side="left", padx=(0, 6))

        self._connect_btn = tk.Button(
            frame, text="Connect BlueStacks",
            bg="#3a3a3a", fg="white", activebackground="#4a4a4a",
            font=("Consolas", 10), width=20, relief="flat",
            command=self._run_connect,
        )
        self._connect_btn.pack(side="left", padx=(0, 6))

        self._detect_btn = tk.Button(
            frame, text="Auto-detect IPs",
            bg="#3a3a3a", fg="white", activebackground="#4a4a4a",
            font=("Consolas", 10), width=16, relief="flat",
            command=self._run_autodetect,
        )
        self._detect_btn.pack(side="left", padx=(0, 6))

        map_menu = tk.OptionMenu(frame, self._map_var, "Map 1 (Lair)", "Lair NF", "Map 2", "Map 3")
        map_menu.configure(bg="#3a3a3a", fg="white", activebackground="#4a4a4a",
                           font=("Consolas", 10), relief="flat", highlightthickness=0)
        map_menu["menu"].configure(bg="#3a3a3a", fg="white", font=("Consolas", 10))
        map_menu.pack(side="left")

        self._timer_label = tk.Label(
            frame, text="00:00:00", bg=self.BG, fg=self.HDR_FG,
            font=("Consolas", 10),
        )
        self._timer_label.pack(side="right")

    # ----------------------------------------------------------- Console I/O --

    def _redirect_stdout(self):
        redir = _ConsoleRedirect(self._console_q)
        sys.stdout = redir
        sys.stderr = redir

    def _poll_console(self):
        try:
            while True:
                text = self._console_q.get_nowait()
                self._console.configure(state="normal")
                self._console.insert("end", text)
                self._console.see("end")
                self._console.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(80, self._poll_console)

    # --------------------------------------------------------- Connection check --

    def _check_connections(self):
        def check():
            try:
                result = subprocess.run(
                    "adb devices", shell=True, capture_output=True, text=True
                )
                connected = set()
                for line in result.stdout.strip().splitlines()[1:]:
                    if "\tdevice" in line:
                        connected.add(line.split("\t")[0].strip())
            except Exception:
                connected = set()

            def update():
                all_ok = True
                for lbl, inst in zip(self._status_labels, instances):
                    if inst["ip"] in connected:
                        lbl.configure(fg="#4caf50")  # green
                    else:
                        lbl.configure(fg="#f44336")  # red
                        all_ok = False
                self._start_btn.configure(
                    state="normal" if all_ok else "disabled"
                )

            self.root.after(0, update)

        threading.Thread(target=check, daemon=True).start()
        self.root.after(10000, self._check_connections)

    # -------------------------------------------------------------- Gold --

    def _refresh_gold(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                values = state.get("previous", [])
                for i, lbl in enumerate(self._gold_labels):
                    lbl.configure(text=str(values[i]) if i < len(values) else "—")
            except Exception:
                pass
        self.root.after(5000, self._refresh_gold)

    # ------------------------------------------------------------ Bot control --

    def _toggle_bot(self):
        if not self._bot_running:
            stop_flag.clear()
            self._bot_running = True
            self._start_time = time.time()
            self._start_btn.configure(text="■  Stop Bot",
                                      bg="#6b2e2e", activebackground="#8c3d3d")
            self._bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
            self._bot_thread.start()
            self._update_timer()
        else:
            stop_flag.stop()
            self._bot_running = False
            self._start_btn.configure(text="Stopping...",
                                      bg="#7a5c00", activebackground="#7a5c00",
                                      state="disabled")

    def _update_timer(self):
        if not self._bot_running:
            return
        elapsed = int(time.time() - self._start_time)
        h, remainder = divmod(elapsed, 3600)
        m, s = divmod(remainder, 60)
        self._timer_label.configure(
            text=f"{h:02d}:{m:02d}:{s:02d}",
            fg=self.ACCENT,
        )
        self.root.after(1000, self._update_timer)

    def _bot_loop(self):
        from bot_setup import print_monitor_info, connect_bluestacks_devices, check_adb_devices
        from adb_utils import tap_all_instances, hold_click_all_instances
        from ocr_utils import get_enemies_remaining, search_words, search_words_stacked
        from game_actions import (
            host_game, host_game_map2, host_game_map3, join_game, invite, battle, mob_clear, navigate_to_top,
            first_boss_battle, second_boss_battle, final_boss_battle,
            loot, potspam, use_buffs, use_skills, log_out, clear_inv, run_map2_dungeon, run_map3_dungeon,
        )

        try:
            log_dir = r"C:\ProgramData\BlueStacks_nxt\Logs"
            try:
                for entry in os.scandir(log_dir):
                    try:
                        if entry.is_file():
                            os.remove(entry.path)
                        elif entry.is_dir():
                            shutil.rmtree(entry.path)
                    except Exception:
                        pass
                print("BlueStacks logs cleared.")
            except Exception as e:
                print(f"Could not clear BlueStacks logs: {e}")

            print_monitor_info()
            connect_bluestacks_devices()
            check_adb_devices()

            inv_counter = 0
            selected_map = self._map_var.get()

            while self._bot_running:
                search_retry  = 0
                enemy_retry   = 0
                stacked_retry = 0

                while search_retry < RETRY_LIMIT and self._bot_running:
                    if search_words(["World", "Map"], 1588, 415, 1650, 434, 60):
                        print("World Map found.")
                        break
                    search_retry += 1
                    time.sleep(3)

                if not self._bot_running:
                    break
                if search_retry >= RETRY_LIMIT:
                    print("World Map not found. Stopping.")
                    log_out()
                    break

                if selected_map == "Map 2":
                    host_game_map2()
                elif selected_map == "Map 3":
                    host_game_map3()
                else:
                    host_game()

                while enemy_retry < RETRY_LIMIT and self._bot_running:
                    if selected_map == "Map 2":
                        if search_words(["FORCE", "START"], 1457, 696, 1600, 734, 60):
                            print("Map 2 lobby ready.")
                            break
                    elif get_enemies_remaining():
                        print("Enemies found.")
                        break
                    enemy_retry += 1
                    time.sleep(0.5)

                if not self._bot_running:
                    break

                invite()
                time.sleep(0.3)
                join_game()
                time.sleep(3)

                if enemy_retry >= RETRY_LIMIT:
                    print("Enemies not found. Stopping.")
                    log_out()
                    break

                while stacked_retry < RETRY_LIMIT and self._bot_running:
                    if search_words_stacked(["Minaamage", "Religeous", "Rafakillo", "fierybride"], 0, 449, 144, 611):
                        print("Everyone connected, starting run...")
                        break
                    stacked_retry += 1
                    time.sleep(0.5)

                if not self._bot_running:
                    break
                if stacked_retry >= RETRY_LIMIT:
                    print("Not all players connected. Stopping.")
                    log_out()
                    break

                if selected_map == "Map 2":
                    run_map2_dungeon()
                    log_out()
                    time.sleep(4)
                elif selected_map == "Map 3":
                    run_map3_dungeon()
                    log_out()
                    time.sleep(4)
                else:
                    hold_click_all_instances(instances, 113, 653, 4000)
                    use_buffs()
                    hold_click_all_instances(instances, 81, 527, 4600)
                    use_skills()
                    battle(1)
                    mob_clear()
                    navigate_to_top()
                    first_boss_battle()
                    loot()
                    hold_click_all_instances(instances, 108, 657, 10000)

                    #time.sleep(4)
                    second_boss_battle()
                    hold_click_all_instances(instances, 108, 657, 3000)
                    tap_all_instances(instances, 640, 400)
                    final_boss_battle()
                    loot()
                    hold_click_all_instances(instances, 108, 657, 7000)
                    loot()
                    if selected_map != "Lair NF":
                        tap_all_instances(instances, 640, 400)
                        tap_all_instances(instances, 640, 400)
                        hold_click_all_instances(instances, 80, 531, 4500)
                        #potspam(3)
                        hold_click_all_instances(instances, 80, 531, 4500)
                        use_skills()
                        hold_click_all_instances(instances, 80, 531, 1000)
                        tap_all_instances(instances, 1023, 467)
                        time.sleep(0.5)
                        loot()
                        hold_click_all_instances(instances, 177, 595, 2000)
                        tap_all_instances(instances, 1233, 187)
                        tap_all_instances(instances, 1169, 643)
                        time.sleep(0.5)
                        tap_all_instances(instances, 213, 500)
                        time.sleep(0.5)
                        loot()
                        hold_click_all_instances(instances, 187, 600, 800)
                        loot()
                    log_out()
                    time.sleep(4)

                inv_counter += 1
                if inv_counter >= 40:
                    clear_inv()
                    tap_all_instances(instances, 287, 133)
                    time.sleep(0.1)
                    tap_all_instances(instances, 956, 281)
                    time.sleep(0.1)
                    tap_all_instances(instances, 1240, 104)
                    time.sleep(0.1)
                    tap_all_instances(instances, 287, 133)
                    time.sleep(0.1)
                    tap_all_instances(instances, 967, 157)
                    time.sleep(0.1)
                    tap_all_instances(instances, 1240, 104)
                    time.sleep(0.1)
                    tap_all_instances(instances, 41, 45)
                    inv_counter = 0

        except StopIteration:
            print("Bot stopped by user.")
        except Exception as e:
            print(f"Bot error: {e}")
            try:
                log_out()
            except Exception as log_out_error:
                print(f"logout() also failed: {log_out_error}")
        finally:
            self._bot_running = False
            self.root.after(0, lambda: self._start_btn.configure(
                text="▶  Start Bot", bg="#2e6b2e", activebackground="#3d8c3d",
                state="normal"
            ))
            self.root.after(0, lambda: self._timer_label.configure(fg=self.HDR_FG))
            print("Bot stopped.")

    # --------------------------------------------------------- Connect devices --

    def _run_connect(self):
        ips = [var.get().strip() for var in self._ip_vars]
        save_ips(ips)  # update instances in memory + write settings.json
        self._connect_btn.configure(state="disabled", text="Connecting...")

        def do():
            from bot_setup import disconnect_all_devices, connect_bluestacks_devices
            disconnect_all_devices()
            connect_bluestacks_devices()
            self.root.after(0, lambda: self._connect_btn.configure(
                state="normal", text="Connect BlueStacks"
            ))
            self._check_connections()

        threading.Thread(target=do, daemon=True).start()

    # ------------------------------------------------------------ Auto-detect --

    def _run_autodetect(self):
        self._detect_btn.configure(state="disabled", text="Scanning...")

        def do():
            from bot_setup import auto_detect_devices
            new_ips, matched = auto_detect_devices()
            if new_ips:
                def update_fields():
                    for var, ip in zip(self._ip_vars, new_ips):
                        var.set(ip)
                self.root.after(0, update_fields)
            self.root.after(0, lambda: self._detect_btn.configure(
                state="normal", text="Auto-detect IPs"
            ))
            self._check_connections()

        threading.Thread(target=do, daemon=True).start()

    # --------------------------------------------------------- Clear inventory --

    def _run_clear_inv(self):
        self._inv_btn.configure(state="disabled", text="Running...")

        def do():
            from game_actions import clear_inv
            from adb_utils import tap_all_instances
            clear_inv()
            tap_all_instances(instances, 287, 133)
            time.sleep(0.1)
            tap_all_instances(instances, 956, 281)
            time.sleep(0.1)
            tap_all_instances(instances, 1240, 104)
            time.sleep(0.1)
            tap_all_instances(instances, 287, 133)
            time.sleep(0.1)
            tap_all_instances(instances, 967, 157)
            time.sleep(0.1)
            tap_all_instances(instances, 1240, 104)
            time.sleep(0.1)
            tap_all_instances(instances, 41, 45)
            self.root.after(0, lambda: self._inv_btn.configure(
                state="normal", text="Clear Inventory"
            ))

        threading.Thread(target=do, daemon=True).start()


def launch():
    root = tk.Tk()
    LairbotApp(root)
    root.mainloop()
