"""LOGGER: keeps the paper account and writes the human-readable files.

  data/state.json   the paper account (source of truth: cash, positions, closed trades)
  Trade_Ledger.md   every paper trade with all the fields from the build prompt
  Learning.md       numeric reviews every 10 and 25 trades (Claude adds the written lessons)

The bot never edits config.json or Strategy.md: strategy changes are made by you, from reviews.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(ROOT, "data", "state.json")
LEDGER_PATH = os.path.join(ROOT, "Trade_Ledger.md")
LEARNING_PATH = os.path.join(ROOT, "Learning.md")
BACKTEST_SUMMARY = os.path.join(ROOT, "data", "backtest_summary.json")


# ---------------------------------------------------------------- state

def new_state(cfg: dict, now: datetime) -> dict:
    bank = float(cfg["starting_bankroll"])
    return {
        "version": 1,
        "created_at": now.isoformat(),
        "starting_bankroll": bank,
        "cash": bank,
        "day": now.date().isoformat(),
        "day_start_equity": bank,
        "positions": [],
        "closed": [],
        "traded_market_ids": [],
        "equity_curve": [],
        "reviews_done": [],
        "next_id": 1,
    }


def load_state(cfg: dict, now: datetime, path: str = STATE_PATH) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return new_state(cfg, now)


def save_state(state: dict, path: str = STATE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, path)  # atomic: a crash never leaves a half-written file


# ---------------------------------------------------------------- recording trades

def open_position(state: dict, quote, fill, confidence: str, stake: float, now: datetime,
                  cfg: dict) -> dict:
    x = cfg["exits"]
    days = (quote.event_time - now).total_seconds() / 86400 if quote.event_time else None
    pos = {
        "id": state["next_id"],
        "strategy": "A-price-range",
        "event_id": quote.event_id,
        "event_title": quote.event_title,
        "market_id": quote.market_id,
        "question": quote.question,
        "outcome": quote.outcome,
        "token_id": quote.token_id,
        "category": quote.category,
        "direction": f"BUY {quote.outcome}",
        "confidence": confidence,
        "stake": stake,
        "opened_at": now.isoformat(),
        "entry_price": fill.avg_price,
        "shares": fill.shares,
        "cost": fill.net_cost,
        "fee_entry": fill.fee,
        "fee_rate": quote.fee_rate,
        "take_profit": round(fill.avg_price * x["take_profit_mult"], 4),
        "stop_loss": round(fill.avg_price * x["stop_loss_mult"], 4),
        "event_time": quote.event_time.isoformat() if quote.event_time else None,
        "trigger": f"E1 ask {quote.best_ask:.3f} in range; {confidence} confidence",
        "conditions": {
            "ask": quote.best_ask, "bid": quote.best_bid, "spread": quote.spread,
            "volume_24h": round(quote.volume_24h, 2),
            "days_to_event": round(days, 2) if days is not None else None,
            "levels_used": fill.levels_used,
        },
        "last_bid": quote.best_bid,
    }
    state["next_id"] += 1
    state["cash"] = round(state["cash"] - fill.net_cost, 6)
    state["positions"].append(pos)
    if quote.market_id not in state["traded_market_ids"]:
        state["traded_market_ids"].append(quote.market_id)
    return pos


def record_partial_exit(state: dict, pos: dict, fill, reason: str) -> None:
    """A sale that only partly filled: bank the cash, keep the rest of the position open,
    and remember the reason so the next scan keeps selling. One trade = one ledger record."""
    pos.setdefault("orig_shares", pos["shares"])
    pos["partial_shares"] = round(pos.get("partial_shares", 0.0) + fill.shares, 6)
    pos["partial_gross"] = round(pos.get("partial_gross", 0.0) + fill.gross, 6)
    pos["partial_proceeds"] = round(pos.get("partial_proceeds", 0.0) + fill.net_proceeds, 6)
    pos["partial_fees"] = round(pos.get("partial_fees", 0.0) + fill.fee, 6)
    pos["shares"] = round(pos["shares"] - fill.shares, 6)
    pos["pending_exit"] = reason
    state["cash"] = round(state["cash"] + fill.net_proceeds, 6)


def close_position(state: dict, pos: dict, shares: float, exit_price: float, proceeds: float,
                   fee: float, reason: str, now: datetime) -> dict:
    """Close what is left of a position (`shares` must be all remaining shares) and write ONE
    record for the whole trade, including any earlier partial sales."""
    total_shares = pos.get("orig_shares", pos["shares"])
    sold_before = pos.get("partial_shares", 0.0)
    total_proceeds = round(pos.get("partial_proceeds", 0.0) + proceeds, 6)
    total_fee = round(pos.get("partial_fees", 0.0) + fee, 6)
    gross_now = proceeds + fee  # this fill before fees (settlements have fee 0)
    avg_exit = (pos.get("partial_gross", 0.0) + gross_now) / (sold_before + shares) if (sold_before + shares) else exit_price
    pnl = round(total_proceeds - pos["cost"], 6)
    drop = {"last_bid", "orig_shares", "partial_shares", "partial_gross", "partial_proceeds",
            "partial_fees", "pending_exit", "read_failures"}
    record = {k: v for k, v in pos.items() if k not in drop}
    record.update({
        "shares": total_shares,
        "closed_at": now.isoformat(),
        "exit_price": round(avg_exit, 6),
        "proceeds": total_proceeds,
        "fee_exit": total_fee,
        "pnl": pnl,
        "pnl_pct": round(pnl / pos["cost"] * 100, 2) if pos["cost"] else 0.0,
        "exit_reason": reason,
        "result": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "FLAT"),
        "observations": _observation(pos, avg_exit, reason, now)
                        + (f" Sold in parts ({sold_before:g} + {shares:g} shares)." if sold_before else ""),
    })
    state["cash"] = round(state["cash"] + proceeds, 6)
    state["closed"].append(record)
    state["positions"].remove(pos)
    return record


def _observation(pos: dict, exit_price: float, reason: str, now: datetime) -> str:
    """Plain facts only. Opinions and lessons are for the written reviews."""
    held_h = (now - datetime.fromisoformat(pos["opened_at"])).total_seconds() / 3600
    move = (exit_price / pos["entry_price"] - 1) * 100 if pos["entry_price"] else 0
    note = f"Held {held_h:.0f}h; price moved {move:+.1f}% (entry {pos['entry_price']:.3f} -> exit {exit_price:.3f})."
    if reason.startswith("X2") and exit_price < pos["stop_loss"] - 0.005:
        note += f" Stop gapped: filled below stop {pos['stop_loss']:.3f}."
    return note


# ---------------------------------------------------------------- statistics

def stats(closed: list, equity_curve: list) -> dict:
    wins = [t["pnl"] for t in closed if t["pnl"] > 0]
    losses = [t["pnl"] for t in closed if t["pnl"] < 0]
    n = len(closed)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    peak, max_dd = None, 0.0
    for _, eq in equity_curve:
        peak = eq if peak is None else max(peak, eq)
        if peak:
            max_dd = max(max_dd, (peak - eq) / peak)
    return {
        "trades": n,
        "win_rate": round(len(wins) / n * 100, 1) if n else 0.0,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "risk_reward": round(avg_win / abs(avg_loss), 2) if avg_loss else None,
        "total_pnl": round(sum(t["pnl"] for t in closed), 2),
        "expectancy": round(sum(t["pnl"] for t in closed) / n, 2) if n else 0.0,
        "max_drawdown_pct": round(max_dd * 100, 2),
    }


# ---------------------------------------------------------------- markdown files

def _fmt_time(iso: str | None) -> str:
    return iso[:16].replace("T", " ") + " UTC" if iso else "-"


def render_ledger(state: dict, equity: float, now: datetime, path: str = LEDGER_PATH) -> None:
    s = stats(state["closed"], state["equity_curve"])
    lines = [
        "# Trade_Ledger.md",
        f"Paper trades only. Updated {_fmt_time(now.isoformat())}. Strategy: Version A (Strategy.md).",
        "",
        "## Account",
        f"- Equity: **${equity:,.2f}** (start ${state['starting_bankroll']:,.2f}, "
        f"P&L {equity - state['starting_bankroll']:+,.2f})",
        f"- Cash: ${state['cash']:,.2f} · Open positions: {len(state['positions'])}",
        f"- Closed trades: {s['trades']} · Win rate {s['win_rate']}% · Avg win ${s['avg_win']} · "
        f"Avg loss ${s['avg_loss']} · R:R {s['risk_reward']} · Max drawdown {s['max_drawdown_pct']}%",
        "",
        "## Open positions",
    ]
    if state["positions"]:
        lines += ["| # | Market | Direction | Entry | Shares | Stake | Stop | Target | Last bid | Opened | Event time |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for p in state["positions"]:
            lines.append(f"| {p['id']} | {p['question']} | {p['direction']} | {p['entry_price']:.3f} | "
                         f"{p['shares']:g} | ${p['cost']:.2f} | {p['stop_loss']:.3f} | {p['take_profit']:.3f} | "
                         f"{(p.get('last_bid') or 0):.3f} | {_fmt_time(p['opened_at'])} | {_fmt_time(p['event_time'])} |")
    else:
        lines.append("None.")
    lines += ["", "## Closed trades"]
    if state["closed"]:
        lines += ["| # | Market | Direction | Entry | Exit | Stake | Stop | Target | Strategy | Trigger | "
                  "Conditions at entry | Exit reason | Result | P&L | Observations |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for t in reversed(state["closed"]):
            c = t["conditions"]
            cond = (f"ask {c['ask']}, spread {c['spread']}, vol24h ${c['volume_24h']:,.0f}, "
                    f"{c['days_to_event']}d to event")
            lines.append(f"| {t['id']} | {t['question']} | {t['direction']} | {t['entry_price']:.3f} | "
                         f"{t['exit_price']:.3f} | ${t['cost']:.2f} | {t['stop_loss']:.3f} | {t['take_profit']:.3f} | "
                         f"{t['strategy']} | {t['trigger']} | {cond} | {t['exit_reason']} | {t['result']} | "
                         f"{t['pnl']:+.2f} ({t['pnl_pct']:+.1f}%) | {t['observations']} |")
    else:
        lines.append("None yet.")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def maybe_write_reviews(state: dict, now: datetime, path: str = LEARNING_PATH) -> list[int]:
    """Append a numeric review to Learning.md at every 10th trade, a full one at every 25th."""
    n = len(state["closed"])
    due = [k for k in range(10, n + 1, 5) if (k % 10 == 0 or k % 25 == 0) and k not in state["reviews_done"]]
    if not due:
        return []
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(LEARNING_TEMPLATE)
    backtest = None
    if os.path.exists(BACKTEST_SUMMARY):
        with open(BACKTEST_SUMMARY, encoding="utf-8") as fh:
            backtest = json.load(fh)
    blocks = []
    for k in due:
        s_all = stats(state["closed"][:k], state["equity_curve"])
        s_last = stats(state["closed"][max(0, k - 10):k], [])
        kind = "25-trade analysis" if k % 25 == 0 else "10-trade review"
        b = [f"\n## {kind}: trades 1-{k} (written {now.date().isoformat()})",
             f"- All {k} trades: win rate {s_all['win_rate']}%, avg win ${s_all['avg_win']}, "
             f"avg loss ${s_all['avg_loss']}, R:R {s_all['risk_reward']}, total P&L ${s_all['total_pnl']}",
             f"- Last 10 trades: win rate {s_last['win_rate']}%, P&L ${s_last['total_pnl']}"]
        if k % 25 == 0:
            exits = {}
            for t in state["closed"][:k]:
                code = t["exit_reason"].split(" ")[0]
                exits[code] = exits.get(code, 0) + 1
            gaps = sum(1 for t in state["closed"][:k] if "Stop gapped" in t["observations"])
            b += [f"- Max drawdown so far: {s_all['max_drawdown_pct']}%",
                  f"- Exit reasons: " + ", ".join(f"{c} x{v}" for c, v in sorted(exits.items())),
                  f"- Stops that gapped past the stop price: {gaps}"]
            if backtest:
                b.append(f"- Backtest for comparison: win rate {backtest.get('win_rate')}%, "
                         f"avg win ${backtest.get('avg_win')}, avg loss ${backtest.get('avg_loss')}, "
                         f"max drawdown {backtest.get('max_drawdown_pct')}%")
        b.append("- Written lessons: _to be added in the review with Claude. "
                 "No strategy change is made from this block alone._")
        blocks.append("\n".join(b))
        state["reviews_done"].append(k)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(blocks) + "\n")
    return due


LEARNING_TEMPLATE = """# Learning.md
What the paper trades are teaching us. Numbers are added by the bot every 10 and 25 trades;
lessons are written with Claude during reviews. Never change the strategy after one trade.

## Repeated mistakes
_None recorded yet._

## Strengths
_None recorded yet._

## Weaknesses
_None recorded yet._

## Improvements to test (need evidence from 25+ trades before changing Strategy.md)
_None recorded yet._

---
# Reviews
"""
