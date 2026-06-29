from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.alpha_brain import score_coin
from database.memory import setup_database, save_scan, get_scans
from services.market_service import get_token_pairs, get_market_summary, scan_live_market
from core.paper_trader import create_paper_trade, get_paper_state
from core.trade_manager import update_open_trades
from core.learning import get_learning_report
from core.alpha_engine import start_alpha_engine, stop_alpha_engine, get_alpha_engine_state
from core.performance import get_performance
app = FastAPI(title="Alpha OS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_database()


@app.get("/")
def home():
    return {
        "message": "Alpha OS backend is running",
        "status": "online"
    }


@app.get("/scan")
def scan():
    live_coins = scan_live_market(limit=8)
    results = []
    paper_trades = []

    for coin in live_coins:
        result = score_coin(coin)
        save_scan(result["coin_name"], result)
        results.append(result)

        if result.get("score", 0) >= 30:
            trade_signal = {
                **result,
                "price_usd": coin.get("price_usd") or 0,
            }

            trade = create_paper_trade(trade_signal)

            if trade:
                paper_trades.append(trade)

    results = sorted(results, key=lambda item: item.get("score", 0), reverse=True)

    return {
        "count": len(results),
        "results": results,
        "paper_trades_created": len(paper_trades),
        "paper_trades": paper_trades,
    }

@app.get("/market/token/{token_address}")
def market_token(token_address: str):
    pairs = get_token_pairs(token_address)

    return {
        "token_address": token_address,
        "count": len(pairs),
        "pairs": pairs
    }


@app.get("/market/summary/{token_address}")
def market_summary(token_address: str):
    return get_market_summary(token_address)


@app.get("/discover")
def discover():
    coins = scan_live_market(limit=12)

    return {
        "count": len(coins),
        "coins": coins
    }@app.post("/paper/trade")
def paper_trade(signal: dict):
    trade = create_paper_trade(signal)

    if not trade:
        return {
            "created": False,
            "message": "No valid price for trade"
        }

    return {
        "created": True,
        "trade": trade
    }


@app.get("/paper/state")
def paper_state_endpoint():
    return get_paper_state()


@app.get("/paper/performance")
def paper_performance_endpoint():
    return get_performance()


@app.post("/paper/update")
def paper_update(price_lookup: dict):
    return update_open_trades(price_lookup)


@app.get("/paper/learning")
def paper_learning():
    return get_learning_report()


@app.post("/engine/start")
def engine_start():
    return start_alpha_engine()


@app.post("/engine/stop")
def engine_stop():
    return stop_alpha_engine()


@app.get("/engine/state")
def engine_state():
    return get_alpha_engine_state()