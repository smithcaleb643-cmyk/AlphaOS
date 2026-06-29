from datetime import datetime
from core.paper_trader import paper_state


def update_open_trades(price_lookup):
    still_open = []

    for trade in paper_state["open_trades"]:
        token = trade.get("token_address")
        current_price = float(price_lookup.get(token, trade["current_price"]))

        trade["current_price"] = current_price

        pnl_percent = ((current_price - trade["entry_price"]) / trade["entry_price"]) * 100
        pnl_usd = trade["size_usd"] * (pnl_percent / 100)

        trade["pnl_percent"] = round(pnl_percent, 2)
        trade["pnl_usd"] = round(pnl_usd, 2)

        if current_price >= trade["take_profit"]:
            trade["status"] = "CLOSED_TP"
            trade["closed_at"] = datetime.utcnow().isoformat()
            paper_state["cash"] += trade["size_usd"] + trade["pnl_usd"]
            paper_state["closed_trades"].append(trade)

        elif current_price <= trade["stop_loss"]:
            trade["status"] = "CLOSED_STOP"
            trade["closed_at"] = datetime.utcnow().isoformat()
            paper_state["cash"] += trade["size_usd"] + trade["pnl_usd"]
            paper_state["closed_trades"].append(trade)

        else:
            still_open.append(trade)

    paper_state["open_trades"] = still_open

    return paper_state