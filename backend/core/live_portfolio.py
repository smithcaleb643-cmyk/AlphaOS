from core.live_wallet_reader import live_wallet_status
from core.live_trade_journal import load_live_trade_journal
from services.market_service import get_market_summary

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL_MINT = "So11111111111111111111111111111111111111112"


def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(float(value or default))
    except Exception:
        return default


def raw_to_ui_amount(raw_amount, decimals=6):
    return safe_float(raw_amount) / (10 ** decimals)


def get_current_token_price(token_address, fallback_price=0):
    current_price = safe_float(fallback_price)

    if not token_address:
        return current_price

    try:
        summary = get_market_summary(token_address)
        if summary.get("found") and safe_float(summary.get("price_usd")) > 0:
            current_price = safe_float(summary.get("price_usd"))
    except Exception as error:
        print("LIVE PORTFOLIO PRICE LOOKUP FAILED:", token_address, error)

    return current_price


def build_live_positions(open_buys, sells_by_mint):
    positions = []

    for trade in open_buys:
        signal = trade.get("signal", {}) or {}
        token_address = signal.get("token_address") or trade.get("token_address")

        symbol = signal.get("symbol") or signal.get("coin_name") or token_address or "UNKNOWN"

        bought_raw = safe_int(trade.get("out_amount_raw"))
        sold_raw = sells_by_mint.get(token_address, 0)
        remaining_raw = max(0, bought_raw - sold_raw)

        if remaining_raw <= 0:
            continue

        entry_price = safe_float(signal.get("price_usd"))
        quantity = raw_to_ui_amount(remaining_raw, 6)
        original_quantity = raw_to_ui_amount(bought_raw, 6)
        current_price = get_current_token_price(token_address, entry_price)

        entry_value_usd = safe_float(trade.get("swap_usd_value"))
        remaining_ratio = remaining_raw / bought_raw if bought_raw else 1
        remaining_entry_value_usd = entry_value_usd * remaining_ratio

        current_value_usd = quantity * current_price if current_price else 0
        pnl_usd = current_value_usd - remaining_entry_value_usd if remaining_entry_value_usd else 0
        pnl_percent = (pnl_usd / remaining_entry_value_usd * 100) if remaining_entry_value_usd else 0

        positions.append({
            "trade_id": trade.get("id"),
            "symbol": symbol,
            "coin_name": signal.get("coin_name") or symbol,
            "mint": token_address,
            "quantity": quantity,
            "original_quantity": original_quantity,
            "amount_raw": str(remaining_raw),
            "original_amount_raw": str(bought_raw),
            "entry_price": entry_price,
            "current_price": current_price,
            "entry_value_usd": remaining_entry_value_usd,
            "original_entry_value_usd": entry_value_usd,
            "current_value_usd": current_value_usd,
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent,
            "entry_score": signal.get("score"),
            "probability": signal.get("probability"),
            "risk_score": signal.get("risk_score"),
            "reason": signal.get("reason"),
            "entry_time": trade.get("created_at"),
            "signature": trade.get("signature"),
            "tp1_hit": trade.get("tp1_hit", False),
            "tp2_hit": trade.get("tp2_hit", False),
            "tp3_hit": trade.get("tp3_hit", False),
            "runner_mode": trade.get("runner_mode", False),
            "highest_seen": trade.get("highest_seen", entry_price),
            "stop_loss": trade.get("stop_loss", entry_price * 0.90 if entry_price else 0),
            "partial_exits": trade.get("partial_exits", []),
        })

    return positions


def get_live_portfolio():
    wallet = live_wallet_status()
    journal = load_live_trade_journal()

    tokens = wallet.get("tokens", [])
    trades = journal.get("trades", [])

    usdc = 0
    wallet_balances = {}

    for token in tokens:
        mint = token.get("mint")
        amount = safe_float(token.get("amount"))

        if mint == USDC_MINT:
            usdc = amount

        if mint:
            wallet_balances[mint] = amount

    sent_buys = [
        t for t in trades
        if (
            t.get("status") == "SENT"
            and t.get("type") == "BUY"
            and t.get("input_mint") == SOL_MINT
            and t.get("token_address") != SOL_MINT
        )
    ]

    sent_sells = [
        t for t in trades
        if (
            t.get("status") in ["SENT", "CONFIRMED"]
            and t.get("type") == "SELL"
        )
    ]

    sells_by_mint = {}
    for sell in sent_sells:
        mint = sell.get("token_address") or sell.get("input_mint")
        sells_by_mint[mint] = sells_by_mint.get(mint, 0) + safe_int(sell.get("in_amount_raw"))

    positions = build_live_positions(sent_buys, sells_by_mint)

    verified_positions = []

    for position in positions:
        mint = position.get("mint")
        wallet_amount = wallet_balances.get(mint, 0)

        if wallet_amount <= 0:
            print(f"Skipping ghost position: {mint}")
            continue

        position["quantity"] = wallet_amount
        position["amount_raw"] = str(int(wallet_amount * (10 ** 6)))

        verified_positions.append(position)

    positions = verified_positions

    unrealized_pnl = sum(
        safe_float(p.get("pnl_usd"))
        for p in positions
    )

    return {
        "ok": True,
        "wallet_address": wallet.get("wallet_address"),
        "sol_balance": wallet.get("sol_balance", 0),
        "token_count": wallet.get("token_count", 0),
        "tokens": tokens,
        "positions": positions,
        "usdc_balance": usdc,
        "open_positions": len(positions),
        "trades_today": len(sent_buys) + len(sent_sells),
        "realized_pnl_usd": 0,
        "unrealized_pnl_usd": unrealized_pnl,
        "today_pnl_usd": unrealized_pnl,
        "journal_count": journal.get("count", len(trades)),
    }