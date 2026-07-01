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


def build_live_positions(open_buys):
    positions = []

    for trade in open_buys:
        signal = trade.get("signal", {}) or {}
        token_address = signal.get("token_address") or trade.get("token_address")

        symbol = (
            signal.get("symbol")
            or signal.get("coin_name")
            or token_address
            or "UNKNOWN"
        )

        entry_price = safe_float(signal.get("price_usd"))
        quantity = raw_to_ui_amount(trade.get("out_amount_raw"), 6)
        current_price = get_current_token_price(token_address, entry_price)

        current_value_usd = quantity * current_price if current_price else 0
        entry_value_usd = safe_float(trade.get("swap_usd_value"))

        pnl_usd = current_value_usd - entry_value_usd if entry_value_usd else 0
        pnl_percent = (pnl_usd / entry_value_usd * 100) if entry_value_usd else 0

        positions.append({
            "symbol": symbol,
            "coin_name": signal.get("coin_name") or symbol,
            "mint": token_address,
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": current_price,
            "entry_value_usd": entry_value_usd,
            "current_value_usd": current_value_usd,
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent,
            "entry_score": signal.get("score"),
            "probability": signal.get("probability"),
            "risk_score": signal.get("risk_score"),
            "reason": signal.get("reason"),
            "entry_time": trade.get("created_at"),
            "signature": trade.get("signature"),
        })

    return positions


def get_live_portfolio():
    wallet = live_wallet_status()
    journal = load_live_trade_journal()

    tokens = wallet.get("tokens", [])
    trades = journal.get("trades", [])

    usdc = 0

    for token in tokens:
        if token.get("mint") == USDC_MINT:
            usdc = token.get("amount", 0)

    wallet_mints = {
        token.get("mint")
        for token in tokens
        if safe_float(token.get("amount")) > 0
    }

    sent_buys = [
        t for t in trades
        if (
            t.get("status") == "SENT"
            and t.get("type") == "BUY"
            and t.get("input_mint") == SOL_MINT
            and t.get("token_address") in wallet_mints
        )
    ]

    sent_sells = [
        t for t in trades
        if (
            t.get("status") == "SENT"
            and t.get("type") == "SELL"
        )
    ]

    sold_mints = {
        t.get("token_address")
        for t in sent_sells
    }

    open_buys = [
        t for t in sent_buys
        if t.get("token_address") not in sold_mints
    ]

    positions = build_live_positions(open_buys)

    unrealized_pnl = sum(safe_float(p.get("pnl_usd")) for p in positions)

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
        "journal_count": journal.get("count", 0),
    }