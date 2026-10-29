"""One scan of the bot. GitHub Actions runs this every hour.

    python -m bot.run              normal run (mode comes from config.json)
    python -m bot.run --dry-run    read data and print what would happen; saves nothing
    python -m bot.run --check-feed only test that the data feed works, then stop

Order of work in each scan:
  1. manage open paper positions (exit rules X1-X5)
  2. mark everything to the current bid and check the day's P&L
  3. look for new entries (F1-F6, E1-E5), pass each through the risk manager, paper-fill it
  4. save the account and rewrite the ledger, brief and scan report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import data_feed as feed
from . import ledger
from .brief import write_brief, write_scan_report
from .risk import check_new_trade, stake_for
from .simulator import simulate_buy, simulate_sell
from .strategy import exit_reason, select_entries

CONFIG_PATH = os.path.join(ledger.ROOT, "config.json")


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def equity_of(state: dict) -> float:
    """Cash plus open positions valued at the last known best bid (what we could sell for)."""
    # A position with no bid yet is valued at what it cost, not at zero: a missing quote must not
    # look like a loss and trip the daily loss limit (review finding #4).
    total = state["cash"]
    for p in state["positions"]:
        bid = p.get("last_bid")
        total += p["shares"] * bid if bid is not None else p["cost"] - p.get("partial_proceeds", 0.0)
    return round(total, 6)


MAX_READ_FAILURES = 24  # hourly scans in a row; after this a position is closed at its last bid


def _give_up(state, pos, why, now, scan):
    """Market data has been unavailable for a full day: close at the last known bid and say so."""
    bid = pos.get("last_bid") or 0.0
    rec = ledger.close_position(state, pos, pos["shares"], bid, pos["shares"] * bid, 0.0,
                                f"X5 market data unavailable for {MAX_READ_FAILURES}h ({why}); marked at last bid", now)
    scan["closed"].append(rec)
    scan["errors"].append(f"Position #{pos['id']} closed at last bid {bid:.3f} after {MAX_READ_FAILURES} failed reads. Check it by hand.")


def manage_positions(state: dict, cfg: dict, now: datetime, scan: dict, api=feed) -> None:
    for pos in list(state["positions"]):
        try:
            quotes = api.fetch_market_quotes(pos["market_id"], pos["category"], cfg)
            q = next((x for x in quotes if x.token_id == pos["token_id"]), None)
            if q is None:
                raise RuntimeError("outcome not found in market data")
        except Exception as err:
            pos["read_failures"] = pos.get("read_failures", 0) + 1
            if pos["read_failures"] >= MAX_READ_FAILURES:
                _give_up(state, pos, str(err)[:80], now, scan)
            else:
                scan["errors"].append(f"Position #{pos['id']}: could not read market ({err}); "
                                      f"kept open ({pos['read_failures']}/{MAX_READ_FAILURES})")
            continue
        pos["read_failures"] = 0
        if q.best_bid is not None:  # keep the previous mark if the market has no bid right now
            pos["last_bid"] = q.best_bid

        # Market already resolved: settle at its final price, whatever it is (1, 0, or a split
        # such as 0.5). No trading fee on redemption.
        if q.closed:
            if len(q.outcome_prices) == 2 and q.outcome_prices[q.outcome_index] is not None:
                final = q.outcome_prices[q.outcome_index]
                rec = ledger.close_position(state, pos, pos["shares"], final, pos["shares"] * final, 0.0,
                                            "Settled at resolution", now)
                scan["closed"].append(rec)
            else:
                pos["read_failures"] = pos.get("read_failures", 0) + 1
                scan["errors"].append(f"Position #{pos['id']}: market closed but no final price yet")
            continue

        # A sale that only partly filled last time keeps going with its original reason.
        reason = pos.get("pending_exit") or exit_reason(pos, q, now, cfg)
        if not reason:
            continue
        try:
            book = api.fetch_book(pos["token_id"])
        except Exception as err:
            scan["errors"].append(f"Position #{pos['id']}: {reason} but no order book ({err}); retry next scan")
            continue
        fill = simulate_sell(book, pos["shares"], pos["fee_rate"])
        if fill is None:
            scan["errors"].append(f"Position #{pos['id']}: {reason} but no bids; retry next scan")
            continue
        if fill.shares < pos["shares"] - 1e-9:
            # Thin book: bank what sold, keep selling the rest next scan under the same reason.
            ledger.record_partial_exit(state, pos, fill, reason)
            scan["errors"].append(f"Position #{pos['id']}: {reason}, sold {fill.shares:g} of "
                                  f"{fill.shares + pos['shares']:g} shares; rest next scan")
            continue
        rec = ledger.close_position(state, pos, fill.shares, fill.avg_price, fill.net_proceeds,
                                    fill.fee, reason, now)
        scan["closed"].append(rec)


def roll_day(state: dict, equity: float, now: datetime) -> None:
    """At the first scan of each UTC day, remember the starting equity for the daily loss limit."""
    today = now.date().isoformat()
    if state["day"] != today:
        state["day"] = today
        state["day_start_equity"] = equity


def find_entries(state: dict, cfg: dict, now: datetime, scan: dict, api=feed) -> None:
    try:
        events = api.fetch_events(cfg, now)
    except Exception as err:
        scan["errors"].append(f"Could not read market list: {err}")
        return
    quotes = [q for ev in events for q in feed.quotes_from_event(ev, cfg)]
    scan["events"], scan["quotes"] = len(events), len(quotes)

    held_events = {p["event_id"] for p in state["positions"]}
    signals, skipped = select_entries(quotes, now, cfg, held_events, set(state["traded_market_ids"]))
    scan["skipped"] = skipped

    for q, confidence in signals:
        equity = equity_of(state)
        stake = stake_for(confidence, equity, cfg)
        info = {"question": q.question, "outcome": q.outcome, "ask": q.best_ask, "spread": q.spread,
                "volume_24h": q.volume_24h, "confidence": confidence,
                "days_to_event": (q.event_time - now).total_seconds() / 86400}
        blocked = check_new_trade(state, stake, equity, cfg)
        if blocked:
            info["action"] = f"not traded: {blocked}"
            scan["signals"].append(info)
            continue
        try:
            book = api.fetch_book(q.token_id)
        except Exception as err:
            info["action"] = f"not traded: no order book ({err})"
            scan["signals"].append(info)
            continue
        fill = simulate_buy(book, stake, cfg["entry"]["max_price"], q.fee_rate, cfg["stakes"]["min_shares"])
        if fill is None or fill.avg_price < cfg["entry"]["min_price"] - 1e-9:
            info["action"] = "not traded: order book could not fill inside the price range"
            scan["signals"].append(info)
            continue
        pos = ledger.open_position(state, q, fill, confidence, stake, now, cfg)
        info["action"] = f"PAPER BUY #{pos['id']}: {fill.shares:g} sh @ {fill.avg_price:.3f}, cost ${fill.net_cost:.2f}"
        scan["signals"].append(info)
        scan["opened"].append(pos)


def run(cfg: dict, now: datetime | None = None, dry_run: bool = False, api=feed,
        root: str = ledger.ROOT) -> dict:
    """One full scan. `root` is the folder holding data/, reports/ and the .md files."""
    now = now or datetime.now(timezone.utc)
    if dry_run:
        cfg = {**cfg, "mode": "scan_only"}  # a dry run can never open paper trades
    state_path = os.path.join(root, "data", "state.json")
    state = ledger.load_state(cfg, now, state_path)
    scan = {"mode": cfg["mode"], "events": 0, "quotes": 0, "signals": [], "opened": [],
            "closed": [], "skipped": {}, "errors": []}

    manage_positions(state, cfg, now, scan, api)
    roll_day(state, equity_of(state), now)
    find_entries(state, cfg, now, scan, api)

    equity = equity_of(state)
    state["equity_curve"].append([now.isoformat(), equity])
    if not dry_run:
        ledger.maybe_write_reviews(state, now, os.path.join(root, "Learning.md"))
        ledger.save_state(state, state_path)
        ledger.render_ledger(state, equity, now, os.path.join(root, "Trade_Ledger.md"))
        write_scan_report(scan, now, os.path.join(root, "reports", "last_scan.md"))
        write_brief(state, equity, scan, cfg, now, os.path.join(root, "reports", "brief.md"))
    return {"state": state, "scan": scan, "equity": equity}


def check_feed(cfg: dict) -> int:
    """Prove the data reads correctly before any paper trade: list, quote, book, history."""
    now = datetime.now(timezone.utc)
    events = feed.fetch_events(cfg, now)
    quotes = [q for ev in events for q in feed.quotes_from_event(ev, cfg)]
    print(f"Events: {len(events)}  Outcomes: {len(quotes)}")
    by_cat = {}
    for q in quotes:
        by_cat[q.category] = by_cat.get(q.category, 0) + 1
    print("Outcomes by category:", by_cat)
    # Only markets that are actually trading have an order book.
    live = [q for q in quotes if q.best_ask is not None and q.best_bid is not None and q.active
            and not q.closed and q.accepting_orders and not q.uma_status and 0.05 < q.best_ask < 0.95]
    if not live:
        print("FAIL: no tradable quotes with prices")
        return 1
    # One sample per category: the busiest tradable outcome in each.
    samples = {}
    for q in sorted(live, key=lambda x: -x.volume_24h):
        samples.setdefault(q.category, q)
    good = 0
    for cat, q in samples.items():
        try:
            book = feed.fetch_book(q.token_id)
            hist = feed.fetch_price_history(q.token_id)
        except Exception as err:
            print(f"[{cat}] {q.question} [{q.outcome}]: ERROR {err}")
            continue
        sane = book.best_bid is not None and book.best_ask is not None and book.best_bid < book.best_ask
        close = sane and abs(book.best_ask - q.best_ask) <= 0.02 and abs(book.best_bid - q.best_bid) <= 0.02
        good += sane and close
        print(f"[{cat}] {q.question} [{q.outcome}] | Gamma bid/ask {q.best_bid}/{q.best_ask} | "
              f"book bid/ask {book.best_bid}/{book.best_ask} ({len(book.bids)}/{len(book.asks)} levels) | "
              f"fee {q.fee_rate} | history points {len(hist)} | {'OK' if close else 'MISMATCH'}")
    ok = good >= max(1, len(samples) - 1)  # allow one sample to move between the two reads
    print(f"FEED OK ({good}/{len(samples)} samples match)" if ok else f"FAIL: only {good}/{len(samples)} samples match")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Polymarket paper bot (Strategy A)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check-feed", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.check_feed:
        return check_feed(cfg)
    result = run(cfg, dry_run=args.dry_run)
    scan = result["scan"]
    print(f"mode={scan['mode']} events={scan['events']} outcomes={scan['quotes']} "
          f"signals={len(scan['signals'])} opened={len(scan['opened'])} closed={len(scan['closed'])} "
          f"equity={result['equity']:.2f}")
    for s in scan["signals"]:
        print(f"  SIGNAL {s['question']} [{s['outcome']}] ask {s['ask']:.3f} -> {s['action']}")
    for e in scan["errors"]:
        print(f"  ERROR {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
