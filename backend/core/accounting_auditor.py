from core.paper_trader import get_paper_state

STARTING_BALANCE = 10000


def trade_remaining_value(trade):
    qty = float(trade.get("quantity") or 0)
    current = float(trade.get("current_price") or trade.get("entry_price") or 0)
    return qty * current


def trade_unrealized_pnl(trade):
    return float(trade.get("pnl_usd") or 0)


def trade_realized_pnl(trade):
    return float(trade.get("realized_pnl_usd") or 0)


def closed_trade_pnl(trade):
    if trade.get("final_pnl_usd") is not None:
        return float(trade.get("final_pnl_usd") or 0)

    return float(trade.get("realized_pnl_usd") or 0) + float(trade.get("pnl_usd") or 0)


def run_accounting_audit():
    state = get_paper_state()

    cash = float(state.get("cash") or 0)
    open_trades = state.get("open_trades", [])
    closed_trades = state.get("closed_trades", [])

    open_value = sum(trade_remaining_value(t) for t in open_trades)
    open_unrealized_pnl = sum(trade_unrealized_pnl(t) for t in open_trades)
    open_realized_pnl = sum(trade_realized_pnl(t) for t in open_trades)
    closed_pnl = sum(closed_trade_pnl(t) for t in closed_trades)

    equity = cash + open_value
    total_pnl = equity - STARTING_BALANCE

    audit = {
        "starting_balance": STARTING_BALANCE,
        "cash": round(cash, 2),
        "open_value": round(open_value, 2),
        "equity": round(equity, 2),
        "total_pnl": round(total_pnl, 2),
        "closed_pnl": round(closed_pnl, 2),
        "open_unrealized_pnl": round(open_unrealized_pnl, 2),
        "open_realized_pnl": round(open_realized_pnl, 2),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "cash_plus_open_value_formula": f"{round(cash, 2)} + {round(open_value, 2)} = {round(equity, 2)}",
        "is_balanced": True,
        "warnings": [],
    }

    if cash < 0:
        audit["is_balanced"] = False
        audit["warnings"].append("Cash is negative.")

    if equity < 0:
        audit["is_balanced"] = False
        audit["warnings"].append("Equity is negative.")

    if len(open_trades) == 0 and abs(equity - cash) > 0.01:
        audit["is_balanced"] = False
        audit["warnings"].append("No open trades but equity does not equal cash.")

    return audit