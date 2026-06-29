from datetime import datetime

STARTING_BALANCE = 10000
TRADE_SIZE = 100

paper_state = {
    "cash": STARTING_BALANCE,
    "open_trades": [],
    "closed_trades": [],
}


def already_open(token_address):
    return any(t.get("token_address") == token_address for t in paper_state["open_trades"])


def create_paper_trade(signal):
    entry = float(signal.get("price_usd") or 0)
    token = signal.get("token_address")

    if entry <= 0 or not token:
        return None

    if already_open(token):
        return None

    trade = {
        "id": len(paper_state["open_trades"]) + len(paper_state["closed_trades"]) + 1,
        "coin_name": signal.get("coin_name"),
        "symbol": signal.get("symbol"),
        "token_address": token,
        "action": "PAPER_BUY",
        "status": "OPEN",
        "entry_price": entry,
        "current_price": entry,
        "size_usd": TRADE_SIZE,
        "quantity": TRADE_SIZE / entry,
        "stop_loss": entry * 0.90,
        "take_profit": entry * 1.15,
        "score": signal.get("score"),
        "probability": signal.get("probability"),
        "risk_score": signal.get("risk_score"),
        "reason": signal.get("reason"),
        "opened_at": datetime.utcnow().isoformat(),
        "closed_at": None,
        "pnl_usd": 0,
        "pnl_percent": 0,
    }

    paper_state["cash"] -= TRADE_SIZE
    paper_state["open_trades"].append(trade)

    return trade


def get_paper_state():
    return paper_state