from core.live_swap_builder import build_swap_transaction
from core.live_execution_safety import evaluate_swap_build
from core.live_transaction_signer import sign_swap_transaction
from core.live_transaction_sender import send_signed_transaction
from core.live_trade_journal import record_live_buy


def execute_live_buy(signal: dict):
    output_mint = signal.get("token_address")
    sol_amount = float(signal.get("sol_amount") or 0.01)
    slippage_bps = int(signal.get("slippage_bps") or 100)

    if not output_mint:
        result = {
            "ok": False,
            "stage": "VALIDATION",
            "error": "token_address is required",
            "signal": signal,
        }
        record_live_buy(result, signal)
        return result

    built = build_swap_transaction(
        output_mint=output_mint,
        sol_amount=sol_amount,
        slippage_bps=slippage_bps,
    )

    if not built.get("ok"):
        result = {
            "ok": False,
            "stage": "BUILD_SWAP",
            "error": built.get("error"),
            "built": built,
        }
        record_live_buy(result, signal)
        return result

    safety = evaluate_swap_build(built)

    if not safety.get("approved"):
        result = {
            "ok": False,
            "stage": "EXECUTION_SAFETY",
            "error": safety.get("reason"),
            "safety": safety,
            "built": built,
        }
        record_live_buy(result, signal)
        return result

    signed = sign_swap_transaction(built.get("swap_transaction"))

    if not signed.get("ok"):
        result = {
            "ok": False,
            "stage": "SIGN",
            "error": signed.get("error"),
            "built": built,
            "safety": safety,
        }
        record_live_buy(result, signal)
        return result

    sent = send_signed_transaction(signed.get("signed_transaction"))

    result = {
        "ok": sent.get("ok", False),
        "stage": "SENT" if sent.get("ok") else "SEND_FAILED",
        "signature": sent.get("signature"),
        "error": sent.get("error"),
        "built": built,
        "safety": safety,
        "sent": sent,
        "message": "Live buy executed." if sent.get("ok") else "Live buy failed during send.",
    }

    journal_entry = record_live_buy(result, signal)
    result["journal_entry"] = journal_entry

    return result