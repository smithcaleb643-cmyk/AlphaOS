import threading
import time
from datetime import datetime
from core.control_brain import control_brain

from core.alpha_brain import score_coin
from core.adaptive_learning import apply_learning_to_signal
from core.paper_trader import get_paper_state
from core.trade_manager import update_open_trades

from services.market_service import scan_live_market, get_market_summary


PRICE_REFRESH_SECONDS = 5
DISCOVERY_SCAN_SECONDS = 45
RATE_LIMIT_COOLDOWN_SECONDS = 60
DISCOVERY_LIMIT = 100

engine_state = {
    "running": False,
    "last_scan_count": 0,
    "last_trades_created": 0,
    "last_trades_blocked": 0,
    "last_prices_updated": 0,
    "cycles": 0,
    "message": "Alpha Engine idle",

    "last_price_refresh_at": None,
    "last_discovery_scan_at": None,
    "next_price_refresh_in": 0,
    "next_discovery_scan_in": 0,

    "discovery_cooldown_until": 0,
    "discovery_cooldown_remaining": 0,
    "rate_limit_events": 0,

    "price_refresh_seconds": PRICE_REFRESH_SECONDS,
    "discovery_scan_seconds": DISCOVERY_SCAN_SECONDS,

    "last_blocked_reasons": [],
    "last_ranked_opportunities": [],
    "last_best_opportunity": None,
    "execution_layer": "Execution Manager",
}

price_cache = {}
price_cache_ttl_seconds = 10


def now_iso():
    return datetime.utcnow().isoformat()


def seconds_until(timestamp):
    return max(0, int(float(timestamp or 0) - time.time()))


def is_rate_limit_error(error):
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text


def get_cached_token_price(token):
    cached = price_cache.get(token)
    if not cached:
        return None

    age = time.time() - cached.get("timestamp", 0)
    if age > price_cache_ttl_seconds:
        return None

    return cached.get("price")


def set_cached_token_price(token, price, source="DexScreener"):
    price_cache[token] = {
        "price": float(price),
        "source": source,
        "timestamp": time.time(),
        "updated_at": now_iso(),
    }


def unique_open_trade_tokens():
    state = get_paper_state()
    open_trades = state.get("open_trades", [])
    seen = set()
    tokens = []

    for trade in open_trades:
        token = trade.get("token_address")
        if not token or token in seen:
            continue

        seen.add(token)
        tokens.append(token)

    return tokens


def fetch_token_price(token):
    cached = get_cached_token_price(token)
    if cached:
        return cached

    summary = get_market_summary(token)

    if not summary.get("found"):
        return None

    price = float(summary.get("price_usd") or 0)

    if price <= 0:
        return None

    set_cached_token_price(token, price)
    return price


def build_open_trade_price_lookup():
    price_lookup = {}

    for token in unique_open_trade_tokens():
        try:
            price = fetch_token_price(token)

            if price and price > 0:
                price_lookup[token] = price

        except Exception as error:
            if is_rate_limit_error(error):
                engine_state["rate_limit_events"] += 1
                engine_state["message"] = "Rate limit during price refresh. Alpha is still running."
                print("PRICE REFRESH RATE LIMITED:", token, error)
                break

            print("OPEN TRADE PRICE REFRESH FAILED:", token, error)

    return price_lookup


def refresh_open_trade_prices():
    price_lookup = build_open_trade_price_lookup()

    if price_lookup:
        update_open_trades(price_lookup)

    engine_state["last_prices_updated"] = len(price_lookup)
    engine_state["last_price_refresh_at"] = now_iso()

    return price_lookup


def discovery_is_in_cooldown():
    remaining = seconds_until(engine_state.get("discovery_cooldown_until", 0))
    engine_state["discovery_cooldown_remaining"] = remaining
    return remaining > 0


def start_discovery_cooldown(reason="rate limit"):
    engine_state["discovery_cooldown_until"] = time.time() + RATE_LIMIT_COOLDOWN_SECONDS
    engine_state["discovery_cooldown_remaining"] = RATE_LIMIT_COOLDOWN_SECONDS
    engine_state["rate_limit_events"] += 1
    engine_state["message"] = f"Discovery paused for {RATE_LIMIT_COOLDOWN_SECONDS}s because of {reason}."


def rank_opportunities(opportunities):
    ranked = sorted(
        opportunities,
        key=lambda item: (
            float(item.get("score") or 0),
            float(item.get("probability") or 0),
            -float(item.get("risk_score") or 0),
        ),
        reverse=True,
    )

    engine_state["last_ranked_opportunities"] = [
        {
            "coin": item.get("symbol") or item.get("coin_name"),
            "score": item.get("score"),
            "probability": item.get("probability"),
            "risk_score": item.get("risk_score"),
            "wallet_adjustment": item.get("wallet_adjustment", 0),
        }
        for item in ranked[:10]
    ]

    return ranked


def build_opportunities_from_scan(coins):
    opportunities = []
    scanner_price_lookup = {}

    for coin in coins:
        token = coin.get("token_address")
        price = float(coin.get("price_usd") or 0)

        if token and price > 0:
            scanner_price_lookup[token] = price
            set_cached_token_price(token, price)

        if not token or price <= 0:
            continue

        result = score_coin(coin)
        result = apply_learning_to_signal(result)

        opportunities.append(
            {
                **coin,
                **result,
                "token_address": token,
                "price_usd": price,
            }
        )

    return opportunities, scanner_price_lookup


from core.control_brain import control_brain

def try_execute_opportunity(opportunity):

    signal = {
        "token_address": opportunity.get("token_address"),
        "score": opportunity.get("score"),
        "risk_score": opportunity.get("risk_score"),
        "probability": opportunity.get("probability"),
        "price_usd": opportunity.get("price_usd"),
        "symbol": opportunity.get("symbol") or opportunity.get("coin_name"),
    }

    result = control_brain.execute(signal)

    return result



def get_ranked_live_opportunities(limit=DISCOVERY_LIMIT):
    """
    Shared live opportunity pipeline.

    This uses the same scanner, Alpha Brain scoring, learning adjustments,
    and ranking logic as the paper Alpha Engine, but does not execute trades.
    Live Alpha can use this to make decisions without duplicating brain logic.
    """
    if discovery_is_in_cooldown():
        return {
            "ok": False,
            "reason": "cooldown",
            "coins": [],
            "opportunities": [],
            "ranked": [],
        }

    try:
        coins = scan_live_market(limit=limit)
    except Exception as error:
        if is_rate_limit_error(error):
            print("LIVE OPPORTUNITY SCAN RATE LIMITED:", error)
            start_discovery_cooldown("DexScreener 429")
            return {
                "ok": False,
                "reason": "rate_limit",
                "coins": [],
                "opportunities": [],
                "ranked": [],
                "error": str(error),
            }

        return {
            "ok": False,
            "reason": "scan_error",
            "coins": [],
            "opportunities": [],
            "ranked": [],
            "error": str(error),
        }

    opportunities, scanner_price_lookup = build_opportunities_from_scan(coins)
    ranked = rank_opportunities(opportunities)

    if scanner_price_lookup:
        update_open_trades(scanner_price_lookup)

    engine_state["last_scan_count"] = len(coins)
    engine_state["last_ranked_opportunities"] = [
        {
            "coin": item.get("symbol") or item.get("coin_name"),
            "score": item.get("score"),
            "probability": item.get("probability"),
            "risk_score": item.get("risk_score"),
            "action": item.get("action"),
        }
        for item in ranked[:10]
    ]
    engine_state["last_discovery_scan_at"] = now_iso()

    return {
        "ok": True,
        "reason": None,
        "coins": coins,
        "opportunities": opportunities,
        "ranked": ranked,
    }


def get_best_live_opportunity(minimum_score=70, limit=10):
    """
    Returns the best BUY opportunity above minimum_score.
    Does not execute a trade.
    """
    scan = get_ranked_live_opportunities(limit=limit)

    if not scan.get("ok"):
        return {
            "ok": False,
            "reason": scan.get("reason"),
            "error": scan.get("error"),
            "opportunity": None,
        }

    for opportunity in scan.get("ranked", []):
        score = int(opportunity.get("score") or 0)
        action = opportunity.get("action")

        if action in ["BUY", "WATCH"] and score >= int(minimum_score):
            engine_state["last_best_opportunity"] = {
                "coin": opportunity.get("symbol") or opportunity.get("coin_name"),
                "score": opportunity.get("score"),
                "probability": opportunity.get("probability"),
                "risk_score": opportunity.get("risk_score"),
                "action": opportunity.get("action"),
                "token_address": opportunity.get("token_address"),
                "reason": opportunity.get("reason"),
            }

            return {
                "ok": True,
                "reason": "best_candidate_found",
                "opportunity": opportunity,
            }

    engine_state["last_best_opportunity"] = None

    return {
        "ok": False,
        "reason": "no_buy_candidate",
        "opportunity": None,
    }


def run_discovery_scan():
    if discovery_is_in_cooldown():
        return {"coins": [], "trades_created": 0, "skipped": True, "reason": "cooldown"}

    try:
        coins = scan_live_market(limit=DISCOVERY_LIMIT)
    except Exception as error:
        if is_rate_limit_error(error):
            print("DISCOVERY RATE LIMITED:", error)
            start_discovery_cooldown("DexScreener 429")
            return {"coins": [], "trades_created": 0, "skipped": True, "reason": "rate_limit"}

        raise

    opportunities, scanner_price_lookup = build_opportunities_from_scan(coins)
    ranked = rank_opportunities(opportunities)

    trades_created = 0
    trades_blocked = 0
    blocked_reasons = []

    for opportunity in ranked:
        result = try_execute_opportunity(opportunity)

        if result.get("ok"):
            trades_created += 1
        else:
            trades_blocked += 1

            if len(blocked_reasons) < 10:
                blocked_reasons.append({
                    "coin": result.get("signal", {}).get("symbol"),
                    "score": result.get("signal", {}).get("score"),
                    "reason": result.get("reason"),
                })

    if scanner_price_lookup:
        update_open_trades(scanner_price_lookup)

    engine_state["last_scan_count"] = len(coins)
    engine_state["last_trades_created"] = trades_created
    engine_state["last_trades_blocked"] = trades_blocked
    engine_state["last_blocked_reasons"] = blocked_reasons
    engine_state["last_discovery_scan_at"] = now_iso()

    return {
        "coins": coins,
        "trades_created": trades_created,
        "trades_blocked": trades_blocked,
        "skipped": False,
        "reason": None,
    }


def alpha_engine_loop():

    last_price_refresh = time.time()
    last_discovery_scan = time.time()

    while engine_state["running"]:

        try:
            print("🧠 ENGINE LOOP ACTIVE - cycle", engine_state["cycles"])

            current = time.time()

            if current - last_price_refresh >= PRICE_REFRESH_SECONDS:
                refresh_open_trade_prices()
                last_price_refresh = current

            if current - last_discovery_scan >= DISCOVERY_SCAN_SECONDS:
                run_discovery_scan()
                last_discovery_scan = current

            engine_state["cycles"] += 1
            

            if not discovery_is_in_cooldown():
                engine_state["message"] = "Alpha Engine running"

        except Exception as error:
            print("ENGINE ERROR:", error)

        time.sleep(1.5)


def start_alpha_engine():
    if engine_state["running"]:
        return engine_state

    engine_state["running"] = True
    engine_state["message"] = "Alpha Engine started"

    thread = threading.Thread(target=alpha_engine_loop, daemon=True)
    thread.start()

    return engine_state


def stop_alpha_engine():
    engine_state["running"] = False
    engine_state["message"] = "Alpha Engine stopped"
    return engine_state


def get_alpha_engine_state():
    return engine_state
