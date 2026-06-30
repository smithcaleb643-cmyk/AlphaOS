import threading
import time
from datetime import datetime

from core.alpha_brain import score_coin
from core.adaptive_learning import apply_learning_to_signal
from core.paper_trader import get_paper_state
from core.trade_manager import update_open_trades
from core.paper_broker import paper_broker
from core.risk_manager import approve_trade
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
    return sorted(
        opportunities,
        key=lambda item: (
            float(item.get("score") or 0),
            float(item.get("probability") or 0),
            -float(item.get("risk_score") or 0),
        ),
        reverse=True,
    )


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

    scanner_price_lookup = {}
    opportunities = []
    trades_created = 0
    trades_blocked = 0
    blocked_reasons = []

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

    ranked = rank_opportunities(opportunities)

    for opportunity in ranked:
        state = get_paper_state()
        approval = approve_trade(opportunity, state)

        opportunity["risk_approval"] = approval

        if not approval.get("approved"):
            trades_blocked += 1

            if len(blocked_reasons) < 10:
                blocked_reasons.append(
                    {
                        "coin": opportunity.get("symbol") or opportunity.get("coin_name"),
                        "score": opportunity.get("score"),
                        "reason": approval.get("reason"),
                    }
                )

            continue

        response = paper_broker.buy(opportunity)

        if response.get("ok"):
            trades_created += 1
        else:
            trades_blocked += 1

            if len(blocked_reasons) < 10:
                blocked_reasons.append(
                    {
                        "coin": opportunity.get("symbol") or opportunity.get("coin_name"),
                        "score": opportunity.get("score"),
                        "reason": response.get("message"),
                    }
                )

    if scanner_price_lookup:
        update_open_trades(scanner_price_lookup)

    engine_state["last_scan_count"] = len(coins)
    engine_state["last_trades_created"] = trades_created
    engine_state["last_trades_blocked"] = trades_blocked
    engine_state["last_blocked_reasons"] = blocked_reasons
    engine_state["last_discovery_scan_at"] = now_iso()
    engine_state["message"] = "Alpha Engine running"

    return {
        "coins": coins,
        "trades_created": trades_created,
        "trades_blocked": trades_blocked,
        "skipped": False,
        "reason": None,
    }


def update_scheduler_state(last_price_refresh, last_discovery_scan):
    current = time.time()

    engine_state["next_price_refresh_in"] = max(
        0,
        int(PRICE_REFRESH_SECONDS - (current - last_price_refresh)),
    )

    if discovery_is_in_cooldown():
        engine_state["next_discovery_scan_in"] = engine_state["discovery_cooldown_remaining"]
    else:
        engine_state["next_discovery_scan_in"] = max(
            0,
            int(DISCOVERY_SCAN_SECONDS - (current - last_discovery_scan)),
        )


def alpha_engine_loop():
    last_price_refresh = 0
    last_discovery_scan = 0

    while engine_state["running"]:
        try:
            current = time.time()

            if current - last_price_refresh >= PRICE_REFRESH_SECONDS:
                refresh_open_trade_prices()
                last_price_refresh = current

            if current - last_discovery_scan >= DISCOVERY_SCAN_SECONDS:
                run_discovery_scan()
                last_discovery_scan = current

            engine_state["cycles"] += 1
            update_scheduler_state(last_price_refresh, last_discovery_scan)

            if not discovery_is_in_cooldown():
                engine_state["message"] = "Alpha Engine running"

        except Exception as error:
            print("ENGINE ERROR:", error)

            if is_rate_limit_error(error):
                start_discovery_cooldown("rate limit")
            else:
                engine_state["message"] = f"Engine error: {error}"

        time.sleep(1)


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