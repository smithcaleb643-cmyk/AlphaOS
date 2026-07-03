from datetime import datetime
import time

from core.alpha_brain import evaluate_exit_decision
from core.live_portfolio import get_live_portfolio
from core.live_sell_executor import execute_live_sell
from core.live_exit_state import is_position_exiting, mark_position_exiting, clear_position_exiting
from core.live_trade_journal import load_live_trade_journal, save_live_trade_journal


SELL_RETRY_ATTEMPTS = 3
SELL_RETRY_DELAY_SECONDS = 4


def safe_int(value, default=0):
    try:
        return int(float(value or default))
    except Exception:
        return default


def minutes_held(entry_time):
    try:
        started = datetime.fromisoformat(entry_time)
        return (datetime.utcnow() - started).total_seconds() / 60
    except Exception:
        return 0


def raw_fraction(amount_raw, fraction):
    return str(max(1, int(safe_int(amount_raw) * float(fraction or 1))))


def update_buy_trade_state(position, updates):
    journal = load_live_trade_journal()
    trades = journal.get("trades", [])

    for trade in trades:
        if trade.get("id") == position.get("trade_id"):
            trade.update(updates)
            save_live_trade_journal(trades)
            return trade

    return None


def add_partial_exit_note(position, label, fraction, result):
    journal = load_live_trade_journal()
    trades = journal.get("trades", [])

    for trade in trades:
        if trade.get("id") == position.get("trade_id"):
            trade.setdefault("partial_exits", [])
            trade["partial_exits"].append({
                "label": label,
                "percent_sold": fraction,
                "signature": result.get("signature"),
                "created_at": datetime.utcnow().isoformat(),
                "pnl_percent": position.get("pnl_percent"),
                "price": position.get("current_price"),
            })
            save_live_trade_journal(trades)
            return trade

    return None


def sell_with_retry(position, amount_raw, label, slippage_bps=150):
    token_address = position.get("mint")
    last_result = None

    for attempt in range(1, SELL_RETRY_ATTEMPTS + 1):
        result = execute_live_sell({
            "token_address": token_address,
            "amount_raw": str(amount_raw),
            "slippage_bps": slippage_bps,
            "exit_reason": label,
            "entry_signature": position.get("signature"),
            "entry_price": position.get("entry_price"),
            "exit_price": position.get("current_price"),
            "pnl_percent": position.get("pnl_percent"),
            "pnl_usd": position.get("pnl_usd"),
            "held_minutes": minutes_held(position.get("entry_time")),
            "sell_attempt": attempt,
        })

        last_result = result

        if result.get("ok"):
            result["sell_attempts"] = attempt
            return result

        time.sleep(SELL_RETRY_DELAY_SECONDS)

    return last_result or {
        "ok": False,
        "error": "Sell failed before any result.",
    }


def manage_open_positions():
    portfolio = get_live_portfolio()
    positions = portfolio.get("positions", [])
    actions = []

    print(f"EXIT CHECK: {len(positions)} positions")

    for p in positions:
        print(
            "EXIT POSITION:",
            p.get("symbol"),
            "mint=", p.get("mint"),
            "entry=", p.get("entry_price"),
            "current=", p.get("current_price"),
            "pnl=", p.get("pnl_percent"),
            "amount_raw=", p.get("amount_raw"),
        )

    for position in positions:
        token_address = position.get("mint")
        decision = evaluate_exit_decision(position)

        if not decision.get("should_sell"):
            update_buy_trade_state(position, decision.get("updates", {}))
            actions.append({
                "symbol": position.get("symbol"),
                "action": "HOLD",
                "reason": decision.get("message"),
            })
            continue

        if is_position_exiting(token_address):
            actions.append({
                "symbol": position.get("symbol"),
                "action": "EXIT_BLOCKED",
                "reason": "Sell already pending or previously failed. Manual review required.",
                "result": {
                    "ok": False,
                    "error": "Exit state already active.",
                },
            })
            continue

        mark_position_exiting(token_address)

        amount_raw = position.get("amount_raw")

        if not amount_raw or int(float(amount_raw)) <= 0:
            actions.append({
                "symbol": position.get("symbol"),
                "action": "SELL_BLOCKED",
                "reason": "No valid wallet-backed amount_raw found. Manual review required.",
                "result": {
                    "ok": False,
                    "error": "Missing amount_raw",
                },
            })
            clear_position_exiting(token_address)
            continue

        sell_amount_raw = raw_fraction(
            amount_raw,
            decision.get("fraction", 1.0),
        )

        result = sell_with_retry(
            position=position,
            amount_raw=sell_amount_raw,
            label=decision.get("label"),
            slippage_bps=300 if decision.get("urgent") else 150,
        )

        if result.get("ok"):
            update_buy_trade_state(position, decision.get("updates", {}))

            if float(decision.get("fraction") or 1.0) < 1.0:
                add_partial_exit_note(
                    position,
                    decision.get("label"),
                    decision.get("fraction"),
                    result,
                )

            clear_position_exiting(token_address)
        else:
            actions.append({
                "symbol": position.get("symbol"),
                "action": "SELL_FAILED",
                "reason": decision.get("message"),
                "result": result,
            })
            continue

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