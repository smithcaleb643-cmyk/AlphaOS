from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.alpha_brain import score_coin
from database.memory import setup_database, save_scan, get_scans
from services.market_service import get_token_pairs, get_market_summary, scan_live_market

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

    for coin in live_coins:
        result = score_coin(coin)
        save_scan(result["coin_name"], result)
        results.append(result)

    results = sorted(results, key=lambda item: item.get("score", 0), reverse=True)

    return {
        "count": len(results),
        "results": results
    }


@app.get("/memory")
def memory():
    scans = get_scans()

    return {
        "count": len(scans),
        "scans": scans
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
    }