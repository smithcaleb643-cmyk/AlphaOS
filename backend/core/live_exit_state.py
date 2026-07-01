import time

EXITING_POSITIONS = {}
SELL_COOLDOWN_SECONDS = 45


def is_position_exiting(token_address):
    if not token_address:
        return False

    last_exit = EXITING_POSITIONS.get(token_address)

    if not last_exit:
        return False

    return (time.time() - last_exit) < SELL_COOLDOWN_SECONDS


def mark_position_exiting(token_address):
    if token_address:
        EXITING_POSITIONS[token_address] = time.time()


def clear_position_exiting(token_address):
    if token_address in EXITING_POSITIONS:
        del EXITING_POSITIONS[token_address]