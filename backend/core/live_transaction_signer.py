import os
import base64

from solders.keypair import Keypair
from solders.transaction import VersionedTransaction


def load_keypair():
    raw = os.getenv("SOLANA_PRIVATE_KEY") or os.getenv("WALLET_PRIVATE_KEY")

    if not raw:
        return None

    raw = raw.strip()

    try:
        return Keypair.from_base58_string(raw)
    except Exception:
        pass

    try:
        raw = raw.strip("[]")
        secret = bytes(int(x.strip()) for x in raw.split(","))
        return Keypair.from_bytes(secret)
    except Exception:
        return None


def sign_swap_transaction(swap_tx_base64: str, keypair=None):
    if keypair is None:
        keypair = load_keypair()

    if keypair is None:
        return {"ok": False, "error": "Missing wallet keypair"}

    try:
        tx_bytes = base64.b64decode(swap_tx_base64)
        tx = VersionedTransaction.from_bytes(tx_bytes)

        signed_tx = VersionedTransaction(tx.message, [keypair])

        return {
            "ok": True,
            "signed_transaction": base64.b64encode(bytes(signed_tx)).decode("utf-8"),
            "wallet_address": str(keypair.pubkey()),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}