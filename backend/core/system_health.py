import os
from datetime import datetime

from core.accounting_auditor import run_accounting_audit
from core.alpha_engine import get_alpha_engine_state
from core.learning import get_learning_report
from core.learning_memory import load_learning_memory
from core.paper_trader import get_paper_state
from core.price_audit import read_recent_price_events


DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)

PAPER_STATE_FILE = os.path.join(DATA_DIR, "paper_state.json")
LEARNING_MEMORY_FILE = os.path.join(DATA_DIR, "learning_memory.json")
LEARNING_SNAPSHOTS_FILE = os.path.join(DATA_DIR, "learning_snapshots.jsonl")
PRICE_AUDIT_FILE = os.path.join(DATA_DIR, "price_audit.jsonl")


def file_info(path):
    exists = os.path.exists(path)

    if not exists:
        return {
            "exists": False,
            "path": path,
            "size_bytes": 0,
            "modified_at": None,
        }

    return {
        "exists": True,
        "path": path,
        "size_bytes": os.path.getsize(path),
        "modified_at": datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat(),
    }


def get_last_price_update_age_seconds():
    events = read_recent_price_events(limit=1)

    if not events:
        return None

    timestamp = events[-1].get("timestamp")

    if not timestamp:
        return None

    try:
        event_time = datetime.fromisoformat(timestamp)
        return round((datetime.utcnow() - event_time).total_seconds(), 2)
    except Exception:
        return None


def calculate_confidence(learning, accounting, engine_state, warnings):
    win_rate = float(learning.get("win_rate") or 0)
    total_trades = int(learning.get("total_trades") or 0)
    total_pnl = float(accounting.get("total_pnl") or 0)

    confidence = 35

    confidence += min(25, total_trades / 20)

    if win_rate >= 55:
        confidence += 25
    elif win_rate >= 52:
        confidence += 18
    elif win_rate >= 50:
        confidence += 10
    else:
        confidence -= 10

    if total_pnl > 0:
        confidence += 15
    else:
        confidence -= 15

    if engine_state.get("running"):
        confidence += 5

    confidence -= len(warnings) * 7

    return max(0, min(100, round(confidence, 1)))


def get_strategy_mode(confidence, accounting, learning):
    open_trades = int(accounting.get("open_trades") or 0)
    win_rate = float(learning.get("win_rate") or 0)

    if confidence >= 80 and win_rate >= 52:
        return "Aggressive Momentum"
    if open_trades > 80:
        return "Exposure Control"
    if confidence >= 60:
        return "Balanced Hunter"
    return "Defensive Learning"


def get_alpha_mood(confidence, warnings, engine_state):
    if not engine_state.get("running"):
        return "Standby"
    if warnings:
        return "Cautious"
    if confidence >= 80:
        return "Confident"
    if confidence >= 60:
        return "Focused"
    return "Defensive"


def get_alpha_thought(confidence, accounting, learning, warnings, engine_state):
    if warnings:
        return f"I am monitoring a warning: {warnings[0]}"

    if not engine_state.get("running"):
        return "Engine is stopped. My memory is saved and accounting is balanced, but prices are stale until scanning resumes."

    win_rate = float(learning.get("win_rate") or 0)
    total_pnl = float(accounting.get("total_pnl") or 0)

    if confidence >= 80 and total_pnl > 0:
        return f"My current edge is positive. Win rate is {win_rate}%, and account equity is above starting balance."
    if total_pnl > 0:
        return "I am profitable but still collecting more evidence before increasing aggression."
    return "I am still learning. I should stay defensive until the data proves a stronger edge."


def get_learning_bars(learning, accounting):
    win_rate = float(learning.get("win_rate") or 0)
    total_trades = int(learning.get("total_trades") or 0)
    total_pnl = float(accounting.get("total_pnl") or 0)
    closed_pnl = float(accounting.get("closed_pnl") or 0)

    return [
        {"name": "Trade Experience", "value": max(0, min(100, round(total_trades / 10, 1)))},
        {"name": "Win Rate Strength", "value": max(0, min(100, round(win_rate * 1.5, 1)))},
        {"name": "Profit Edge", "value": max(0, min(100, round(50 + total_pnl / 150, 1)))},
        {"name": "Closed Profit Quality", "value": max(0, min(100, round(50 + closed_pnl / 150, 1)))},
        {"name": "Risk Discipline", "value": max(0, min(100, 82))},
    ]


def get_system_health():
    warnings = []

    state = get_paper_state()
    accounting = run_accounting_audit()
    saved_learning = load_learning_memory()
    learning = get_learning_report()
    engine_state = get_alpha_engine_state()

    paper_file = file_info(PAPER_STATE_FILE)
    learning_file = file_info(LEARNING_MEMORY_FILE)
    learning_snapshots_file = file_info(LEARNING_SNAPSHOTS_FILE)
    price_audit_file = file_info(PRICE_AUDIT_FILE)

    open_trades = state.get("open_trades", [])
    closed_trades = state.get("closed_trades", [])

    last_price_age = get_last_price_update_age_seconds()

    if not paper_file["exists"]:
        warnings.append("Paper state file does not exist yet.")

    if not learning_file["exists"]:
        warnings.append("Learning memory file does not exist yet.")

    if not price_audit_file["exists"]:
        warnings.append("Price audit file does not exist yet.")

    if not accounting.get("is_balanced", False):
        warnings.append("Accounting audit is not balanced.")

    if last_price_age is None:
        warnings.append("No price audit events found yet.")
    elif last_price_age > 300 and len(open_trades) > 0:
        warnings.append(f"Last price update is stale: {last_price_age} seconds old.")

    if float(accounting.get("cash", 0)) < 0:
        warnings.append("Cash is negative.")

    if float(accounting.get("equity", 0)) < 0:
        warnings.append("Equity is negative.")

    status = "SAFE" if len(warnings) == 0 else "WARNING"
    confidence = calculate_confidence(learning, accounting, engine_state, warnings)

    brain = {
        "mood": get_alpha_mood(confidence, warnings, engine_state),
        "confidence": confidence,
        "strategy_mode": get_strategy_mode(confidence, accounting, learning),
        "thought": get_alpha_thought(confidence, accounting, learning, warnings, engine_state),
        "learning_bars": get_learning_bars(learning, accounting),
        "engine_running": engine_state.get("running", False),
        "cycles": engine_state.get("cycles", 0),
        "last_scan_count": engine_state.get("last_scan_count", 0),
        "last_trades_created": engine_state.get("last_trades_created", 0),
        "wallet_ai": "STANDBY",
    }

    return {
        "status": status,
        "checked_at": datetime.utcnow().isoformat(),
        "backend_online": True,
        "paper_state_loaded": True,
        "paper_state_file": paper_file,
        "learning_memory_file": learning_file,
        "learning_snapshots_file": learning_snapshots_file,
        "price_audit_file": price_audit_file,
        "saved_learning": {
            "saved_at": saved_learning.get("saved_at"),
            "reason": saved_learning.get("reason"),
            "has_learning": saved_learning.get("learning") is not None,
        },
        "learning": learning,
        "brain": brain,
        "accounting": accounting,
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "last_price_update_age_seconds": last_price_age,
        "warnings": warnings,
    }