import threading
import time

from core.live_alpha_controller import (
    LIVE_ALPHA_STATE,
    stop_live_alpha,
)

from core.live_portfolio import get_live_portfolio
from core.live_trade_executor import execute_live_buy


_loop_thread = None


def _alpha_loop():

    while LIVE_ALPHA_STATE["running"]:

        try:

            portfolio = get_live_portfolio()

            # --------------------------
            # Safety 1
            # Daily loss
            # --------------------------

            if portfolio["today_pnl_usd"] <= -LIVE_ALPHA_STATE["max_daily_loss_usd"]:
                print("LIVE ALPHA: Daily loss reached.")
                stop_live_alpha()
                break

            # --------------------------
            # Safety 2
            # Max positions
            # --------------------------

            if portfolio["open_positions"] >= LIVE_ALPHA_STATE["max_open_positions"]:
                LIVE_ALPHA_STATE["last_action"] = "Waiting: max positions reached."
                time.sleep(10)
                continue

            # --------------------------
            # TODO
            # Real Scanner
            # --------------------------

            #
            # This is where Alpha Brain
            # will soon inject
            #
            # scanner results
            #
            # For tonight we simply wait.
            #

            LIVE_ALPHA_STATE["scans_today"] += 1
            LIVE_ALPHA_STATE["last_action"] = "Scanning..."

            time.sleep(10)

        except Exception as e:
            LIVE_ALPHA_STATE["last_action"] = str(e)
            time.sleep(5)


def launch_live_alpha():

    global _loop_thread

    if _loop_thread and _loop_thread.is_alive():
        return

    _loop_thread = threading.Thread(
        target=_alpha_loop,
        daemon=True,
    )

    _loop_thread.start()