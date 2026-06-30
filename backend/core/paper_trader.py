import json
import os
import shutil
from datetime import datetime

from core.price_audit import log_price_event

STARTING_BALANCE = 10000
TRADE_SIZE = 100

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
STATE_FILE = os.path.join(DATA_DIR, "paper_state.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def default_state():
    return {
        "cash": STARTING_BALANCE,
        "open_trades": [],
        "closed_trades": [],
        "settings": {
            "starting_cash": STARTING_BALANCE,
            "trade_size": TRADE_SIZE,
            "memory_preserved": True,
        },
    }


def ensure_data_folder():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def now():
    return datetime.utcnow().isoformat()


def save_paper_state():
    ensure_data_folder()

    temp_file = STATE_FILE + ".tmp"
    backup_file = os.path.join(
        BACKUP_DIR,
        f"paper_state_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
    )

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(paper_state, file, indent=2, ensure_ascii=False)

    with open(temp_file, "r", encoding="utf-8") as file:
        json.load(file)

    if os.path.exists(STATE_FILE):
        try:
            shutil.copyfile(STATE_FILE, backup_file)
        except Exception as error:
            print("BACKUP FAILED:", error)

    os.replace(temp_file, STATE_FILE)


def load_paper_state():
    ensure_data_folder()

    if not os.path.exists(STATE_FILE):
        return default_state()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        data.setdefault("cash", STARTING_BALANCE)
        data.setdefault("open_trades", [])
        data.setdefault("closed_trades", [])
        data.setdefault("settings", {})
        data["settings"].setdefault("starting_cash", STARTING_BALANCE)
        data["settings"].setdefault("trade_size", TRADE_SIZE)
        data["settings"].setdefault("memory_preserved", True)

        return data
    except Exception as error:
        print("PAPER STATE LOAD FAILED:", error)
        return default_state()


paper_state = load_paper_state()


def get_trade_size():
    return float(paper_state.get("settings", {}).get("trade_size", TRADE_SIZE))


def already_open(token_address):
    return any(t.get("token_address") == token_address for t in paper_state["open_trades"])


def recalc_trade(trade, current_price, source="DexScreener", event_type="PRICE_UPDATE"):
    entry = float(trade.get("entry_price") or 0)
    qty = float(trade.get("quantity") or 0)
    current = float(current_price or entry)

    pnl_usd = (current - entry) * qty
    pnl_percent = ((current - entry) / entry) * 100 if entry > 0 else 0

    trade["current_price"] = current
    trade["pnl_usd"] = round(pnl_usd, 4)
    trade["pnl_percent"] = round(pnl_percent, 2)
    trade["last_price_source"] = source
    trade["last_price_updated_at"] = now()

    trade.setdefault("price_history", [])
    trade["price_history"].append(
        {
            "timestamp": trade["last_price_updated_at"],
            "price": current,
            "source": source,
            "event_type": event_type,
            "pnl_usd": trade["pnl_usd"],
            "pnl_percent": trade["pnl_percent"],
        }
    )

    if len(trade["price_history"]) > 75:
        trade["price_history"] = trade["price_history"][-75:]

    log_price_event(
        {
            "event_type": event_type,
            "trade_id": trade.get("id"),
            "coin_name": trade.get("coin_name"),
            "symbol": trade.get("symbol"),
            "token_address": trade.get("token_address"),
            "price": current,
            "source": source,
            "pnl_usd": trade["pnl_usd"],
            "pnl_percent": trade["pnl_percent"],
        }
    )

    save_paper_state()
    return trade


def create_paper_trade(signal):
    trade_size = get_trade_size()

    entry = float(signal.get("price_usd") or 0)
    token = signal.get("token_address")

    if entry <= 0 or not token:
        return None

    if already_open(token):
        return None

    if paper_state["cash"] < trade_size:
        print("TRADE REJECTED: not enough cash")
        return None

    opened_at = now()
    real_wallets = signal.get("real_wallets") or signal.get("wallets") or []

    trade = {
        "id": len(paper_state["open_trades"]) + len(paper_state["closed_trades"]) + 1,
        "coin_name": signal.get("coin_name"),
        "symbol": signal.get("symbol"),
        "token_address": token,
        "pair_address": signal.get("pair_address"),
        "dex_url": signal.get("dex_url"),
        "action": "PAPER_BUY",
        "status": "OPEN",
        "entry_price": entry,
        "current_price": entry,
        "size_usd": trade_size,
        "original_size_usd": trade_size,
        "quantity": trade_size / entry,
        "stop_loss": entry * 0.90,
        "take_profit": entry * 1.15,
        "highest_seen": entry,
        "score": signal.get("score"),
        "original_score": signal.get("original_score", signal.get("score")),
        "learning_adjustment": signal.get("learning_adjustment", 0),
        "probability": signal.get("probability"),
        "risk_score": signal.get("risk_score"),
        "reason": signal.get("reason"),
        "review": "Click Review and Alpha will rethink this trade.",
        "recommendation": "WAIT",
        "opened_at": opened_at,
        "closed_at": None,
        "pnl_usd": 0,
        "pnl_percent": 0,
        "realized_pnl_usd": 0,
        "partial_exits": [],
        "real_wallets": real_wallets,
        "wallets": real_wallets,
        "wallet_adjustment": signal.get("wallet_adjustment", 0),
        "wallet_summary": signal.get("wallet_summary", "No wallet intelligence available yet."),
        "price_source": "DexScreener",
        "entry_price_source": "DexScreener",
        "last_price_source": "DexScreener",
        "last_price_updated_at": opened_at,
        "price_history": [
            {
                "timestamp": opened_at,
                "price": entry,
                "source": "DexScreener",
                "event_type": "ENTRY",
                "pnl_usd": 0,
                "pnl_percent": 0,
            }
        ],
    }

    paper_state["cash"] -= trade_size
    paper_state["open_trades"].append(trade)

    log_price_event(
        {
            "event_type": "ENTRY",
            "trade_id": trade.get("id"),
            "coin_name": trade.get("coin_name"),
            "symbol": trade.get("symbol"),
            "token_address": token,
            "price": entry,
            "source": "DexScreener",
            "pnl_usd": 0,
            "pnl_percent": 0,
        }
    )

    save_paper_state()
    return trade


def close_paper_trade(trade_id, exit_price=None, reason="MANUAL_SELL"):
    for trade in list(paper_state["open_trades"]):
        if int(trade.get("id")) == int(trade_id):
            price = float(exit_price or trade.get("current_price") or trade.get("entry_price"))
            recalc_trade(trade, price, event_type=reason)

            realized_open_pnl = float(trade.get("pnl_usd") or 0)
            already_realized = float(trade.get("realized_pnl_usd") or 0)

            trade["status"] = reason
            trade["closed_at"] = now()
            trade["final_pnl_usd"] = round(already_realized + realized_open_pnl, 4)

            paper_state["cash"] += float(trade.get("size_usd") or 0) + realized_open_pnl
            paper_state["open_trades"].remove(trade)
            paper_state["closed_trades"].append(trade)

            log_price_event(
                {
                    "event_type": reason,
                    "trade_id": trade.get("id"),
                    "coin_name": trade.get("coin_name"),
                    "symbol": trade.get("symbol"),
                    "token_address": trade.get("token_address"),
                    "price": price,
                    "source": "DexScreener",
                    "pnl_usd": trade.get("final_pnl_usd"),
                    "pnl_percent": trade.get("pnl_percent"),
                }
            )

            save_paper_state()
            return trade

    return None


def review_paper_trade(trade_id):
    for trade in paper_state["open_trades"]:
        if int(trade.get("id")) == int(trade_id):
            pnl = float(trade.get("pnl_percent") or 0)
            score = int(trade.get("score") or 0)
            risk = int(trade.get("risk_score") or 0)

            if pnl >= 20:
                trade["recommendation"] = "TRAIL WINNER"
                trade["review"] = "Alpha sees a strong runner. Keep trailing and protect gains."
            elif pnl >= 10:
                trade["recommendation"] = "SECURE PROFIT"
                trade["review"] = "Alpha sees strong profit. Consider locking gains or tightening the stop."
            elif pnl >= 5:
                trade["recommendation"] = "WATCH PROFIT"
                trade["review"] = "Alpha sees profit building. Holding is reasonable, but protect gains."
            elif pnl <= -8:
                trade["recommendation"] = "DANGER"
                trade["review"] = "Alpha sees serious weakness. This trade is close to failing."
            elif pnl <= -5:
                trade["recommendation"] = "CAUTION"
                trade["review"] = "Alpha sees weakness. Price is moving toward the risk zone."
            elif score >= 60 and risk <= 45:
                trade["recommendation"] = "HOLD"
                trade["review"] = "Alpha still likes this setup. Edge remains acceptable."
            else:
                trade["recommendation"] = "WATCH"
                trade["review"] = "Alpha is cautious. No emergency exit, but conviction is not high."

            trade["last_reviewed_at"] = now()
            save_paper_state()
            return trade

    return None


def reset_paper_account(starting_cash=10000, trade_size=None):
    starting_cash = float(starting_cash)

    if trade_size is None:
        trade_size = get_trade_size()
    else:
        trade_size = float(trade_size)

    paper_state["cash"] = starting_cash
    paper_state["open_trades"] = []
    paper_state["closed_trades"] = []
    paper_state["settings"] = {
        "starting_cash": starting_cash,
        "trade_size": trade_size,
        "reset_at": now(),
        "memory_preserved": True,
    }

    save_paper_state()

    return {
        "ok": True,
        "message": "Paper account reset. Learning memory preserved.",
        "cash": paper_state["cash"],
        "trade_size": trade_size,
        "open_trades": 0,
        "closed_trades": 0,
    }


def set_paper_trade_size(trade_size):
    trade_size = float(trade_size)

    paper_state.setdefault("settings", {})
    paper_state["settings"]["trade_size"] = trade_size
    paper_state["settings"]["updated_at"] = now()

    save_paper_state()

    return {
        "ok": True,
        "trade_size": trade_size,
    }


def get_paper_state():
    return paper_state