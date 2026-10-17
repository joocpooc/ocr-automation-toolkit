import threading

_local = threading.local()


class Triggered(Exception):
    """Raised in the owning thread at the next checkpoint once a watcher fires."""

    def __init__(self, watcher):
        super().__init__(f"{watcher.name} triggered: {watcher.result}")
        self.watcher = watcher


class Watcher:
    """Run check() continuously on a background thread while a with-block runs.

    check() returns a truthy value (e.g. "zori", "towne") or None. Once it returns
    a value in `stop_on` (None = any truthy value) `confirmations` times in a row,
    the with-block is aborted at the next checkpoint - every ADB call and every
    stop_flag.check() is one - and execution resumes right after the with-statement.
    The triggering value is left in .result (None if the block ended on its own).

    `confirmations` is an int, or a dict of {value: count} (missing values = 1).
    Every read (including None) is also buffered; drain() returns and clears them,
    so a loop can see what was on screen during its last iteration.
    """

    def __init__(self, check, stop_on=None, confirmations=1, interval=0.1, name="watcher"):
        self.check = check
        self.stop_on = stop_on
        self.confirmations = confirmations
        self.interval = interval
        self.name = name
        self.result = None
        self._fired = threading.Event()
        self._done = threading.Event()
        self._reads = []
        self._lock = threading.Lock()

    def _needed(self, value):
        if isinstance(self.confirmations, dict):
            return self.confirmations.get(value, 1)
        return self.confirmations

    def _run(self):
        streak_value, streak = None, 0
        while not self._done.is_set():
            try:
                value = self.check()
            except Exception as e:
                print(f"[{self.name}] check failed: {e}")
                value = None
            with self._lock:
                self._reads.append(value)

            if value and (self.stop_on is None or value in self.stop_on):
                streak = streak + 1 if value == streak_value else 1
                streak_value = value
                if streak >= self._needed(value):
                    self.result = value
                    print(f"[{self.name}] '{value}' detected, moving on immediately.")
                    self._fired.set()
                    return
            else:
                streak_value, streak = None, 0
            self._done.wait(self.interval)

    def drain(self):
        """Return every read since the last drain() and clear the buffer."""
        with self._lock:
            reads, self._reads = self._reads, []
        return reads

    def __enter__(self):
        if not hasattr(_local, "stack"):
            _local.stack = []
        _local.stack.append(self)
        threading.Thread(target=self._run, daemon=True, name=self.name).start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._done.set()
        _local.stack.remove(self)
        return isinstance(exc, Triggered) and exc.watcher is self


def checkpoint():
    """Abort the current with-Watcher block if its watcher has fired.
    Only affects the thread that opened the block (worker threads are untouched)."""
    for w in getattr(_local, "stack", ()):
        if w._fired.is_set():
            raise Triggered(w)
