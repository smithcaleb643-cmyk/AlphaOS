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


def wallet_has_token(token_mint):
    wallet = live_wallet_status()

    for token in wallet.get("tokens", []):
        if token.get("mint") == token_mint and safe_float(token.get("amount")) > 0:
            return True

    return False


def confirm_buy_received(token_mint, attempts=6, delay_seconds=2):
    for _ in range(attempts):
        time.sleep(delay_seconds)

        if wallet_has_token(token_mint):
            return {
                "ok": True,
                "confirmed": True,
                "message": "Token received in wallet.",
            }

    return {
        "ok": False,
        "confirmed": False,
        "message": "Wallet never received purchased token.",
    }


def execute_live_buy(signal: dict):
    global BUY_IN_PROGRESS

    if BUY_IN_PROGRESS:
        return {
            "ok": False,
            "type": "BUY",
            "stage": "BUY_LOCK",
            "error": "Another buy is already executing.",
            "signal": signal,
        }

    BUY_IN_PROGRESS = True

    try:
        output_mint = signal.get("token_address")

        usd_amount = safe_float(signal.get("usd_amount") or signal.get("trade_size_usd"))
        explicit_sol_amount = signal.get("sol_amount")

        if usd_amount > 0:
            sol_amount = usd_to_sol_amount(usd_amount)
        else:
            sol_amount = safe_float(explicit_sol_amount or 0.01)

        slippage_bps = int(signal.get("slippage_bps") or 100)

        if not output_mint:
            result = {
                "ok": False,
                "type": "BUY",
                "stage": "VALIDATION",
                "error": "token_address is required",
                "signal": signal,
            }
            record_live_buy(result, signal)
            return result

        sol_usd_price = get_sol_usd_price()

        signal["usd_amount"] = usd_amount
        signal["sol_amount"] = sol_amount
        signal["sol_usd_price"] = sol_usd_price

        built = build_swap_transaction(
            output_mint=output_mint,
            sol_amount=sol_amount,
            slippage_bps=slippage_bps,
        )

        if not built.get("ok"):
            result = {
                "ok": False,
                "type": "BUY",
                "stage": "BUILD_SWAP",
                "error": built.get("error"),
                "built": built,
                "signal": signal,
            }
            record_live_buy(result, signal)
            return result

        safety = evaluate_swap_build(built)

        if not safety.get("approved"):
            result = {
                "ok": False,
                "type": "BUY",
                "stage": "EXECUTION_SAFETY",
                "error": safety.get("reason"),
                "safety": safety,
                "built": built,
                "signal": signal,
            }
            record_live_buy(result, signal)
            return result

        # =========================
        # FIXED SIGNING CALL
        # =========================
        signed = sign_swap_transaction(
            built.get("swap_transaction")
        )

        if not signed.get("ok"):
            result = {
                "ok": False,
                "type": "BUY",
                "stage": "SIGN",
                "error": signed.get("error"),
                "built": built,
                "safety": safety,
                "signed": signed,
                "signal": signal,
            }
            record_live_buy(result, signal)
            return result

        sent = send_signed_transaction(signed.get("signed_transaction"))

        result = {
            "ok": sent.get("ok", False),
            "type": "BUY",
            "stage": "SENT" if sent.get("ok") else "SEND_FAILED",
            "signature": sent.get("signature"),
            "error": sent.get("error"),
            "built": built,
            "safety": safety,
            "signed": signed,
            "sent": sent,
            "signal": signal,
            "message": "Live buy sent." if sent.get("ok") else "Live buy failed during send.",
        }

        if sent.get("ok"):
            confirmation = confirm_buy_received(output_mint)
            result["confirmation"] = confirmation

            if confirmation.get("ok"):
                result["stage"] = "CONFIRMED"
                result["message"] = "Live buy confirmed. Token received in wallet."
                result["ok"] = True
            else:
                result["stage"] = "CONFIRM_FAILED"
                result["error"] = confirmation.get("message")
                result["ok"] = False

        record_live_buy(result, signal)

        return result

    finally:
        BUY_IN_PROGRESS = False