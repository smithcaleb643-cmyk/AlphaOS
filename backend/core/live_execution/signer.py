from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
import base64


def sign_swap(result, keypair: Keypair):
    try:
        tx_b64 = result.get("swap_transaction") or result.get("swapTransaction")

        if not tx_b64:
            return {"ok": False, "error": "Missing swap transaction"}

        # decode base64
        tx_bytes = base64.b64decode(tx_b64)

        # deserialize transaction
        tx = VersionedTransaction.from_bytes(tx_bytes)

        # SIGNING FIX (correct solders method)
        signed_tx = VersionedTransaction(
            tx.message,
            [keypair]   # signer list
        )

        return {
            "ok": True,
            "signed_transaction": base64.b64encode(bytes(signed_tx)).decode("utf-8")
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }