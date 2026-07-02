from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
import base64


def sign_swap(result, keypair: Keypair):
    try:
        tx_b64 = result.get("swap_transaction") or result.get("swapTransaction")

        if not tx_b64:
            return {"ok": False, "error": "Missing swap transaction"}

        # decode base64 → bytes
        tx_bytes = base64.b64decode(tx_b64)

        # convert → VersionedTransaction
        tx = VersionedTransaction.from_bytes(tx_bytes)

        # sign
        signed_tx = VersionedTransaction(tx.message, [keypair])

        return {
            "ok": True,
            "signed_transaction": signed_tx
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }