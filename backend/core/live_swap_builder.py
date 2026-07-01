import requests

from core.jupiter_service import (
    JUPITER_QUOTE_URL,
    SOL_MINT,
    sol_to_lamports,
)

JUPITER_SWAP_URL = "https://quote-api.jup.ag/v6/swap"

ALPHA_TEST_WALLET = "E6js7TDTJm13uH79zQCBHMs9CKfwm4hjyXSDGurULkwY"


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


def build_swap_transaction(output_mint, sol_amount=0.01, slippage_bps=100, wallet_address=ALPHA_TEST_WALLET):
    try:
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
            "quote": quote,
            "swap_transaction": swap_data.get("swapTransaction"),
            "last_valid_block_height": swap_data.get("lastValidBlockHeight"),
            "raw": swap_data,
            "message": "Swap transaction built but not signed or sent.",
        }

    except Exception as error:
        return {
            "ok": False,
            "wallet_address": wallet_address,
            "output_mint": output_mint,
            "sol_amount": sol_amount,
            "slippage_bps": slippage_bps,
            "error": str(error),
        }