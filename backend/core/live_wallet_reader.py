import os
import time
import requests
from solders.keypair import Keypair

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

TOKEN_PROGRAMS = [
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFJC7nCnMb4nNq7Ls8U",
]

_wallet_cache = None
_wallet_cache_time = 0
CACHE_SECONDS = 1

_session = requests.Session()


def get_alpha_wallet_address():
    private_key = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key:
        return None
    return str(Keypair.from_base58_string(private_key).pubkey())


ALPHA_TEST_WALLET = get_alpha_wallet_address()


def clear_wallet_cache():
    global _wallet_cache, _wallet_cache_time
    _wallet_cache = None
    _wallet_cache_time = 0


def rpc_call(method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    response = _session.post(SOLANA_RPC_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def read_sol_balance(wallet_address=None):
    wallet_address = wallet_address or get_alpha_wallet_address()

    if not wallet_address:
        return {
            "ok": False,
            "connected": False,
            "error": "Missing wallet address",
        }

    try:
        data = rpc_call("getBalance", [wallet_address])

        if "result" not in data:
            print("SOL BALANCE RPC ERROR:", data)
            return {
                "ok": False,
                "connected": False,
                "error": data,
            }

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
        [
            wallet_address,
            {"programId": program_id},
            {"encoding": "jsonParsed"},
        ],
    )

    if "result" not in data:
        print("TOKEN ACCOUNT RPC ERROR:", data)
        return []

    accounts = data["result"].get("value", [])
    tokens = []

    for account in accounts:
        try:
            info = account["account"]["data"]["parsed"]["info"]
            token_amount = info.get("tokenAmount", {})

            amount_raw = token_amount.get("amount", "0")
            decimals = int(token_amount.get("decimals") or 0)

            if int(amount_raw) <= 0:
                continue

            ui_amount = token_amount.get("uiAmount")

            if ui_amount is None:
                ui_amount = int(amount_raw) / (10 ** decimals) if decimals else int(amount_raw)

            tokens.append({
                "mint": info.get("mint"),
                "amount": float(ui_amount),
                "amount_raw": str(amount_raw),
                "decimals": decimals,
                "program_id": program_id,
            })

        except Exception as error:
            print("TOKEN ACCOUNT PARSE FAILED:", error)

    return tokens


def read_token_accounts(wallet_address=None):
    wallet_address = wallet_address or get_alpha_wallet_address()

    if not wallet_address:
        return {
            "token_count": 0,
            "tokens": [],
        }

    all_tokens = []

    for program_id in TOKEN_PROGRAMS:
        try:
            all_tokens.extend(
                read_token_accounts_for_program(wallet_address, program_id)
            )
        except Exception as error:
            print("TOKEN PROGRAM READ FAILED:", program_id, error)

    return {
        "token_count": len(all_tokens),
        "tokens": all_tokens,
    }


def live_wallet_status(force_refresh=False):
    global _wallet_cache, _wallet_cache_time

    now = time.time()

    if not force_refresh and _wallet_cache and (now - _wallet_cache_time) < CACHE_SECONDS:
        return _wallet_cache

    wallet_address = get_alpha_wallet_address()

    balance = read_sol_balance(wallet_address)
    tokens = read_token_accounts(wallet_address)

    result = {
        "ok": balance.get("ok"),
        "connected": balance.get("connected"),
        "wallet_address": wallet_address,
        "sol_balance": balance.get("sol_balance", 0),
        "lamports": balance.get("lamports", 0),
        "token_count": tokens.get("token_count", 0),
        "tokens": tokens.get("tokens", []),
    }

    _wallet_cache = result
    _wallet_cache_time = now

    return result