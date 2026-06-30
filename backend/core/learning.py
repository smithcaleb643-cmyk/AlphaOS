from core.paper_trader import get_paper_state


def bucket_score(score):
    score = int(score or 0)
    if score >= 80:
        return "80-100"
    if score >= 60:
        return "60-79"
    if score >= 40:
        return "40-59"
    if score >= 20:
        return "20-39"
    return "0-19"


def bucket_risk(risk):
    risk = int(risk or 0)
    if risk <= 20:
        return "LOW"
    if risk <= 45:
        return "MEDIUM"
    if risk <= 70:
        return "HIGH"
    return "EXTREME"


def get_learning_report():
    state = get_paper_state()
    closed = state.get("closed_trades", [])

    total = len(closed)
    wins = 0
    losses = 0
    total_pnl = 0
    score_buckets = {}
    risk_buckets = {}

    for trade in closed:
        pnl = float(trade.get("pnl_usd") or 0)
        score = int(trade.get("score") or 0)
        risk = int(trade.get("risk_score") or 0)

        total_pnl += pnl
        if pnl >= 0:
            wins += 1
        else:
            losses += 1

        score_key = bucket_score(score)
        risk_key = bucket_risk(risk)

        for buckets, key in [(score_buckets, score_key), (risk_buckets, risk_key)]:
            if key not in buckets:
                buckets[key] = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0, "win_rate": 0}

            buckets[key]["trades"] += 1
            buckets[key]["pnl"] += pnl

            if pnl >= 0:
                buckets[key]["wins"] += 1
            else:
                buckets[key]["losses"] += 1

    for buckets in [score_buckets, risk_buckets]:
        for bucket in buckets.values():
            if bucket["trades"] > 0:
                bucket["win_rate"] = round((bucket["wins"] / bucket["trades"]) * 100, 2)
                bucket["pnl"] = round(bucket["pnl"], 2)

    win_rate = round((wins / total) * 100, 2) if total else 0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2),
        "average_pnl": round(total_pnl / total, 2) if total else 0,
        "score_buckets": score_buckets,
        "risk_buckets": risk_buckets,
        "summary": build_learning_summary(total, wins, losses, score_buckets, risk_buckets),
    }


def build_learning_summary(total, wins, losses, score_buckets, risk_buckets):
    if total == 0:
        return "Alpha has not learned from any closed trades yet."

    return (
        f"Alpha has learned from {total} closed trades. "
        f"Wins: {wins}, Losses: {losses}. "
        f"Score buckets: {score_buckets}. "
        f"Risk buckets: {risk_buckets}."
    )