from core.live_trade_journal import load_live_trade_journal
from core.live_trade_ledger import all_trades, get_open_trades, get_closed_trades
from core.live_portfolio import get_live_portfolio


def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


def bucket_score(score):
    score = safe_float(score)

    if score >= 80:
        return "80-100"
    if score >= 70:
        return "70-79"
    if score >= 60:
        return "60-69"
    if score >= 50:
        return "50-59"

    return "0-49"


def build_live_analytics():
    journal = load_live_trade_journal()
    portfolio = get_live_portfolio()

    trades = journal.get("trades", [])
    ledger = all_trades()

    buys = [t for t in trades if t.get("type") == "BUY"]
    sells = [t for t in trades if t.get("type") == "SELL"]

    successful_buys = [t for t in buys if t.get("status") == "SENT"]
    failed_buys = [t for t in buys if t.get("status") == "FAILED"]

    confirmed_sells = [
        t for t in sells
        if t.get("stage") == "CONFIRMED"
        or t.get("message") == "Sell confirmed"
    ]

    failed_sells = [
        t for t in sells
        if t.get("stage") in ["SEND_FAIL", "EXCEPTION", "UNCONFIRMED"]
        or t.get("status") == "FAILED"
    ]

    score_buckets = {}

    for buy in successful_buys:
        signal = buy.get("signal", {}) or {}
        score = signal.get("score")
        bucket = bucket_score(score)

        if bucket not in score_buckets:
            score_buckets[bucket] = {
                "count": 0,
                "tokens": [],
            }

        score_buckets[bucket]["count"] += 1

        token = buy.get("token_address")
        if token and token not in score_buckets[bucket]["tokens"]:
            score_buckets[bucket]["tokens"].append(token)

    tokens_traded = {}

    for trade in trades:
        token = trade.get("token_address")
        if not token:
            continue

        if token not in tokens_traded:
            tokens_traded[token] = {
                "token": token,
                "symbol": (trade.get("signal", {}) or {}).get("symbol"),
                "coin_name": (trade.get("signal", {}) or {}).get("coin_name"),
                "buys": 0,
                "sells": 0,
                "buy_usd": 0,
                "sell_usd": 0,
            }

        if trade.get("type") == "BUY":
            tokens_traded[token]["buys"] += 1
            tokens_traded[token]["buy_usd"] += safe_float(trade.get("swap_usd_value"))

        if trade.get("type") == "SELL":
            tokens_traded[token]["sells"] += 1
            tokens_traded[token]["sell_usd"] += safe_float(trade.get("swap_usd_value"))

    token_rows = list(tokens_traded.values())

    for row in token_rows:
        row["net_usd"] = row["sell_usd"] - row["buy_usd"]

    token_rows = sorted(token_rows, key=lambda r: r["net_usd"])

    total_buy_usd = sum(safe_float(t.get("swap_usd_value")) for t in successful_buys)
    total_sell_usd = sum(safe_float(t.get("swap_usd_value")) for t in confirmed_sells)

    scores = [
        safe_float((t.get("signal", {}) or {}).get("score"))
        for t in successful_buys
        if (t.get("signal", {}) or {}).get("score") is not None
    ]

    avg_score = sum(scores) / len(scores) if scores else 0

    unrealized_pnl = safe_float(portfolio.get("unrealized_pnl_usd"))
    fee_burn_estimate = max(0, total_buy_usd - total_sell_usd - unrealized_pnl)

    exit_reasons = {}

    for sell in sells:
        signal = sell.get("signal", {}) or {}
        reason = signal.get("exit_reason") or sell.get("stage") or "UNKNOWN"
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    return {
        "ok": True,
        "summary": {
            "journal_count": journal.get("count", len(trades)),
            "ledger_count": len(ledger),

            "total_buys": len(buys),
            "successful_buys": len(successful_buys),
            "failed_buys": len(failed_buys),

            "total_sells": len(sells),
            "confirmed_sells": len(confirmed_sells),
            "failed_sells": len(failed_sells),

            "open_positions": portfolio.get("open_positions", 0),
            "open_ledger_trades": len(get_open_trades()),
            "closed_ledger_trades": len(get_closed_trades()),

            "total_buy_usd": total_buy_usd,
            "total_sell_usd": total_sell_usd,
            "net_realized_like_usd": total_sell_usd - total_buy_usd,

            "suspected_fee_or_untracked_loss_usd": fee_burn_estimate,
            "average_buy_score": avg_score,
        },
        "score_buckets": score_buckets,
        "tokens": {
            "worst": token_rows[:8],
            "best": list(reversed(token_rows[-8:])),
            "count": len(token_rows),
        },
        "exit_reasons": exit_reasons,
        "portfolio": portfolio,
    }


# Alias so either import name works.
def live_analytics():
    return build_live_analytics()
