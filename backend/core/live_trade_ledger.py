"""
live_trade_ledger.py

AlphaOS Live Trade Ledger

The ledger is the single source of truth for every trade.

Execution writes to it.
Learning reads from it.
UI visualizes it.
Analytics queries it.

Nothing should ever have to reconstruct a trade again.
"""

from pathlib import Path
from datetime import datetime
import json
import uuid

LEDGER_PATH = Path("data/live_trade_ledger.json")

LEDGER_PATH.parent.mkdir(exist_ok=True)


# ============================================================
# Internal Helpers
# ============================================================

def _now():
    return datetime.utcnow().isoformat()


def _load():
    if not LEDGER_PATH.exists():
        return []

    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(data):
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ============================================================
# Public API
# ============================================================

def create_trade(entry_data: dict):

    ledger = _load()

    trade = {
        "trade_id": str(uuid.uuid4()),

        "status": "OPEN",

        "created_at": _now(),

        "updated_at": _now(),

        "entry": entry_data,

        "updates": [],

        "exit": None,

        "analytics": {}
    }

    ledger.append(trade)

    _save(ledger)

    return trade["trade_id"]


def update_trade(trade_id, update):

    ledger = _load()

    for trade in ledger:

        if trade["trade_id"] == trade_id:

            trade["updates"].append({
                "time": _now(),
                **update
            })

            trade["updated_at"] = _now()

            _save(ledger)

            return True

    return False


def close_trade(trade_id, exit_data):

    ledger = _load()

    for trade in ledger:

        if trade["trade_id"] == trade_id:

            trade["status"] = "CLOSED"

            trade["exit"] = exit_data

            trade["updated_at"] = _now()

            analytics = {}

            try:

                entry_price = float(
                    trade["entry"].get("entry_price", 0)
                )

                exit_price = float(
                    exit_data.get("exit_price", 0)
                )

                if entry_price > 0:

                    analytics["price_return_percent"] = (
                        (exit_price - entry_price)
                        / entry_price
                    ) * 100

            except Exception:
                pass

            trade["analytics"] = analytics

            _save(ledger)

            return True

    return False


def get_open_trades():

    return [
        t
        for t in _load()
        if t["status"] == "OPEN"
    ]


def get_closed_trades():

    return [
        t
        for t in _load()
        if t["status"] == "CLOSED"
    ]


def get_trade(trade_id):

    for trade in _load():

        if trade["trade_id"] == trade_id:

            return trade

    return None


def all_trades():

    return _load()