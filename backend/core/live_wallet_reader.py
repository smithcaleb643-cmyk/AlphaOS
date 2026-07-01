import requests
import time

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

ALPHA_TEST_WALLET = "EFHxUKFpWTfgy64Q6rdsieDYTSgVVbfP1wqg5WaEEise"

TOKEN_PROGRAMS = [
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFJC7nCnMb4nNq7Ls8U",
]


_wallet_cache = None
_wallet_cache_time = 0
CACHE_SECONDS = 5


def rpc_call(method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    response = requests.post(SOLANA_RPC_URL, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def read_sol_balance(wallet_address=ALPHA_TEST_WALLET):
    try:
        data = rpc_call("getBalance", [wallet_address])
        lamports = data["result"]["value"]

        return {
            "ok": True,
            "connected": True,
            "lamports": lamports,
            "sol_balance": lamports / 1_000_000_000,
        }

    except Exception as error:
        return {
            "ok": False,
            "connected": False,
            "error": str(error),
        }


def read_token_accounts_for_program(wallet_address, program_id):
    data = rpc_call(
        "getTokenAccountsByOwner",
        [wallet_address, {"programId": program_id}, {"encoding": "jsonParsed"}],
    )

    tokens = []

    for account in data["result"]["value"]:
        info = account["account"]["data"]["parsed"]["info"]
        token_amount = info.get("tokenAmount", {})

        amount_raw = token_amount.get("amount", "0")

        if int(amount_raw) <= 0:
            continue

        tokens.append({
            "mint": info.get("mint"),
            "amount": float(token_amount.get("uiAmount") or 0),
        })

    return tokens


def read_token_accounts(wallet_address=ALPHA_TEST_WALLET):
    all_tokens = []

    for program_id in TOKEN_PROGRAMS:
        try:
            all_tokens.extend(
                read_token_accounts_for_program(wallet_address, program_id)
            )
        except Exception as error:
            print("TOKEN PROGRAM READ FAILED:", error)

    return {
        "token_count": len(all_tokens),
        "tokens": all_tokens,
    }


def live_wallet_status():
    global _wallet_cache, _wallet_cache_time

    now = time.time()

    if _wallet_cache and (now - _wallet_cache_time) < CACHE_SECONDS:
        return _wallet_cache

    balance = read_sol_balance()
    tokens = read_token_accounts()

    result = {
        "ok": balance.get("ok"),
        "connected": balance.get("connected"),
        "wallet_address": ALPHA_TEST_WALLET,
        "sol_balance": balance.get("sol_balance", 0),
        "lamports": balance.get("lamports", 0),
        "token_count": tokens.get("token_count", 0),
        "tokens": tokens.get("tokens", []),
    }

    _wallet_cache = result
    _wallet_cache_time = now

    return result