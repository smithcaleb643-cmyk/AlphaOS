import base64
import requests

SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"


def rpc_call(method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    response = requests.post(SOLANA_RPC_URL, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def send_signed_transaction(signed_transaction_base64):
    try:
        if not signed_transaction_base64:
            return {
                "ok": False,
                "error": "Missing signed_transaction.",
            }

        raw_bytes = base64.b64decode(signed_transaction_base64)
        raw_base64 = base64.b64encode(raw_bytes).decode("utf-8")

        result = rpc_call(
            "sendTransaction",
            [
                raw_base64,
                {
                    "encoding": "base64",
                    "skipPreflight": False,
                    "preflightCommitment": "confirmed",
                    "maxRetries": 3,
                },
            ],
        )

        if "error" in result:
            return {
                "ok": False,
                "error": result["error"],
                "raw": result,
            }

        return {
            "ok": True,
            "signature": result.get("result"),
            "raw": result,
            "message": "Signed transaction sent to Solana.",
        }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error),
        }