import threading

_event = threading.Event()

def stop():
    _event.set()

def clear():
    _event.clear()

def is_stopped():
    return _event.is_set()

def check():
    """Raise StopIteration if stop has been requested."""
    if _event.is_set():
        raise StopIteration("Bot stopped by user.")
