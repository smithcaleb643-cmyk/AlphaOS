from core.broker import Broker, broker_response
from core.paper_trader import (
    create_paper_trade,
    close_paper_trade,
    get_paper_state,
)


class PaperBroker(Broker):
    def buy(self, signal: dict):
        trade = create_paper_trade(signal)

        if not trade:
            return broker_response(
                ok=False,
                message="Paper trade was not created.",
                data={},
            )

        return broker_response(
            ok=True,
            message="Paper trade created.",
            data={"trade": trade},
        )

    def sell(self, trade_id: int, reason: str = "MANUAL_SELL"):
        trade = close_paper_trade(trade_id, reason=reason)

        if not trade:
            return broker_response(
                ok=False,
                message="Paper trade not found.",
                data={},
            )

        return broker_response(
            ok=True,
            message="Paper trade closed.",
            data={"trade": trade},
        )

    def get_balance(self):
        state = get_paper_state()

        return broker_response(
            ok=True,
            message="Paper balance loaded.",
            data={
                "cash": state.get("cash", 0),
                "settings": state.get("settings", {}),
            },
        )

    def get_positions(self):
        state = get_paper_state()

        return broker_response(
            ok=True,
            message="Paper positions loaded.",
            data={
                "open_trades": state.get("open_trades", []),
                "closed_trades": state.get("closed_trades", []),
            },
        )


paper_broker = PaperBroker()