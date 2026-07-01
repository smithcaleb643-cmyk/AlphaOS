import base64
import json

def sign_swap(swap_tx):
    try:
        # pretend serialization layer (placeholder for real keypair signing)
        serialized = json.dumps(swap_tx)

        encoded = base64.b64encode(serialized.encode()).decode()

        return {
            "ok": True,
            "signed_transaction": encoded
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }