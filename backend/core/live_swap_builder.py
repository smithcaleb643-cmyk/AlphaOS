import requests

from core.alpha_wallet_manager import get_alpha_wallet_address
from core.jupiter_service import (
    JUPITER_QUOTE_URL,
    SOL_MINT,
    sol_to_lamports,
)
from core.live_wallet_reader import read_sol_balance

JUPITER_SWAP_URL = "https://lite-api.jup.ag/swap/v1/swap"

MIN_SOL_BUFFER = 0.003


def get_quote_for_swap(output_mint, sol_amount=0.01, slippage_bps=100):
    params = {
        "inputMint": SOL_MINT,
        "outputMint": output_mint,
        "amount": sol_to_lamports(sol_amount),
        "slippageBps": int(slippage_bps),
    }

    response = requests.get(JUPITER_QUOTE_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def check_wallet_has_enough_sol(wallet_address, sol_amount):
    balance = read_sol_balance(wallet_address)

    if not balance.get("ok"):
        return {
            "ok": False,
            "approved": False,
            "reason": "Could not read live wallet balance.",
            "balance": balance,
        }

    sol_balance = float(balance.get("sol_balance") or 0)
    required = float(sol_amount) + MIN_SOL_BUFFER

    if sol_balance < required:
        return {
            "ok": True,
            "approved": False,
            "reason": f"Not enough SOL. Wallet has {sol_balance}, needs at least {required}.",
            "sol_balance": sol_balance,
            "required_sol": required,
        }

    return {
        "ok": True,
        "approved": True,
        "reason": "Wallet has enough SOL for swap plus fee buffer.",
        "sol_balance": sol_balance,
        "required_sol": required,
    }


def build_swap_transaction(output_mint, sol_amount=0.01, slippage_bps=100, wallet_address=None):
    try:
        wallet_address = wallet_address or get_alpha_wallet_address()

        balance_check = check_wallet_has_enough_sol(wallet_address, sol_amount)

        if not balance_check.get("approved"):
            return {
                "ok": False,
                "wallet_address": wallet_address,
                "output_mint": output_mint,
                "sol_amount": sol_amount,
                "slippage_bps": slippage_bps,
                "balance_check": balance_check,
                "error": balance_check.get("reason"),
            }

        quote = get_quote_for_swap(
            output_mint=output_mint,
            sol_amount=sol_amount,
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
            "output_mint": output_mint,
            "sol_amount": sol_amount,
            "slippage_bps": slippage_bps,
            "balance_check": balance_check,
            "quote": quote,
            "swap_transaction": swap_data.get("swapTransaction"),
            "last_valid_block_height": swap_data.get("lastValidBlockHeight"),
            "raw": swap_data,
            "message": "Swap transaction built but not signed or sent.",
        }

    except Exception as error:
        return {
            "ok": False,
            "output_mint": output_mint,
            "sol_amount": sol_amount,
            "slippage_bps": slippage_bps,
            "error": str(error),
        }