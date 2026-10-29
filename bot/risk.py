"""RISK MANAGER: every paper trade must pass here first.

Checks, in order (Strategy.md section 6):
  1. mode and kill switch
  2. daily loss limit ($100, realised + unrealised, per UTC day)
  3. total open exposure (30% of current bankroll)
  4. enough paper cash for the stake
"""

from __future__ import annotations


def stake_for(confidence: str, equity: float, cfg: dict) -> float:
    """3% of current bankroll normally, 5% for high confidence."""
    pct = cfg["stakes"]["high_pct"] if confidence == "high" else cfg["stakes"]["normal_pct"]
    return round(max(0.0, equity) * pct, 2)


def open_exposure(state: dict) -> float:
    """Money tied up in open positions, at what we paid (fees included)."""
    return round(sum(p["cost"] for p in state["positions"]), 6)


def daily_pnl(state: dict, equity: float) -> float:
    return round(equity - state["day_start_equity"], 6)


def check_new_trade(state: dict, stake: float, equity: float, cfg: dict) -> str | None:
    """None = allowed. Otherwise the reason this trade is blocked."""
    if cfg["mode"] != "paper":
        return f"mode is '{cfg['mode']}' (signals only)"
    if cfg["kill_switch"]:
        return "kill switch is ON"
    if daily_pnl(state, equity) <= -cfg["risk"]["daily_loss_limit"]:
        return f"daily loss limit hit ({daily_pnl(state, equity):.2f})"
    cap = equity * cfg["risk"]["max_exposure_pct"]
    if open_exposure(state) + stake > cap + 1e-9:
        return f"exposure cap: {open_exposure(state):.2f} + {stake:.2f} > {cap:.2f}"
    if stake > state["cash"] + 1e-9:
        return f"not enough paper cash ({state['cash']:.2f})"
    if stake <= 0:
        return "stake is zero"
    return None
