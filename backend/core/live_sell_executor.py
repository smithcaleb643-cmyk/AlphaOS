import requests
import time

from core.live_wallet_reader import get_alpha_wallet_address, live_wallet_status
from core.jupiter_service import JUPITER_QUOTE_URL, SOL_MINT
from core.live_transaction_signer import sign_swap_transaction
from core.live_transaction_sender import send_signed_transaction
from core.live_trade_journal import record_live_sell
from core.live_learning_recorder import record_live_completed_trade

JUPITER_SWAP_URL = "https://lite-api.jup.ag/swap/v1/swap"


def get_sell_quote(input_mint, amount_raw, slippage_bps=150):
    params = {
        "inputMint": input_mint,
        "outputMint": SOL_MINT,
        "amount": str(amount_raw),
        "slippageBps": int(slippage_bps),
    }

    response = requests.get(JUPITER_QUOTE_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def build_sell_transaction(input_mint, amount_raw, slippage_bps=150):
    wallet_address = get_alpha_wallet_address()

    if not wallet_address:
        return {
            "ok": False,
            "stage": "WALLET_FAIL",
            "error": "Missing wallet address from SOLANA_PRIVATE_KEY",
        }

    quote = get_sell_quote(input_mint, amount_raw, slippage_bps)

    payload = {
        "quoteResponse": quote,
        "userPublicKey": wallet_address,
        "wrapAndUnwrapSol": True,
        "dynamicComputeUnitLimit": True,
        "prioritizationFeeLamports": "auto",
    }

    response = requests.post(JUPITER_SWAP_URL, json=payload, timeout=20)
    response.raise_for_status()
    swap_data = response.json()

    return {
        "ok": True,
        "wallet_address": wallet_address,
        "input_mint": input_mint,
        "output_mint": SOL_MINT,
        "amount_raw": str(amount_raw),
        "slippage_bps": slippage_bps,
        "quote": quote,
        "swap_transaction": swap_data.get("swapTransaction"),
        "last_valid_block_height": swap_data.get("lastValidBlockHeight"),
        "raw": swap_data,
    }


def _get_token_raw(wallet, mint):
    for token in wallet.get("tokens", []):
        if token.get("mint") == mint:
            return int(float(token.get("amount_raw") or 0))
    return 0


def _is_blockhash_error(error):
    text = str(error or "").lower()
    return "blockhash not found" in text or "blockhash" in text


def send_sell_with_fresh_blockhash_retry(input_mint, amount_raw, slippage_bps):
    last_built = None
    last_signed = None
    last_sent = None

    for attempt in range(1, 3):
        built = build_sell_transaction(input_mint, amount_raw, slippage_bps)
        last_built = built

        if not built.get("ok"):
            return {
                "ok": False,
                "stage": built.get("stage", "BUILD_FAIL"),
                "error": built.get("error"),
                "built": built,
                "signed": last_signed,
                "sent": last_sent,
                "attempt": attempt,
            }

        if not built.get("swap_transaction"):
            return {
                "ok": False,
                "stage": "BUILD_FAIL",
                "error": "No swap transaction from Jupiter",
                "built": built,
                "signed": last_signed,
                "sent": last_sent,
                "attempt": attempt,
            }

        signed = sign_swap_transaction(built["swap_transaction"])
        last_signed = signed

        if not signed.get("ok"):
            return {
                "ok": False,
                "stage": "SIGN_FAIL",
                "error": signed.get("error"),
                "built": built,
                "signed": signed,
                "sent": last_sent,
                "attempt": attempt,
            }

        sent = send_signed_transaction(signed.get("signed_transaction"))
        last_sent = sent

        if sent.get("ok") and sent.get("signature"):
            return {
                "ok": True,
                "stage": "SENT",
                "signature": sent.get("signature"),
                "built": built,
                "signed": signed,
                "sent": sent,
                "attempt": attempt,
            }

        error = sent.get("error")

        if _is_blockhash_error(error) and attempt == 1:
            time.sleep(1)
            continue

        return {
            "ok": False,
            "stage": "SEND_FAIL",
            "error": error,
            "built": built,
            "signed": signed,
            "sent": sent,
            "attempt": attempt,
        }

    return {
        "ok": False,
        "stage": "SEND_FAIL",
        "error": "Sell send failed after fresh blockhash retry.",
        "built": last_built,
        "signed": last_signed,
        "sent": last_sent,
        "attempt": 2,
    }


def execute_live_sell(payload: dict):
    input_mint = payload.get("token_address") or payload.get("input_mint")
    amount_raw = payload.get("amount_raw")
    slippage_bps = int(payload.get("slippage_bps") or 150)

    if not input_mint:
        return {"ok": False, "stage": "VALIDATION", "error": "missing token_address"}

    if not amount_raw:
        return {"ok": False, "stage": "VALIDATION", "error": "missing amount_raw"}

    try:
        before_wallet = live_wallet_status()
        before_raw = _get_token_raw(before_wallet, input_mint)

        sent_result = send_sell_with_fresh_blockhash_retry(
            input_mint=input_mint,
            amount_raw=amount_raw,
            slippage_bps=slippage_bps,
        )

        if not sent_result.get("ok"):
            result = {
                "ok": False,
                "type": "SELL",
                "stage": sent_result.get("stage", "SEND_FAIL"),
                "error": sent_result.get("error"),
                "built": sent_result.get("built"),
                "signed": sent_result.get("signed"),
                "sent": sent_result.get("sent"),
                "send_attempt": sent_result.get("attempt"),
                "signal": payload,
            }
            record_live_sell(result, payload)
            return result

        signature = sent_result["signature"]
        confirmed = False

        for _ in range(6):
            time.sleep(2)
            wallet = live_wallet_status()
            remaining_raw = _get_token_raw(wallet, input_mint)

            if remaining_raw <= 0:
                confirmed = True
                break

            if remaining_raw < before_raw:
                confirmed = True
                break

        result = {
            "ok": confirmed,
            "type": "SELL",
            "stage": "CONFIRMED" if confirmed else "UNCONFIRMED",
            "signature": signature,
            "error": None if confirmed else "Sell not confirmed on-chain",
            "built": sent_result.get("built"),
            "signed": sent_result.get("signed"),
            "sent": sent_result.get("sent"),
            "send_attempt": sent_result.get("attempt"),
            "signal": payload,
            "message": "Sell confirmed" if confirmed else "Sell failed confirmation check",
        }

        record_live_sell(result, payload)

        if confirmed:
            record_live_completed_trade(payload, result)

        return result

    except Exception as e:
        result = {
            "ok": False,
            "type": "SELL",
            "stage": "EXCEPTION",
            "error": str(e),
            "signal": payload,
        }

        try:
            record_live_sell(result, payload)
        except Exception:
            pass

        return result