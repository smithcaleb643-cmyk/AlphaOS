from core.live_execution.builder import build_swap
from core.live_execution.signer import sign_swap
from core.live_transaction_sender import send_signed_transaction
import os
from solders.keypair import Keypair


def get_keypair():
    private_key = os.getenv("SOLANA_PRIVATE_KEY")

    if not private_key:
        raise Exception("Missing SOLANA_PRIVATE_KEY in environment")

    return Keypair.from_base58_string(private_key)


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

        # STEP 1: GET WALLET
        keypair = get_keypair()

        # STEP 2: BUILD SWAP
        built = build_swap(
            token_address,
            amount,
            slippage_bps,
            str(keypair.pubkey())
        )

        if not built:
            return {
                "ok": False,
                "stage": "BUILD_FAILED",
                "error": "No response from builder"
            }

        if not built.get("ok"):
            return {
                "ok": False,
                "stage": built.get("stage", "BUILD_FAILED"),
                "error": built.get("error") or built.get("raw") or built
            }

        # extract swap tx safely
        swap_tx = built.get("swapTransaction") or built.get("swap_transaction")

        if not swap_tx:
            return {
                "ok": False,
                "stage": "NO_SWAP_TX",
                "error": built,
            }

        # STEP 3: SIGN SWAP
        signed = sign_swap(
            {"swapTransaction": swap_tx},
            keypair
        )

        if not signed or not signed.get("ok"):
            return {
                "ok": False,
                "stage": "SIGN_FAILED",
                "error": signed,
            }

        # STEP 4: SEND TX
        sent = send_signed_transaction(signed["signed_transaction"])

        return sent

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXECUTOR_ERROR",
            "error": str(e),
        }