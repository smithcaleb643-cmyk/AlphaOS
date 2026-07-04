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
    return safe_float(raw_amount) / (10 ** int(decimals or 0))


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


def _wallet_token_index(tokens):
    balances = {}

    for token in tokens:
        mint = token.get("mint")

        if not mint:
            continue

        balances[mint] = {
            "mint": mint,
            "amount": safe_float(token.get("amount")),
            "amount_raw": safe_int(token.get("amount_raw")),
            "decimals": safe_int(token.get("decimals"), 6),
            "program_id": token.get("program_id"),
        }

    return balances


def _is_live_buy(trade):
    return (
        trade.get("status") == "SENT"
        and trade.get("type") == "BUY"
        and trade.get("input_mint") == SOL_MINT
        and trade.get("token_address") != SOL_MINT
    )


def _is_live_sell(trade):
    return (
        trade.get("status") in ["SENT", "CONFIRMED"]
        and trade.get("type") == "SELL"
    )


def _group_buys_by_mint(trades):
    grouped = {}

    for trade in trades:
        if not _is_live_buy(trade):
            continue

        signal = trade.get("signal", {}) or {}
        mint = (
            trade.get("token_address")
            or trade.get("output_mint")
            or signal.get("token_address")
        )

        if not mint or mint in [SOL_MINT, USDC_MINT]:
            continue

        grouped.setdefault(mint, []).append(trade)

    return grouped


def _sells_by_mint(trades):
    sold = {}

    for trade in trades:
        if not _is_live_sell(trade):
            continue

        mint = (
            trade.get("token_address")
            or trade.get("input_mint")
            or (trade.get("signal", {}) or {}).get("token_address")
            or (trade.get("signal", {}) or {}).get("input_mint")
        )

        if not mint:
            continue

        sold[mint] = sold.get(mint, 0) + safe_int(trade.get("in_amount_raw"))

    return sold


def _latest_trade(trades):
    if not trades:
        return {}

    return sorted(
        trades,
        key=lambda trade: safe_int(trade.get("id")),
        reverse=True,
    )[0]


def _merge_partial_exits(trades):
    exits = []

    for trade in trades:
        trade_exits = trade.get("partial_exits", [])
        if isinstance(trade_exits, list):
            exits.extend(trade_exits)

    return exits


def _any_trade_flag(trades, key, default=False):
    for trade in trades:
        if trade.get(key) is True:
            return True

    return default


def _max_trade_value(trades, key, fallback=0):
    values = [safe_float(trade.get(key)) for trade in trades if trade.get(key) is not None]
    values = [value for value in values if value > 0]

    if not values:
        return fallback

    return max(values)


def build_live_positions(open_buys_by_mint, sells_by_mint, wallet_balances):
    """
    Build ONE managed live position per wallet mint.

    Important:
    The wallet is the source of truth for current quantity.
    The journal is history/cost basis.

    Old bug:
    Every BUY trade became its own position, then each got overwritten with the full
    wallet balance. That made Alpha think one wallet bag was several separate bags.

    New behavior:
    Multiple BUY trades for the same mint are merged into one live position.
    """

    positions = []

    for mint, buy_trades in open_buys_by_mint.items():
        wallet_token = wallet_balances.get(mint)

        if not wallet_token:
            print(f"Skipping ghost position: {mint}")
            continue

        wallet_raw = safe_int(wallet_token.get("amount_raw"))
        wallet_quantity = safe_float(wallet_token.get("amount"))
        decimals = safe_int(wallet_token.get("decimals"), 6)

        if wallet_raw <= 0 or wallet_quantity <= 0:
            print(f"Skipping empty wallet position: {mint}")
            continue

        latest = _latest_trade(buy_trades)
        signal = latest.get("signal", {}) or {}

        symbol = (
            signal.get("symbol")
            or signal.get("coin_name")
            or latest.get("symbol")
            or mint
            or "UNKNOWN"
        )

        total_bought_raw = sum(safe_int(trade.get("out_amount_raw")) for trade in buy_trades)
        total_sold_raw = safe_int(sells_by_mint.get(mint, 0))
        journal_remaining_raw = max(0, total_bought_raw - total_sold_raw)

        total_entry_value_usd = sum(
            safe_float(trade.get("swap_usd_value"))
            for trade in buy_trades
        )

        original_quantity = raw_to_ui_amount(total_bought_raw, decimals)

        if total_bought_raw > 0:
            wallet_remaining_ratio = min(1.0, wallet_raw / total_bought_raw)
        else:
            wallet_remaining_ratio = 1.0

        remaining_entry_value_usd = total_entry_value_usd * wallet_remaining_ratio

        if original_quantity > 0:
            average_entry_price = total_entry_value_usd / original_quantity
        else:
            average_entry_price = safe_float(signal.get("price_usd"))

        current_price = get_current_token_price(mint, average_entry_price)

        current_value_usd = wallet_quantity * current_price if current_price else 0
        pnl_usd = current_value_usd - remaining_entry_value_usd if remaining_entry_value_usd else 0
        pnl_percent = (pnl_usd / remaining_entry_value_usd * 100) if remaining_entry_value_usd else 0

        highest_seen = max(
            _max_trade_value(buy_trades, "highest_seen", average_entry_price),
            current_price,
            average_entry_price,
        )

        stop_loss = _max_trade_value(
            buy_trades,
            "stop_loss",
            average_entry_price * 0.90 if average_entry_price else 0,
        )

        trade_ids = [trade.get("id") for trade in buy_trades if trade.get("id") is not None]

        positions.append({
            "trade_id": latest.get("id"),
            "trade_ids": trade_ids,
            "merged_buys": len(buy_trades),
            "symbol": symbol,
            "coin_name": signal.get("coin_name") or symbol,
            "mint": mint,

            # Wallet-backed current quantity.
            "quantity": wallet_quantity,
            "amount_raw": str(wallet_raw),
            "decimals": decimals,

            # Journal-backed accumulated entry/cost basis.
            "original_quantity": original_quantity,
            "original_amount_raw": str(total_bought_raw),
            "journal_remaining_raw": str(journal_remaining_raw),
            "journal_sold_raw": str(total_sold_raw),

            "entry_price": average_entry_price,
            "current_price": current_price,
            "entry_value_usd": remaining_entry_value_usd,
            "original_entry_value_usd": total_entry_value_usd,
            "current_value_usd": current_value_usd,
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent,

            "entry_score": signal.get("score"),
            "probability": signal.get("probability"),
            "risk_score": signal.get("risk_score"),
            "reason": signal.get("reason"),
            "entry_time": latest.get("created_at"),
            "signature": latest.get("signature"),

            # One state per live wallet bag.
            "tp1_hit": _any_trade_flag(buy_trades, "tp1_hit", False),
            "tp2_hit": _any_trade_flag(buy_trades, "tp2_hit", False),
            "tp3_hit": _any_trade_flag(buy_trades, "tp3_hit", False),
            "runner_mode": _any_trade_flag(buy_trades, "runner_mode", False),
            "highest_seen": highest_seen,
            "stop_loss": stop_loss,
            "partial_exits": _merge_partial_exits(buy_trades),
        })

    return positions


def get_live_portfolio():
    wallet = live_wallet_status()
    journal = load_live_trade_journal()

    tokens = wallet.get("tokens", [])
    trades = journal.get("trades", [])

    usdc = 0
    wallet_balances = _wallet_token_index(tokens)

    for token in tokens:
        if token.get("mint") == USDC_MINT:
            usdc = safe_float(token.get("amount"))

    sent_buys = [
        trade for trade in trades
        if _is_live_buy(trade)
    ]

    sent_sells = [
        trade for trade in trades
        if _is_live_sell(trade)
    ]

    buys_by_mint = _group_buys_by_mint(sent_buys)
    sold_by_mint = _sells_by_mint(sent_sells)

    positions = build_live_positions(
        open_buys_by_mint=buys_by_mint,
        sells_by_mint=sold_by_mint,
        wallet_balances=wallet_balances,
    )

    unrealized_pnl = sum(
        safe_float(position.get("pnl_usd"))
        for position in positions
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
