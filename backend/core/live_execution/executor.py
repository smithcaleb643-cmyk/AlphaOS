from core.live_execution.builder import build_swap
from core.live_execution.signer import sign_swap
from core.live_execution.sender import send_swap


def execute_live_buy(token_address: str, trade_size_usd: float, slippage_bps: int = 300):
    try:
        built = build_swap(token_address, trade_size_usd, slippage_bps)

        if not built.get("ok"):
            return built

        signed = sign_swap(built["swap_transaction"])

        if not signed.get("ok"):
            return signed

        sent = send_swap(signed["signed_transaction"])

        return {
            "ok": sent.get("ok", False),
            "stage": "SENT" if sent.get("ok") else "FAILED",
            "signature": sent.get("signature"),
            "error": sent.get("error"),
        }

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXECUTOR_ERROR",
            "error": str(e),
        }