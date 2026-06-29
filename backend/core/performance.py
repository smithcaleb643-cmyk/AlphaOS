from core.paper_trader import paper_state


def get_performance():
    closed = paper_state["closed_trades"]
    open_trades = paper_state["open_trades"]

    wins = [t for t in closed if t["pnl_usd"] > 0]
    losses = [t for t in closed if t["pnl_usd"] <= 0]

    total_pnl = sum(t["pnl_usd"] for t in closed)
    win_rate = (len(wins) / len(closed) * 100) if closed else 0

    return {
        "cash": round(paper_state["cash"], 2),
        "starting_balance": 10000,
        "open_trades": len(open_trades),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "equity": round(paper_state["cash"] + sum(t["size_usd"] + t["pnl_usd"] for t in open_trades), 2),
    }