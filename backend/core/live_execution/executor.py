from core.live_execution.builder import build_swap
from core.live_execution.signer import sign_swap
from core.live_transaction_sender import send_signed_transaction


def execute_live_buy(payload: dict):
    try:
        token_address = payload.get("token_address")
        amount = payload.get("trade_size_usd")
        slippage_bps = payload.get("slippage_bps", 100)

        if not token_address or not amount:
            return {
                "ok": False,
                "stage": "VALIDATION_ERROR",
                "error": "Missing token_address or trade_size_usd",
            }

        # STEP 1: BUILD SWAP (FIXED SIGNATURE)
        built = build_swap(
            token_address,
            amount,
            slippage_bps
        )

        if not built or not built.get("ok"):
            return {
                "ok": False,
                "stage": "BUILD_FAILED",
                "error": built,
            }

        # STEP 2: SIGN SWAP
        signed = sign_swap(built)

        if not signed or not signed.get("ok"):
            return {
                "ok": False,
                "stage": "SIGN_FAILED",
                "error": signed,
            }

        # STEP 3: SEND TX
        sent = send_signed_transaction(signed["signed_transaction"])

        return sent

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXECUTOR_ERROR",
            "error": str(e),
        }