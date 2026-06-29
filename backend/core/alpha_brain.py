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