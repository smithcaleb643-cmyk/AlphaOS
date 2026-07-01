from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.accounting_auditor import run_accounting_audit
from core.alpha_wallet_manager import get_alpha_wallet_status
from core.live_decision_report import build_live_decision_report
from core.adaptive_learning import apply_learning_to_signal
from core.live_transaction_signer import sign_swap_transaction
from core.live_transaction_sender import send_signed_transaction
from core.live_sell_executor import execute_live_sell
from core.live_trade_executor import execute_live_buy
from core.live_trade_journal import load_live_trade_journal
from core.live_portfolio import get_live_portfolio
from core.live_alpha_controller import (
    get_live_alpha_state,
    start_live_alpha,
    stop_live_alpha,
    update_live_alpha_settings,
)
from core.alpha_brain import score_coin
from core.alpha_engine import start_alpha_engine, stop_alpha_engine, get_alpha_engine_state
from core.jupiter_service import quote_sol_to_token
from core.live_swap_builder import build_swap_transaction
from core.learning import get_learning_report
from core.learning_memory import save_learning_memory, load_learning_memory
from core.paper_trader import (
    create_paper_trade,
    get_paper_state,
    close_paper_trade,
    review_paper_trade,
    reset_paper_account,
    set_paper_trade_size,
    get_all_paper_profiles,
    select_paper_profile,
    create_paper_profile,
    clone_paper_profile,
    delete_paper_profile,
)
from core.performance import get_performance
from core.price_audit import read_recent_price_events
from core.system_health import get_system_health
from core.trade_manager import update_open_trades
from core.wallet_intelligence import (
    apply_wallet_intelligence_to_signal,
    get_wallet_brain_report,
    save_wallet_scan,
    learn_wallets_from_closed_trades,
)
from database.memory import setup_database, save_scan, get_scans
from services.market_service import get_token_pairs, get_market_summary, scan_live_market
from services.solana_wallet_service import scan_token_wallets


app = FastAPI(title="Alpha OS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_database()


def slim_trade(trade):
    clean = dict(trade)
    clean.pop("price_history", None)
    clean.pop("audit_notes", None)

    if isinstance(clean.get("partial_exits"), list):
        clean["partial_exits"] = clean["partial_exits"][-5:]

    if isinstance(clean.get("real_wallets"), list):
        clean["real_wallets"] = clean["real_wallets"][:10]
        clean["wallets"] = clean["real_wallets"]

    return clean


@app.get("/")
def home():
    return {"message": "Alpha OS backend is running", "status": "online"}


@app.get("/system/health")
def system_health():
    return get_system_health()


@app.get("/wallet/brain")
def wallet_brain():
    return get_wallet_brain_report()


@app.post("/wallet/learn")
def wallet_learn():
    return learn_wallets_from_closed_trades(get_paper_state())


@app.get("/wallet/token/{token_address}/scan")
def wallet_token_scan(token_address: str):
    scan = scan_token_wallets(token_address, limit=10)

    if not scan.get("ok"):
        return scan

    saved = save_wallet_scan(
        token_address=token_address,
        wallets=scan.get("wallets", []),
        source=scan.get("source", "public_solana_rpc"),
    )

    return {**scan, "saved": saved}


@app.get("/scan")
def scan():
    live_coins = scan_live_market(limit=8)
    results = []
    paper_trades = []

    for coin in live_coins:
        token = (
            coin.get("token_address")
            or coin.get("address")
            or coin.get("mint")
            or coin.get("base_token_address")
        )

        if token:
            wallet_scan = scan_token_wallets(token, limit=5)
            coin["real_wallets"] = wallet_scan.get("wallets", [])

        result = score_coin(coin)
        result = apply_learning_to_signal(result)
        result = apply_wallet_intelligence_to_signal(result, coin)

        save_scan(result.get("coin_name", "Unknown"), result)
        results.append(result)

        if result.get("score", 0) >= 30 and result.get("action") != "REJECT":
            trade_signal = {**coin, **result, "price_usd": coin.get("price_usd") or 0}
            trade = create_paper_trade(trade_signal)

            if trade:
                paper_trades.append(trade)

    results = sorted(results, key=lambda item: item.get("score", 0), reverse=True)

    return {
        "count": len(results),
        "results": results,
        "paper_trades_created": len(paper_trades),
        "paper_trades": paper_trades,
    }


@app.get("/memory")
def memory():
    scans = get_scans()
    return {"count": len(scans), "scans": scans}


@app.get("/market/token/{token_address}")
def market_token(token_address: str):
    pairs = get_token_pairs(token_address)
    return {"token_address": token_address, "count": len(pairs), "pairs": pairs}


@app.get("/market/summary/{token_address}")
def market_summary(token_address: str):
    return get_market_summary(token_address)


@app.get("/discover")
def discover():
    coins = scan_live_market(limit=12)
    return {"count": len(coins), "coins": coins}


@app.get("/profiles")
def profiles():
    return get_all_paper_profiles()


@app.post("/profiles/select")
def profiles_select(settings: dict):
    name = settings.get("name") or settings.get("profile") or settings.get("active_profile")
    return select_paper_profile(name)


@app.post("/profiles/create")
def profiles_create(settings: dict):
    return create_paper_profile(
        name=settings.get("name"),
        starting_cash=settings.get("starting_cash", 10000),
        trade_size=settings.get("trade_size", 100),
        risk_mode=settings.get("risk_mode", "NORMAL"),
    )


@app.post("/profiles/clone")
def profiles_clone(settings: dict):
    return clone_paper_profile(
        source_name=settings.get("source_name"),
        new_name=settings.get("new_name"),
    )


@app.post("/profiles/delete")
def profiles_delete(settings: dict):
    name = settings.get("name") or settings.get("profile")
    return delete_paper_profile(name)


@app.post("/paper/trade")
def paper_trade(signal: dict):
    signal = apply_wallet_intelligence_to_signal(signal, signal)
    trade = create_paper_trade(signal)

    if not trade:
        return {
            "created": False,
            "message": "No valid price, duplicate open trade, or not enough cash.",
        }

    return {"created": True, "trade": trade}


@app.post("/paper/reset")
def paper_reset(settings: dict):
    stop_alpha_engine()

    starting_cash = settings.get("starting_cash", 10000)
    trade_size = settings.get("trade_size", None)

    return reset_paper_account(
        starting_cash=starting_cash,
        trade_size=trade_size,
    )


@app.post("/paper/trade-size")
def paper_trade_size(settings: dict):
    trade_size = settings.get("trade_size", 100)
    return set_paper_trade_size(trade_size)


@app.get("/paper/state")
def paper_state_endpoint():
    state = get_paper_state()
    profiles_data = get_all_paper_profiles()

    open_trades = state.get("open_trades", [])
    closed_trades = state.get("closed_trades", [])

    return {
        "active_profile": profiles_data.get("active_profile"),
        "profiles": profiles_data.get("profiles", []),
        "cash": state.get("cash", 10000),
        "settings": state.get("settings", {}),
        "open_trades": [slim_trade(t) for t in open_trades[-50:]],
        "closed_trades": [slim_trade(t) for t in closed_trades[-50:]],
        "open_count": len(open_trades),
        "closed_count": len(closed_trades),
        "limited": True,
    }


@app.get("/paper/performance")
def paper_performance_endpoint():
    performance = get_performance()
    profiles_data = get_all_paper_profiles()

    if isinstance(performance, dict):
        performance["active_profile"] = profiles_data.get("active_profile")
        performance["profiles"] = profiles_data.get("profiles", [])

    return performance


@app.post("/paper/update")
def paper_update(price_lookup: dict):
    return update_open_trades(price_lookup)


@app.get("/paper/learning")
def paper_learning():
    return get_learning_report()


@app.post("/paper/learning/save")
def save_learning():
    return save_learning_memory(reason="manual_api_save")


@app.get("/paper/learning/saved")
def get_saved_learning():
    return load_learning_memory()


@app.get("/paper/audit")
def paper_audit(limit: int = 100):
    return {"events": read_recent_price_events(limit)}


@app.get("/paper/audit/accounting")
def paper_accounting_audit():
    return run_accounting_audit()


@app.post("/paper/trade/{trade_id}/review")
def review_trade(trade_id: int):
    trade = review_paper_trade(trade_id)

    if trade is None:
        return {"ok": False, "message": "Trade not found"}

    return {"ok": True, "trade": trade}


@app.post("/paper/trade/{trade_id}/sell")
def sell_trade(trade_id: int):
    trade = close_paper_trade(trade_id, reason="MANUAL_SELL")

    if trade is None:
        return {"ok": False, "message": "Trade not found"}

    return {"ok": True, "trade": trade}


@app.post("/engine/start")
def engine_start():
    return start_alpha_engine()


@app.post("/engine/stop")
def engine_stop():
    return stop_alpha_engine()


@app.get("/engine/state")
def engine_state():
    return get_alpha_engine_state()


@app.get("/live/wallet/status")
def live_wallet_status_endpoint():
    try:
        from core.live_wallet_reader import live_wallet_status
        return live_wallet_status()
    except Exception as error:
        return {
            "ok": False,
            "connected": False,
            "message": "Live wallet reader failed to load.",
            "error": str(error),
        }


@app.get("/live/alpha/state")
def live_alpha_state_endpoint():
    return get_live_alpha_state()


@app.post("/live/alpha/start")
def live_alpha_start_endpoint():
    return start_live_alpha()


@app.post("/live/alpha/stop")
def live_alpha_stop_endpoint():
    return stop_live_alpha()


@app.post("/live/alpha/settings")
def live_alpha_settings_endpoint(payload: dict):
    return update_live_alpha_settings(payload)


@app.get("/live/alpha-wallet/status")
def live_alpha_wallet_status():
    return get_alpha_wallet_status()


@app.get("/live/portfolio")
def live_portfolio():
    return get_live_portfolio()


@app.get("/live/trade-journal")
def live_trade_journal():
    return load_live_trade_journal()


@app.post("/live/decision/report")
def live_decision_report(payload: dict):
    return build_live_decision_report(payload)


@app.post("/live/jupiter/quote")
def live_jupiter_quote(payload: dict):
    output_mint = payload.get("output_mint")
    sol_amount = payload.get("sol_amount", 0.01)
    slippage_bps = payload.get("slippage_bps", 100)

    if not output_mint:
        return {"ok": False, "error": "output_mint is required"}

    return quote_sol_to_token(output_mint, sol_amount, slippage_bps)


@app.post("/live/jupiter/build-swap")
def live_jupiter_build_swap(payload: dict):
    output_mint = payload.get("output_mint")
    sol_amount = payload.get("sol_amount", 0.01)
    slippage_bps = payload.get("slippage_bps", 100)

    if not output_mint:
        return {"ok": False, "error": "output_mint is required"}

    return build_swap_transaction(output_mint, sol_amount, slippage_bps)


@app.post("/live/execute/buy")
def live_execute_buy_endpoint(payload: dict):
    return execute_live_buy(payload)


@app.post("/live/execute/sell")
def live_execute_sell_endpoint(payload: dict):
    return execute_live_sell(payload)