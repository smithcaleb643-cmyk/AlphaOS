from core.live_execution.builder import build_swap
from core.live_execution.signer import sign_swap
from core.live_transaction_sender import send_signed_transaction
from core.live_trade_journal import record_live_buy
from core.live_wallet_reader import live_wallet_status, clear_wallet_cache
from core.live_trade_ledger import create_trade

import os
import time
from solders.keypair import Keypair

# -------------------------
# SIMPLE STATE TRACKING (NO NEW FILES)
# -------------------------
TRADE_FEED = []
POSITIONS = {}

BUY_CONFIRM_ATTEMPTS = 12
BUY_CONFIRM_DELAY_SECONDS = 0.5


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
        timeout=10,
    )

    try:
        return res.json()["result"]["value"] / 1e9
    except Exception:
        return 0.0


def _get_token_raw(wallet, mint):
    for token in wallet.get("tokens", []):
        if token.get("mint") == mint:
            try:
                return int(float(token.get("amount_raw") or 0))
            except Exception:
                return 0
    return 0


def _extract_output_mint(built, fallback_token_address):
    quote = built.get("quote", {}) or {}

    return (
        quote.get("outputMint")
        or built.get("output_mint")
        or built.get("outputMint")
        or fallback_token_address
    )


def confirm_buy_received(token_address, before_raw=0):
    """
    Confirms the wallet actually received the bought token.

    This prevents Alpha from recording BUY trades that were merely sent but
    not yet visible in the wallet. Portfolio/exits depend on wallet-backed
    positions, so this makes sell management reliable.
    """
    clear_wallet_cache()

    last_wallet = None
    last_raw = before_raw

    for _ in range(BUY_CONFIRM_ATTEMPTS):
        time.sleep(BUY_CONFIRM_DELAY_SECONDS)

        wallet = live_wallet_status(force_refresh=True)
        last_wallet = wallet
        last_raw = _get_token_raw(wallet, token_address)

        if last_raw > before_raw:
            return {
                "ok": True,
                "stage": "BUY_CONFIRMED",
                "before_raw": str(before_raw),
                "after_raw": str(last_raw),
                "wallet": wallet,
            }

    return {
        "ok": False,
        "stage": "BUY_UNCONFIRMED",
        "before_raw": str(before_raw),
        "after_raw": str(last_raw),
        "wallet": last_wallet,
        "error": "Buy transaction was sent, but token balance did not appear in wallet yet.",
    }


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

        before_wallet = live_wallet_status(force_refresh=True)
        before_raw = _get_token_raw(before_wallet, token_address)

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
                "stage": built.get("stage", "BUILD_FAILED") if isinstance(built, dict) else "BUILD_FAILED",
                "error": built.get("error") if isinstance(built, dict) else built,
            }

        output_mint = _extract_output_mint(built, token_address)

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

        signature = sent.get("signature")

        # -------------------------
        # CONFIRM WALLET RECEIVED TOKEN
        # -------------------------
        confirm = confirm_buy_received(
            token_address=output_mint,
            before_raw=before_raw,
        )

        if not confirm.get("ok"):
            result = {
                **sent,
                "ok": False,
                "stage": "BUY_UNCONFIRMED",
                "signature": signature,
                "error": confirm.get("error"),
                "built": built,
                "sent": sent,
                "confirm": confirm,
            }

            # Do NOT record this as a live BUY position.
            # It was sent, but Alpha cannot manage/sell what the wallet reader cannot see.
            return result

        # -------------------------
        # TRADE FEED LOG
        # -------------------------
        TRADE_FEED.append(
            {
                "token": output_mint,
                "amount": amount,
                "signature": signature,
                "status": "filled",
            }
        )

        # -------------------------
        # POSITION TRACKING
        # -------------------------
        POSITIONS[output_mint] = {
            "entry": amount,
            "status": "open",
        }

        # -------------------------
        # CREATE LEDGER ENTRY
        # -------------------------
        ledger_trade_id = create_trade({
            "token_address": output_mint,
            "symbol": payload.get("symbol"),
            "coin_name": payload.get("coin_name"),
            "entry_price": payload.get("price_usd"),
            "trade_size_usd": amount,
            "signature": signature,
            "score": payload.get("score"),
            "probability": payload.get("probability"),
            "risk_score": payload.get("risk_score"),
            "reason": payload.get("reason"),
            "wallet_before_raw": confirm.get("before_raw"),
            "wallet_after_raw": confirm.get("after_raw"),
        })

        record_live_buy(
            {
                **sent,
                "ok": True,
                "stage": "BUY_CONFIRMED",
                "signature": signature,
                "built": built,
                "sent": sent,
                "confirm": confirm,
                "ledger_trade_id": ledger_trade_id,
            },
            {**payload,"ledger_trade_id":ledger_trade_id},
        )

        clear_wallet_cache()

        return {
            **sent,
            "ok": True,
            "stage": "BUY_CONFIRMED",
            "signature": signature,
            "ledger_trade_id": ledger_trade_id,
            "confirm": {
                "before_raw": confirm.get("before_raw"),
                "after_raw": confirm.get("after_raw"),
            },
        }

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXECUTOR_ERROR",
            "error": str(e),
        }
