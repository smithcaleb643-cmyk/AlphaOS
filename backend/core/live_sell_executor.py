from core.alpha_wallet_manager import get_alpha_wallet_address
from core.jupiter_service import JUPITER_QUOTE_URL, SOL_MINT
from core.live_transaction_signer import sign_swap_transaction
from core.live_transaction_sender import send_signed_transaction
from core.live_trade_journal import record_live_sell
from core.live_learning_recorder import record_live_completed_trade

import requests


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

    quote = get_sell_quote(
        input_mint=input_mint,
        amount_raw=amount_raw,
        slippage_bps=slippage_bps,
    )

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


def execute_live_sell(payload: dict):
    input_mint = payload.get("token_address") or payload.get("input_mint")
    amount_raw = payload.get("amount_raw")
    slippage_bps = int(payload.get("slippage_bps") or 150)

    if not input_mint:
        return {
            "ok": False,
            "type": "SELL",
            "stage": "VALIDATION",
            "error": "token_address is required",
            "signal": payload,
        }

    if not amount_raw:
        return {
            "ok": False,
            "type": "SELL",
            "stage": "VALIDATION",
            "error": "amount_raw is required",
            "signal": payload,
        }

    try:
        built = build_sell_transaction(
            input_mint=input_mint,
            amount_raw=amount_raw,
            slippage_bps=slippage_bps,
        )

        if not built.get("swap_transaction"):
            result = {
                "ok": False,
                "type": "SELL",
                "stage": "BUILD_SELL_SWAP",
                "error": "Jupiter did not return swap_transaction.",
                "built": built,
                "signal": payload,
            }
            record_live_sell(result, payload)
            return result

        signed = sign_swap_transaction(built.get("swap_transaction"))

        if not signed.get("ok"):
            result = {
                "ok": False,
                "type": "SELL",
                "stage": "SIGN",
                "error": signed.get("error"),
                "built": built,
                "signal": payload,
            }
            record_live_sell(result, payload)
            return result

        sent = send_signed_transaction(signed.get("signed_transaction"))

        result = {
            "ok": sent.get("ok", False),
            "type": "SELL",
            "stage": "SENT" if sent.get("ok") else "SEND_FAILED",
            "signature": sent.get("signature"),
            "error": sent.get("error"),
            "built": built,
            "sent": sent,
            "message": "Live sell executed." if sent.get("ok") else "Live sell failed during send.",
            "signal": payload,
        }

        journal_entry = record_live_sell(result, payload)
        result["journal_entry"] = journal_entry

        if result.get("ok"):
            result["learned"] = record_live_completed_trade(payload, result)

        return result

    except Exception as error:
        result = {
            "ok": False,
            "type": "SELL",
            "stage": "ERROR",
            "error": str(error),
            "signal": payload,
        }

        try:
            record_live_sell(result, payload)
        except Exception:
            pass

        return result
