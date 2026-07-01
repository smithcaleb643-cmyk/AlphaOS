import json
import os
from datetime import datetime

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
MOCK_FILE = os.path.join(DATA_DIR, "live_mock_trades.json")


def _ensure():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_mock_trades():
    _ensure()

    if not os.path.exists(MOCK_FILE):
        return {"ok": True, "count": 0, "trades": []}

    with open(MOCK_FILE, "r", encoding="utf-8") as f:
        trades = json.load(f)

    return {"ok": True, "count": len(trades), "trades": trades}


def save_mock_trades(trades):
    _ensure()

    with open(MOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2)


def execute_mock_buy(signal):
    journal = load_mock_trades()
    trades = journal.get("trades", [])

    trade = {
        "id": len(trades) + 1,
        "type": "MOCK_BUY",
        "status": "OPEN",
        "created_at": datetime.utcnow().isoformat(),
        "coin_name": signal.get("coin_name"),
        "symbol": signal.get("symbol"),
        "token_address": signal.get("token_address"),
        "score": signal.get("score"),
        "probability": signal.get("probability"),
        "risk_score": signal.get("risk_score"),
        "reason": signal.get("reason"),
        "usd_amount": signal.get("usd_amount", 1.0),
        "entry_price": signal.get("price_usd"),
        "message": "Mock buy recorded. No real money spent.",
    }

    trades.append(trade)
    save_mock_trades(trades)

    return {
        "ok": True,
        "mock": True,
        "trade": trade,
        "message": "Mock buy executed.",
    }