import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.price_audit import log_price_event

DEX_TOKEN_PAIRS = "https://api.dexscreener.com/token-pairs/v1/solana"
DEX_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"

_session = requests.Session()

_pair_cache = {}
_profiles_cache = {
    "time": 0,
    "data": [],
}

PAIR_CACHE_SECONDS = 8
PROFILE_CACHE_SECONDS = 12
MAX_SCAN_WORKERS = 10


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _cache_get(cache, key, max_age):
    item = cache.get(key)
    if not item:
        return None

    created_at, data = item
    if time.time() - created_at > max_age:
        cache.pop(key, None)
        return None

    return data


def _cache_set(cache, key, data):
    cache[key] = (time.time(), data)


def get_token_pairs(token_address, use_cache=True):
    if use_cache:
        cached = _cache_get(_pair_cache, token_address, PAIR_CACHE_SECONDS)
        if cached is not None:
            return cached

    response = _session.get(f"{DEX_TOKEN_PAIRS}/{token_address}", timeout=8)
    response.raise_for_status()
    data = response.json()

    _cache_set(_pair_cache, token_address, data)
    return data


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


def audit_market_summary(summary, source="market_summary"):
    try:
        if summary.get("found"):
            log_price_event({
                "source": source,
                "token_address": summary.get("token_address"),
                "symbol": summary.get("symbol"),
                "price_usd": summary.get("price_usd"),
                "liquidity_usd": (summary.get("liquidity") or {}).get("usd", 0),
                "volume_h24": (summary.get("volume") or {}).get("h24", 0),
                "market_cap": summary.get("market_cap"),
                "dex": summary.get("dex"),
                "pair_address": summary.get("pair_address"),
            })
    except Exception as error:
        print("PRICE AUDIT LOG FAILED:", error)


def get_market_summary(token_address):
    pairs = get_token_pairs(token_address)

    if not pairs:
        return {"found": False, "message": "No pairs found"}

    best_pair = pairs[0]
    summary = normalize_pair(best_pair)
    audit_market_summary(summary, source="get_market_summary")
    return summary


def discover_solana_tokens(limit=10, use_cache=True):
    now = time.time()

    if (
        use_cache
        and _profiles_cache["data"]
        and now - _profiles_cache["time"] < PROFILE_CACHE_SECONDS
    ):
        return _profiles_cache["data"][:limit]

    response = _session.get(DEX_PROFILES, timeout=8)
    response.raise_for_status()

    profiles = response.json()
    solana_profiles = [
        item
        for item in profiles
        if item.get("chainId") == "solana" and item.get("tokenAddress")
    ]

    _profiles_cache["time"] = now
    _profiles_cache["data"] = solana_profiles

    return solana_profiles[:limit]


def _scan_one_profile(profile):
    token_address = profile.get("tokenAddress")

    if not token_address:
        return None

    try:
        pairs = get_token_pairs(token_address)

        if not pairs:
            return None

        best_pair = pairs[0]
        normalized = normalize_pair(best_pair)
        audit_market_summary(normalized, source="scan_live_market")

        return {
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

    except Exception as error:
        print("Failed live coin:", token_address, error)
        return None


def scan_live_market(limit=8):
    profiles = discover_solana_tokens(limit=limit)
    coins = []

    if not profiles:
        return coins

    workers = min(MAX_SCAN_WORKERS, max(1, len(profiles)))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_scan_one_profile, profile) for profile in profiles]

        for future in as_completed(futures):
            coin = future.result()
            if coin:
                coins.append(coin)

    return coins