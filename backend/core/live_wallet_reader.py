import requests

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

ALPHA_TEST_WALLET = "EFHxUKFpWTfgy64Q6rdsieDYTSgVVbfP1wqg5WaEEise"

TOKEN_PROGRAMS = [
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFJC7nCnMb4nNq7Ls8U",
]


def lamports_to_sol(lamports):
    return lamports / 1_000_000_000


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

        if "error" in data:
            raise Exception(data["error"])

        lamports = data["result"]["value"]

        return {
            "ok": True,
            "connected": True,
            "wallet_address": wallet_address,
            "rpc_url": SOLANA_RPC_URL,
            "lamports": lamports,
            "sol_balance": lamports_to_sol(lamports),
        }

    except Exception as error:
        return {
            "ok": False,
            "connected": False,
            "wallet_address": wallet_address,
            "rpc_url": SOLANA_RPC_URL,
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

    if "error" in data:
        raise Exception(data["error"])

    tokens = []

    for account in data["result"]["value"]:
        info = account["account"]["data"]["parsed"]["info"]
        token_amount = info.get("tokenAmount", {})

        amount_raw = token_amount.get("amount", "0")
        decimals = int(token_amount.get("decimals", 0) or 0)
        ui_amount = float(token_amount.get("uiAmount") or 0)

        if int(amount_raw or 0) <= 0:
            continue

        tokens.append({
            "mint": info.get("mint"),
            "amount": ui_amount,
            "amount_raw": amount_raw,
            "decimals": decimals,
            "token_account": account.get("pubkey"),
            "program_id": program_id,
        })

    return tokens


def read_token_accounts(wallet_address=ALPHA_TEST_WALLET):
    try:
        all_tokens = []

        for program_id in TOKEN_PROGRAMS:
            try:
                all_tokens.extend(
                    read_token_accounts_for_program(wallet_address, program_id)
                )
            except Exception as error:
                print("TOKEN PROGRAM READ FAILED:", program_id, error)

        return {
            "ok": True,
            "connected": True,
            "wallet_address": wallet_address,
            "token_count": len(all_tokens),
            "tokens": all_tokens,
        }

    except Exception as error:
        return {
            "ok": False,
            "connected": False,
            "wallet_address": wallet_address,
            "error": str(error),
        }


def live_wallet_status():
    balance = read_sol_balance()
    tokens = read_token_accounts()

    return {
        "ok": balance.get("ok", False),
        "connected": balance.get("connected", False),
        "wallet_address": ALPHA_TEST_WALLET,
        "rpc_url": SOLANA_RPC_URL,
        "sol_balance": balance.get("sol_balance", 0),
        "lamports": balance.get("lamports", 0),
        "token_count": tokens.get("token_count", 0),
        "tokens": tokens.get("tokens", []),
        "balance_status": balance,
        "token_status": tokens,
    }