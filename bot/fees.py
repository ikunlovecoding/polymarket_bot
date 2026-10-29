"""Polymarket taker fees.

Source: Polymarket docs, "Fees" page (read 2026-10-29):
    fee = shares x rate x price x (1 - price)
Only the taker pays. Paper trades always cross the spread, so they are always taker trades.
Each market publishes its own `feeSchedule.rate` in the Gamma API. We use that when it exists
and fall back to the category default from config.json only when it is missing.
"""


def taker_fee(shares: float, price: float, rate: float) -> float:
    """Fee in USDC for buying or selling `shares` at `price` (0-1) with fee `rate`."""
    if shares <= 0 or rate <= 0:
        return 0.0
    # Polymarket rounds fees to 5 decimal places.
    return round(shares * rate * price * (1.0 - price), 5)


def market_fee_rate(market: dict, category: str, cfg: dict) -> float:
    """Pick the fee rate for one market: its own schedule first, then the config default."""
    if market.get("feesEnabled") is False:
        return 0.0
    schedule = market.get("feeSchedule")
    if isinstance(schedule, dict) and schedule.get("rate") is not None:
        return float(schedule["rate"])
    return float(cfg["fees"]["default_rates"].get(category, 0.05))
