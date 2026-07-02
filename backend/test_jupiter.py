from core.live_execution.builder import build_swap

result = build_swap(
    token_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    amount=0.001,
    slippage_bps=100
)

print(result)