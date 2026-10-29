"""BACKTEST, step 1: download resolved markets and their hourly price history.

Runs on GitHub Actions (Polymarket's APIs are reachable from there). Read-only, public data.

    python -m bot.backtest_collect list       # find usable resolved markets -> data/backtest/markets.json.gz
    python -m bot.backtest_collect history    # download their hourly prices -> data/backtest/dataset.json.gz

Which markets are kept (none of these filters look into the future in a way that helps a trade):
  - resolved, binary, in our four categories, not politics/elections/geopolitics
  - event time inside the test window
  - total volume >= $5,000: a market below this could never pass F3 ($5,000 in 24h), so
    dropping it removes only markets the bot could never have traded
  - a resolution source is named (F5)
  - the market was open at least 3 days before the event (otherwise F2 can never pass)
If a category has more markets than --cap, a fixed random sample is taken (random = no bias).

Output: data/backtest/dataset.json.gz with, per market, the hourly price of outcome 0 from
15 days before the event until it closed. Outcome 1's price is 1 minus outcome 0's.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from . import data_feed as feed
from .fees import market_fee_rate
from .ledger import ROOT
from .run import load_config

OUT = os.path.join(ROOT, "data", "backtest", "dataset.json.gz")


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


MAX_OFFSET = 1900  # Gamma refuses offsets above ~2000 (HTTP 422)


def _fetch_window(tag: str, t: datetime, t2: datetime) -> list[dict] | None:
    """All closed events in [t, t2). None if the window holds too many to page through."""
    out, offset = [], 0
    while True:
        batch = feed.get_json(f"{feed.GAMMA}/events", {
            "closed": "true", "tag_slug": tag, "limit": 100, "offset": offset,
            "end_date_min": _iso(t), "end_date_max": _iso(t2),
            "order": "endDate", "ascending": "true"})
        out += batch or []
        if not batch or len(batch) < 100:
            return out
        offset += 100
        if offset > MAX_OFFSET:
            return None


def records_in_window(tag: str, a: datetime, b: datetime, cfg: dict, start: datetime,
                      end: datetime) -> tuple[list[dict], int]:
    """Usable market records for one tag and time window, splitting busy windows in half.

    Returns (records, number_of_events_seen). Events are reduced to records straight away,
    so the large raw responses are not kept in memory.
    """
    got = _fetch_window(tag, a, b)
    if got is None:
        if b - a <= timedelta(minutes=30):
            print(f"  warning: too many {tag} events in {a}..{b}; some skipped", file=sys.stderr, flush=True)
            return [], 0
        mid = a + (b - a) / 2
        r1, n1 = records_in_window(tag, a, mid, cfg, start, end)
        r2, n2 = records_in_window(tag, mid, b, cfg, start, end)
        return r1 + r2, n1 + n2
    recs = []
    for ev in got:
        recs += market_records(ev, cfg, start, end)
    return recs, len(got)


def market_records(ev: dict, cfg: dict, start: datetime, end: datetime) -> list[dict]:
    category = feed.event_category(ev, cfg)
    if category is None:
        return []
    out = []
    for m in ev.get("markets") or []:
        outcomes = feed._json_list(m.get("outcomes"))
        tokens = feed._json_list(m.get("clobTokenIds"))
        if len(outcomes) != 2 or len(tokens) != 2:
            continue
        event_time = feed.market_event_time(m, ev, category)
        opened = feed.parse_time(m.get("startDate")) or feed.parse_time(m.get("createdAt"))
        closed_at = feed.parse_time(m.get("closedTime")) or event_time
        vol = feed._num(m.get("volumeNum")) or feed._num(m.get("volume")) or 0
        if not event_time or not opened or not (start <= event_time <= end):
            continue
        if vol < cfg["filters"]["min_volume_24h"]:
            continue
        if not (m.get("resolutionSource") or "").strip():
            continue
        if opened > event_time - timedelta(days=cfg["filters"]["min_days_to_event"]):
            continue
        out.append({
            "market_id": str(m.get("id")), "event_id": str(ev.get("id")), "event_title": ev.get("title", ""),
            "question": m.get("question", ""), "category": category, "outcomes": outcomes,
            "token0": str(tokens[0]), "final_prices": [feed._num(p) for p in feed._json_list(m.get("outcomePrices"))],
            "event_time": _iso(event_time), "opened": _iso(opened), "closed_at": _iso(closed_at),
            "volume": round(vol, 2), "fee_rate": market_fee_rate(m, category, cfg),
        })
    return out


def sample_key(market_id: str) -> str:
    return hashlib.sha256(market_id.encode()).hexdigest()  # fixed "random" order


def fetch_history(rec: dict) -> list:
    ev_t = datetime.fromisoformat(rec["event_time"].replace("Z", "+00:00"))
    cl_t = datetime.fromisoformat(rec["closed_at"].replace("Z", "+00:00"))
    t0 = int((ev_t - timedelta(days=15)).timestamp())
    t1 = int((min(cl_t, ev_t + timedelta(days=2)) + timedelta(hours=2)).timestamp())
    if t1 <= t0:
        t1 = t0 + 3600
    for attempt in range(4):
        try:
            raw = feed.get_json(f"{feed.CLOB}/prices-history",
                                {"market": rec["token0"], "startTs": t0, "endTs": t1, "fidelity": 60})
            return [[int(p["t"]), int(round(float(p["p"]) * 1000))] for p in raw.get("history") or []]
        except Exception:
            time.sleep(3 * (attempt + 1))
    return None  # failed


LIST_OUT = os.path.join(ROOT, "data", "backtest", "markets.json.gz")


def stage_list(args, cfg, start, end) -> int:
    windows = []
    for tags in cfg["categories"].values():
        for tag in tags:
            t = start
            while t < end + timedelta(days=10):  # sports end dates can trail the game by a week
                windows.append((tag, t, t + timedelta(days=1)))
                t += timedelta(days=1)
    recs: dict[str, dict] = {}
    events_seen: dict[str, int] = {}
    t0, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futs = {pool.submit(records_in_window, tag, a, b, cfg, start, end): tag for tag, a, b in windows}
        for fut in as_completed(futs):
            tag = futs[fut]
            try:
                rs, n = fut.result()
            except Exception as err:
                print(f"  window failed for {tag}: {err}", file=sys.stderr, flush=True)
                continue
            events_seen[tag] = events_seen.get(tag, 0) + n
            for r in rs:
                recs.setdefault(r["market_id"], r)
            done += 1
            if done % 200 == 0:
                print(f"  listed {done}/{len(windows)} day-windows, {len(recs)} usable markets "
                      f"({time.time() - t0:.0f}s)", flush=True)
    print("closed events seen per tag:", events_seen, flush=True)
    by_cat: dict[str, int] = {}
    for r in recs.values():
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    print("usable markets per category:", by_cat, flush=True)
    os.makedirs(os.path.dirname(LIST_OUT), exist_ok=True)
    with gzip.open(LIST_OUT, "wt", encoding="utf-8") as fh:
        json.dump({"listed_at": _iso(datetime.now(timezone.utc)), "start": args.start, "end": args.end,
                   "events_seen": events_seen, "usable_per_category": by_cat,
                   "markets": list(recs.values())}, fh, separators=(",", ":"))
    print(f"Saved market list to {LIST_OUT} ({os.path.getsize(LIST_OUT) / 1e6:.1f} MB)", flush=True)
    return 0


def stage_history(args) -> int:
    with gzip.open(LIST_OUT, "rt", encoding="utf-8") as fh:
        listing = json.load(fh)
    by_cat: dict[str, list] = {}
    for r in listing["markets"]:
        by_cat.setdefault(r["category"], []).append(r)
    chosen = []
    for cat, rs in sorted(by_cat.items()):
        rs.sort(key=lambda r: sample_key(r["market_id"]))
        chosen += rs[: args.cap]
        print(f"category {cat}: {len(rs)} usable, using {min(len(rs), args.cap)}", flush=True)

    deadline = time.time() + args.max_minutes * 60
    t0, done, failed, skipped = time.time(), 0, 0, 0
    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        def work(r):
            if time.time() > deadline:
                return "skip"
            return fetch_history(r)
        futs = {pool.submit(work, r): r for r in chosen}
        for fut in as_completed(futs):
            r, h = futs[fut], fut.result()
            if h == "skip":
                skipped += 1
                r["history"] = None
            elif h is None:
                failed += 1
                r["history"] = []
            else:
                r["history"] = h
            done += 1
            if done % 1000 == 0:
                print(f"  history {done}/{len(chosen)} ({time.time() - t0:.0f}s, {failed} failed)", flush=True)
    kept = [r for r in chosen if r["history"] is not None]
    payload = {"collected_at": _iso(datetime.now(timezone.utc)), "start": listing["start"], "end": listing["end"],
               "cap_per_category": args.cap, "usable_per_category": listing["usable_per_category"],
               "history_failed": failed, "not_fetched_time_limit": skipped, "markets": kept}
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    print(f"Saved {len(kept)} markets ({failed} history failures, {skipped} skipped for time) to {OUT}, "
          f"{os.path.getsize(OUT) / 1e6:.1f} MB", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["list", "history"])
    ap.add_argument("--start", default="2026-04-28")
    ap.add_argument("--end", default="2026-10-27")
    ap.add_argument("--cap", type=int, default=12000, help="max markets per category (random sample)")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--max-minutes", type=float, default=200, help="history stage time budget")
    args = ap.parse_args(argv)
    cfg = load_config()
    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    return stage_list(args, cfg, start, end) if args.stage == "list" else stage_history(args)


if __name__ == "__main__":
    sys.exit(main())
