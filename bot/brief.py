"""ALERTS: writes reports/brief.md (the morning brief) and reports/last_scan.md (what the last scan saw).

The bot rewrites both files on every run, so they are always current. A Claude scheduled task
reads reports/brief.md each morning and sends it to you.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from .ledger import ROOT, stats
from .risk import daily_pnl, open_exposure

BRIEF_PATH = os.path.join(ROOT, "reports", "brief.md")
SCAN_PATH = os.path.join(ROOT, "reports", "last_scan.md")


def write_scan_report(scan: dict, now: datetime, path: str = SCAN_PATH) -> None:
    lines = [f"# Last scan: {now.isoformat()[:16].replace('T', ' ')} UTC",
             f"- Mode: **{scan['mode']}**",
             f"- Events read: {scan['events']} · outcomes checked: {scan['quotes']}",
             f"- Signals: {len(scan['signals'])} · paper trades opened: {len(scan['opened'])} · "
             f"closed: {len(scan['closed'])}"]
    if scan["errors"]:
        lines += ["", "## Errors"] + [f"- {e}" for e in scan["errors"]]
    lines += ["", "## Signals"]
    if scan["signals"]:
        lines += ["| Market | Outcome | Ask | Spread | 24h vol | Days to event | Confidence | Action |",
                  "|---|---|---|---|---|---|---|---|"]
        for s in scan["signals"]:
            lines.append(f"| {s['question']} | {s['outcome']} | {s['ask']:.3f} | {s['spread']:.3f} | "
                         f"${s['volume_24h']:,.0f} | {s['days_to_event']:.1f} | {s['confidence']} | {s['action']} |")
    else:
        lines.append("No market met every rule.")
    lines += ["", "## Why markets were skipped (counts)"]
    for reason, count in sorted(scan["skipped"].items(), key=lambda kv: -kv[1]):
        lines.append(f"- {reason}: {count}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def write_brief(state: dict, equity: float, scan: dict, cfg: dict, now: datetime,
                path: str = BRIEF_PATH) -> None:
    since = now - timedelta(hours=24)
    opened_24h = [p for p in state["positions"] + state["closed"]
                  if datetime.fromisoformat(p["opened_at"]) >= since]
    closed_24h = [t for t in state["closed"] if datetime.fromisoformat(t["closed_at"]) >= since]
    s = stats(state["closed"], state["equity_curve"])
    cap = equity * cfg["risk"]["max_exposure_pct"]
    lines = [
        f"# Morning brief: {now.date().isoformat()}",
        f"_Generated {now.isoformat()[:16].replace('T', ' ')} UTC · mode **{cfg['mode']}** · paper money only_",
        "",
        "## Account",
        f"- Equity **${equity:,.2f}** ({equity - state['starting_bankroll']:+,.2f} since start)",
        f"- Today so far: {daily_pnl(state, equity):+,.2f} (limit -${cfg['risk']['daily_loss_limit']:.0f})",
        f"- Exposure: ${open_exposure(state):,.2f} of ${cap:,.2f} allowed",
        f"- Kill switch: {'ON' if cfg['kill_switch'] else 'off'}",
        f"- Closed trades: {s['trades']} · win rate {s['win_rate']}% · total P&L ${s['total_pnl']}",
        "",
        "## Open paper positions",
    ]
    if state["positions"]:
        for p in state["positions"]:
            bid = p.get("last_bid") or 0
            unreal = p["shares"] * bid - p["cost"]
            lines.append(f"- #{p['id']} {p['question']} · {p['direction']} @ {p['entry_price']:.3f} · "
                         f"bid {bid:.3f} · {unreal:+.2f} · stop {p['stop_loss']:.3f} / target {p['take_profit']:.3f}")
    else:
        lines.append("- None")
    lines += ["", "## Last 24 hours"]
    lines += [f"- Opened #{p['id']} {p['question']} ({p['outcome']}) @ {p['entry_price']:.3f}" for p in opened_24h] or []
    lines += [f"- Closed #{t['id']} {t['question']}: {t['exit_reason']}, {t['pnl']:+.2f}" for t in closed_24h] or []
    if not opened_24h and not closed_24h:
        lines.append("- No trades")
    lines += ["", "## Signals in the latest scan"]
    if scan["signals"]:
        lines += [f"- {x['question']} · {x['outcome']} @ {x['ask']:.3f} · {x['confidence']} · {x['action']}"
                  for x in scan["signals"]]
    else:
        lines.append("- None")
    if scan["errors"]:
        lines += ["", "## Problems"] + [f"- {e}" for e in scan["errors"]]
    lines += ["", "## Waiting for your approval",
              "- Nothing. Paper trades need no approval, and this bot cannot place real trades."]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
