from enum import Enum
from core.paper_trader import create_paper_trade, get_paper_state
from core.trade_manager import update_open_trades
from core.live_execution.executor import execute_live_buy


class ExecutionMode(Enum):
    PAPER_ONLY = "PAPER_ONLY"
    MIRROR = "MIRROR"
    LIVE = "LIVE"


class ControlBrain:
    def __init__(self):
        self.mode = ExecutionMode.PAPER_ONLY

        self.learning_bias = 0.0
        self.max_risk_score = 70
        self.min_score_to_trade = 60

        self.paper_first_required = True
        self.kill_switch = False

        self.stats = {
            "paper_trades": 0,
            "live_trades": 0,
            "blocked_trades": 0,
        }

    # -------------------------
    # MODE CONTROL
    # -------------------------

    def set_mode(self, mode: ExecutionMode):
        self.mode = mode

    def enable_live(self):
        self.mode = ExecutionMode.LIVE

    def enable_mirror(self):
        self.mode = ExecutionMode.MIRROR

    def enable_paper_only(self):
        self.mode = ExecutionMode.PAPER_ONLY

    def stop_all_trading(self):
        self.kill_switch = True

    # -------------------------
    # LEARNING SYSTEM
    # -------------------------

    def apply_learning(self, signal):
        base_score = float(signal.get("score", 0))
        adjusted = base_score + self.learning_bias

        signal["adjusted_score"] = adjusted
        return signal

    def update_learning_bias(self, trade_result):
        pnl = float(trade_result.get("pnl_percent", 0))

        if pnl > 5:
            self.learning_bias += 0.5
        elif pnl < -5:
            self.learning_bias -= 0.5

        self.learning_bias = max(-10, min(10, self.learning_bias))

    # -------------------------
    # DECISION GATE
    # -------------------------

    def should_trade(self, signal):
        if self.kill_switch:
            return False, "KILL_SWITCH"

        if signal.get("risk_score", 0) > self.max_risk_score:
            return False, "RISK_TOO_HIGH"

        if signal.get("adjusted_score", 0) < self.min_score_to_trade:
            return False, "LOW_SCORE"

        return True, "OK"

    # -------------------------
    # EXECUTION CONTROL
    # -------------------------

    def execute(self, signal):
        """
        Central execution router.
        """

        signal = self.apply_learning(signal)

        allowed, reason = self.should_trade(signal)

        if not allowed:
            self.stats["blocked_trades"] += 1
            return {
                "ok": False,
                "reason": reason,
                "mode": self.mode.value,
            }

        # -------------------------
        # PAPER ONLY
        # -------------------------
        if self.mode == ExecutionMode.PAPER_ONLY:
            trade = create_paper_trade(signal)
            self.stats["paper_trades"] += 1

            return {
                "ok": True,
                "mode": "PAPER",
                "trade": trade,
            }

        # -------------------------
        # MIRROR MODE
        # -------------------------
        if self.mode == ExecutionMode.MIRROR:
            trade = create_paper_trade(signal)
            self.stats["paper_trades"] += 1

            return {
                "ok": True,
                "mode": "MIRROR",
                "trade": trade,
            }

        # -------------------------
        # LIVE MODE (FIXED)
        # -------------------------
        if self.mode == ExecutionMode.LIVE:

            # THIS IS THE FIX — actual execution now happens
            result = execute_live_buy(signal)

            self.stats["live_trades"] += 1

            return result

        return {
            "ok": False,
            "reason": "UNKNOWN_MODE",
        }


# Global instance
control_brain = ControlBrain()