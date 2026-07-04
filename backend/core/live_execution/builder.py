import requests

QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
SWAP_URL = "https://api.jup.ag/swap/v1/swap"
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

LAMPORTS_PER_SOL = 1_000_000_000
USDC_DECIMALS = 1_000_000

# Keep some SOL untouched so Alpha does not spend the wallet into dust.
MIN_SOL_RESERVE = 0.01

_session = requests.Session()


def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


def rpc_call(method, params=None):
    response = _session.post(
        SOLANA_RPC_URL,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or [],
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_wallet_lamports(wallet_address):
    if not wallet_address:
        return 0

    try:
        data = rpc_call("getBalance", [wallet_address])
        return int(data.get("result", {}).get("value") or 0)
    except Exception as error:
        print("BUILDER BALANCE CHECK FAILED:", error)
        return 0


def get_sol_usd_price():
    """
    Uses Jupiter's SOL -> USDC quote as the SOL/USD price source.

    This avoids treating trade_size_usd as SOL.
    """
    one_sol_lamports = LAMPORTS_PER_SOL

    response = _session.get(
        QUOTE_URL,
        params={
            "inputMint": SOL_MINT,
            "outputMint": USDC_MINT,
            "amount": str(one_sol_lamports),
            "slippageBps": 50,
        },
        timeout=10,
    )
    response.raise_for_status()

    quote = response.json()
    out_amount = safe_float(quote.get("outAmount"))

    if out_amount <= 0:
        raise Exception(f"Could not read SOL/USD from Jupiter quote: {quote}")

    return out_amount / USDC_DECIMALS


def usd_to_lamports(usd_amount):
    usd_amount = safe_float(usd_amount)

    if usd_amount <= 0:
        return 0

    sol_price = get_sol_usd_price()

    if sol_price <= 0:
        raise Exception("Invalid SOL/USD price")

    sol_amount = usd_amount / sol_price
    lamports = int(sol_amount * LAMPORTS_PER_SOL)

    return max(1, lamports)


def build_swap(token_address, amount, slippage_bps, user_wallet=None):
    """
    IMPORTANT:
    `amount` is treated as USD, not SOL.

    Old bug:
    amount=0.05 was converted directly to 0.05 SOL:
        int(0.05 * 1_000_000_000) = 50,000,000 lamports

    Fixed behavior:
    amount=0.05 means $0.05 worth of SOL.
    """
    try:
        usd_amount = safe_float(amount)

        if not token_address:
            return {
                "ok": False,
                "stage": "VALIDATION",
                "error": "Missing token address",
            }

        if usd_amount <= 0:
            return {
                "ok": False,
                "stage": "VALIDATION",
                "error": "Trade size must be greater than 0 USD",
            }

        lamports = usd_to_lamports(usd_amount)

        wallet_lamports = get_wallet_lamports(user_wallet)
        reserve_lamports = int(MIN_SOL_RESERVE * LAMPORTS_PER_SOL)

        if wallet_lamports <= reserve_lamports:
            return {
                "ok": False,
                "stage": "CAPITAL_PROTECTION",
                "error": (
                    f"Wallet is at or below reserve. "
                    f"wallet_sol={wallet_lamports / LAMPORTS_PER_SOL:.9f}, "
                    f"reserve_sol={MIN_SOL_RESERVE}"
                ),
                "wallet_lamports": wallet_lamports,
                "reserve_lamports": reserve_lamports,
            }

        spendable_lamports = wallet_lamports - reserve_lamports

        if lamports > spendable_lamports:
            return {
                "ok": False,
                "stage": "INSUFFICIENT_SPENDABLE_SOL",
                "error": (
                    f"Trade requires {lamports} lamports, but only "
                    f"{spendable_lamports} lamports are spendable after reserve."
                ),
                "requested_usd": usd_amount,
                "requested_lamports": lamports,
                "wallet_lamports": wallet_lamports,
                "reserve_lamports": reserve_lamports,
                "spendable_lamports": spendable_lamports,
            }

        # -------------------------
        # QUOTE
        # -------------------------
        quote_res = _session.get(
            QUOTE_URL,
            params={
                "inputMint": SOL_MINT,
                "outputMint": token_address,
                "amount": str(lamports),
                "slippageBps": int(slippage_bps),
            },
            timeout=10,
        )

        if quote_res.status_code != 200:
            return {
                "ok": False,
                "stage": "QUOTE_FAILED",
                "error": quote_res.text,
                "requested_usd": usd_amount,
                "requested_lamports": lamports,
            }

        quote = quote_res.json()

        # -------------------------
        # SWAP
        # -------------------------
        swap_res = _session.post(
            SWAP_URL,
            json={
                "quoteResponse": quote,
                "userPublicKey": user_wallet,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto",
                "wrapAndUnwrapSol": True,
            },
            timeout=10,
        )

        if swap_res.status_code != 200:
            return {
                "ok": False,
                "stage": "SWAP_FAILED",
                "error": swap_res.text,
                "quote": quote,
                "requested_usd": usd_amount,
                "requested_lamports": lamports,
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
                "quote": quote,
                "requested_usd": usd_amount,
                "requested_lamports": lamports,
            }

        sol_amount = lamports / LAMPORTS_PER_SOL

        return {
            "ok": True,
            "swapTransaction": tx,
            "quote": quote,
            "input_mint": SOL_MINT,
            "output_mint": token_address,
            "wallet_address": user_wallet,
            "slippage_bps": int(slippage_bps),
            "trade_size_usd": usd_amount,
            "sol_amount": sol_amount,
            "lamports": lamports,
            "wallet_lamports": wallet_lamports,
            "reserve_lamports": reserve_lamports,
        }

    except Exception as e:
        return {
            "ok": False,
            "stage": "EXCEPTION",
            "error": str(e),
        }
