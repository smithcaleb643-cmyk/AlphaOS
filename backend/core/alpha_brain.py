from datetime import datetime

TP1_PERCENT = 6
TP2_PERCENT = 12
TP3_PERCENT = 24

TP_SELL_FRACTION = 0.25
BASE_STOP_LOSS_MULTIPLIER = 0.90
BREAKEVEN_MULTIPLIER = 1.00
LOCKED_PROFIT_MULTIPLIER = 1.05
TRAILING_STOP_MULTIPLIER = 0.90
MAX_HOLD_MINUTES = 45


def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


def minutes_held(value):
    try:
        if not value:
            return 0
        started = datetime.fromisoformat(value)
        return (datetime.utcnow() - started).total_seconds() / 60
    except Exception:
        return 0


def score_coin(coin):
    liquidity = float(coin.get("liquidity", 0) or 0)
    volume = float(coin.get("volume", 0) or 0)
    market_cap = float(coin.get("market_cap", 0) or 0)
    holders = coin.get("holders", None)
    age_minutes = float(coin.get("age_minutes", 0) or 0)
    price_change = float(coin.get("price_change", 0) or 0)

    score = 0
    risk = 0
    reasons = []

    if liquidity >= 100000:
        score += 30
        reasons.append("Strong liquidity")
    elif liquidity >= 25000:
        score += 18
        reasons.append("Acceptable liquidity")
    elif liquidity >= 10000:
        score += 8
        risk += 10
        reasons.append("Thin liquidity")
    else:
        risk += 30
        reasons.append("Very low liquidity")

    if volume >= 500000:
        score += 30
        reasons.append("Strong volume")
    elif volume >= 75000:
        score += 18
        reasons.append("Volume is active")
    elif volume >= 15000:
        score += 8
        reasons.append("Some volume")
    else:
        risk += 20
        reasons.append("Weak volume")

    if 8 <= price_change <= 75:
        score += 22
        reasons.append("Healthy momentum")
    elif -8 <= price_change < 8:
        score += 8
        reasons.append("Momentum is neutral")
    elif price_change > 120:
        risk += 25
        reasons.append("Price may already be overextended")
    elif price_change < -20:
        risk += 25
        reasons.append("Price is breaking down")

    if 50000 <= market_cap <= 30000000:
        score += 15
        reasons.append("Market cap is tradable")
    elif market_cap > 30000000:
        score += 5
        reasons.append("Large market cap")
    else:
        risk += 8
        reasons.append("Market cap is very small or missing")

    if age_minutes >= 30:
        score += 10
        reasons.append("Not extremely new")
    elif age_minutes >= 10:
        score += 4
        risk += 5
        reasons.append("Still early")
    else:
        risk += 12
        reasons.append("Very new launch risk")

    if holders is None or holders == 0:
        reasons.append("Holder data unavailable")
    else:
        holders = float(holders)
        if holders >= 100:
            score += 8
            reasons.append("Decent holder base")
        elif holders >= 25:
            score += 3
            reasons.append("Small holder base")
        else:
            risk += 12
            reasons.append("Very low holder count")

    score = max(0, min(100, score - int(risk * 0.25)))
    risk = max(0, min(100, risk))
    probability = max(0, min(100, score + 8 - int(risk * 0.5)))

    if score >= 70 and risk <= 45:
        action = "BUY"
        status = "watching"
    elif score >= 30:
        action = "WATCH"
        status = "watching"
    else:
        action = "REJECT"
        status = "rejected"

    return {
        "coin_name": coin.get("coin_name", "Unknown"),
        "symbol": coin.get("symbol", coin.get("coin_name", "Unknown")),
        "score": score,
        "action": action,
        "probability": probability,
        "risk_score": risk,
        "status": status,
        "liquidity": liquidity,
        "volume": volume,
        "market_cap": market_cap,
        "holders": holders if holders else None,
        "age_minutes": age_minutes,
        "price_change": price_change,
        "token_address": coin.get("token_address"),
        "pair_address": coin.get("pair_address"),
        "dex_url": coin.get("dex_url"),
        "reason": ", ".join(reasons) + ".",
    }


def rank_candidates(candidates):
    return sorted(
        candidates,
        key=lambda item: (
            safe_float(item.get("score")),
            safe_float(item.get("probability")),
            -safe_float(item.get("risk_score")),
        ),
        reverse=True,
    )


def evaluate_exit_decision(position):
    entry = safe_float(position.get("entry_price"))
    current = safe_float(position.get("current_price"), entry)

    if entry <= 0 or current <= 0:
        return {
            "should_sell": False,
            "label": "HOLD",
            "updates": {},
            "message": "Holding. Missing valid entry/current price.",
        }

    pnl_percent = safe_float(position.get("pnl_percent"))
    if pnl_percent == 0:
        pnl_percent = ((current - entry) / entry) * 100

    old_highest = safe_float(position.get("highest_seen"), entry)
    highest_seen = max(old_highest, current)

    stop_loss = safe_float(
        position.get("stop_loss"),
        entry * BASE_STOP_LOSS_MULTIPLIER,
    )

    updates = {}

    if highest_seen > old_highest:
        updates["highest_seen"] = highest_seen

    if position.get("tp3_hit"):
        trailing_stop = highest_seen * TRAILING_STOP_MULTIPLIER
        if trailing_stop > stop_loss:
            stop_loss = trailing_stop
            updates["stop_loss"] = trailing_stop

    if pnl_percent <= -10:
        return {
            "should_sell": True,
            "label": "CLOSED_MAX_LOSS",
            "fraction": 1.0,
            "updates": updates,
            "urgent": True,
            "exit_price": current,
            "message": f"Max loss hit: {round(pnl_percent, 2)}%. Sell 100%.",
        }

    if current <= stop_loss:
        return {
            "should_sell": True,
            "label": "CLOSED_STOP",
            "fraction": 1.0,
            "updates": updates,
            "urgent": True,
            "exit_price": current,
            "message": f"Stop hit ({round(pnl_percent, 2)}%). Sell 100%.",
        }

    if not position.get("tp1_hit") and pnl_percent >= TP1_PERCENT:
        return {
            "should_sell": True,
            "label": "TP1_25_PERCENT",
            "fraction": TP_SELL_FRACTION,
            "updates": {
                **updates,
                "tp1_hit": True,
                "stop_loss": entry * BREAKEVEN_MULTIPLIER,
            },
            "message": f"TP1 hit: {round(pnl_percent, 2)}%. Sell 25%, stop to breakeven.",
        }

    if not position.get("tp2_hit") and pnl_percent >= TP2_PERCENT:
        return {
            "should_sell": True,
            "label": "TP2_25_PERCENT",
            "fraction": TP_SELL_FRACTION,
            "updates": {
                **updates,
                "tp2_hit": True,
                "runner_mode": True,
                "stop_loss": entry * LOCKED_PROFIT_MULTIPLIER,
            },
            "message": f"TP2 hit: {round(pnl_percent, 2)}%. Sell 25%, lock +5%.",
        }

    if not position.get("tp3_hit") and pnl_percent >= TP3_PERCENT:
        return {
            "should_sell": True,
            "label": "TP3_25_PERCENT",
            "fraction": TP_SELL_FRACTION,
            "updates": {
                **updates,
                "tp3_hit": True,
                "runner_mode": True,
                "stop_loss": highest_seen * TRAILING_STOP_MULTIPLIER,
                "highest_seen": highest_seen,
            },
            "message": f"TP3 hit: {round(pnl_percent, 2)}%. Sell 25%, trail runner.",
        }

    held = minutes_held(position.get("entry_time") or position.get("opened_at"))
    if held >= MAX_HOLD_MINUTES:
        return {
            "should_sell": True,
            "label": "MAX_HOLD_TIME",
            "fraction": 1.0,
            "updates": updates,
            "exit_price": current,
            "message": f"Max hold reached: {round(held, 1)} min.",
        }

    return {
        "should_sell": False,
        "label": "HOLD",
        "updates": updates,
        "message": f"Holding. P&L {round(pnl_percent, 2)}%.",
    }