import os
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction


def load_keypair():
    raw = os.getenv("WALLET_PRIVATE_KEY")

    if not raw:
        return None

    try:
        secret = bytes(int(x) for x in raw.split(","))
        return Keypair.from_bytes(secret)
    except:
        return None


def sign_swap_transaction(swap_tx_base64: str, keypair=None):
    if keypair is None:
        keypair = load_keypair()

    if keypair is None:
        return {"ok": False, "error": "Missing wallet keypair"}

    try:
        tx_bytes = base64.b64decode(swap_tx_base64)

        tx = VersionedTransaction.from_bytes(tx_bytes)

        message_bytes = bytes(tx.message)

        signature = keypair.sign_message(message_bytes)

        signed_tx = VersionedTransaction.populate(tx.message, [signature])

        final_b64 = base64.b64encode(bytes(signed_tx)).decode("utf-8")

        return {
            "ok": True,
            "signed_transaction": final_b64,
            "wallet_address": str(keypair.pubkey()),
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }