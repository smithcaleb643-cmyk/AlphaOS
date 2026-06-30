from core.broker import Broker, broker_response


class LiveBroker(Broker):
    def __init__(self):
        self.enabled = False
        self.manual_approval_required = True

    def buy(self, signal: dict):
        return broker_response(
            ok=False,
            message="Live trading is not enabled yet. Manual approval mode must be built first.",
            data={
                "signal": signal,
                "execution_mode": "LIVE_DISABLED",
            },
        )

    def sell(self, trade_id: int, reason: str = "MANUAL_SELL"):
        return broker_response(
            ok=False,
            message="Live selling is not enabled yet.",
            data={
                "trade_id": trade_id,
                "reason": reason,
                "execution_mode": "LIVE_DISABLED",
            },
        )

    def get_balance(self):
        return broker_response(
            ok=True,
            message="Live broker read-only placeholder.",
            data={
                "connected": False,
                "sol_balance": 0,
                "message": "Wallet connection not configured yet.",
            },
        )

    def get_positions(self):
        return broker_response(
            ok=True,
            message="Live broker positions placeholder.",
            data={
                "positions": [],
                "message": "Wallet connection not configured yet.",
            },
        )


live_broker = LiveBroker()