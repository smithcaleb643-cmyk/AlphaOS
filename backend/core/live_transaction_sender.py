import base64
import requests
import time

RPC_URL = "https://api.mainnet-beta.solana.com"


def extract_tx(tx):
    if not tx:
        return None

    if isinstance(tx, str):
        return tx

    if isinstance(tx, dict):
        return (
            tx.get("signed_transaction")
            or tx.get("swap_transaction")
            or tx.get("raw")
        )

    return None


def rpc_send(tx_b64):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sendTransaction",
        "params": [
            tx_b64,
            {
                "encoding": "base64",
                "skipPreflight": True,   # 🔥 IMPORTANT FIX
                "maxRetries": 3
            }
        ]
    }

    return requests.post(RPC_URL, json=payload, timeout=20).json()


def send_signed_transaction(signed_transaction):
    try:
        tx = extract_tx(signed_transaction)

        if not tx:
            return {"ok": False, "error": "Missing transaction"}

        # 🔥 retry loop (THIS IS THE STABILIZER)
        last_error = None

        for _ in range(3):
            result = rpc_send(tx)

            if "result" in result:
                return {
                    "ok": True,
                    "signature": result["result"]
                }

            last_error = result.get("error")

            # small delay before retry
            time.sleep(0.4)

        return {
            "ok": False,
            "error": last_error
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }