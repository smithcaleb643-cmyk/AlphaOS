import threading
import time

from core.alpha_brain import score_coin
from core.paper_trader import create_paper_trade
from core.trade_manager import update_open_trades
from services.market_service import scan_live_market


MIN_TRADE_SCORE = 10

engine_state = {
    "running": False,
    "last_scan_count": 0,
    "last_trades_created": 0,
    "cycles": 0,
    "message": "Alpha Engine idle",
}


def get_token_address(coin):
    return (
        coin.get("token_address")
        or coin.get("address")
        or coin.get("mint")
        or coin.get("base_token_address")
        or coin.get("pair_address")
    )


def get_price_usd(coin):
    price = (
        coin.get("price_usd")
        or coin.get("priceUsd")
        or coin.get("price")
        or coin.get("current_price")
    )

    try:
        return float(price)
    except (TypeError, ValueError):
        return 0


def alpha_engine_loop():
    while engine_state["running"]:
        try:
            coins = scan_live_market(limit=12)
            price_lookup = {}
            trades_created = 0

            print("ALPHA ENGINE CYCLE")
            print("coins found:", len(coins))

            for coin in coins:
                token = get_token_address(coin)
                price = get_price_usd(coin)

                result = score_coin(coin)
                score = result.get("score", 0)

                print("SCAN DEBUG:", {
                    "coin": coin.get("coin_name") or coin.get("symbol") or coin.get("name"),
                    "token": token,
                    "price": price,
                    "score": score,
                    "action": result.get("action"),
                })

                if token and price:
                    price_lookup[token] = price

                if not token:
                    print("REJECTED: missing token address")
                    continue

                if not price:
                    print("REJECTED: missing price")
                    continue

                if score < MIN_TRADE_SCORE:
                    print("REJECTED: score too low")
                    continue

                trade_payload = {
                    **coin,
                    **result,
                    "token_address": token,
                    "price_usd": price,
                }

                print("CREATING PAPER TRADE:", trade_payload)

                trade = create_paper_trade(trade_payload)

                if trade:
                    trades_created += 1
                    print("TRADE CREATED:", trade)
                else:
                    print("TRADE FAILED")

            update_open_trades(price_lookup)

            engine_state["last_scan_count"] = len(coins)
            engine_state["last_trades_created"] = trades_created
            engine_state["cycles"] += 1
            engine_state["message"] = "Alpha Engine running"

        except Exception as error:
            print("ENGINE ERROR:", error)
            engine_state["message"] = f"Engine error: {error}"

        time.sleep(10)


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