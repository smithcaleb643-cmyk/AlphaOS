import base64

from solders.transaction import VersionedTransaction

from core.alpha_wallet_manager import load_alpha_keypair


def sign_swap_transaction(swap_transaction_base64):
    try:
        if not swap_transaction_base64:
            return {
                "ok": False,
                "error": "Missing swap transaction.",
            }

        keypair = load_alpha_keypair()

        raw_transaction = base64.b64decode(swap_transaction_base64)
        unsigned_tx = VersionedTransaction.from_bytes(raw_transaction)

        signed_tx = VersionedTransaction(unsigned_tx.message, [keypair])

        signed_tx_base64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")

        return {
            "ok": True,
            "wallet_address": str(keypair.pubkey()),
            "signed_transaction": signed_tx_base64,
            "message": "Transaction signed locally but not sent.",
        }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error),
        }