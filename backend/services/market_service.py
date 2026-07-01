import requests

DEX_TOKEN_PAIRS = "https://api.dexscreener.com/token-pairs/v1/solana"
DEX_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"


def get_token_pairs(token_address):
    response = requests.get(f"{DEX_TOKEN_PAIRS}/{token_address}", timeout=10)
    response.raise_for_status()
    return response.json()


def get_market_summary(token_address):
    pairs = get_token_pairs(token_address)

    if not pairs:
        return {"found": False, "message": "No pairs found"}

    best_pair = pairs[0]
    return normalize_pair(best_pair)


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_pair(pair):
    base = pair.get("baseToken", {}) or {}
    quote = pair.get("quoteToken", {}) or {}

    liquidity = pair.get("liquidity") or {}
    volume = pair.get("volume") or {}
    price_change = pair.get("priceChange") or {}

    price_usd = safe_float(
        pair.get("priceUsd")
        or pair.get("price_usd")
        or pair.get("usdPrice")
        or pair.get("price")
    )

    return {
        "found": True,
        "chain": pair.get("chainId"),
        "dex": pair.get("dexId"),
        "pair_address": pair.get("pairAddress"),
        "token_address": base.get("address"),
        "coin_name": base.get("symbol") or base.get("name") or "Unknown",
        "symbol": base.get("symbol") or "Unknown",
        "base_token": base,
        "quote_token": quote,
        "price_usd": price_usd,
        "price_native": safe_float(pair.get("priceNative")),
        "price_change": price_change,
        "volume": volume,
        "liquidity": liquidity,
        "market_cap": pair.get("marketCap") or pair.get("fdv") or 0,
        "fdv": pair.get("fdv") or 0,
        "holders": pair.get("holders") or 0,
        "age_minutes": 60,
        "url": pair.get("url"),
    }


def discover_solana_tokens(limit=10):
    response = requests.get(DEX_PROFILES, timeout=10)
    response.raise_for_status()

    profiles = response.json()
    solana_profiles = [
        item
        for item in profiles
        if item.get("chainId") == "solana" and item.get("tokenAddress")
    ]

    return solana_profiles[:limit]


def scan_live_market(limit=8):
    profiles = discover_solana_tokens(limit=limit)
    coins = []

    for profile in profiles:
        token_address = profile.get("tokenAddress")

        try:
            pairs = get_token_pairs(token_address)

            if not pairs:
                continue

            best_pair = pairs[0]

            normalized = normalize_pair(best_pair)

            coin = {
                "coin_name": normalized["coin_name"],
                "symbol": normalized["symbol"],
                "token_address": normalized["token_address"],
                "pair_address": normalized["pair_address"],
                "dex_url": normalized["url"],
                "price_usd": normalized["price_usd"],
                "liquidity": normalized["liquidity"].get("usd", 0),
                "volume": normalized["volume"].get("h24", 0),
                "market_cap": normalized["market_cap"],
                "holders": normalized["holders"],
                "age_minutes": normalized["age_minutes"],
                "price_change": normalized["price_change"].get("h24", 0),
            }

            coins.append(coin)

        except Exception as error:
            print("Failed live coin:", token_address, error)

    return coins