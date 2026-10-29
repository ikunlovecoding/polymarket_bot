"""ORDER SIMULATOR: paper fills against the real order book.

Nothing here can send an order. It only does arithmetic on a book we downloaded:
  - a paper BUY walks the asks from the cheapest up, never paying above `max_price`;
  - a paper SELL walks the bids from the highest down.
Fees use Polymarket's taker formula (fees.py). Shares are whole numbers, as in Strategy.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .data_feed import Book
from .fees import taker_fee


@dataclass
class Fill:
    shares: float
    avg_price: float      # volume-weighted price, before fees
    gross: float          # shares x price (cost for buys, proceeds for sells)
    fee: float
    levels_used: int

    @property
    def net_cost(self) -> float:      # buys: what the trade cost in total
        return round(self.gross + self.fee, 6)

    @property
    def net_proceeds(self) -> float:  # sells: what we receive after fees
        return round(self.gross - self.fee, 6)


def simulate_buy(book: Book, budget: float, max_price: float, fee_rate: float,
                 min_shares: float) -> Fill | None:
    """Spend at most `budget` USDC (fees included) buying from the asks. None = no fill."""
    remaining = budget
    shares = gross = fee = 0.0
    levels = 0
    for price, size in book.asks:
        if price > max_price + 1e-9 or remaining <= 0:
            break
        cost_per_share = price + taker_fee(1, price, fee_rate)
        n = math.floor(min(size, remaining / cost_per_share))  # whole shares we can afford here
        # Fee rounding can push the total a hair over budget: step down until it fits.
        while n > 0 and n * price + taker_fee(n, price, fee_rate) > remaining + 1e-9:
            n -= 1
        if n <= 0:
            break
        f = taker_fee(n, price, fee_rate)
        shares += n
        gross += n * price
        fee += f
        remaining -= n * price + f
        levels += 1
        if n < size:  # budget ran out inside this level
            break
    if shares < max(min_shares, book.min_order_size):
        return None
    return Fill(shares=shares, avg_price=round(gross / shares, 6), gross=round(gross, 6),
                fee=round(fee, 6), levels_used=levels)


def simulate_sell(book: Book, shares: float, fee_rate: float) -> Fill | None:
    """Sell up to `shares` into the bids. May fill partly if the book is thin. None = no bids."""
    left = shares
    sold = gross = fee = 0.0
    levels = 0
    for price, size in book.bids:
        if left <= 0:
            break
        n = min(size, left)
        sold += n
        gross += n * price
        fee += taker_fee(n, price, fee_rate)
        left -= n
        levels += 1
    if sold <= 0:
        return None
    return Fill(shares=sold, avg_price=round(gross / sold, 6), gross=round(gross, 6),
                fee=round(fee, 6), levels_used=levels)
