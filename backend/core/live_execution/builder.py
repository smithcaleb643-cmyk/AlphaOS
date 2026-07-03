import requests

QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
SWAP_URL = "https://api.jup.ag/swap/v1/swap"


def build_swap(token_address, amount, slippage_bps, user_wallet=None):
    try:
        SOL_MINT = "So11111111111111111111111111111111111111112"

        # -------------------------
        # QUOTE
        # -------------------------
        quote_res = requests.get(
            QUOTE_URL,
            params={
                "inputMint": SOL_MINT,
                "outputMint": token_address,
                "amount": str(int(float(amount) * 1_000_000_000)),
                "slippageBps": slippage_bps,
            },
            timeout=10,
        )

        if quote_res.status_code != 200:
            return {
                "ok": False,
                "stage": "QUOTE_FAILED",
                "error": quote_res.text,
            }

        quote = quote_res.json()

        # -------------------------
        # SWAP
        # -------------------------
        swap_res = requests.post(
            SWAP_URL,
            json={
                "quoteResponse": quote,
                "userPublicKey": user_wallet,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto",
            },
            timeout=10,
        )

        if swap_res.status_code != 200:
            return {
                "ok": False,
                "stage": "SWAP_FAILED",
                "error": swap_res.text,
            }

        swap = swap_res.json()

        # -------------------------
        # EXTRACT TRANSACTION
        # -------------------------
        tx = swap.get("swapTransaction")

        if not tx or not isinstance(tx, str):
            return {
                "ok": False,
                "stage": "NO_TRANSACTION",
                "error": swap,
            }

        # -------------------------
        # SUCCESS
        # -------------------------
        return {
            "ok": True,
            "swapTransaction": tx,
            "quote": quote,
            "input_mint": SOL_MINT,
            "output_mint": token_address,
            "wallet_address": user_wallet,
            "slippage_bps": slippage_bps,
            "sol_amount": amount,
        }

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXCEPTION",
            "error": str(e),
        }