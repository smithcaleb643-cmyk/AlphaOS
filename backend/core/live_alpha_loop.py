import threading
import time

from core.live_alpha_controller import LIVE_ALPHA_STATE, stop_live_alpha
from core.live_portfolio import get_live_portfolio
from core.live_execution.executor import execute_live_buy
from core.alpha_brain import rank_candidates
from core.alpha_engine import get_ranked_live_opportunities
from core.live_position_manager import manage_open_positions
from core.live_mock_executor import execute_mock_buy
from core.paper_trader import get_paper_state
from core.risk_manager import approve_trade

_loop_thread = None
_last_buy_time = 0
_last_scan_time = 0
_scan_backoff_until = 0

EXIT_CHECK_SECONDS = 1
SCAN_CHECK_SECONDS = 20
SCAN_ERROR_BACKOFF_SECONDS = 45
POST_BUY_PAUSE_SECONDS = 5


def coin_name(candidate):
    return (
        candidate.get("coin_name")
        or candidate.get("symbol")
        or candidate.get("name")
        or candidate.get("token_address")
        or "UNKNOWN"
    )


def execute_candidate(candidate):
    name = coin_name(candidate)

    if LIVE_ALPHA_STATE["execution_mode"] == "MOCK":
        return execute_mock_buy({
            "coin_name": name,
            "symbol": name,
            "token_address": candidate.get("token_address"),
            "score": int(candidate.get("score") or 0),
            "probability": candidate.get("probability", 0),
            "risk_score": candidate.get("risk_score", 0),
            "reason": candidate.get("reason", ""),
            "usd_amount": LIVE_ALPHA_STATE["trade_size_usd"],
            "price_usd": candidate.get("price_usd"),
        })

    return execute_live_buy({
        "token_address": candidate.get("token_address"),
        "trade_size_usd": LIVE_ALPHA_STATE["trade_size_usd"],
        "slippage_bps": 300,
        "coin_name": name,
        "symbol": name,
        "score": int(candidate.get("score") or 0),
        "probability": candidate.get("probability", 0),
        "risk_score": candidate.get("risk_score", 0),
        "reason": candidate.get("reason", ""),
        "price_usd": candidate.get("price_usd"),
    })


def exit_failure_detected(position_result):
    for action in position_result.get("actions", []):
        result = action.get("result") or {}

        if action.get("action") in ["EXIT_BLOCKED", "SELL_FAILED"]:
            return True, action

        if action.get("action") == "SELL" and result.get("ok") is False:
            return True, action

    return False, None


def build_live_risk_state(portfolio):
    paper_state = get_paper_state()
    paper_settings = dict(paper_state.get("settings", {}))

    starting_cash = float(paper_settings.get("starting_cash") or 10000)
    trade_size = float(paper_settings.get("trade_size") or LIVE_ALPHA_STATE["trade_size_usd"])

    return {
        "cash": starting_cash,
        "open_trades": portfolio.get("positions", []),
        "settings": {
            **paper_settings,
            "starting_cash": starting_cash,
            "trade_size": trade_size,
        },
    }


def is_rate_limit_error(scan_or_result):
    text = str(scan_or_result).lower()
    return (
        "429" in text
        or "too many requests" in text
        or "rate limit" in text
        or "ratelimit" in text
    )


def _alpha_loop():
    global _last_buy_time, _last_scan_time, _scan_backoff_until

    while LIVE_ALPHA_STATE["running"]:
        try:
            # ================================
            # FAST LANE: EXITS ALWAYS FIRST
            # ================================
            LIVE_ALPHA_STATE["last_action"] = "Fast exit check..."

            position_result = manage_open_positions()
            failed_exit, failed_action = exit_failure_detected(position_result)

            if failed_exit:
                LIVE_ALPHA_STATE["auto_buy_enabled"] = False
                LIVE_ALPHA_STATE["running"] = False
                LIVE_ALPHA_STATE["last_action"] = (
                    f"🚨 EXIT FAILURE: {failed_action.get('symbol')} — "
                    f"{failed_action.get('reason')}. Auto Buy disabled."
                )
                break

            if position_result.get("actions"):
                last = position_result["actions"][-1]
                LIVE_ALPHA_STATE["last_action"] = (
                    f"Exit manager: {last.get('action')} — {last.get('reason')}"
                )

            portfolio = get_live_portfolio()

            if portfolio.get("today_pnl_usd", 0) <= -LIVE_ALPHA_STATE["max_daily_loss_usd"]:
                LIVE_ALPHA_STATE["auto_buy_enabled"] = False
                LIVE_ALPHA_STATE["last_action"] = "Daily loss limit reached. Stopping."
                stop_live_alpha()
                break

            # ================================
            # SLOW LANE: SCANS / NEW BUYS ONLY
            # ================================
            now = time.time()

            if now < _scan_backoff_until:
                wait_left = int(_scan_backoff_until - now)
                LIVE_ALPHA_STATE["last_action"] = (
                    f"Exit checks live. Scan backoff {wait_left}s."
                )
                time.sleep(EXIT_CHECK_SECONDS)
                continue

            if now - _last_scan_time < SCAN_CHECK_SECONDS:
                time.sleep(EXIT_CHECK_SECONDS)
                continue

            _last_scan_time = now

            open_positions = int(portfolio.get("open_positions") or 0)
            max_positions = int(LIVE_ALPHA_STATE["max_open_positions"])

            if open_positions >= max_positions:
                LIVE_ALPHA_STATE["last_action"] = "Exit checks live. Max positions reached."
                time.sleep(EXIT_CHECK_SECONDS)
                continue

            remaining = LIVE_ALPHA_STATE["buy_cooldown_seconds"] - (now - _last_buy_time)

            if remaining > 0:
                LIVE_ALPHA_STATE["last_action"] = (
                    f"Exit checks live. Buy cooldown {int(remaining)}s."
                )
                time.sleep(EXIT_CHECK_SECONDS)
                continue

            if not LIVE_ALPHA_STATE["auto_buy_enabled"]:
                LIVE_ALPHA_STATE["last_action"] = "Exit checks live. Auto Buy OFF."
                time.sleep(EXIT_CHECK_SECONDS)
                continue

            LIVE_ALPHA_STATE["scans_today"] += 1
            LIVE_ALPHA_STATE["last_action"] = "Scanning for new entries..."

            scan = get_ranked_live_opportunities(limit=20)

            if is_rate_limit_error(scan):
                _scan_backoff_until = time.time() + SCAN_ERROR_BACKOFF_SECONDS
                LIVE_ALPHA_STATE["last_action"] = (
                    f"Rate limited. Exits still live. Pausing scans {SCAN_ERROR_BACKOFF_SECONDS}s."
                )
                time.sleep(EXIT_CHECK_SECONDS)
                continue

            if not scan.get("ok"):
                LIVE_ALPHA_STATE["last_action"] = f"Scan skipped: {scan.get('reason')}"
                time.sleep(EXIT_CHECK_SECONDS)
                continue

            ranked = rank_candidates(scan.get("ranked", []))

            held_tokens = {
                p.get("mint")
                for p in portfolio.get("positions", [])
                if p.get("mint")
            }

            risk_state = build_live_risk_state(portfolio)

            slots_left = max_positions - open_positions
            bought = 0
            skipped = 0
            blocked = 0
            last_reason = None

            for candidate in ranked:
                if slots_left <= 0:
                    break

                token_address = candidate.get("token_address")
                name = coin_name(candidate)
                action = candidate.get("action")

                if not token_address:
                    skipped += 1
                    last_reason = "Missing token address"
                    continue

                if token_address in held_tokens:
                    skipped += 1
                    last_reason = f"Already holding {name}"
                    continue

                if action != "BUY":
                    skipped += 1
                    last_reason = f"Action not BUY: {action}"
                    continue

                score = int(candidate.get("score") or 0)
                minimum_score = int(LIVE_ALPHA_STATE.get("minimum_score") or 70)

                if score < minimum_score:
                    skipped += 1
                    last_reason = f"Score {score} below live minimum {minimum_score}"
                    continue

                approval = approve_trade(candidate, risk_state)
                candidate["risk_approval"] = approval

                if not approval.get("approved"):
                    blocked += 1
                    last_reason = approval.get("reason")
                    continue

                LIVE_ALPHA_STATE["last_action"] = f"Buying {name}..."

                result = execute_candidate(candidate)

                if is_rate_limit_error(result):
                    _scan_backoff_until = time.time() + SCAN_ERROR_BACKOFF_SECONDS
                    LIVE_ALPHA_STATE["last_action"] = (
                        f"Buy rate limited. Exits still live. Pausing scans {SCAN_ERROR_BACKOFF_SECONDS}s."
                    )
                    break

                if result.get("ok"):
                    _last_buy_time = time.time()
                    bought += 1
                    slots_left -= 1
                    held_tokens.add(token_address)
                    LIVE_ALPHA_STATE["trades_today"] += 1
                    LIVE_ALPHA_STATE["last_action"] = f"LIVE BUY: {name}"
                    time.sleep(POST_BUY_PAUSE_SECONDS)
                else:
                    blocked += 1
                    last_reason = result.get("error") or result.get("message")
                    LIVE_ALPHA_STATE["last_action"] = (
                        f"BUY FAILED {name}: "
                        f"{result.get('stage')} | "
                        f"{result.get('error')} | "
                        f"{result.get('message')}"
                    )

            if bought == 0:
                sample = ranked[0] if ranked else {}
                LIVE_ALPHA_STATE["last_action"] = (
                    f"No buys. ranked={len(ranked)}, blocked={blocked}, skipped={skipped}, "
                    f"top={coin_name(sample)}, action={sample.get('action')}, "
                    f"score={sample.get('score')}, reason={last_reason}"
                )

            time.sleep(EXIT_CHECK_SECONDS)

        except Exception as error:
            LIVE_ALPHA_STATE["auto_buy_enabled"] = False
            LIVE_ALPHA_STATE["running"] = False
            LIVE_ALPHA_STATE["last_action"] = f"🚨 Live loop crash: {error}"
            time.sleep(2)


def launch_live_alpha():
    global _loop_thread

    if _loop_thread and _loop_thread.is_alive():
        return

    _loop_thread = threading.Thread(target=_alpha_loop, daemon=True)
    _loop_thread.start()