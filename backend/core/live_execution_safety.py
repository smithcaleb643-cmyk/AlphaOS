from core.broker import Broker, broker_response
from core.live_wallet_reader import live_wallet_status
from core.live_swap_builder import build_swap_transaction
from core.live_execution_safety import evaluate_swap_build


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

        output_mint = signal.get("token_address")
        sol_amount = float(signal.get("sol_amount") or self.max_trade_sol)

        if not output_mint:
            return broker_response(
                ok=False,
                message="Live buy blocked: token_address missing.",
                data={"signal": signal},
            )

        if sol_amount > self.max_trade_sol:
            return broker_response(
                ok=False,
                message=f"Live buy blocked: sol_amount exceeds max {self.max_trade_sol}.",
                data={"sol_amount": sol_amount},
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
                },
            )

        return broker_response(
            ok=True,
            message="Live swap built and approved by safety checks, but not signed or sent.",
            data={
                "swap": swap,
                "safety": safety,
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