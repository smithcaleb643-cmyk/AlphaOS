import json
import os

from solders.keypair import Keypair

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WALLET_FILE = os.path.join(BACKEND_DIR, "secrets", "alpha_trading_wallet.json")


def load_alpha_keypair():
    if not os.path.exists(WALLET_FILE):
        raise FileNotFoundError("Alpha trading wallet file not found.")

    with open(WALLET_FILE, "r", encoding="utf-8") as file:
        secret_bytes = json.load(file)

    return Keypair.from_bytes(bytes(secret_bytes))


def get_alpha_wallet_address():
    keypair = load_alpha_keypair()
    return str(keypair.pubkey())


def get_alpha_wallet_status():
    try:
        address = get_alpha_wallet_address()

        return {
            "ok": True,
            "wallet_loaded": True,
            "wallet_address": address,
            "wallet_file_exists": os.path.exists(WALLET_FILE),
        }

    except Exception as error:
        return {
            "ok": False,
            "wallet_loaded": False,
            "wallet_file_exists": os.path.exists(WALLET_FILE),
            "error": str(error),
        }