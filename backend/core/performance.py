from core.paper_trader import get_paper_state


def get_performance():
    state = get_paper_state()

    settings = state.get("settings", {})
    starting_balance = float(settings.get("starting_cash") or 10000)
    cash = float(state.get("cash") or 0)

    open_trades = state.get("open_trades", [])
    closed_trades = state.get("closed_trades", [])

    open_value = 0
    open_pnl = 0

    for trade in open_trades:
        qty = float(trade.get("quantity") or 0)
        entry = float(trade.get("entry_price") or 0)
        current = float(trade.get("current_price") or entry)

        value = qty * current
        pnl = (current - entry) * qty

        open_value += value
        open_pnl += pnl

    closed_pnl = 0
    wins = 0
    losses = 0

    for trade in closed_trades:
        pnl = float(trade.get("final_pnl_usd") or trade.get("realized_pnl_usd") or trade.get("pnl_usd") or 0)
        closed_pnl += pnl

        if pnl >= 0:
            wins += 1
        else:
            losses += 1

    equity = cash + open_value
    total_pnl = equity - starting_balance

    total_closed = len(closed_trades)
    win_rate = round((wins / total_closed) * 100, 2) if total_closed else 0

    return {
        "starting_balance": round(starting_balance, 4),
        "cash": round(cash, 4),
        "open_value": round(open_value, 4),
        "equity": round(equity, 4),
        "open_pnl": round(open_pnl, 4),
        "closed_pnl": round(closed_pnl, 4),
        "total_pnl": round(total_pnl, 4),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "return_percent": round((total_pnl / starting_balance) * 100, 2) if starting_balance else 0,
    }