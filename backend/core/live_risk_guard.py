from datetime import datetime, date

LIVE_RISK_STATE = {
    "live_trading_enabled": False,
    "kill_switch": True,
    "max_trade_sol": 0.01,
    "max_daily_loss_usd": 10,
    "max_open_live_trades": 3,
    "minimum_sol_reserve": 0.003,
    "daily_realized_pnl_usd": 0,
    "open_live_trades": 0,
    "last_reset_date": str(date.today()),
}


def reset_daily_if_needed():
    today = str(date.today())

    if LIVE_RISK_STATE.get("last_reset_date") != today:
        LIVE_RISK_STATE["daily_realized_pnl_usd"] = 0
        LIVE_RISK_STATE["last_reset_date"] = today


def get_live_risk_state():
    reset_daily_if_needed()
    return {
        **LIVE_RISK_STATE,
        "checked_at": datetime.utcnow().isoformat(),
    }


def set_live_trading_enabled(enabled: bool):
    LIVE_RISK_STATE["live_trading_enabled"] = bool(enabled)
    return get_live_risk_state()


def set_kill_switch(enabled: bool):
    LIVE_RISK_STATE["kill_switch"] = bool(enabled)
    return get_live_risk_state()


def approve_live_buy(sol_amount, sol_balance=0):
    reset_daily_if_needed()

    sol_amount = float(sol_amount or 0)
    sol_balance = float(sol_balance or 0)

    if not LIVE_RISK_STATE["live_trading_enabled"]:
        return {
            "approved": False,
            "reason": "Live trading is disabled.",
            "state": get_live_risk_state(),
        }

    if LIVE_RISK_STATE["kill_switch"]:
        return {
            "approved": False,
            "reason": "Kill switch is ON.",
            "state": get_live_risk_state(),
        }

    if sol_amount <= 0:
        return {
            "approved": False,
            "reason": "Trade amount must be greater than zero.",
            "state": get_live_risk_state(),
        }

    if sol_amount > LIVE_RISK_STATE["max_trade_sol"]:
        return {
            "approved": False,
            "reason": f"Trade amount {sol_amount} SOL exceeds max {LIVE_RISK_STATE['max_trade_sol']} SOL.",
            "state": get_live_risk_state(),
        }

    if LIVE_RISK_STATE["open_live_trades"] >= LIVE_RISK_STATE["max_open_live_trades"]:
        return {
            "approved": False,
            "reason": "Maximum open live trades reached.",
            "state": get_live_risk_state(),
        }

    if abs(float(LIVE_RISK_STATE["daily_realized_pnl_usd"])) >= LIVE_RISK_STATE["max_daily_loss_usd"]:
        return {
            "approved": False,
            "reason": "Daily loss limit reached.",
            "state": get_live_risk_state(),
        }

    required = sol_amount + float(LIVE_RISK_STATE["minimum_sol_reserve"])

    if sol_balance < required:
        return {
            "approved": False,
            "reason": f"Not enough SOL after reserve. Wallet has {sol_balance}, needs {required}.",
            "state": get_live_risk_state(),
        }

    return {
        "approved": True,
        "reason": "Approved by live risk guard.",
        "state": get_live_risk_state(),
    }