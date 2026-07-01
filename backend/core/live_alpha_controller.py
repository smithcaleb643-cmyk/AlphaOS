from datetime import datetime

LIVE_ALPHA_STATE = {
    "running": False,
    "mode": "LIVE",
    "trade_size_usd": 1.0,
    "max_open_positions": 1,
    "max_daily_loss_usd": 2.0,
    "daily_profit_target_usd": 5.0,
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

    from core.live_alpha_loop import launch_live_alpha
    launch_live_alpha()

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

    LIVE_ALPHA_STATE["last_action"] = "Live Alpha settings updated."

    return get_live_alpha_state()