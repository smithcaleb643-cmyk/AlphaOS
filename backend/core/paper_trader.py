import json
import os
import shutil
from datetime import datetime

from core.price_audit import log_price_event
from core.profile_manager import (
    get_profile,
    get_profiles_state,
    get_active_profile_name,
    save_profiles_state,
    list_profiles,
    set_active_profile,
    create_profile,
    clone_profile,
    delete_profile,
    reset_profile,
    set_profile_trade_size,
)

STARTING_BALANCE = 10000
TRADE_SIZE = 100

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
LEGACY_STATE_FILE = os.path.join(DATA_DIR, "paper_state.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def ensure_data_folder():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def now():
    return datetime.utcnow().isoformat()


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


def _active_profile():
    profile = get_profile()

    if profile is None:
        profiles_state = get_profiles_state()
        profiles_state.setdefault("profiles", {})
        profiles_state["profiles"]["Main"] = {
            "name": "Main",
            **default_state(),
        }
        profiles_state["active_profile"] = "Main"
        save_profiles_state(profiles_state)
        profile = get_profile("Main")

    profile.setdefault("cash", STARTING_BALANCE)
    profile.setdefault("open_trades", [])
    profile.setdefault("closed_trades", [])
    profile.setdefault("settings", {})
    profile["settings"].setdefault("starting_cash", STARTING_BALANCE)
    profile["settings"].setdefault("trade_size", TRADE_SIZE)
    profile["settings"].setdefault("memory_preserved", True)

    return profile


def migrate_legacy_paper_state_if_needed():
    ensure_data_folder()

    if not os.path.exists(LEGACY_STATE_FILE):
        return

    try:
        with open(LEGACY_STATE_FILE, "r", encoding="utf-8") as file:
            legacy = json.load(file)
    except Exception as error:
        print("LEGACY PAPER STATE READ FAILED:", error)
        return

    if not isinstance(legacy, dict) or "profiles" in legacy:
        return

    profiles_state = get_profiles_state()
    profiles_state.setdefault("profiles", {})
    main = profiles_state["profiles"].get("Main")

    if not main:
        return

    main_settings = main.setdefault("settings", {})
    already_migrated = main_settings.get("migrated_from_legacy_paper_state")
    main_has_history = bool(main.get("open_trades")) or bool(main.get("closed_trades"))

    if already_migrated or main_has_history:
        return

    legacy_settings = legacy.get("settings", {}) if isinstance(legacy.get("settings"), dict) else {}

    main["cash"] = legacy.get("cash", STARTING_BALANCE)
    main["open_trades"] = legacy.get("open_trades", []) if isinstance(legacy.get("open_trades"), list) else []
    main["closed_trades"] = legacy.get("closed_trades", []) if isinstance(legacy.get("closed_trades"), list) else []
    main["settings"] = {
        **main_settings,
        **legacy_settings,
        "starting_cash": legacy_settings.get("starting_cash", STARTING_BALANCE),
        "trade_size": legacy_settings.get("trade_size", TRADE_SIZE),
        "memory_preserved": True,
        "migrated_from_legacy_paper_state": True,
        "migrated_at": now(),
        "updated_at": now(),
    }

    profiles_state["active_profile"] = "Main"
    profiles_state.setdefault("shared", {})
    profiles_state["shared"]["legacy_paper_state_migrated_at"] = now()

    try:
        backup_file = os.path.join(
            BACKUP_DIR,
            f"legacy_paper_state_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        )
        shutil.copyfile(LEGACY_STATE_FILE, backup_file)
    except Exception as error:
        print("LEGACY PAPER BACKUP FAILED:", error)

    save_profiles_state(profiles_state)
    print("LEGACY PAPER STATE MIGRATED INTO MAIN PROFILE")


migrate_legacy_paper_state_if_needed()


def save_paper_state():
    save_profiles_state(get_profiles_state())


def load_paper_state():
    migrate_legacy_paper_state_if_needed()
    return _active_profile()


paper_state = load_paper_state()


def refresh_paper_state():
    global paper_state
    paper_state = _active_profile()
    return paper_state


def get_trade_size():
    state = refresh_paper_state()
    return float(state.get("settings", {}).get("trade_size", TRADE_SIZE))


def already_open(token_address):
    state = refresh_paper_state()
    return any(t.get("token_address") == token_address for t in state["open_trades"])


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
    trade["profile"] = get_active_profile_name()

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
            "profile": get_active_profile_name(),
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
    state = refresh_paper_state()
    trade_size = get_trade_size()

    entry = float(signal.get("price_usd") or 0)
    token = signal.get("token_address")

    if entry <= 0 or not token:
        return None

    if already_open(token):
        return None

    if state["cash"] < trade_size:
        print(f"TRADE REJECTED [{get_active_profile_name()}]: not enough cash")
        return None

    opened_at = now()
    real_wallets = signal.get("real_wallets") or signal.get("wallets") or []

    trade = {
        "id": len(state["open_trades"]) + len(state["closed_trades"]) + 1,
        "profile": get_active_profile_name(),
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

    state["cash"] -= trade_size
    state["open_trades"].append(trade)

    log_price_event(
        {
            "event_type": "ENTRY",
            "profile": get_active_profile_name(),
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
    state = refresh_paper_state()

    for trade in list(state["open_trades"]):
        if int(trade.get("id")) == int(trade_id):
            price = float(exit_price or trade.get("current_price") or trade.get("entry_price"))
            recalc_trade(trade, price, event_type=reason)

            realized_open_pnl = float(trade.get("pnl_usd") or 0)
            already_realized = float(trade.get("realized_pnl_usd") or 0)

            trade["status"] = reason
            trade["closed_at"] = now()
            trade["profile"] = get_active_profile_name()
            trade["final_pnl_usd"] = round(already_realized + realized_open_pnl, 4)

            state["cash"] += float(trade.get("size_usd") or 0) + realized_open_pnl
            state["open_trades"].remove(trade)
            state["closed_trades"].append(trade)

            log_price_event(
                {
                    "event_type": reason,
                    "profile": get_active_profile_name(),
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
    state = refresh_paper_state()

    for trade in state["open_trades"]:
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
            trade["profile"] = get_active_profile_name()
            save_paper_state()
            return trade

    return None


def reset_paper_account(starting_cash=10000, trade_size=None):
    result = reset_profile(
        name=get_active_profile_name(),
        starting_cash=starting_cash,
        trade_size=trade_size,
    )

    refresh_paper_state()

    if not result.get("ok"):
        return result

    profile = result.get("profile", {})

    return {
        "ok": True,
        "message": "Active paper profile reset. Learning memory preserved.",
        "active_profile": get_active_profile_name(),
        "cash": profile.get("cash"),
        "trade_size": profile.get("settings", {}).get("trade_size"),
        "open_trades": len(profile.get("open_trades", [])),
        "closed_trades": len(profile.get("closed_trades", [])),
    }


def set_paper_trade_size(trade_size):
    result = set_profile_trade_size(
        name=get_active_profile_name(),
        trade_size=trade_size,
    )
    refresh_paper_state()
    return result


def get_paper_state():
    return refresh_paper_state()


def get_all_paper_profiles():
    return list_profiles()


def select_paper_profile(name):
    result = set_active_profile(name)
    refresh_paper_state()
    return result


def create_paper_profile(name, starting_cash=10000, trade_size=100, risk_mode="NORMAL"):
    result = create_profile(
        name=name,
        starting_cash=starting_cash,
        trade_size=trade_size,
        risk_mode=risk_mode,
    )
    refresh_paper_state()
    return result


def clone_paper_profile(source_name=None, new_name=None):
    result = clone_profile(source_name=source_name, new_name=new_name)
    refresh_paper_state()
    return result


def delete_paper_profile(name):
    result = delete_profile(name)
    refresh_paper_state()
    return result
