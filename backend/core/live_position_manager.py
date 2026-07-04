from datetime import datetime
import time

from core.alpha_brain import evaluate_exit_decision
from core.live_portfolio import get_live_portfolio
from core.live_sell_executor import execute_live_sell
from core.live_exit_state import is_position_exiting, mark_position_exiting, clear_position_exiting
from core.live_trade_journal import load_live_trade_journal, save_live_trade_journal


SELL_RETRY_ATTEMPTS = 2
SELL_RETRY_DELAY_SECONDS = 1


def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


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
                "pnl_percent": result.get("audit_pnl_percent", position.get("pnl_percent")),
                "portfolio_pnl_percent": position.get("pnl_percent"),
                "price": position.get("current_price"),
                "entry_price": position.get("entry_price"),
                "exit_price": position.get("current_price"),
                "audit": result.get("audit"),
            })
            save_live_trade_journal(trades)
            return trade

    return None


def calculate_exit_audit(position, sell_amount_raw, label):
    """
    This is a debugging/audit calculation.

    It does NOT depend on the journal's existing pnl_percent.
    It recalculates sanity P&L from entry/current price and also records the
    portfolio value-based P&L already supplied by get_live_portfolio().

    If these disagree wildly, the bug is upstream in pricing/accounting.
    """
    entry_price = safe_float(position.get("entry_price"))
    exit_price = safe_float(position.get("current_price"), entry_price)

    amount_raw = safe_int(position.get("amount_raw"))
    sell_raw = safe_int(sell_amount_raw)
    fraction = sell_raw / amount_raw if amount_raw > 0 else 0

    quantity = safe_float(position.get("quantity"))
    sell_quantity = quantity * fraction if quantity > 0 else 0

    entry_value_full = safe_float(position.get("entry_value_usd"))
    current_value_full = safe_float(position.get("current_value_usd"))

    entry_value_for_sell = entry_value_full * fraction
    exit_value_for_sell = current_value_full * fraction

    value_pnl_usd = exit_value_for_sell - entry_value_for_sell
    value_pnl_percent = (
        (value_pnl_usd / entry_value_for_sell) * 100
        if entry_value_for_sell > 0
        else 0
    )

    price_pnl_percent = (
        ((exit_price - entry_price) / entry_price) * 100
        if entry_price > 0 and exit_price > 0
        else 0
    )

    portfolio_pnl_percent = safe_float(position.get("pnl_percent"))
    portfolio_pnl_usd = safe_float(position.get("pnl_usd"))

    suspicious = False
    warnings = []

    if entry_price > 0 and exit_price > 0:
        if exit_price < entry_price and portfolio_pnl_percent > 0:
            suspicious = True
            warnings.append("Portfolio PnL is positive while exit price is below entry price.")

        if exit_price > entry_price and portfolio_pnl_percent < 0:
            suspicious = True
            warnings.append("Portfolio PnL is negative while exit price is above entry price.")

    if abs(portfolio_pnl_percent - price_pnl_percent) > 100:
        suspicious = True
        warnings.append("Portfolio PnL differs from price-based PnL by more than 100 percentage points.")

    audit = {
        "token_address": position.get("mint"),
        "symbol": position.get("symbol"),
        "label": label,
        "created_at": datetime.utcnow().isoformat(),

        "entry_price": entry_price,
        "exit_price": exit_price,
        "price_pnl_percent": price_pnl_percent,

        "portfolio_pnl_percent": portfolio_pnl_percent,
        "portfolio_pnl_usd": portfolio_pnl_usd,

        "entry_value_full": entry_value_full,
        "current_value_full": current_value_full,
        "entry_value_for_sell": entry_value_for_sell,
        "exit_value_for_sell": exit_value_for_sell,
        "value_pnl_usd": value_pnl_usd,
        "value_pnl_percent": value_pnl_percent,

        "quantity": quantity,
        "amount_raw": str(amount_raw),
        "sell_amount_raw": str(sell_raw),
        "sell_fraction": fraction,

        "suspicious": suspicious,
        "warnings": warnings,
    }

    return audit


def print_exit_audit(audit, decision):
    print("\n" + "=" * 72)
    print("LIVE EXIT AUDIT")
    print("=" * 72)
    print("Token:", audit.get("token_address"))
    print("Symbol:", audit.get("symbol"))
    print("Reason:", audit.get("label"))
    print("Decision Message:", decision.get("message"))
    print("-" * 72)
    print("Entry Price:", audit.get("entry_price"))
    print("Exit/Current Price:", audit.get("exit_price"))
    print("Price-Based PnL %:", round(safe_float(audit.get("price_pnl_percent")), 6))
    print("-" * 72)
    print("Portfolio PnL %:", round(safe_float(audit.get("portfolio_pnl_percent")), 6))
    print("Portfolio PnL USD:", round(safe_float(audit.get("portfolio_pnl_usd")), 6))
    print("-" * 72)
    print("Entry Value Full:", round(safe_float(audit.get("entry_value_full")), 8))
    print("Current Value Full:", round(safe_float(audit.get("current_value_full")), 8))
    print("Entry Value Sold:", round(safe_float(audit.get("entry_value_for_sell")), 8))
    print("Exit Value Sold:", round(safe_float(audit.get("exit_value_for_sell")), 8))
    print("Value-Based PnL USD:", round(safe_float(audit.get("value_pnl_usd")), 8))
    print("Value-Based PnL %:", round(safe_float(audit.get("value_pnl_percent")), 6))
    print("-" * 72)
    print("Amount Raw:", audit.get("amount_raw"))
    print("Sell Raw:", audit.get("sell_amount_raw"))
    print("Sell Fraction:", round(safe_float(audit.get("sell_fraction")), 6))
    print("-" * 72)

    if audit.get("suspicious"):
        print("🚨 SUSPICIOUS EXIT MATH DETECTED")
        for warning in audit.get("warnings", []):
            print(" -", warning)
    else:
        print("Exit math sanity check passed.")

    print("=" * 72 + "\n")


def sell_with_retry(position, amount_raw, label, slippage_bps=150, audit=None):
    token_address = position.get("mint")
    last_result = None

    if audit is None:
        audit = calculate_exit_audit(position, amount_raw, label)

    # Prefer value-based PnL for payload because it uses the same cost basis
    # that portfolio uses. Keep price-based and portfolio PnL in audit fields.
    audit_pnl_percent = audit.get("value_pnl_percent")
    audit_pnl_usd = audit.get("value_pnl_usd")

    for attempt in range(1, SELL_RETRY_ATTEMPTS + 1):
        result = execute_live_sell({
            "token_address": token_address,
            "amount_raw": str(amount_raw),
            "slippage_bps": slippage_bps,
            "exit_reason": label,
            "entry_signature": position.get("signature"),

            "entry_price": audit.get("entry_price"),
            "exit_price": audit.get("exit_price"),

            # Corrected/sanity PnL fields.
            "pnl_percent": audit_pnl_percent,
            "pnl_usd": audit_pnl_usd,

            # Debug comparison fields.
            "audit_price_pnl_percent": audit.get("price_pnl_percent"),
            "audit_value_pnl_percent": audit.get("value_pnl_percent"),
            "audit_value_pnl_usd": audit.get("value_pnl_usd"),
            "portfolio_pnl_percent": audit.get("portfolio_pnl_percent"),
            "portfolio_pnl_usd": audit.get("portfolio_pnl_usd"),
            "audit": audit,

            "held_minutes": minutes_held(position.get("entry_time")),
            "sell_attempt": attempt,
        })

        last_result = result

        if result.get("ok"):
            result["sell_attempts"] = attempt
            result["audit"] = audit
            result["audit_pnl_percent"] = audit_pnl_percent
            result["audit_pnl_usd"] = audit_pnl_usd
            return result

        if attempt < SELL_RETRY_ATTEMPTS:
            time.sleep(SELL_RETRY_DELAY_SECONDS)

    if last_result:
        last_result["audit"] = audit
        last_result["audit_pnl_percent"] = audit_pnl_percent
        last_result["audit_pnl_usd"] = audit_pnl_usd
        return last_result

    return {
        "ok": False,
        "error": "Sell failed before any result.",
        "audit": audit,
        "audit_pnl_percent": audit_pnl_percent,
        "audit_pnl_usd": audit_pnl_usd,
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

        audit = calculate_exit_audit(
            position=position,
            sell_amount_raw=sell_amount_raw,
            label=decision.get("label"),
        )
        print_exit_audit(audit, decision)

        result = sell_with_retry(
            position=position,
            amount_raw=sell_amount_raw,
            label=decision.get("label"),
            slippage_bps=300 if decision.get("urgent") else 150,
            audit=audit,
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
