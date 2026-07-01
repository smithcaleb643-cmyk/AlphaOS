from datetime import datetime

from core.live_portfolio import get_live_portfolio
from core.live_sell_executor import execute_live_sell
from core.live_exit_state import is_position_exiting, mark_position_exiting, clear_position_exiting


TAKE_PROFIT_PERCENT = 20
STOP_LOSS_PERCENT = -10
MAX_HOLD_MINUTES = 45


def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


def minutes_held(entry_time):
    try:
        started = datetime.fromisoformat(entry_time)
        return (datetime.utcnow() - started).total_seconds() / 60
    except Exception:
        return 0


def raw_amount_from_quantity(quantity, decimals=6):
    return str(int(safe_float(quantity) * (10 ** decimals)))


def evaluate_position_exit(position):
    pnl_percent = safe_float(position.get("pnl_percent"))
    held_minutes = minutes_held(position.get("entry_time"))

    if pnl_percent >= TAKE_PROFIT_PERCENT:
        return {"should_sell": True, "reason": "TAKE_PROFIT", "message": f"Take profit hit: {round(pnl_percent, 2)}%"}

    if pnl_percent <= STOP_LOSS_PERCENT:
        return {"should_sell": True, "reason": "STOP_LOSS", "message": f"Stop loss hit: {round(pnl_percent, 2)}%"}

    if held_minutes >= MAX_HOLD_MINUTES:
        return {"should_sell": True, "reason": "MAX_HOLD_TIME", "message": f"Max hold reached: {round(held_minutes, 1)} min"}

    return {"should_sell": False, "reason": "HOLD", "message": f"Holding. P&L {round(pnl_percent, 2)}%, held {round(held_minutes, 1)} min"}


def manage_open_positions():
    portfolio = get_live_portfolio()
    positions = portfolio.get("positions", [])
    actions = []

    for position in positions:
        token_address = position.get("mint")
        decision = evaluate_position_exit(position)

        if not decision.get("should_sell"):
            actions.append({
                "symbol": position.get("symbol"),
                "action": "HOLD",
                "reason": decision.get("message"),
            })
            continue

        if is_position_exiting(token_address):
            actions.append({
                "symbol": position.get("symbol"),
                "action": "WAITING",
                "reason": "Sell already pending",
            })
            continue

        mark_position_exiting(token_address)

        result = execute_live_sell({
            "token_address": token_address,
            "amount_raw": raw_amount_from_quantity(position.get("quantity")),
            "slippage_bps": 150,
            "exit_reason": decision.get("reason"),
            "entry_signature": position.get("signature"),
            "entry_price": position.get("entry_price"),
            "exit_price": position.get("current_price"),
            "pnl_percent": position.get("pnl_percent"),
            "pnl_usd": position.get("pnl_usd"),
            "held_minutes": minutes_held(position.get("entry_time")),
        })

        if not result.get("ok"):
            clear_position_exiting(token_address)

        actions.append({
            "symbol": position.get("symbol"),
            "action": "SELL",
            "reason": decision.get("message"),
            "result": result,
        })

    return {
        "ok": True,
        "checked": len(positions),
        "actions": actions,
    }