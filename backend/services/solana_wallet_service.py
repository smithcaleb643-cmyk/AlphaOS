import requests
from datetime import datetime

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"


def rpc_call(method, params):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    response = requests.post(SOLANA_RPC_URL, json=payload, timeout=15)
    return response.json()


def get_token_signatures(token_address, limit=15):
    data = rpc_call(
        "getSignaturesForAddress",
        [
            token_address,
            {
                "limit": limit,
            },
        ],
    )

    return data.get("result", []) or []


def get_transaction(signature):
    data = rpc_call(
        "getTransaction",
        [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
            },
        ],
    )

    return data.get("result")


def extract_wallets_from_transaction(tx):
    wallets = set()

    if not tx:
        return []

    transaction = tx.get("transaction", {})
    message = transaction.get("message", {})
    account_keys = message.get("accountKeys", [])

    for account in account_keys:
        if isinstance(account, dict):
            pubkey = account.get("pubkey")
            signer = account.get("signer", False)

            if pubkey and signer:
                wallets.add(pubkey)

    return list(wallets)


def scan_token_wallets(token_address, limit=15):
    signatures = get_token_signatures(token_address, limit=limit)

    wallets = []
    events = []

    for sig_data in signatures:
        signature = sig_data.get("signature")

        if not signature:
            continue

        tx = get_transaction(signature)
        tx_wallets = extract_wallets_from_transaction(tx)

        for wallet in tx_wallets:
            wallets.append(wallet)

            events.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "token_address": token_address,
                    "wallet": wallet,
                    "signature": signature,
                    "source": "public_solana_rpc",
                }
            )

    clean_wallets = []
    seen = set()

    for wallet in wallets:
        if wallet not in seen:
            seen.add(wallet)
            clean_wallets.append(wallet)

    return {
        "ok": True,
        "token_address": token_address,
        "wallets_found": len(clean_wallets),
        "wallets": clean_wallets,
        "events": events,
        "source": "public_solana_rpc",
    }