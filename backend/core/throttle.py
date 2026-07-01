import time

_last_call = {}

def allow_call(key: str, cooldown: float):
    now = time.time()
    last = _last_call.get(key, 0)

    if now - last < cooldown:
        return False

    _last_call[key] = now
    return True