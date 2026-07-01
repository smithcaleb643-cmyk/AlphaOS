import os
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction


# -----------------------------
# LOAD WALLET
# -----------------------------
def load_keypair():
    raw = os.getenv("WALLET_PRIVATE_KEY")

    if not raw:
        return None

    try:
        secret = bytes(int(x) for x in raw.split(","))
        return Keypair.from_bytes(secret)
    except Exception as e:
        return None


# -----------------------------
# SIGN SWAP TX (FIXED FOR SOLDERS 0.28.0)
# -----------------------------
def sign_swap_transaction(swap_tx_base64: str, keypair=None):
    """
    FIXED FOR solders 0.28.0
    """

    if keypair is None:
        keypair = load_keypair()

    if keypair is None:
        return {
            "ok": False,
            "error": "Missing wallet keypair"
        }

    try:
        # decode Jupiter transaction
        tx_bytes = base64.b64decode(swap_tx_base64)

        # load transaction
        tx = VersionedTransaction.from_bytes(tx_bytes)

        # -----------------------------
        # IMPORTANT FIX FOR 0.28.0
        # -----------------------------
        # You must sign the MESSAGE, not the transaction object

        message_bytes = bytes(tx.message)
        signature = keypair.sign_message(message_bytes)

        # attach signature manually
        signed_tx = VersionedTransaction.populate(tx.message, [signature])

        # serialize
        final_bytes = bytes(signed_tx)
        final_b64 = base64.b64encode(final_bytes).decode()

        return {
            "ok": True,
            "wallet_address": str(keypair.pubkey()),
            "signed_transaction": final_b64
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }