from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

def sign_swap(result, keypair: Keypair):
    try:
        tx = result["transaction"]

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