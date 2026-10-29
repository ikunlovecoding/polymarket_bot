"""SIGNAL ENGINE: Strategy Version A ("Price Range"), exactly as written in Strategy.md.

Every rule returns a short reason, so the log can say WHY a market was skipped or exited.
Rule codes (F1, E1, X2, ...) match Strategy.md.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .data_feed import Quote


# ---------------------------------------------------------------- market filter F1-F6

def check_filters(q: Quote, now: datetime, cfg: dict) -> str | None:
    """Return None if the market passes F1-F6, otherwise the reason it fails."""
    f = cfg["filters"]
    if q.category not in cfg["categories"]:
        return "F1 category not allowed"
    if q.event_time is None:
        return "F2 no event time"
    days = (q.event_time - now).total_seconds() / 86400
    if days < f["min_days_to_event"]:
        return f"F2 event too soon ({days:.1f}d)"
    if days > f["max_days_to_event"]:
        return f"F2 event too far ({days:.1f}d)"
    if q.volume_24h < f["min_volume_24h"]:
        return f"F3 24h volume ${q.volume_24h:,.0f} < ${f['min_volume_24h']:,}"
    if q.spread is None:
        return "F4 no quote"
    if q.spread > f["max_spread"] + 1e-9:
        return f"F4 spread {q.spread:.3f} > {f['max_spread']}"
    if f["require_resolution_source"] and not q.resolution_source:
        return "F5 no resolution source named"
    if q.uma_status:
        return f"F5 resolution already started ({q.uma_status})"
    if not q.active or q.closed or not q.accepting_orders:
        return "F6 market not open for trading"
    return None


def check_entry_price(q: Quote, cfg: dict) -> str | None:
    """E1: outcome ask must be inside the price range."""
    e = cfg["entry"]
    if q.best_ask is None:
        return "E1 no ask"
    if not (e["min_price"] - 1e-9 <= q.best_ask <= e["max_price"] + 1e-9):
        return f"E1 ask {q.best_ask:.3f} outside {e['min_price']}-{e['max_price']}"
    return None


# ---------------------------------------------------------------- choosing entries

def select_entries(quotes: list[Quote], now: datetime, cfg: dict,
                   held_event_ids: set, traded_market_ids: set):
    """Pick at most one outcome per event, ranked by 24h volume.

    Returns (signals, skipped) where
      signals = [(quote, confidence), ...] best first, confidence is "high" or "normal"
      skipped = {reason: count} for the scan report
    """
    skipped: dict[str, int] = {}

    def skip(reason: str):
        key = reason.split(" (")[0].split(" $")[0]
        skipped[key] = skipped.get(key, 0) + 1

    # Markets passing F1-F6 (checked once per market, both outcomes share the same answer).
    passing: dict[str, list[Quote]] = {}
    for q in quotes:
        reason = check_filters(q, now, cfg)
        if reason:
            skip(reason)
            continue
        passing.setdefault(q.market_id, []).append(q)

    # Confidence: markets in the top X% by 24h volume among those passing F1-F6.
    vols = sorted({qs[0].market_id: qs[0].volume_24h for qs in passing.values()}.values(), reverse=True)
    n_high = math.ceil(len(vols) * cfg["stakes"]["high_confidence_top_fraction"]) if vols else 0
    high_cut = vols[n_high - 1] if n_high else float("inf")

    best_per_event: dict[str, Quote] = {}
    for qs in passing.values():
        for q in qs:
            if q.event_id in held_event_ids:
                skip("E3 already holding this event")
                continue
            if q.market_id in traded_market_ids:
                skip("E5 market traded before")
                continue
            reason = check_entry_price(q, cfg)
            if reason:
                skip("E1 price outside range")
                continue
            cur = best_per_event.get(q.event_id)
            # Highest volume wins; tie (same market, both outcomes) goes to the cheaper ask.
            if cur is None or (q.volume_24h, -q.best_ask) > (cur.volume_24h, -cur.best_ask):
                best_per_event[q.event_id] = q

    signals = sorted(best_per_event.values(), key=lambda q: -q.volume_24h)
    return [(q, "high" if q.volume_24h >= high_cut else "normal") for q in signals], skipped


# ---------------------------------------------------------------- exits X1-X5

def exit_reason(position: dict, q: Quote | None, now: datetime, cfg: dict) -> str | None:
    """Decide whether an open paper position should be closed now. First rule hit wins."""
    x = cfg["exits"]
    entry = position["entry_price"]
    opened = datetime.fromisoformat(position["opened_at"])

    # X5 invalidation: market gone, paused, resolving, or the book fell apart.
    if q is None:
        return "X5 market data unavailable"
    if q.closed or not q.active or not q.accepting_orders:
        return "X5 market closed or paused"
    if q.uma_status:
        return f"X5 resolution started ({q.uma_status})"
    if q.spread is None or q.spread > x["invalidation_spread"] + 1e-9:
        return "X5 spread too wide"

    bid = q.best_bid
    if bid is not None and bid >= entry * x["take_profit_mult"] - 1e-9:
        return "X1 take profit"
    if bid is not None and bid <= entry * x["stop_loss_mult"] + 1e-9:
        return "X2 stop loss"
    if now - opened >= timedelta(days=x["max_hold_days"]):
        return "X3 time stop"
    if q.event_time and now >= q.event_time - timedelta(hours=x["exit_hours_before_event"]):
        return "X4 pre-resolution exit"
    return None
