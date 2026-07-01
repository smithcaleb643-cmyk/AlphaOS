import threading
import time

from core.live_alpha_controller import LIVE_ALPHA_STATE, stop_live_alpha
from core.live_portfolio import get_live_portfolio
from core.live_trade_executor import execute_live_buy
from core.alpha_engine import get_best_live_opportunity
from core.live_position_manager import manage_open_positions
from core.live_mock_executor import execute_mock_buy

_loop_thread = None
_last_buy_time = 0


def already_holding_token(portfolio, token_address):
    if not token_address:
        return False

    for token in portfolio.get("tokens", []):
        mint = token.get("mint") or token.get("token_address")
        amount = float(token.get("amount") or token.get("balance") or 0)

        if mint == token_address and amount > 0:
            return True

    return False


def _alpha_loop():
    global _last_buy_time

    while LIVE_ALPHA_STATE["running"]:
        try:
            portfolio = get_live_portfolio()

            LIVE_ALPHA_STATE["last_action"] = "Checking open positions..."

            try:
                position_result = manage_open_positions()

                if position_result.get("actions"):
                    LIVE_ALPHA_STATE["last_action"] = (
                        f"Position manager: {position_result['actions'][-1].get('reason')}"
                    )

            except Exception as error:
                LIVE_ALPHA_STATE["last_action"] = f"Position manager error: {error}"

            # Safety 1: daily loss limit
            if portfolio.get("today_pnl_usd", 0) <= -LIVE_ALPHA_STATE["max_daily_loss_usd"]:
                LIVE_ALPHA_STATE["last_action"] = "Daily loss limit reached. Stopping."
                stop_live_alpha()
                break

            # Safety 2: max open positions
            if portfolio.get("open_positions", 0) >= LIVE_ALPHA_STATE["max_open_positions"]:
                LIVE_ALPHA_STATE["last_action"] = "Waiting: max positions reached."
                time.sleep(5)
                continue

            LIVE_ALPHA_STATE["scans_today"] += 1
            LIVE_ALPHA_STATE["last_action"] = "Live scan started..."

            best = get_best_live_opportunity(
                minimum_score=LIVE_ALPHA_STATE["minimum_score"],
                limit=10,
            )

            LIVE_ALPHA_STATE["last_action"] = "Live scan finished. Evaluating candidate..."

            if not best.get("ok"):
                LIVE_ALPHA_STATE["last_action"] = (
                    f"No BUY candidate above score "
                    f"{LIVE_ALPHA_STATE['minimum_score']} ({best.get('reason')})."
                )
                time.sleep(5)
                continue

            candidate = best.get("opportunity") or {}

            name = (
    candidate.get("coin_name")
    or candidate.get("symbol")
    or candidate.get("name")
    or candidate.get("token_address")
    or "UNKNOWN"
)
            score = int(candidate.get("score") or 0)
            probability = candidate.get("probability", 0)
            risk_score = candidate.get("risk_score", 0)
            token_address = candidate.get("token_address")
            reason = candidate.get("reason", "")

            if not token_address:
                LIVE_ALPHA_STATE["last_action"] = f"Cannot buy {name}: missing token address."
                time.sleep(10)
                continue

            if already_holding_token(portfolio, token_address):
                LIVE_ALPHA_STATE["last_action"] = f"Skipping {name}: already holding token."
                time.sleep(10)
                continue

            now = time.time()
            remaining = LIVE_ALPHA_STATE["buy_cooldown_seconds"] - (now - _last_buy_time)

            if remaining > 0:
                LIVE_ALPHA_STATE["last_action"] = (
                    f"Cooldown {int(remaining)}s remaining before next buy."
                )
                time.sleep(3)
                continue

            if not LIVE_ALPHA_STATE["auto_buy_enabled"]:
                LIVE_ALPHA_STATE["last_action"] = (
                    f"WOULD BUY {name} "
                    f"(score {score}, prob {probability}%, risk {risk_score}) "
                    f"(${LIVE_ALPHA_STATE['trade_size_usd']}) "
                    f"(Auto Buy OFF) — {reason[:120]}"
                )
                time.sleep(5)
                continue

            LIVE_ALPHA_STATE["last_action"] = (
                f"Executing {LIVE_ALPHA_STATE['execution_mode']} trade..."
            )

            payload = {
                "coin_name": name,
                "symbol": name,
                "token_address": token_address,
                "score": score,
                "probability": probability,
                "risk_score": risk_score,
                "reason": reason,
                "usd_amount": LIVE_ALPHA_STATE["trade_size_usd"],
                "price_usd": candidate.get("price_usd"),
            }

            if LIVE_ALPHA_STATE["execution_mode"] == "MOCK":
                result = execute_mock_buy(payload)
            else:
                result = execute_live_buy({
                    **payload,
                    "sol_amount": 0.005,
                    "slippage_bps": 100,
                })

            _last_buy_time = time.time()

            if result.get("ok"):
                LIVE_ALPHA_STATE["trades_today"] += 1
                LIVE_ALPHA_STATE["last_action"] = (
                    f"{LIVE_ALPHA_STATE['execution_mode']} BUY: {name}"
                )
            else:
                LIVE_ALPHA_STATE["last_action"] = (
                    f"Trade failed: {result.get('error', result.get('message'))}"
                )

            time.sleep(5)

        except Exception as error:
            LIVE_ALPHA_STATE["last_action"] = f"Loop error: {error}"
            time.sleep(5)


def launch_live_alpha():
    global _loop_thread

    if _loop_thread and _loop_thread.is_alive():
        return

    _loop_thread = threading.Thread(target=_alpha_loop, daemon=True)
    _loop_thread.start()
