from core.accounting_auditor import run_accounting_audit
from core.paper_trader import get_paper_state


def get_performance():
    state = get_paper_state()
    audit = run_accounting_audit()

    closed_trades = state.get("closed_trades", [])

    wins = 0
    losses = 0

    for trade in closed_trades:
        pnl = float(trade.get("final_pnl_usd") or trade.get("pnl_usd") or 0)

        if pnl >= 0:
            wins += 1
        else:
            losses += 1

    total_closed = len(closed_trades)
    win_rate = round((wins / total_closed) * 100, 2) if total_closed else 0

    return {
        **audit,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "return_percent": round((audit["total_pnl"] / audit["starting_balance"]) * 100, 2),
    }