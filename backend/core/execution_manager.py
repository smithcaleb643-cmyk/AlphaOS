from core.paper_broker import paper_broker
from core.live_broker import live_broker


PAPER = "PAPER"
MANUAL_LIVE = "MANUAL_LIVE"
LIVE = "LIVE"


def get_execution_mode(profile_state=None):
    if not profile_state:
        return PAPER

    settings = profile_state.get("settings", {})
    return settings.get("execution_mode", PAPER)


def get_broker(profile_state=None):
    mode = get_execution_mode(profile_state)

    if mode == PAPER:
        return paper_broker

    if mode in [MANUAL_LIVE, LIVE]:
        return live_broker

    return paper_broker


def execute_buy(signal, profile_state=None):
    broker = get_broker(profile_state)
    mode = get_execution_mode(profile_state)

    if mode == MANUAL_LIVE:
        return {
            "ok": False,
            "message": "Manual live approval required. Order was not executed.",
            "data": {
                "execution_mode": MANUAL_LIVE,
                "signal": signal,
                "requires_approval": True,
            },
        }

    return broker.buy(signal)


def execute_sell(trade_id, profile_state=None, reason="MANUAL_SELL"):
    broker = get_broker(profile_state)
    mode = get_execution_mode(profile_state)

    if mode == MANUAL_LIVE:
        return {
            "ok": False,
            "message": "Manual live approval required. Sell order was not executed.",
            "data": {
                "execution_mode": MANUAL_LIVE,
                "trade_id": trade_id,
                "reason": reason,
                "requires_approval": True,
            },
        }

    return broker.sell(trade_id, reason=reason)


def execution_status(profile_state=None):
    mode = get_execution_mode(profile_state)
    broker = get_broker(profile_state)

    balance = broker.get_balance()
    positions = broker.get_positions()

    return {
        "ok": True,
        "execution_mode": mode,
        "balance": balance,
        "positions": positions,
    }