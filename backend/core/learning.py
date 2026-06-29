learning_memory = {
    "total_trades": 0,
    "wins": 0,
    "losses": 0,
    "score_buckets": {},
}


def record_trade_result(trade):
    learning_memory["total_trades"] += 1

    if trade.get("pnl_usd", 0) > 0:
        learning_memory["wins"] += 1
        result = "WIN"
    else:
        learning_memory["losses"] += 1
        result = "LOSS"

    score = int(trade.get("score", 0))
    bucket = f"{(score // 10) * 10}-{(score // 10) * 10 + 9}"

    if bucket not in learning_memory["score_buckets"]:
        learning_memory["score_buckets"][bucket] = {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0,
        }

    learning_memory["score_buckets"][bucket]["trades"] += 1
    learning_memory["score_buckets"][bucket]["total_pnl"] += trade.get("pnl_usd", 0)

    if result == "WIN":
        learning_memory["score_buckets"][bucket]["wins"] += 1
    else:
        learning_memory["score_buckets"][bucket]["losses"] += 1


def get_learning_report():
    return learning_memory