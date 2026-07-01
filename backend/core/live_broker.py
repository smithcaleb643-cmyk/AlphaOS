from core.broker import Broker, broker_response
from core.live_wallet_reader import live_wallet_status
from core.live_swap_builder import build_swap_transaction
from core.live_execution_safety import evaluate_swap_build
from core.live_risk_guard import approve_live_buy
from core.live_transaction_sender import send_signed_transaction


class LiveBroker(Broker):
    def __init__(self):
        self.enabled = False
        self.auto_trading_enabled = False
        self.max_trade_sol = 0.01

    def buy(self, signal: dict):
        if not self.enabled:
            return broker_response(
                ok=False,
                message="Live broker is disabled.",
                data={"signal": signal},
            )

        wallet = live_wallet_status()
        sol_balance = float(wallet.get("sol_balance") or 0)

        output_mint = signal.get("token_address")
        sol_amount = float(signal.get("sol_amount") or self.max_trade_sol)

        if not output_mint:
            return broker_response(
                ok=False,
                message="Live buy blocked: token_address missing.",
                data={"signal": signal},
            )

        risk = approve_live_buy(
            sol_amount=sol_amount,
            sol_balance=sol_balance,
        )

        if not risk.get("approved"):
            return broker_response(
                ok=False,
                message="Live buy blocked by live risk guard.",
                data={
                    "risk": risk,
                    "wallet": wallet,
                    "signal": signal,
                },
            )

        swap = build_swap_transaction(
            output_mint=output_mint,
            sol_amount=sol_amount,
            slippage_bps=100,
        )

        safety = evaluate_swap_build(swap)

        if not safety.get("approved"):
            return broker_response(
                ok=False,
                message="Live buy blocked by execution safety.",
                data={
                    "swap": swap,
                    "safety": safety,
                    "risk": risk,
                },
            )

        # 🔥 REAL EXECUTION STEP (THIS WAS MISSING BEFORE)
        result = send_signed_transaction(swap)

        return broker_response(
            ok=result.get("ok", False),
            message="Live trade executed" if result.get("ok") else "Live trade failed",
            data={
                "swap": swap,
                "safety": safety,
                "risk": risk,
                "execution": result,
            },
        )

    def sell(self, trade_id: int, reason: str = "MANUAL_SELL"):
        return broker_response(
            ok=False,
            message="Live selling is not enabled yet.",
            data={"trade_id": trade_id, "reason": reason},
        )

    def get_balance(self):
        return broker_response(
            ok=True,
            message="Live wallet status loaded.",
            data=live_wallet_status(),
        )

    def get_positions(self):
        wallet = live_wallet_status()

        return broker_response(
            ok=True,
            message="Live wallet positions loaded.",
            data={
                "tokens": wallet.get("tokens", []),
                "token_count": wallet.get("token_count", 0),
            },
        )


live_broker = LiveBroker()