def safe_float(value, default=0):
    try:
        return float(value or default)
    except Exception:
        return default


def quote_price_impact_percent(quote):
    return safe_float(quote.get("priceImpactPct", 0)) * 100


def quote_output_amount(quote):
    return safe_float(quote.get("outAmount", 0))


def quote_input_amount(quote):
    return safe_float(quote.get("inAmount", 0))


def evaluate_live_quote(quote, sol_amount=0.01):
    warnings = []

    if not quote:
        return {
            "approved": False,
            "reason": "No Jupiter quote returned.",
            "warnings": ["Missing quote."],
        }

    price_impact = quote_price_impact_percent(quote)
    out_amount = quote_output_amount(quote)
    in_amount = quote_input_amount(quote)

    if out_amount <= 0:
        warnings.append("Jupiter quote output amount is zero.")

    if in_amount <= 0:
        warnings.append("Jupiter quote input amount is zero.")

    if price_impact > 5:
        warnings.append(f"Price impact too high: {round(price_impact, 2)}%.")

    if sol_amount > 0.01:
        warnings.append("Trade size exceeds current live testing limit of 0.01 SOL.")

    approved = len(warnings) == 0

    return {
        "approved": approved,
        "reason": "Approved for live swap build." if approved else "Blocked by live execution safety.",
        "price_impact_percent": round(price_impact, 4),
        "input_amount": in_amount,
        "output_amount": out_amount,
        "warnings": warnings,
    }


def evaluate_swap_build(swap_result):
    if not swap_result.get("ok"):
        return {
            "approved": False,
            "reason": "Swap build failed.",
            "warnings": [swap_result.get("error", "Unknown swap build error.")],
        }

    if not swap_result.get("swap_transaction"):
        return {
            "approved": False,
            "reason": "Swap transaction missing.",
            "warnings": ["Jupiter did not return a swapTransaction."],
        }

    quote = swap_result.get("quote", {})
    sol_amount = safe_float(swap_result.get("sol_amount", 0.01))

    return evaluate_live_quote(quote, sol_amount=sol_amount)