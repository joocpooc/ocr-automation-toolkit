import threading

import watcher

_event = threading.Event()

def stop():
    _event.set()

def clear():
    _event.clear()

def is_stopped():
    return _event.is_set()

def check():
    """Raise StopIteration if stop has been requested, or abort the current
    with-Watcher block if its watcher has fired."""
    if _event.is_set():
        raise StopIteration("Bot stopped by user.")
    watcher.checkpoint()
