import json
import os
from datetime import datetime

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
WALLET_FILE = os.path.join(DATA_DIR, "wallet_memory.json")


def ensure_data_folder():
    os.makedirs(DATA_DIR, exist_ok=True)


def default_wallet_memory():
    return {
        "wallets": {},
        "events": [],
        "learned_trade_ids": [],
        "last_updated": None,
    }


def now():
    return datetime.utcnow().isoformat()


def load_wallet_memory():
    ensure_data_folder()

    if not os.path.exists(WALLET_FILE):
        return default_wallet_memory()

    try:
        with open(WALLET_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        data.setdefault("wallets", {})
        data.setdefault("events", [])
        data.setdefault("learned_trade_ids", [])
        data.setdefault("last_updated", None)
        return data
    except Exception as error:
        print("WALLET MEMORY LOAD FAILED:", error)
        return default_wallet_memory()


wallet_memory = load_wallet_memory()


def save_wallet_memory():
    ensure_data_folder()
    temp_file = WALLET_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(wallet_memory, file, indent=2, ensure_ascii=False)

    with open(temp_file, "r", encoding="utf-8") as file:
        json.load(file)

    os.replace(temp_file, WALLET_FILE)


def normalize_wallet(wallet):
    if not wallet:
        return None

    wallet = str(wallet).strip()
    if len(wallet) < 32:
        return None

    return wallet


def get_wallet_profile(wallet):
    wallet = normalize_wallet(wallet)
    if not wallet:
        return None

    wallets = wallet_memory["wallets"]

    if wallet not in wallets:
        wallets[wallet] = {
            "address": wallet,
            "times_seen": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0,
            "average_pnl": 0,
            "win_rate": 0,
            "trust_score": 50,
            "rank": "UNKNOWN",
            "first_seen": now(),
            "last_seen": None,
            "notes": [],
            "tokens_seen": [],
        }

    return wallets[wallet]


def recalc_wallet(wallet_data):
    wins = int(wallet_data.get("wins") or 0)
    losses = int(wallet_data.get("losses") or 0)
    total = wins + losses
    pnl = float(wallet_data.get("total_pnl") or 0)

    wallet_data["average_pnl"] = round(pnl / total, 4) if total else 0
    wallet_data["win_rate"] = round((wins / total) * 100, 2) if total else 0

    trust = 50

    if total >= 3:
        trust += min(20, total * 2)

    if wallet_data["win_rate"] >= 70 and total >= 3:
        trust += 25
    elif wallet_data["win_rate"] >= 55 and total >= 3:
        trust += 12
    elif wallet_data["win_rate"] < 40 and total >= 3:
        trust -= 20

    if wallet_data["average_pnl"] > 5:
        trust += 15
    elif wallet_data["average_pnl"] < -3:
        trust -= 15

    wallet_data["trust_score"] = max(0, min(100, round(trust, 1)))

    if wallet_data["trust_score"] >= 85:
        wallet_data["rank"] = "ELITE"
    elif wallet_data["trust_score"] >= 70:
        wallet_data["rank"] = "TRUSTED"
    elif wallet_data["trust_score"] >= 50:
        wallet_data["rank"] = "NEUTRAL"
    elif wallet_data["trust_score"] >= 30:
        wallet_data["rank"] = "WEAK"
    else:
        wallet_data["rank"] = "DANGER"

    return wallet_data


def observe_wallet(wallet, token_address=None, coin_name=None, source="unknown"):
    profile = get_wallet_profile(wallet)
    if not profile:
        return None

    profile["times_seen"] += 1
    profile["last_seen"] = now()

    if token_address:
        profile.setdefault("tokens_seen", [])
        if token_address not in profile["tokens_seen"]:
            profile["tokens_seen"].append(token_address)
            profile["tokens_seen"] = profile["tokens_seen"][-100:]

    wallet_memory["events"].append({
        "timestamp": now(),
        "event": "WALLET_SEEN",
        "wallet": wallet,
        "token_address": token_address,
        "coin_name": coin_name,
        "source": source,
    })

    wallet_memory["events"] = wallet_memory["events"][-1000:]
    wallet_memory["last_updated"] = now()
    save_wallet_memory()

    return profile


def save_wallet_scan(token_address, wallets, coin_name=None, source="public_solana_rpc"):
    saved = []

    for wallet in wallets:
        profile = observe_wallet(
            wallet,
            token_address=token_address,
            coin_name=coin_name,
            source=source,
        )

        if profile:
            saved.append(profile)

    return {
        "saved_wallets": len(saved),
        "wallets": saved,
    }


def learn_wallet_outcome(wallet, pnl_usd, token_address=None, coin_name=None, trade_id=None):
    profile = get_wallet_profile(wallet)
    if not profile:
        return None

    pnl_usd = float(pnl_usd or 0)

    if pnl_usd >= 0:
        profile["wins"] += 1
    else:
        profile["losses"] += 1

    profile["total_pnl"] = round(float(profile.get("total_pnl") or 0) + pnl_usd, 4)
    profile["last_seen"] = now()

    if token_address:
        profile.setdefault("tokens_seen", [])
        if token_address not in profile["tokens_seen"]:
            profile["tokens_seen"].append(token_address)
            profile["tokens_seen"] = profile["tokens_seen"][-100:]

    recalc_wallet(profile)

    wallet_memory["events"].append({
        "timestamp": now(),
        "event": "WALLET_OUTCOME_LEARNED",
        "wallet": wallet,
        "token_address": token_address,
        "coin_name": coin_name,
        "trade_id": trade_id,
        "pnl_usd": pnl_usd,
        "rank": profile["rank"],
        "trust_score": profile["trust_score"],
    })

    wallet_memory["events"] = wallet_memory["events"][-1000:]
    wallet_memory["last_updated"] = now()

    return profile


def learn_wallets_from_closed_trades(paper_state):
    closed_trades = paper_state.get("closed_trades", [])
    learned_ids = set(str(x) for x in wallet_memory.get("learned_trade_ids", []))

    learned_count = 0
    wallet_updates = 0

    for trade in closed_trades:
        trade_id = str(trade.get("id"))

        if trade_id in learned_ids:
            continue

        token_address = trade.get("token_address")
        coin_name = trade.get("coin_name") or trade.get("symbol")

        wallets = trade.get("real_wallets") or trade.get("wallets") or []

        if not wallets and token_address:
            for wallet, profile in wallet_memory.get("wallets", {}).items():
                if token_address in profile.get("tokens_seen", []):
                    wallets.append(wallet)

        if not wallets:
            continue

        pnl = float(
            trade.get("final_pnl_usd")
            if trade.get("final_pnl_usd") is not None
            else trade.get("pnl_usd") or 0
        )

        for wallet in wallets:
            learned = learn_wallet_outcome(
                wallet,
                pnl_usd=pnl,
                token_address=token_address,
                coin_name=coin_name,
                trade_id=trade_id,
            )

            if learned:
                wallet_updates += 1

        learned_ids.add(trade_id)
        learned_count += 1

    wallet_memory["learned_trade_ids"] = list(learned_ids)
    wallet_memory["last_updated"] = now()
    save_wallet_memory()

    return {
        "learned_trades": learned_count,
        "wallet_updates": wallet_updates,
        "wallets_tracked": len(wallet_memory.get("wallets", {})),
    }


def apply_wallet_intelligence_to_signal(signal, coin):
    wallets = coin.get("wallets") or coin.get("real_wallets") or []

    if not wallets:
        signal["wallet_adjustment"] = 0
        signal["wallet_summary"] = "No wallet intelligence available yet."
        return signal

    adjustments = []
    profiles = []

    for wallet in wallets:
        profile = get_wallet_profile(wallet)

        if not profile:
            continue

        recalc_wallet(profile)
        profiles.append(profile)

        trust = float(profile.get("trust_score") or 50)

        if trust >= 85:
            adjustments.append(15)
        elif trust >= 70:
            adjustments.append(8)
        elif trust <= 25:
            adjustments.append(-20)
        elif trust <= 40:
            adjustments.append(-8)
        else:
            adjustments.append(0)

    if not profiles:
        signal["wallet_adjustment"] = 0
        signal["wallet_summary"] = "Wallets found, but no profiles available yet."
        return signal

    adjustment = round(sum(adjustments) / len(adjustments), 2) if adjustments else 0

    old_score = int(signal.get("score") or 0)
    signal["score"] = max(0, min(100, old_score + adjustment))
    signal["wallet_adjustment"] = adjustment

    best = sorted(profiles, key=lambda item: item.get("trust_score", 0), reverse=True)[0]

    signal["wallet_summary"] = (
        f"Wallet intelligence checked {len(profiles)} wallets. "
        f"Best wallet rank {best.get('rank')} with trust {best.get('trust_score')}."
    )

    signal["reason"] = f"{signal.get('reason', '')} Wallet adjustment {adjustment}. {signal['wallet_summary']}"

    return signal


def get_wallet_brain_report():
    wallets = list(wallet_memory.get("wallets", {}).values())
    wallets = sorted(wallets, key=lambda item: item.get("trust_score", 0), reverse=True)

    elite = [w for w in wallets if w.get("rank") == "ELITE"]
    trusted = [w for w in wallets if w.get("rank") == "TRUSTED"]
    danger = [w for w in wallets if w.get("rank") == "DANGER"]

    return {
        "wallets_tracked": len(wallets),
        "elite_wallets": len(elite),
        "trusted_wallets": len(trusted),
        "danger_wallets": len(danger),
        "top_wallets": wallets[:10],
        "recent_events": wallet_memory.get("events", [])[-20:],
        "learned_trade_ids": len(wallet_memory.get("learned_trade_ids", [])),
        "last_updated": wallet_memory.get("last_updated"),
    }