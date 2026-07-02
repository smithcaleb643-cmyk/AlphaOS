import requests

QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
SWAP_URL = "https://api.jup.ag/swap/v1/swap"

WALLET = "EFHxUKFpWTfgy64Q6rdsieDYTSgVVbfP1wqg5WaEEise"


def build_swap(token_address, amount, slippage_bps):
    try:
        input_mint = "So11111111111111111111111111111111111111112"

        # STEP 1 — GET QUOTE
        quote_res = requests.get(QUOTE_URL, params={
            "inputMint": input_mint,
            "outputMint": token_address,
            "amount": str(int(float(amount) * 1_000_000_000)),
            "slippageBps": slippage_bps
        }, timeout=10)

        # IMPORTANT: Jupiter returns useful error text on 400/422
        if quote_res.status_code != 200:
            return {
                "ok": False,
                "stage": "QUOTE_FAILED",
                "error": quote_res.text
            }

        quote = quote_res.json()

        # STEP 2 — VALIDATE QUOTE (IMPORTANT FIX)
        if not quote or "routePlan" not in quote:
            return {
                "ok": False,
                "stage": "BAD_QUOTE",
                "raw": quote
            }

        # STEP 3 — SWAP REQUEST (FIXED FORMAT)
        swap_res = requests.post(SWAP_URL, json={
            "quoteResponse": quote,
            "userPublicKey": WALLET,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "dynamicSlippage": True
        }, timeout=10)

        if swap_res.status_code != 200:
            return {
                "ok": False,
                "stage": "SWAP_FAILED",
                "error": swap_res.text
            }

        swap = swap_res.json()

        # STEP 4 — VALIDATE RESPONSE
        if "swapTransaction" not in swap:
            return {
                "ok": False,
                "stage": "NO_SWAP_TX",
                "raw": swap
            }

        return {
            "ok": True,
            "swap_transaction": swap["swapTransaction"]
        }

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXCEPTION",
            "error": str(e)
        }