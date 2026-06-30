import threading
import time

from core.alpha_brain import score_coin
from core.adaptive_learning import apply_learning_to_signal
from core.paper_trader import create_paper_trade, get_paper_state
from core.trade_manager import update_open_trades
from services.market_service import scan_live_market, get_market_summary


engine_state = {
    "running": False,
    "last_scan_count": 0,
    "last_trades_created": 0,
    "last_prices_updated": 0,
    "cycles": 0,
    "message": "Alpha Engine idle",
}


def build_open_trade_price_lookup():
    """
    Refresh prices for EVERY open trade, even if that token is not found
    in the current live scanner results.
    """
    state = get_paper_state()
    open_trades = state.get("open_trades", [])
    price_lookup = {}

    for trade in open_trades:
        token = trade.get("token_address")

        if not token:
            continue

        try:
            summary = get_market_summary(token)

            if not summary.get("found"):
                continue

            price = float(summary.get("price_usd") or 0)

            if price > 0:
                price_lookup[token] = price

        except Exception as error:
            print("OPEN TRADE PRICE REFRESH FAILED:", token, error)

    return price_lookup


def alpha_engine_loop():
    while engine_state["running"]:
        try:
            coins = scan_live_market(limit=100)
            scanner_price_lookup = {}
            trades_created = 0

            for coin in coins:
                token = coin.get("token_address")
                price = float(coin.get("price_usd") or 0)

                if token and price > 0:
                    scanner_price_lookup[token] = price

                if not token or price <= 0:
                    continue

                result = score_coin(coin)
                result = apply_learning_to_signal(result)

                if result.get("score", 0) < 15:
                    continue

                trade = create_paper_trade(
                    {
                        **coin,
                        **result,
                        "token_address": token,
                        "price_usd": price,
                    }
                )

                if trade:
                    trades_created += 1

            open_trade_price_lookup = build_open_trade_price_lookup()

            price_lookup = {
                **scanner_price_lookup,
                **open_trade_price_lookup,
            }

            update_open_trades(price_lookup)

            engine_state["last_scan_count"] = len(coins)
            engine_state["last_trades_created"] = trades_created
            engine_state["last_prices_updated"] = len(price_lookup)
            engine_state["cycles"] += 1
            engine_state["message"] = "Alpha Engine running"

        except Exception as error:
            print("ENGINE ERROR:", error)
            engine_state["message"] = f"Engine error: {error}"

        time.sleep(2)


def start_alpha_engine():
    if engine_state["running"]:
        return engine_state

    engine_state["running"] = True

    thread = threading.Thread(target=alpha_engine_loop, daemon=True)
    thread.start()

    engine_state["message"] = "Alpha Engine started"
    return engine_state


def stop_alpha_engine():
    engine_state["running"] = False
    engine_state["message"] = "Alpha Engine stopped"
    return engine_state


def get_alpha_engine_state():
    return engine_state