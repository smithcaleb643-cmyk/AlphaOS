import json
import os

from solders.keypair import Keypair

SECRETS_DIR = os.path.join(os.path.dirname(__file__), "secrets")
WALLET_FILE = os.path.join(SECRETS_DIR, "alpha_trading_wallet.json")


def main():
    os.makedirs(SECRETS_DIR, exist_ok=True)

    if os.path.exists(WALLET_FILE):
        print("Alpha wallet already exists.")
        print("Not creating a new one.")
        return

    keypair = Keypair()
    secret_bytes = list(bytes(keypair))

    with open(WALLET_FILE, "w", encoding="utf-8") as file:
        json.dump(secret_bytes, file)

    print("Alpha trading wallet created.")
    print("Public address:")
    print(str(keypair.pubkey()))
    print("")
    print("Private key saved locally at:")
    print(WALLET_FILE)
    print("")
    print("Do NOT upload or share this file.")


if __name__ == "__main__":
    main()