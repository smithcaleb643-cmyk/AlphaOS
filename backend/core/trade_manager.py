from core.paper_trader import get_paper_state, recalc_trade, close_paper_trade, save_paper_state
from core.wallet_intelligence import learn_wallets_from_closed_trades
from core.alpha_brain import evaluate_exit_decision


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
    trade["partial_exits"].append({
        "label": label,
        "percent_sold": percent_to_sell,
        "exit_price": float(exit_price),
        "realized_pnl_usd": round(realized_pnl, 4),
    })

    state = get_paper_state()
    state["cash"] += sell_size + realized_pnl

    trade.setdefault("audit_notes", [])
    trade["audit_notes"].append({
        "event": label,
        "price": float(exit_price),
        "realized_pnl_usd": round(realized_pnl, 4),
    })

    save_paper_state()


def apply_decision_updates(trade, updates):
    if updates:
        trade.update(updates)
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

        decision = evaluate_exit_decision(trade)
        apply_decision_updates(trade, decision.get("updates", {}))

        if not decision.get("should_sell"):
            continue

        fraction = float(decision.get("fraction") or 1.0)
        label = decision.get("label") or "EXIT"

        if fraction < 1.0:
            take_partial_profit(trade, fraction, current_price, label)

            if label == "TP1_25_PERCENT":
                trade["review"] = "TP1 hit. Alpha sold 25% and moved stop to breakeven."
                trade["recommendation"] = "PROTECTING PROFIT"
            elif label == "TP2_25_PERCENT":
                trade["review"] = "TP2 hit. Alpha sold another 25%, locked +5%, and activated runner mode."
                trade["recommendation"] = "RUNNER MODE"
            elif label == "TP3_25_PERCENT":
                trade["review"] = "TP3 hit. Alpha sold another 25% and is trailing the remaining runner."
                trade["recommendation"] = "TRAILING RUNNER"

            save_paper_state()
            continue

        exit_price = decision.get("exit_price") or current_price

        closed = close_paper_trade(
            trade.get("id"),
            exit_price=exit_price,
            reason=label,
        )

        if closed:
            closed_now.append(closed)
            learn_wallets_from_closed_trades(state)

    return {
        "updated": True,
        "closed_now": closed_now,
        "open_trades": state.get("open_trades", []),
        "closed_trades": state.get("closed_trades", []),
    }