def get_profile_rules(state):
    settings = state.get("settings", {})
    starting_cash = float(settings.get("starting_cash") or 10000)
    risk_mode = settings.get("risk_mode", "NORMAL")

    if starting_cash <= 10 or risk_mode == "TINY_ACCOUNT":
        return {
            "max_open_trades": 2,
            "min_score": 85,
            "min_probability": 70,
            "max_risk_score": 35,
            "cash_reserve_percent": 20,
        }

    if starting_cash <= 50 or risk_mode == "SMALL_ACCOUNT":
        return {
            "max_open_trades": 4,
            "min_score": 80,
            "min_probability": 65,
            "max_risk_score": 45,
            "cash_reserve_percent": 15,
        }

    if risk_mode == "CONSERVATIVE":
        return {
            "max_open_trades": 6,
            "min_score": 85,
            "min_probability": 70,
            "max_risk_score": 35,
            "cash_reserve_percent": 25,
        }

    if risk_mode == "HIGH_RISK":
        return {
            "max_open_trades": 20,
            "min_score": 45,
            "min_probability": 40,
            "max_risk_score": 70,
            "cash_reserve_percent": 5,
        }

    return {
        "max_open_trades": 12,
        "min_score": 60,
        "min_probability": 50,
        "max_risk_score": 60,
        "cash_reserve_percent": 10,
    }


def approve_trade(signal, state):
    rules = get_profile_rules(state)

    cash = float(state.get("cash") or 0)
    open_trades = state.get("open_trades", [])
    settings = state.get("settings", {})
    starting_cash = float(settings.get("starting_cash") or 10000)
    trade_size = float(settings.get("trade_size") or 100)

    score = float(signal.get("score") or 0)
    probability = float(signal.get("probability") or 0)
    risk_score = float(signal.get("risk_score") or 0)

    reserve_cash = starting_cash * (rules["cash_reserve_percent"] / 100)

    if len(open_trades) >= rules["max_open_trades"]:
        return {
            "approved": False,
            "reason": f"Blocked: max open trades reached ({rules['max_open_trades']}).",
            "rules": rules,
        }

    if score < rules["min_score"]:
        return {
            "approved": False,
            "reason": f"Blocked: score {score} below required {rules['min_score']}.",
            "rules": rules,
        }

    if probability < rules["min_probability"]:
        return {
            "approved": False,
            "reason": f"Blocked: probability {probability} below required {rules['min_probability']}.",
            "rules": rules,
        }

    if risk_score > rules["max_risk_score"]:
        return {
            "approved": False,
            "reason": f"Blocked: risk score {risk_score} above max {rules['max_risk_score']}.",
            "rules": rules,
        }

    if cash - trade_size < reserve_cash:
        return {
            "approved": False,
            "reason": f"Blocked: cash reserve protected. Cash {cash}, reserve {reserve_cash}.",
            "rules": rules,
        }

    return {
        "approved": True,
        "reason": "Approved by risk manager.",
        "rules": rules,
    }