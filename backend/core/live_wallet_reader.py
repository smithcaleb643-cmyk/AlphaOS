import requests

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

ALPHA_TEST_WALLET = "E6js7TDTJm13uH79zQCBHMs9CKfwm4hjyXSDGurULkwY"


def lamports_to_sol(lamports):
    return lamports / 1_000_000_000


def rpc_call(method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    response = requests.post(
        SOLANA_RPC_URL,
        json=payload,
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def read_sol_balance(wallet_address=ALPHA_TEST_WALLET):
    try:

        data = rpc_call(
            "getBalance",
            [wallet_address],
        )

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


def read_token_accounts(wallet_address=ALPHA_TEST_WALLET):
    try:

        data = rpc_call(
            "getTokenAccountsByOwner",
            [
                wallet_address,
                {
                    "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
                },
                {
                    "encoding": "jsonParsed"
                },
            ],
        )

        if "error" in data:
            raise Exception(data["error"])

        accounts = data["result"]["value"]

        tokens = []

        for account in accounts:

            info = (
                account["account"]["data"]["parsed"]["info"]
            )

            amount = float(
                info["tokenAmount"]["uiAmount"] or 0
            )

            if amount <= 0:
                continue

            tokens.append(
                {
                    "mint": info["mint"],
                    "amount": amount,
                    "decimals": info["tokenAmount"]["decimals"],
                }
            )

        return {
            "ok": True,
            "connected": True,
            "wallet_address": wallet_address,
            "token_count": len(tokens),
            "tokens": tokens,
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