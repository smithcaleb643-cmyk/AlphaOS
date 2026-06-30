from core.learning import get_learning_report


def get_score_bucket(score):
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


def get_risk_bucket(risk):
    risk = int(risk or 0)
    if risk <= 20:
        return "LOW"
    if risk <= 45:
        return "MEDIUM"
    if risk <= 70:
        return "HIGH"
    return "EXTREME"


def get_bucket_adjustment(bucket):
    trades = int(bucket.get("trades", 0) or 0)
    win_rate = float(bucket.get("win_rate", 0) or 0)
    pnl = float(bucket.get("pnl", 0) or 0)

    if trades < 3:
        return 0

    if win_rate >= 70 and pnl > 0:
        return 10
    if win_rate >= 55 and pnl > 0:
        return 5
    if win_rate <= 30 and pnl < 0:
        return -15
    if win_rate <= 45 and pnl < 0:
        return -8

    return 0


def apply_learning_to_signal(signal):
    learning = get_learning_report()

    original_score = int(signal.get("score") or 0)
    risk = int(signal.get("risk_score") or 0)

    score_key = get_score_bucket(original_score)
    risk_key = get_risk_bucket(risk)

    score_bucket = learning.get("score_buckets", {}).get(score_key, {})
    risk_bucket = learning.get("risk_buckets", {}).get(risk_key, {})

    adjustment = get_bucket_adjustment(score_bucket) + get_bucket_adjustment(risk_bucket)
    adjusted_score = max(0, min(100, original_score + adjustment))

    if adjusted_score >= 70 and risk <= 45:
        action = "BUY"
        status = "buy"
    elif adjusted_score >= 35:
        action = "WATCH"
        status = "watching"
    else:
        action = "REJECT"
        status = "rejected"

    signal["original_score"] = original_score
    signal["score"] = adjusted_score
    signal["learning_adjustment"] = adjustment
    signal["action"] = action
    signal["status"] = status
    signal["learning_reason"] = (
        f"Learning adjustment {adjustment}. "
        f"Score bucket {score_key}. Risk bucket {risk_key}."
    )
    signal["reason"] = f"{signal.get('reason', '')} {signal['learning_reason']}"

    return signal