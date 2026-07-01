from core.live_wallet_reader import live_wallet_status
from core.live_trade_journal import load_live_trade_journal


USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def get_live_portfolio():
    wallet = live_wallet_status()
    journal = load_live_trade_journal()

    tokens = wallet.get("tokens", [])
    trades = journal.get("trades", [])

    usdc = 0

    for token in tokens:
        if token.get("mint") == USDC_MINT:
            usdc = token.get("amount", 0)

    sent_trades = [t for t in trades if t.get("status") == "SENT"]

    return {
        "ok": True,
        "wallet_address": wallet.get("wallet_address"),
        "sol_balance": wallet.get("sol_balance", 0),
        "token_count": wallet.get("token_count", 0),
        "tokens": tokens,
        "usdc_balance": usdc,
        "open_positions": len(sent_trades),
        "trades_today": len(sent_trades),
        "realized_pnl_usd": 0,
        "unrealized_pnl_usd": 0,
        "today_pnl_usd": 0,
        "journal_count": journal.get("count", 0),
    }