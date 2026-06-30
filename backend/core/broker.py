from abc import ABC, abstractmethod


class Broker(ABC):
    @abstractmethod
    def buy(self, signal: dict):
        pass

    @abstractmethod
    def sell(self, trade_id: int, reason: str = "MANUAL_SELL"):
        pass

    @abstractmethod
    def get_balance(self):
        pass

    @abstractmethod
    def get_positions(self):
        pass


def broker_response(ok=True, message="", data=None):
    return {
        "ok": ok,
        "message": message,
        "data": data or {},
    }