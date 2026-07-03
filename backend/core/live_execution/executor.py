from core.live_execution.builder import build_swap
from core.live_execution.signer import sign_swap
from core.live_transaction_sender import send_signed_transaction
from core.live_trade_journal import record_live_buy
import os
from solders.keypair import Keypair

# -------------------------
# SIMPLE STATE TRACKING (NO NEW FILES)
# -------------------------
TRADE_FEED = []
POSITIONS = {}


def get_keypair():
    private_key = os.getenv("SOLANA_PRIVATE_KEY")

    if not private_key:
        raise Exception("Missing SOLANA_PRIVATE_KEY in environment")

    return Keypair.from_base58_string(private_key)


# -------------------------
# BALANCE CHECK (INLINE)
# -------------------------
def get_sol_balance(pubkey: str):
    import requests

    res = requests.post(
        "https://api.mainnet-beta.solana.com",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [pubkey],
        },
    )

    try:
        return res.json()["result"]["value"] / 1e9
    except Exception:
        return 0.0


def execute_live_buy(payload: dict):
    try:
        # -------------------------
        # KILL SWITCH (SAFETY)
        # -------------------------
        if payload.get("kill_switch") is True:
            return {"ok": False, "stage": "KILLED"}

        token_address = payload.get("token_address")
        amount = payload.get("trade_size_usd")
        slippage_bps = payload.get("slippage_bps", 100)

        if not token_address or not amount:
            return {
                "ok": False,
                "stage": "VALIDATION_ERROR",
                "error": "Missing token_address or trade_size_usd",
            }

        # -------------------------
        # WALLET
        # -------------------------
        keypair = get_keypair()

        # -------------------------
        # BUILD SWAP
        # -------------------------
        built = build_swap(
            token_address,
            amount,
            slippage_bps,
            str(keypair.pubkey()),
        )

        if not built or not built.get("ok"):
            return {
                "ok": False,
                "stage": built.get("stage", "BUILD_FAILED"),
                "error": built.get("error") or built,
            }

        swap_tx = built.get("swapTransaction")

        if not swap_tx:
            return {
                "ok": False,
                "stage": "NO_SWAP_TX",
                "error": built,
            }

        # -------------------------
        # SIGN
        # -------------------------
        signed = sign_swap(
            {"swapTransaction": swap_tx},
            keypair,
        )

        if not signed or not signed.get("ok"):
            return {
                "ok": False,
                "stage": "SIGN_FAILED",
                "error": signed,
            }

        # -------------------------
        # SEND
        # -------------------------
        sent = send_signed_transaction(signed["signed_transaction"])

        if not sent.get("ok"):
            return sent

        # -------------------------
        # TRADE FEED LOG
        # -------------------------
        TRADE_FEED.append(
            {
                "token": token_address,
                "amount": amount,
                "signature": sent.get("signature"),
                "status": "filled",
            }
        )

        # -------------------------
        # POSITION TRACKING
        # -------------------------
        POSITIONS[token_address] = {
            "entry": amount,
            "status": "open",
        }

        # -------------------------
        # RECORD LIVE TRADE
        # -------------------------
        record_live_buy(
            {
                **sent,
                "built": built,
                "sent": sent,
            },
            payload,
        )

        return sent

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXECUTOR_ERROR",
            "error": str(e),
        }