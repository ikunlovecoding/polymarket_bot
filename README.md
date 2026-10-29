# Polymarket paper bot (Strategy A)

A bot that **pretends** to trade Polymarket so you can find out whether Strategy A works, without risking money.

- **Paper only.** No wallet, no keys, no login. The code can only read public data; a test fails if anything wallet- or order-related ever appears in it.
- **Runs on GitHub Actions** every hour, so your laptop can stay closed.
- **Starts in `scan_only` mode**: it lists signals but opens no paper trades. Switch to `paper` after the backtest and the code review pass.

## How it works

```
data_feed  →  strategy  →  risk  →  simulator  →  ledger  →  brief
 (reads)      (rules)      (limits)  (paper fill)   (records)   (morning report)
```

| File | What it does |
|---|---|
| `bot/data_feed.py` | Reads markets, prices, order books and price history from Polymarket's public APIs |
| `bot/strategy.py` | Rules from Strategy.md: filters F1–F6, entry E1–E5, exits X1–X5 |
| `bot/risk.py` | Daily loss limit, exposure cap, kill switch, stake size |
| `bot/simulator.py` | Paper fills against the real order book, with Polymarket's fees |
| `bot/ledger.py` | The paper account (`data/state.json`), `Trade_Ledger.md`, reviews in `Learning.md` |
| `bot/brief.py` | `reports/brief.md` (morning brief) and `reports/last_scan.md` |
| `bot/run.py` | Runs one scan |
| `config.json` | **All settings.** Change numbers here, never in the code |

## Everyday controls (edit `config.json` on GitHub)

| You want to… | Set |
|---|---|
| Only watch signals | `"mode": "scan_only"` |
| Start paper trading | `"mode": "paper"` |
| Stop all new paper trades now | `"kill_switch": true` (open positions are still exited by their rules) |

## Run it by hand

On GitHub: **Actions → paper-bot → Run workflow**, then pick:
- `check-feed`: proves the data reads correctly (do this first)
- `dry-run`: shows what the bot would do right now, saves nothing
- `scan`: one real scan, saved to the repo

On your own computer: `python -m bot.run --check-feed`, `python -m bot.run --dry-run`, tests with `python -m unittest discover -s tests -v`.

## Known limits
- Exit rules are checked once an hour, so a stop can fill well past −25% if the price jumps between scans.
- A paper fill assumes the book doesn't move while we "trade". Real fills can be worse.
- Results only mean something after enough trades (reviews every 10 and 25).
