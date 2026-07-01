from datetime import datetime

LIVE_ALPHA_STATE = {
    "running": False,
    "mode": "LIVE",
    "execution_mode": "LIVE",
    "trade_size_usd": 1.0,
    "max_open_positions": 10,
    "max_daily_loss_usd": 2.0,
    "daily_profit_target_usd": 5.0,
    "minimum_score": 50,
    "buy_cooldown_seconds": 60,
    "auto_buy_enabled": True,
    "trades_today": 0,
    "scans_today": 0,
    "started_at": None,
    "stopped_at": None,
    "last_action": "Idle",
}


def get_live_alpha_state():
    return {
        **LIVE_ALPHA_STATE,
        "checked_at": datetime.utcnow().isoformat(),
    }


def start_live_alpha():
    LIVE_ALPHA_STATE["running"] = True
    LIVE_ALPHA_STATE["started_at"] = datetime.utcnow().isoformat()
    LIVE_ALPHA_STATE["stopped_at"] = None
    LIVE_ALPHA_STATE["last_action"] = "Live Alpha started."

    print("START LIVE ALPHA: importing loop...")
    from core.live_alpha_loop import launch_live_alpha
    launch_live_alpha()
    print("START LIVE ALPHA: loop launched.")

    return get_live_alpha_state()


def stop_live_alpha():
    LIVE_ALPHA_STATE["running"] = False
    LIVE_ALPHA_STATE["stopped_at"] = datetime.utcnow().isoformat()
    LIVE_ALPHA_STATE["last_action"] = "Live Alpha stopped."
    return get_live_alpha_state()


def update_live_alpha_settings(settings: dict):
    if "trade_size_usd" in settings:
        LIVE_ALPHA_STATE["trade_size_usd"] = float(settings["trade_size_usd"])

    if "max_open_positions" in settings:
        LIVE_ALPHA_STATE["max_open_positions"] = int(settings["max_open_positions"])

    if "max_daily_loss_usd" in settings:
        LIVE_ALPHA_STATE["max_daily_loss_usd"] = float(settings["max_daily_loss_usd"])

    if "daily_profit_target_usd" in settings:
        LIVE_ALPHA_STATE["daily_profit_target_usd"] = float(settings["daily_profit_target_usd"])

    if "minimum_score" in settings:
        LIVE_ALPHA_STATE["minimum_score"] = int(settings["minimum_score"])

    if "buy_cooldown_seconds" in settings:
        LIVE_ALPHA_STATE["buy_cooldown_seconds"] = int(settings["buy_cooldown_seconds"])

    if "auto_buy_enabled" in settings:
        value = settings["auto_buy_enabled"]
        if isinstance(value, str):
            LIVE_ALPHA_STATE["auto_buy_enabled"] = value.lower() in ["true", "1", "yes", "on", "live"]
        else:
            LIVE_ALPHA_STATE["auto_buy_enabled"] = bool(value)

    if "execution_mode" in settings:
        mode = str(settings["execution_mode"]).upper()
        if mode in ["MOCK", "LIVE"]:
            LIVE_ALPHA_STATE["execution_mode"] = mode

    LIVE_ALPHA_STATE["last_action"] = (
        f"Settings updated: {LIVE_ALPHA_STATE['execution_mode']} / "
        f"Auto Buy {'ON' if LIVE_ALPHA_STATE['auto_buy_enabled'] else 'OFF'}."
    )

    return get_live_alpha_state()