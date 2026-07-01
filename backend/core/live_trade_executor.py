import time

from core.live_swap_builder import build_swap_transaction
from core.live_execution_safety import evaluate_swap_build
from core.live_transaction_signer import sign_swap_transaction
from core.live_transaction_sender import send_signed_transaction
from core.live_trade_journal import record_live_buy
from core.live_wallet_reader import live_wallet_status
from services.market_service import get_market_summary

SOL_MINT = "So11111111111111111111111111111111111111112"
BUY_IN_PROGRESS = False


def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


def get_sol_usd_price():
    summary = get_market_summary(SOL_MINT)
    price = safe_float(summary.get("price_usd"))

    if price <= 0:
        raise Exception("Could not fetch SOL/USD price.")

    return price


def usd_to_sol_amount(usd_amount):
    sol_price = get_sol_usd_price()
    return float(usd_amount) / sol_price


def execute_live_buy(signal: dict):
    global BUY_IN_PROGRESS

    if BUY_IN_PROGRESS:
        return {
            "ok": False,
            "stage": "BUY_LOCK",
            "error": "Another trade is running",
        }

    BUY_IN_PROGRESS = True

    try:
        output_mint = signal.get("token_address")

        usd_amount = safe_float(signal.get("usd_amount") or signal.get("trade_size_usd"))
        sol_amount = usd_to_sol_amount(usd_amount) if usd_amount else 0.01
        slippage_bps = int(signal.get("slippage_bps") or 100)

        built = build_swap_transaction(
            output_mint=output_mint,
            sol_amount=sol_amount,
            slippage_bps=slippage_bps,
        )

        if not built.get("ok"):
            return built

        safety = evaluate_swap_build(built)

        if not safety.get("approved"):
            return {
                "ok": False,
                "stage": "SAFETY",
                "error": safety.get("reason"),
                "safety": safety,
            }

        # ----------------------------
        # SIGN (ALWAYS BASE64 STRING)
        # ----------------------------
        signed = sign_swap_transaction(built.get("swap_transaction"))

        if not signed.get("ok"):
            return {
                "ok": False,
                "stage": "SIGN",
                "error": signed.get("error"),
            }

        # ----------------------------
        # SEND (ONLY STRING)
        # ----------------------------
        result = send_signed_transaction(signed.get("signed_transaction"))

        return {
            "ok": result.get("ok", False),
            "stage": "SENT" if result.get("ok") else "SEND_FAILED",
            "signature": result.get("signature"),
            "error": result.get("error"),
        }

    finally:
        BUY_IN_PROGRESS = False