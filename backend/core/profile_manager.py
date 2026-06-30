import json
import os
import shutil
from copy import deepcopy
from datetime import datetime

STARTING_BALANCE = 10000
DEFAULT_TRADE_SIZE = 100

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
PROFILES_FILE = os.path.join(DATA_DIR, "paper_profiles.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def now():
    return datetime.utcnow().isoformat()


def ensure_data_folder():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def default_profile(name="Main", starting_cash=STARTING_BALANCE, trade_size=DEFAULT_TRADE_SIZE, risk_mode="NORMAL"):
    starting_cash = float(starting_cash)
    trade_size = float(trade_size)

    return {
        "name": name,
        "cash": starting_cash,
        "open_trades": [],
        "closed_trades": [],
        "settings": {
            "starting_cash": starting_cash,
            "trade_size": trade_size,
            "risk_mode": risk_mode,
            "memory_preserved": True,
            "created_at": now(),
            "updated_at": now(),
        },
    }


def default_profiles_state():
    return {
        "active_profile": "Main",
        "profiles": {
            "Main": default_profile("Main", 10000, 100, "NORMAL"),
            "$50 Challenge": default_profile("$50 Challenge", 50, 5, "SMALL_ACCOUNT"),
            "$10 Challenge": default_profile("$10 Challenge", 10, 1, "TINY_ACCOUNT"),
            "High Risk": default_profile("High Risk", 1000, 100, "HIGH_RISK"),
            "Conservative": default_profile("Conservative", 10000, 50, "CONSERVATIVE"),
        },
        "shared": {
            "alpha_brain_shared": True,
            "learning_memory_shared": True,
            "wallet_memory_shared": True,
            "created_at": now(),
            "updated_at": now(),
        },
    }


def save_profiles_state(state):
    ensure_data_folder()

    temp_file = PROFILES_FILE + ".tmp"
    backup_file = os.path.join(
        BACKUP_DIR,
        f"paper_profiles_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
    )

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)

    with open(temp_file, "r", encoding="utf-8") as file:
        json.load(file)

    if os.path.exists(PROFILES_FILE):
        try:
            shutil.copyfile(PROFILES_FILE, backup_file)
        except Exception as error:
            print("PROFILE BACKUP FAILED:", error)

    os.replace(temp_file, PROFILES_FILE)


def load_profiles_state():
    ensure_data_folder()

    if not os.path.exists(PROFILES_FILE):
        state = default_profiles_state()
        save_profiles_state(state)
        return state

    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as file:
            state = json.load(file)

        state.setdefault("active_profile", "Main")
        state.setdefault("profiles", {})
        state.setdefault("shared", {})

        if not state["profiles"]:
            state = default_profiles_state()

        if state["active_profile"] not in state["profiles"]:
            state["active_profile"] = next(iter(state["profiles"].keys()))

        for name, profile in state["profiles"].items():
            profile.setdefault("name", name)
            profile.setdefault("cash", STARTING_BALANCE)
            profile.setdefault("open_trades", [])
            profile.setdefault("closed_trades", [])
            profile.setdefault("settings", {})
            profile["settings"].setdefault("starting_cash", profile.get("cash", STARTING_BALANCE))
            profile["settings"].setdefault("trade_size", DEFAULT_TRADE_SIZE)
            profile["settings"].setdefault("risk_mode", "NORMAL")
            profile["settings"].setdefault("memory_preserved", True)
            profile["settings"].setdefault("updated_at", now())

        save_profiles_state(state)
        return state

    except Exception as error:
        print("PROFILE STATE LOAD FAILED:", error)
        state = default_profiles_state()
        save_profiles_state(state)
        return state


profiles_state = load_profiles_state()


def get_profiles_state():
    return profiles_state


def get_active_profile_name():
    return profiles_state.get("active_profile", "Main")


def get_profile(name=None):
    if name is None:
        name = get_active_profile_name()

    return profiles_state.get("profiles", {}).get(name)


def list_profiles():
    output = []

    for name, profile in profiles_state.get("profiles", {}).items():
        open_trades = profile.get("open_trades", [])
        closed_trades = profile.get("closed_trades", [])

        open_value = 0
        for trade in open_trades:
            qty = float(trade.get("quantity") or 0)
            current = float(trade.get("current_price") or trade.get("entry_price") or 0)
            open_value += qty * current

        cash = float(profile.get("cash") or 0)
        equity = cash + open_value

        output.append(
            {
                "name": name,
                "active": name == profiles_state.get("active_profile"),
                "cash": round(cash, 4),
                "equity": round(equity, 4),
                "open_trades": len(open_trades),
                "closed_trades": len(closed_trades),
                "settings": profile.get("settings", {}),
            }
        )

    return {
        "ok": True,
        "active_profile": profiles_state.get("active_profile"),
        "profiles": output,
        "shared": profiles_state.get("shared", {}),
    }


def set_active_profile(name):
    name = str(name or "").strip()

    if name not in profiles_state.get("profiles", {}):
        return {"ok": False, "message": f"Profile '{name}' does not exist."}

    profiles_state["active_profile"] = name
    profiles_state.setdefault("shared", {})["updated_at"] = now()
    save_profiles_state(profiles_state)

    return {
        "ok": True,
        "active_profile": name,
        "message": f"Active profile switched to {name}.",
    }


def create_profile(name, starting_cash=10000, trade_size=100, risk_mode="NORMAL"):
    name = str(name or "").strip()

    if not name:
        return {"ok": False, "message": "Profile name is required."}

    if name in profiles_state.get("profiles", {}):
        return {"ok": False, "message": f"Profile '{name}' already exists."}

    profiles_state["profiles"][name] = default_profile(
        name=name,
        starting_cash=starting_cash,
        trade_size=trade_size,
        risk_mode=risk_mode,
    )
    profiles_state["active_profile"] = name
    profiles_state.setdefault("shared", {})["updated_at"] = now()
    save_profiles_state(profiles_state)

    return {
        "ok": True,
        "message": f"Profile '{name}' created.",
        "active_profile": name,
        "profile": profiles_state["profiles"][name],
    }


def clone_profile(source_name=None, new_name=None):
    if source_name is None:
        source_name = get_active_profile_name()

    source = get_profile(source_name)

    if source is None:
        return {"ok": False, "message": f"Source profile '{source_name}' does not exist."}

    if not new_name:
        base_name = f"{source_name} Copy"
        new_name = base_name
        counter = 2

        while new_name in profiles_state["profiles"]:
            new_name = f"{base_name} {counter}"
            counter += 1

    new_name = str(new_name).strip()

    if new_name in profiles_state["profiles"]:
        return {"ok": False, "message": f"Profile '{new_name}' already exists."}

    clone = deepcopy(source)
    clone["name"] = new_name
    clone.setdefault("settings", {})
    clone["settings"]["created_at"] = now()
    clone["settings"]["updated_at"] = now()
    clone["settings"]["cloned_from"] = source_name

    profiles_state["profiles"][new_name] = clone
    profiles_state["active_profile"] = new_name
    profiles_state.setdefault("shared", {})["updated_at"] = now()
    save_profiles_state(profiles_state)

    return {
        "ok": True,
        "message": f"Profile '{source_name}' cloned into '{new_name}'.",
        "active_profile": new_name,
        "profile": clone,
    }


def delete_profile(name):
    name = str(name or "").strip()

    if name not in profiles_state.get("profiles", {}):
        return {"ok": False, "message": f"Profile '{name}' does not exist."}

    if len(profiles_state["profiles"]) <= 1:
        return {"ok": False, "message": "Cannot delete the last remaining profile."}

    del profiles_state["profiles"][name]

    if profiles_state.get("active_profile") == name:
        profiles_state["active_profile"] = next(iter(profiles_state["profiles"].keys()))

    profiles_state.setdefault("shared", {})["updated_at"] = now()
    save_profiles_state(profiles_state)

    return {
        "ok": True,
        "message": f"Profile '{name}' deleted.",
        "active_profile": profiles_state["active_profile"],
    }


def reset_profile(name=None, starting_cash=10000, trade_size=None):
    if name is None:
        name = get_active_profile_name()

    profile = get_profile(name)

    if profile is None:
        return {"ok": False, "message": f"Profile '{name}' does not exist."}

    starting_cash = float(starting_cash)

    if trade_size is None:
        trade_size = profile.get("settings", {}).get("trade_size", DEFAULT_TRADE_SIZE)

    trade_size = float(trade_size)

    profile["cash"] = starting_cash
    profile["open_trades"] = []
    profile["closed_trades"] = []
    profile["settings"] = {
        **profile.get("settings", {}),
        "starting_cash": starting_cash,
        "trade_size": trade_size,
        "reset_at": now(),
        "updated_at": now(),
        "memory_preserved": True,
    }

    save_profiles_state(profiles_state)

    return {
        "ok": True,
        "message": f"Profile '{name}' reset. Shared learning memory preserved.",
        "active_profile": profiles_state.get("active_profile"),
        "profile": profile,
    }


def set_profile_trade_size(name=None, trade_size=100):
    if name is None:
        name = get_active_profile_name()

    profile = get_profile(name)

    if profile is None:
        return {"ok": False, "message": f"Profile '{name}' does not exist."}

    trade_size = float(trade_size)

    profile.setdefault("settings", {})
    profile["settings"]["trade_size"] = trade_size
    profile["settings"]["updated_at"] = now()

    save_profiles_state(profiles_state)

    return {
        "ok": True,
        "profile": name,
        "trade_size": trade_size,
    }
