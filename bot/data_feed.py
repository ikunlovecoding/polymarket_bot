"""DATA FEED: reads Polymarket's public data. Read-only.

No wallet, no API key, no login. Only plain GET requests to two public services:
  - Gamma API (market list, prices, volume):  https://gamma-api.polymarket.com
  - CLOB API  (order books, price history):   https://clob.polymarket.com

Things learned from real responses on 2026-10-29 (and handled below):
  - Gamma's bestBid/bestAsk are for the FIRST outcome. The second outcome's quote is the mirror:
    ask2 = 1 - bid1, bid2 = 1 - ask1.
  - Sports events carry the game time in `gameStartTime` / `eventStartTime`. Their `endDate`
    can be a week after the game, so endDate must NOT be used as the event time for sports.
  - CLOB order books list bids from lowest to highest and asks from highest to lowest,
    so the best price is at the END of each list. We sort explicitly and never rely on order.
  - Tag filtering works on /events (tag_slug=...), not on /markets.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .fees import market_fee_rate

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


# ---------------------------------------------------------------- HTTP helper

def get_json(url: str, params: dict | None = None, retries: int = 3, timeout: int = 20):
    """GET a URL and parse JSON, retrying a few times on network errors."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-bot/1.0 (read-only)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as err:  # network error, timeout, bad JSON
            last_err = err
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} tries: {url} ({last_err})")


# ---------------------------------------------------------------- data shapes

@dataclass
class Quote:
    """One outcome of one market, e.g. 'Yes' on 'Will Bitcoin reach $82,000 ...?'."""
    event_id: str
    event_title: str
    event_slug: str
    category: str
    market_id: str
    question: str
    outcome: str
    outcome_index: int
    token_id: str
    best_bid: float | None
    best_ask: float | None
    volume_24h: float
    event_time: datetime | None        # when the event happens / resolves
    fee_rate: float
    resolution_source: str
    active: bool
    closed: bool
    accepting_orders: bool
    uma_status: str                    # non-empty once resolution has started
    outcome_prices: list = field(default_factory=list)  # final prices once resolved

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round(self.best_ask - self.best_bid, 6)


@dataclass
class Book:
    """Order book for one outcome token. bids: best (highest) first. asks: best (lowest) first."""
    token_id: str
    bids: list  # [(price, size), ...]
    asks: list
    min_order_size: float
    timestamp_ms: int

    @property
    def best_bid(self):
        return self.bids[0][0] if self.bids else None

    @property
    def best_ask(self):
        return self.asks[0][0] if self.asks else None


# ---------------------------------------------------------------- parsing helpers

def parse_time(value) -> datetime | None:
    """Parse the several timestamp formats Gamma uses into an aware UTC datetime."""
    if not value:
        return None
    s = str(value).strip().replace(" ", "T")
    if s.endswith("+00"):
        s += ":00"
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _json_list(value) -> list:
    """Gamma returns lists like outcomes as JSON strings: '["Yes", "No"]'."""
    if isinstance(value, list):
        return value
    try:
        return json.loads(value or "[]")
    except (TypeError, ValueError):
        return []


def _num(value):
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def event_category(event: dict, cfg: dict) -> str | None:
    """Map an event's tags to one of our four categories, or None if out of scope."""
    tags = {t.get("slug", "").lower() for t in event.get("tags") or []}
    if tags & {t.lower() for t in cfg["excluded_tags"]}:
        return None
    for category, slugs in cfg["categories"].items():  # order in config = priority
        if tags & {s.lower() for s in slugs}:
            return category
    return None


def market_event_time(market: dict, event: dict, category: str) -> datetime | None:
    """When the thing being bet on happens. For sports that is the game start, else the end date."""
    for key in ("gameStartTime", "eventStartTime"):
        t = parse_time(market.get(key))
        if t:
            return t
    if category == "sports":
        t = parse_time(event.get("startTime"))
        if t:
            return t
    return parse_time(market.get("endDate")) or parse_time(event.get("endDate"))


def quotes_from_event(event: dict, cfg: dict, category: str | None = None) -> list[Quote]:
    """Turn one Gamma event into one Quote per outcome of each binary market in it.

    `category` can be passed in when we already know it (open positions), because the
    single-market endpoint does not always include the event's tags.
    """
    category = category or event_category(event, cfg)
    if category is None:
        return []
    out = []
    for m in event.get("markets") or []:
        outcomes = _json_list(m.get("outcomes"))
        tokens = _json_list(m.get("clobTokenIds"))
        if len(outcomes) != 2 or len(tokens) != 2:
            continue  # only binary markets
        bid0, ask0 = _num(m.get("bestBid")), _num(m.get("bestAsk"))
        common = dict(
            event_id=str(event.get("id")),
            event_title=event.get("title", ""),
            event_slug=event.get("slug", ""),
            category=category,
            market_id=str(m.get("id")),
            question=m.get("question", ""),
            volume_24h=_num(m.get("volume24hr")) or 0.0,
            event_time=market_event_time(m, event, category),
            fee_rate=market_fee_rate(m, category, cfg),
            resolution_source=(m.get("resolutionSource") or "").strip(),
            active=bool(m.get("active")) and m.get("enableOrderBook", True) is not False,
            closed=bool(m.get("closed")),
            accepting_orders=m.get("acceptingOrders", True) is not False,
            uma_status=(m.get("umaResolutionStatus") or "").strip(),
            outcome_prices=[_num(p) for p in _json_list(m.get("outcomePrices"))],
        )
        # Outcome 0 uses Gamma's quote directly; outcome 1 is the mirror image.
        bid1 = None if ask0 is None else round(1 - ask0, 6)
        ask1 = None if bid0 is None else round(1 - bid0, 6)
        out.append(Quote(outcome=str(outcomes[0]), outcome_index=0, token_id=str(tokens[0]),
                         best_bid=bid0, best_ask=ask0, **common))
        out.append(Quote(outcome=str(outcomes[1]), outcome_index=1, token_id=str(tokens[1]),
                         best_bid=bid1, best_ask=ask1, **common))
    return out


def parse_book(raw: dict, token_id: str) -> Book:
    """Parse a CLOB /book response. Sorts both sides so the best price comes first."""
    bids = sorted(((float(l["price"]), float(l["size"])) for l in raw.get("bids") or []),
                  key=lambda x: -x[0])
    asks = sorted(((float(l["price"]), float(l["size"])) for l in raw.get("asks") or []),
                  key=lambda x: x[0])
    return Book(token_id=token_id, bids=bids, asks=asks,
                min_order_size=float(raw.get("min_order_size") or 5),
                timestamp_ms=int(raw.get("timestamp") or 0))


# ---------------------------------------------------------------- network calls

def fetch_events(cfg: dict, now: datetime) -> list[dict]:
    """All open events in our categories that could resolve in the next few weeks.

    The time-to-event rule is applied later (strategy.py). Here we only cast a wide net,
    because sports events' endDate can be long after the game.
    """
    f = cfg["feed"]
    params_base = {
        "active": "true",
        "closed": "false",
        "order": "volume24hr",
        "ascending": "false",
        "limit": f["events_per_page"],
        "end_date_min": now.isoformat().replace("+00:00", "Z"),
        "end_date_max": (now + timedelta(days=f["fetch_end_window_days"])).isoformat().replace("+00:00", "Z"),
    }
    seen, events = set(), []
    for slugs in cfg["categories"].values():
        for slug in slugs:
            for page in range(f["max_pages_per_tag"]):
                batch = get_json(f"{GAMMA}/events", {**params_base, "tag_slug": slug,
                                                     "offset": page * f["events_per_page"]})
                if not batch:
                    break
                for ev in batch:
                    if str(ev.get("id")) not in seen:
                        seen.add(str(ev.get("id")))
                        events.append(ev)
                # Sorted by 24h volume: once an event is below the minimum, the rest are too.
                if (_num(batch[-1].get("volume24hr")) or 0) < cfg["filters"]["min_volume_24h"]:
                    break
                if len(batch) < f["events_per_page"]:
                    break
    return events


def fetch_market_quotes(market_id: str, category: str, cfg: dict) -> list[Quote]:
    """Fresh quotes for one market we hold (used to manage open positions)."""
    m = get_json(f"{GAMMA}/markets/{market_id}")
    events = m.get("events") or [{}]
    event = dict(events[0])
    event["markets"] = [m]
    return quotes_from_event(event, cfg, category=category)


def fetch_book(token_id: str) -> Book:
    return parse_book(get_json(f"{CLOB}/book", {"token_id": token_id}), token_id)


def fetch_price_history(token_id: str, fidelity_minutes: int = 60) -> list[tuple[int, float]]:
    """Hourly (default) price history: [(unix_seconds, price), ...]. Used by the backtest."""
    raw = get_json(f"{CLOB}/prices-history",
                   {"market": token_id, "interval": "max", "fidelity": fidelity_minutes})
    return [(int(p["t"]), float(p["p"])) for p in raw.get("history") or []]
