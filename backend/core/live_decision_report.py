from core.live_execution_safety import evaluate_live_quote
from core.live_risk_guard import approve_live_buy
from core.live_wallet_reader import live_wallet_status
from core.jupiter_service import quote_sol_to_token


def build_live_decision_report(signal: dict):
    wallet = live_wallet_status()
    sol_balance = float(wallet.get("sol_balance") or 0)

    output_mint = signal.get("token_address")
    sol_amount = float(signal.get("sol_amount") or 0.01)

    if not output_mint:
        return {
            "ok": False,
            "decision": "BLOCK",
            "reason": "Missing token_address.",
            "signal": signal,
        }

    risk = approve_live_buy(
        sol_amount=sol_amount,
        sol_balance=sol_balance,
    )

    quote_result = quote_sol_to_token(
        output_mint=output_mint,
        sol_amount=sol_amount,
        slippage_bps=100,
    )

    quote = quote_result.get("quote", {}) if quote_result.get("ok") else {}
    execution = evaluate_live_quote(quote, sol_amount=sol_amount)

    approved = risk.get("approved") and execution.get("approved")

    return {
        "ok": True,
        "decision": "BUY_APPROVED" if approved else "BLOCK",
        "reason": "Live buy approved by risk and execution checks."
        if approved
        else "Live buy blocked by one or more safety checks.",
        "wallet": wallet,
        "signal": {
            "coin": signal.get("symbol") or signal.get("coin_name"),
            "token_address": output_mint,
            "score": signal.get("score"),
            "probability": signal.get("probability"),
            "risk_score": signal.get("risk_score"),
            "wallet_summary": signal.get("wallet_summary"),
            "sol_amount": sol_amount,
        },
        "risk_guard": risk,
        "quote_ok": quote_result.get("ok"),
        "execution_safety": execution,
        "quote_error": quote_result.get("error"),
        "quote": quote,
    }