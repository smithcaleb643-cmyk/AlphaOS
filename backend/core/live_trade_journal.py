import json
import os
from datetime import datetime

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
JOURNAL_FILE = os.path.join(DATA_DIR, "live_trade_journal.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_live_trade_journal():
    ensure_data_dir()

    if not os.path.exists(JOURNAL_FILE):
        return {
            "ok": True,
            "count": 0,
            "trades": [],
        }

    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as file:
            trades = json.load(file)

        return {
            "ok": True,
            "count": len(trades),
            "trades": trades,
        }

    except Exception as error:
        return {
            "ok": False,
            "count": 0,
            "trades": [],
            "error": str(error),
        }


def save_live_trade_journal(trades):
    ensure_data_dir()

    with open(JOURNAL_FILE, "w", encoding="utf-8") as file:
        json.dump(trades, file, indent=2)


def record_live_buy(execution_result, signal=None):
    journal = load_live_trade_journal()
    trades = journal.get("trades", [])

    built = execution_result.get("built", {})
    quote = built.get("quote", {})
    sent = execution_result.get("sent", {})

    trade = {
        "id": len(trades) + 1,
        "type": "BUY",
        "status": "SENT" if execution_result.get("ok") else "FAILED",
        "created_at": datetime.utcnow().isoformat(),
        "wallet_address": built.get("wallet_address"),
        "token_address": built.get("output_mint"),
        "sol_amount": built.get("sol_amount"),
        "slippage_bps": built.get("slippage_bps"),
        "input_mint": quote.get("inputMint"),
        "output_mint": quote.get("outputMint"),
        "in_amount_raw": quote.get("inAmount"),
        "out_amount_raw": quote.get("outAmount"),
        "swap_usd_value": quote.get("swapUsdValue"),
        "price_impact_pct": quote.get("priceImpactPct"),
        "signature": execution_result.get("signature") or sent.get("signature"),
        "stage": execution_result.get("stage"),
        "message": execution_result.get("message"),
        "error": execution_result.get("error"),
        "signal": signal or {},
    }

    trades.append(trade)
    save_live_trade_journal(trades)

    return trade

def record_live_sell(execution_result, signal=None):
    journal = load_live_trade_journal()
    trades = journal.get("trades", [])

    built = execution_result.get("built", {})
    quote = built.get("quote", {})
    sent = execution_result.get("sent", {})

    trade = {
        "id": len(trades) + 1,
        "type": "SELL",
        "status": "SENT" if execution_result.get("ok") else "FAILED",
        "created_at": datetime.utcnow().isoformat(),
        "wallet_address": built.get("wallet_address"),
        "token_address": built.get("input_mint"),
        "slippage_bps": built.get("slippage_bps"),
        "input_mint": quote.get("inputMint"),
        "output_mint": quote.get("outputMint"),
        "in_amount_raw": quote.get("inAmount"),
        "out_amount_raw": quote.get("outAmount"),
        "swap_usd_value": quote.get("swapUsdValue"),
        "price_impact_pct": quote.get("priceImpactPct"),
        "signature": execution_result.get("signature") or sent.get("signature"),
        "stage": execution_result.get("stage"),
        "message": execution_result.get("message"),
        "error": execution_result.get("error"),
        "signal": signal or {},
    }

    trades.append(trade)
    save_live_trade_journal(trades)
    return trade
