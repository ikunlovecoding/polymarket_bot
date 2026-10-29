"""BACKTEST, step 2: replay Strategy A on resolved markets, hour by hour. Offline.

    python -m bot.backtest                      # uses data/backtest/dataset.json.gz
    python -m bot.backtest --split 2026-08-28   # in-sample before, out-of-sample from this date

How a trade is simulated (the same rules as the live bot, with these stated differences):
  - Prices are Polymarket's hourly price history. There is no historical order book, so we
    BUY at price + 1c and SELL at price - 1c (the "1c slippage per side" in Strategy.md),
    then charge each market's own taker fee on top.
  - F3 (24h volume) and F4 (spread) can't be checked historically. The collector only keeps
    markets with >= $5,000 total volume (a necessary condition for F3), so this backtest is
    somewhat more permissive than the live bot.
  - Confidence uses 24h volume, which history doesn't have, so every trade is staked at 3%
    (normal). A 5% run is reported for comparison.
  - The live bot ranks same-hour signals by 24h volume. Here they are taken in a fixed random
    order, which is unbiased.
  - Rules are checked once per hour, like the live bot. Exits before entries.
No information from after the decision hour is used for any decision (no lookahead):
only prices at or before hour H are used at hour H.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .fees import taker_fee
from .ledger import ROOT
from .run import load_config

DATASET = os.path.join(ROOT, "data", "backtest", "dataset.json.gz")
REPORT = os.path.join(ROOT, "reports", "backtest.md")
SUMMARY = os.path.join(ROOT, "data", "backtest_summary.json")
HOUR = 3600
SLIP = 0.01          # per side
STALE_HOURS = 3      # a price older than this is treated as "no data this hour"
PRICE_LAG = HOUR     # conservative: decisions at hour H use prices stamped H-1h or earlier
GAP_PENALTY = 0.01   # extra cost when forced to exit with no fresh price


def ts(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def hour_floor(t: int) -> int:
    return t - t % HOUR


# ---------------------------------------------------------------- preparing market series

class Series:
    """One market's hourly price of outcome 0, forward-filled for at most STALE_HOURS."""

    def __init__(self, rec: dict):
        self.rec = rec
        self.market_id = rec["market_id"]
        self.event_id = rec["event_id"]
        self.category = rec["category"]
        self.fee_rate = rec["fee_rate"]
        self.event_t = ts(rec["event_time"])
        self.closed_t = ts(rec["closed_at"])
        self.final = rec["final_prices"]
        self.order_key = hashlib.sha256(self.market_id.encode()).hexdigest()
        pts = sorted((int(t), p / 1000.0) for t, p in rec.get("history") or [])
        self.prices: dict[int, float] = {}
        if not pts:
            return
        i = 0
        h = hour_floor(pts[0][0]) + HOUR
        last_pt = None
        end = min(self.closed_t, pts[-1][0] + STALE_HOURS * HOUR)
        while h <= end:
            # Only points stamped at least PRICE_LAG before h count. If Polymarket stamps an
            # hourly bucket with its start time but fills it with the end price, this still
            # never lets hour h see a price from after h (review finding #7).
            while i < len(pts) and pts[i][0] <= h - PRICE_LAG:
                last_pt = pts[i]
                i += 1
            if last_pt and h - last_pt[0] <= STALE_HOURS * HOUR:
                self.prices[h] = last_pt[1]
            h += HOUR

    def price(self, h: int, outcome: int) -> float | None:
        p = self.prices.get(h)
        if p is None:
            return None
        return p if outcome == 0 else round(1 - p, 6)


# ---------------------------------------------------------------- the simulation

def simulate(series: list[Series], cfg: dict, stake_pct: float, start: int, end: int,
             unlimited: bool = False) -> dict:
    """Replay hour by hour from `start` to `end` (unix seconds).

    unlimited=False: a $1,000 paper account with every risk limit (realistic).
    unlimited=True : every signal is taken at a fixed $30 stake, no limits (more trades,
                     used only for per-trade statistics).
    """
    f, e, x, r = cfg["filters"], cfg["entry"], cfg["exits"], cfg["risk"]
    bank = float(cfg["starting_bankroll"])
    cash, day, day_start_eq = bank, None, bank
    positions, trades, curve = [], [], []
    traded, held_events = set(), set()

    by_start = sorted(series, key=lambda s: s.event_t)
    active: list[Series] = []
    nxt = 0

    def equity(h):
        val = cash
        for p in positions:
            px = p["series"].price(h, p["outcome"])
            bid = max(0.0, (px if px is not None else p["last_bid"] + SLIP) - SLIP)
            val += p["shares"] * bid
        return val

    h = hour_floor(start)
    while h <= end:
        # markets enter the active set 14 days before their event, leave after they close
        while nxt < len(by_start) and by_start[nxt].event_t - f["max_days_to_event"] * 86400 <= h:
            active.append(by_start[nxt])
            nxt += 1
        if h % (24 * HOUR) == 0:
            active = [s for s in active if s.closed_t + 2 * 86400 >= h]

        # ---- exits first
        for p in list(positions):
            s, k = p["series"], p["outcome"]
            reason, exit_px, fee = None, None, 0.0
            if h >= s.closed_t:
                final = s.final[k] if len(s.final) == 2 and s.final[k] is not None else None
                if final is None:
                    px = s.price(h, k)
                    final = px if px is not None else p["last_bid"]
                reason, exit_px = "Settled at resolution", final
                proceeds = p["shares"] * final
            else:
                px = s.price(h, k)
                time_up = h - p["opened"] >= x["max_hold_days"] * 86400
                near_event = h >= s.event_t - x["exit_hours_before_event"] * HOUR
                if px is None:
                    # No fresh price. Price-based exits can't fire, but the time-based ones must,
                    # or the position would ride into resolution (review finding #1). Exit at the
                    # last known bid minus a penalty, and label it so it shows in the report.
                    if not (time_up or near_event):
                        continue
                    bid = max(0.0, p["last_bid"] - GAP_PENALTY)
                    reason = ("X3 time stop" if time_up else "X4 pre-resolution exit") + " (no fresh price)"
                else:
                    bid = max(0.0, px - SLIP)
                    p["last_bid"] = bid
                    if bid >= p["entry"] * x["take_profit_mult"] - 1e-9:
                        reason = "X1 take profit"
                    elif bid <= p["entry"] * x["stop_loss_mult"] + 1e-9:
                        reason = "X2 stop loss"
                    elif time_up:
                        reason = "X3 time stop"
                    elif near_event:
                        reason = "X4 pre-resolution exit"
                if reason is None:
                    continue
                exit_px = bid
                fee = taker_fee(p["shares"], bid, s.fee_rate)
                proceeds = p["shares"] * bid - fee
            pnl = proceeds - p["cost"]
            cash += proceeds
            positions.remove(p)
            held_events.discard(s.event_id)
            trades.append({"market_id": s.market_id, "question": s.rec["question"], "category": s.category,
                           "outcome": s.rec["outcomes"][k], "opened": p["opened"], "closed": h,
                           "entry": p["entry"], "exit": exit_px, "shares": p["shares"], "cost": p["cost"],
                           "pnl": pnl, "pnl_pct": pnl / p["cost"] * 100, "reason": reason,
                           "event_t": s.event_t, "fee_rate": s.fee_rate})

        # ---- daily loss bookkeeping (UTC day)
        eq = equity(h)
        d = datetime.fromtimestamp(h, timezone.utc).date()
        if d != day:
            day, day_start_eq = d, eq

        # ---- entries
        if unlimited or (eq - day_start_eq > -r["daily_loss_limit"]):
            cands = []
            for s in active:
                if s.market_id in traded or s.event_id in held_events:
                    continue
                days = (s.event_t - h) / 86400
                if not (f["min_days_to_event"] <= days <= f["max_days_to_event"]) or h >= s.closed_t:
                    continue
                for k in (0, 1):
                    px = s.price(h, k)
                    if px is None:
                        continue
                    ask = round(px + SLIP, 6)
                    if e["min_price"] - 1e-9 <= ask <= e["max_price"] + 1e-9:
                        cands.append((s.order_key, k, s, ask))
            # Random-but-fixed order across markets; within one market the cheaper outcome first,
            # matching the live bot's tie-break (review finding #9).
            cands.sort(key=lambda c: (c[0], c[3]))
            for _, k, s, ask in cands:
                if s.market_id in traded or s.event_id in held_events:
                    continue  # one per event / market
                stake = 30.0 if unlimited else round(max(0.0, eq) * stake_pct, 2)
                if not unlimited:
                    exposure = sum(p["cost"] for p in positions)
                    if exposure + stake > eq * r["max_exposure_pct"] + 1e-9 or stake > cash + 1e-9:
                        continue
                per_share = ask + taker_fee(1, ask, s.fee_rate)
                shares = math.floor(stake / per_share)
                while shares > 0 and shares * ask + taker_fee(shares, ask, s.fee_rate) > stake + 1e-9:
                    shares -= 1
                if shares < cfg["stakes"]["min_shares"]:
                    continue
                cost = shares * ask + taker_fee(shares, ask, s.fee_rate)
                cash -= cost
                positions.append({"series": s, "outcome": k, "entry": ask, "shares": shares, "cost": cost,
                                  "opened": h, "last_bid": max(0.0, ask - 2 * SLIP)})
                traded.add(s.market_id)
                held_events.add(s.event_id)

        if not unlimited:
            curve.append((h, equity(h)))
        h += HOUR

    # close anything still open at the end at its last bid (marked, flagged)
    for p in positions:
        trades.append({"market_id": p["series"].market_id, "question": p["series"].rec["question"],
                       "category": p["series"].category, "outcome": p["series"].rec["outcomes"][p["outcome"]],
                       "opened": p["opened"], "closed": end, "entry": p["entry"], "exit": p["last_bid"],
                       "shares": p["shares"], "cost": p["cost"],
                       "pnl": p["shares"] * p["last_bid"] - p["cost"],
                       "pnl_pct": (p["shares"] * p["last_bid"] - p["cost"]) / p["cost"] * 100,
                       "reason": "Open at end (marked)", "event_t": p["series"].event_t,
                       "fee_rate": p["series"].fee_rate})
        cash += p["shares"] * p["last_bid"]
    return {"trades": trades, "curve": curve, "final_equity": cash if not unlimited else None}


# ---------------------------------------------------------------- statistics

def planned_breakeven(entry: float, fee_rate: float, tp: float = 1.5, sl: float = 0.75) -> float:
    """Win rate needed to break even if every trade ends exactly at +50% or -25% of the entry
    price, after fees on both sides. Uses only what is known when the trade is opened."""
    cost = entry + taker_fee(1, entry, fee_rate)
    win_bid, loss_bid = min(0.999, entry * tp), entry * sl
    win = win_bid - taker_fee(1, win_bid, fee_rate) - cost
    loss = loss_bid - taker_fee(1, loss_bid, fee_rate) - cost
    return abs(loss) / (win + abs(loss)) if win > 0 else 1.0


def summarize(trades: list, curve: list, bank: float) -> dict:
    n = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]   # same convention as the live ledger
    avg_w = sum(t["pnl"] for t in wins) / len(wins) if wins else 0.0
    avg_l = sum(t["pnl"] for t in losses) / len(losses) if losses else 0.0
    avg_wp = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0.0
    avg_lp = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0.0
    total = sum(t["pnl"] for t in trades)
    peak, mdd = None, 0.0
    for _, eq in curve:
        peak = eq if peak is None else max(peak, eq)
        if peak > 0:
            mdd = max(mdd, (peak - eq) / peak)
    months = None
    if curve:
        months = (curve[-1][0] - curve[0][0]) / (30.44 * 86400)
    # Break-even fixed in advance from each trade's entry price, fee rate and slippage, not from
    # the results themselves (review finding #5). Averaged over the trades actually taken.
    be = sum(planned_breakeven(t["entry"], t.get("fee_rate", 0.05)) for t in trades) / n * 100 if n else None
    return {
        "trades": n,
        "win_rate": round(len(wins) / n * 100, 1) if n else 0.0,
        "breakeven_win_rate": round(be, 1) if be is not None else None,
        "avg_win": round(avg_w, 2), "avg_loss": round(avg_l, 2),
        "avg_win_pct": round(avg_wp, 1), "avg_loss_pct": round(avg_lp, 1),
        "risk_reward": round(avg_w / abs(avg_l), 2) if avg_l else None,
        "total_pnl": round(total, 2),
        "expectancy": round(total / n, 2) if n else 0.0,
        "expectancy_pct": round(sum(t["pnl_pct"] for t in trades) / n, 2) if n else 0.0,
        "return_pct": round(total / bank * 100, 2),
        "monthly_return_pct": round(total / bank * 100 / months, 2) if months else None,
        "max_drawdown_pct": round(mdd * 100, 2),
    }


def breakdown(trades: list, key) -> dict:
    groups = defaultdict(list)
    for t in trades:
        groups[key(t)].append(t)
    out = {}
    for g, ts_ in sorted(groups.items()):
        n = len(ts_)
        out[g] = {"trades": n, "win_rate": round(sum(t["pnl"] > 0 for t in ts_) / n * 100, 1),
                  "avg_pnl_pct": round(sum(t["pnl_pct"] for t in ts_) / n, 2),
                  "total_pnl": round(sum(t["pnl"] for t in ts_), 2)}
    return out


def price_bucket(t):
    lo = int(t["entry"] * 20) * 5
    return f"{lo:02d}-{lo + 5:02d}c"


# ---------------------------------------------------------------- report

def verdict(oos: dict, oos_all: dict) -> tuple[bool, list]:
    """Strategy.md section 8: fails if any of these is true (checked on out-of-sample data)."""
    fails = []
    if oos_all["breakeven_win_rate"] is not None and oos_all["win_rate"] < oos_all["breakeven_win_rate"]:
        fails.append(f"out-of-sample win rate {oos_all['win_rate']}% < break-even {oos_all['breakeven_win_rate']}%")
    if oos["total_pnl"] <= 0:
        fails.append(f"out-of-sample net P&L ${oos['total_pnl']} <= 0")
    if oos["max_drawdown_pct"] > 20:
        fails.append(f"max drawdown {oos['max_drawdown_pct']}% > 20%")
    return (not fails), fails


def table(rows: dict, title: str) -> list:
    lines = [f"| {title} | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |", "|---|---|---|---|---|"]
    for k, v in rows.items():
        lines.append(f"| {k} | {v['trades']} | {v['win_rate']}% | {v['avg_pnl_pct']:+.2f}% | ${v['total_pnl']:+,.2f} |")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=DATASET)
    ap.add_argument("--split", default="2026-08-28")
    args = ap.parse_args(argv)
    cfg = load_config()
    bank = float(cfg["starting_bankroll"])

    with gzip.open(args.dataset, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    series = [Series(r) for r in data["markets"]]
    with_data = [s for s in series if s.prices]
    start = ts(data["start"] + "T00:00:00Z") - 14 * 86400
    end = ts(data["end"] + "T23:00:00Z")
    split = ts(args.split + "T00:00:00Z")
    ins = [s for s in with_data if s.event_t < split]
    oos = [s for s in with_data if s.event_t >= split]

    results = {}
    for name, ss, a, b in (("in_sample", ins, start, split), ("out_of_sample", oos, split - 14 * 86400, end)):
        port = simulate(ss, cfg, cfg["stakes"]["normal_pct"], a, b)
        port5 = simulate(ss, cfg, cfg["stakes"]["high_pct"], a, b)
        allsig = simulate(ss, cfg, 0, a, b, unlimited=True)
        results[name] = {
            "markets": len(ss),
            "portfolio": summarize(port["trades"], port["curve"], bank),
            "portfolio_5pct": summarize(port5["trades"], port5["curve"], bank),
            "all_signals": summarize(allsig["trades"], [], bank),
            "by_category": breakdown(allsig["trades"], lambda t: t["category"]),
            "by_exit": breakdown(allsig["trades"], lambda t: t["reason"].split(" ")[0] if t["reason"][0] == "X" else t["reason"]),
            "by_price": breakdown(allsig["trades"], price_bucket),
        }
    ok, fails = verdict(results["out_of_sample"]["portfolio"], results["out_of_sample"]["all_signals"])

    summary = {"generated": datetime.now(timezone.utc).isoformat()[:16], "dataset_collected": data["collected_at"],
               "window": [data["start"], data["end"]], "split": args.split, "passed": ok, "fails": fails,
               "markets_total": len(series), "markets_with_history": len(with_data),
               **{k: results["out_of_sample"]["portfolio"][k] for k in ("win_rate", "avg_win", "avg_loss", "max_drawdown_pct")},
               "results": results}
    os.makedirs(os.path.dirname(SUMMARY), exist_ok=True)
    with open(SUMMARY, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    write_report(summary, data)
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
    return 0


def write_report(s: dict, data: dict) -> None:
    R = s["results"]
    L = [f"# Backtest: Strategy A", f"Generated {s['generated']} UTC from data collected {s['dataset_collected'][:16]} UTC.",
         "",
         f"## Verdict: {'PASSED' if s['passed'] else 'FAILED'}",
         ]
    L += ([f"- {x}" for x in s["fails"]] if s["fails"] else ["- Out-of-sample results meet every rule in Strategy.md section 8."])
    L += ["", "## Data",
          f"- Events from {s['window'][0]} to {s['window'][1]}; in-sample before {s['split']}, out-of-sample from {s['split']}.",
          f"- Resolved markets used: **{s['markets_with_history']:,}** with price history (of {s['markets_total']:,} collected).",
          f"- Usable markets found per category before sampling: {data.get('usable_per_category')}; cap {data.get('cap_per_category')} per category.",
          "", "## Results"]
    hdr = ["| | Markets | Trades | Win rate | Break-even | Avg win | Avg loss | R:R | Net P&L | Return | Per month | Max drawdown |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    L += hdr
    for name in ("in_sample", "out_of_sample"):
        for label, key in (("$1,000 account, 3% stakes", "portfolio"), ("$1,000 account, 5% stakes", "portfolio_5pct"),
                           ("every signal, $30 each", "all_signals")):
            m = R[name][key]
            L.append(f"| {name.replace('_', '-')}: {label} | {R[name]['markets']:,} | {m['trades']:,} | {m['win_rate']}% | "
                     f"{m['breakeven_win_rate']}% | ${m['avg_win']} ({m['avg_win_pct']:+}%) | ${m['avg_loss']} ({m['avg_loss_pct']:+}%) | "
                     f"{m['risk_reward']} | ${m['total_pnl']:+,.2f} | {m['return_pct']:+}% | "
                     f"{'' if m['monthly_return_pct'] is None else str(m['monthly_return_pct']) + '%'} | "
                     f"{'' if key == 'all_signals' else str(m['max_drawdown_pct']) + '%'} |")
    for name in ("in_sample", "out_of_sample"):
        L += ["", f"### {name.replace('_', '-')}: every signal, broken down"]
        L += table(R[name]["by_category"], "Category") + [""]
        L += table(R[name]["by_exit"], "Exit") + [""]
        L += table(R[name]["by_price"], "Entry price")
    L += ["", "## Assumptions and limits",
          "- No historical order book: buys at hourly price + 1c, sells at price - 1c, plus each market's taker fee.",
          "- 24h volume and spread can't be checked historically; markets with under $5,000 total volume are excluded.",
          "- All stakes 3% (confidence needs 24h volume). A 5% run is shown for comparison.",
          "- Same-hour signals taken in a fixed random order (the live bot uses 24h volume).",
          "- Rules checked hourly; a stop can fill below -25% if the price jumps between hours.",
          "- Hourly prices are Polymarket's price history series, not executed trades.",
          "- Decisions at hour H use prices stamped H-1h or earlier (conservative, avoids any 1-hour lookahead).",
          "- If a market has no fresh price when a time-based exit is due, it exits at the last known bid minus 1c.",
          "- Only events that fully closed are included, and game times are their final values (postponements included).",
          "- X5 (invalidation on wide spreads or disputes) is live-bot only; the backtest has no spread data.",
          "- Break-even win rate is fixed in advance from each trade's entry price and fee rate (exit exactly at +50% / -25%)."]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
