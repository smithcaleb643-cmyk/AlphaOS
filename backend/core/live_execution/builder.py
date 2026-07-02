import requests

QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
SWAP_URL = "https://api.jup.ag/swap/v1/swap"


def build_swap(token_address, amount, slippage_bps, user_wallet):
    try:
        SOL_MINT = "So11111111111111111111111111111111111111112"

        # -----------------------------
        # STEP 1: GET QUOTE
        # -----------------------------
        quote_res = requests.get(QUOTE_URL, params={
            "inputMint": SOL_MINT,
            "outputMint": token_address,
            "amount": str(int(float(amount) * 1_000_000_000)),
            "slippageBps": slippage_bps
        }, timeout=10)

        if quote_res.status_code != 200:
            return {
                "ok": False,
                "stage": "QUOTE_FAILED",
                "error": quote_res.text
            }

        quote = quote_res.json()

        if not quote:
            return {
                "ok": False,
                "stage": "BAD_QUOTE",
                "error": "Empty quote response"
            }

        # -----------------------------
        # STEP 2: BUILD SWAP
        # -----------------------------
        swap_res = requests.post(SWAP_URL, json={
            "quoteResponse": quote,
            "userPublicKey": user_wallet,
            "wrapAndUnwrapSol": True
        }, timeout=10)

        # IMPORTANT: DO NOT TRY TO PARSE IF FAILED
        if swap_res.status_code != 200:
            return {
                "ok": False,
                "stage": "SWAP_FAILED",
                "error": swap_res.text
            }

        swap = swap_res.json()

        # -----------------------------
        # STEP 3: EXTRACT TX (STRICT)
        # -----------------------------
        tx = swap.get("swapTransaction")

        if not tx:
            return {
                "ok": False,
                "stage": "NO_SWAP_TX",
                "error": swap
            }

        # -----------------------------
        # SUCCESS
        # -----------------------------
        return {
            "ok": True,
            "swapTransaction": tx
        }

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXCEPTION",
            "error": str(e)
        }