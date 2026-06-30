from core.paper_trader import get_paper_state, recalc_trade, close_paper_trade, save_paper_state
from core.wallet_intelligence import learn_wallets_from_closed_trades


def take_partial_profit(trade, percent_to_sell, exit_price, label):
    qty = float(trade.get("quantity") or 0)
    size_usd = float(trade.get("size_usd") or 0)
    entry = float(trade.get("entry_price") or 0)

    sell_qty = qty * percent_to_sell
    sell_size = size_usd * percent_to_sell
    realized_pnl = (float(exit_price) - entry) * sell_qty

    trade["quantity"] = qty - sell_qty
    trade["size_usd"] = size_usd - sell_size
    trade["realized_pnl_usd"] = round(float(trade.get("realized_pnl_usd") or 0) + realized_pnl, 4)

    trade.setdefault("partial_exits", [])
    trade["partial_exits"].append(
        {
            "label": label,
            "percent_sold": percent_to_sell,
            "exit_price": float(exit_price),
            "realized_pnl_usd": round(realized_pnl, 4),
        }
    )

    state = get_paper_state()
    state["cash"] += sell_size + realized_pnl

    trade.setdefault("audit_notes", [])
    trade["audit_notes"].append(
        {
            "event": label,
            "price": float(exit_price),
            "realized_pnl_usd": round(realized_pnl, 4),
        }
    )

    save_paper_state()


def update_open_trades(price_lookup):
    state = get_paper_state()
    open_trades = list(state.get("open_trades", []))
    closed_now = []

    for trade in open_trades:
        token = trade.get("token_address")
        current_price = price_lookup.get(token)

        if not current_price:
            continue

        current_price = float(current_price)
        entry = float(trade.get("entry_price") or 0)

        if entry <= 0:
            continue

        recalc_trade(trade, current_price, source="DexScreener", event_type="PRICE_UPDATE")
        pnl_percent = float(trade.get("pnl_percent") or 0)

        highest_seen = float(trade.get("highest_seen") or entry)
        if current_price > highest_seen:
            trade["highest_seen"] = current_price
            highest_seen = current_price

        if pnl_percent >= 6 and not trade.get("tp1_hit"):
            trade["tp1_hit"] = True
            take_partial_profit(trade, 0.25, current_price, "TP1_25_PERCENT")
            trade["stop_loss"] = entry
            trade["review"] = "TP1 hit. Alpha sold 25% and moved stop to breakeven."
            trade["recommendation"] = "PROTECTING PROFIT"

        if pnl_percent >= 12 and not trade.get("tp2_hit"):
            trade["tp2_hit"] = True
            take_partial_profit(trade, 0.25, current_price, "TP2_25_PERCENT")
            trade["stop_loss"] = entry * 1.05
            trade["runner_mode"] = True
            trade["review"] = "TP2 hit. Alpha sold another 25%, locked +5%, and activated runner mode."
            trade["recommendation"] = "RUNNER MODE"

        if pnl_percent >= 24 and not trade.get("tp3_hit"):
            trade["tp3_hit"] = True
            take_partial_profit(trade, 0.25, current_price, "TP3_25_PERCENT")
            trade["stop_loss"] = highest_seen * 0.90
            trade["review"] = "TP3 hit. Alpha sold another 25% and is trailing the remaining runner."
            trade["recommendation"] = "TRAILING RUNNER"

        if trade.get("tp3_hit"):
            trailing_stop = highest_seen * 0.90
            if trailing_stop > float(trade.get("stop_loss") or 0):
                trade["stop_loss"] = trailing_stop
                trade["review"] = "Runner is still alive. Alpha raised the trailing stop."

        save_paper_state()

        if current_price <= float(trade.get("stop_loss") or 0):
            close_reason = "CLOSED_STOP"

            if trade.get("tp3_hit"):
                close_reason = "CLOSED_TRAILING_RUNNER"
            elif trade.get("tp2_hit"):
                close_reason = "CLOSED_LOCKED_PROFIT"
            elif trade.get("tp1_hit"):
                close_reason = "CLOSED_BREAKEVEN"

            closed = close_paper_trade(
                trade.get("id"),
                exit_price=trade.get("stop_loss"),
                reason=close_reason,
            )

            if closed:
                closed_now.append(closed)
                learn_wallets_from_closed_trades(state)

            continue

    return {
        "updated": True,
        "closed_now": closed_now,
        "open_trades": state.get("open_trades", []),
        "closed_trades": state.get("closed_trades", []),
    }