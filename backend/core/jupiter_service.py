import requests

JUPITER_QUOTE_URL = "https://lite-api.jup.ag/swap/v1/quote"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2q8DMdKb3CXxjEfQZBqPohPmp"


def sol_to_lamports(sol_amount):
    return int(float(sol_amount) * 1_000_000_000)


def get_quote(input_mint, output_mint, amount_raw, slippage_bps=100):
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": int(amount_raw),
            "slippageBps": int(slippage_bps),
        }

        response = requests.get(JUPITER_QUOTE_URL, params=params, timeout=15)
        response.raise_for_status()

        return {
            "ok": True,
            "quote": response.json(),
        }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error),
        }


def quote_sol_to_token(output_mint, sol_amount=0.01, slippage_bps=100):
    return get_quote(
        input_mint=SOL_MINT,
        output_mint=output_mint,
        amount_raw=sol_to_lamports(sol_amount),
        slippage_bps=slippage_bps,
    )