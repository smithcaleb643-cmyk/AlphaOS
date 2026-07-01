import json
import os
from datetime import datetime

from core.learning_memory import save_learning_memory

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
LIVE_LEARNING_FILE = os.path.join(DATA_DIR, "live_completed_trades.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_live_completed_trades():
    ensure_data_dir()

    if not os.path.exists(LIVE_LEARNING_FILE):
        return []

    try:
        with open(LIVE_LEARNING_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_live_completed_trades(trades):
    ensure_data_dir()

    with open(LIVE_LEARNING_FILE, "w", encoding="utf-8") as file:
        json.dump(trades, file, indent=2)


def record_live_completed_trade(payload, sell_result):
    trades = load_live_completed_trades()

    learned = {
        "id": len(trades) + 1,
        "created_at": datetime.utcnow().isoformat(),
        "type": "LIVE_COMPLETED_TRADE",
        "token_address": payload.get("token_address"),
        "entry_signature": payload.get("entry_signature"),
        "exit_signature": sell_result.get("signature"),
        "entry_price": payload.get("entry_price"),
        "exit_price": payload.get("exit_price"),
        "pnl_percent": payload.get("pnl_percent"),
        "pnl_usd": payload.get("pnl_usd"),
        "held_minutes": payload.get("held_minutes"),
        "exit_reason": payload.get("exit_reason"),
        "raw_payload": payload,
    }

    trades.append(learned)
    save_live_completed_trades(trades)

    try:
        save_learning_memory(reason="live_trade_closed")
    except Exception as error:
        learned["learning_save_error"] = str(error)

    return learned