# Backtest: Strategy A
Generated 2026-10-29T08:00 UTC from data collected 2026-10-29T08:00 UTC.

## Verdict: FAILED
- out-of-sample win rate 30.2% < break-even 42.5%
- out-of-sample net P&L $-601.98 <= 0
- max drawdown 67.98% > 20%

## Data
- Events from 2026-04-28 to 2026-10-27; in-sample before 2026-08-28, out-of-sample from 2026-08-28.
- Resolved markets used: **538** with price history (of 9,924 collected).
- Usable markets found per category before sampling: {'sports': 76674, 'crypto': 4145, 'economics': 386, 'tech': 393}; cap 5000 per category.

## Results
| | Markets | Trades | Win rate | Break-even | Avg win | Avg loss | R:R | Net P&L | Return | Per month | Max drawdown |
|---|---|---|---|---|---|---|---|---|---|---|---|
| in-sample: $1,000 account, 3% stakes | 64 | 50 | 26.0% | 42.5% | $27.27 (+113.3%) | $-14.51 (-55.7%) | 1.88 | $-182.53 | -18.25% | -4.09% | 34.33% |
| in-sample: $1,000 account, 5% stakes | 64 | 50 | 26.0% | 42.5% | $39.45 (+113.3%) | $-22.19 (-55.7%) | 1.78 | $-308.07 | -30.81% | -6.9% | 51.26% |
| in-sample: every signal, $30 each | 64 | 50 | 26.0% | 42.5% | $33.74 (+113.3%) | $-16.55 (-55.6%) | 2.04 | $-173.80 | -17.38% |  |  |
| out-of-sample: $1,000 account, 3% stakes | 474 | 238 | 31.1% | 42.5% | $16.05 (+62.1%) | $-10.91 (-46.1%) | 1.47 | $-601.98 | -60.2% | -24.45% | 67.98% |
| out-of-sample: $1,000 account, 5% stakes | 474 | 215 | 27.4% | 42.3% | $19.96 (+59.4%) | $-12.89 (-45.0%) | 1.55 | $-833.14 | -83.31% | -33.83% | 83.66% |
| out-of-sample: every signal, $30 each | 474 | 242 | 30.2% | 42.5% | $18.38 (+61.7%) | $-13.72 (-46.0%) | 1.34 | $-976.98 | -97.7% |  |  |

### in-sample: every signal, broken down
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 29 | 27.6% | -11.70% | $-100.57 |
| economics | 1 | 0.0% | -30.75% | $-9.07 |
| sports | 10 | 40.0% | +10.27% | $+30.59 |
| tech | 10 | 10.0% | -31.81% | $-94.75 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 5 | 100.0% | +157.85% | $+234.58 |
| X1 | 7 | 100.0% | +94.09% | $+196.55 |
| X2 | 35 | 0.0% | -58.47% | $-608.84 |
| X3 | 3 | 33.3% | +4.46% | $+3.91 |

| Entry price | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| 20-25c | 11 | 18.2% | -22.86% | $-75.05 |
| 25-30c | 8 | 37.5% | +50.11% | $+119.65 |
| 30-35c | 3 | 66.7% | +11.73% | $+10.39 |
| 35-40c | 7 | 14.3% | -26.69% | $-55.87 |
| 40-45c | 4 | 25.0% | +0.08% | $-0.11 |
| 45-50c | 2 | 50.0% | +22.19% | $+13.02 |
| 50-55c | 15 | 20.0% | -41.86% | $-185.84 |

### out-of-sample: every signal, broken down
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 99 | 47.5% | +4.88% | $+144.24 |
| economics | 60 | 16.7% | -25.92% | $-463.50 |
| sports | 5 | 40.0% | -7.61% | $-11.35 |
| tech | 78 | 17.9% | -27.72% | $-646.38 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 5 | 40.0% | +1.56% | $+3.05 |
| X1 | 69 | 100.0% | +60.74% | $+1,247.20 |
| X2 | 160 | 0.0% | -46.37% | $-2,211.51 |
| X3 | 7 | 14.3% | -8.51% | $-17.73 |
| X4 | 1 | 100.0% | +6.80% | $+2.01 |

| Entry price | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| 20-25c | 53 | 22.6% | -22.24% | $-352.28 |
| 25-30c | 40 | 27.5% | -19.25% | $-230.00 |
| 30-35c | 33 | 42.4% | +7.03% | $+69.26 |
| 35-40c | 26 | 23.1% | -19.63% | $-152.09 |
| 40-45c | 23 | 26.1% | -14.87% | $-102.16 |
| 45-50c | 32 | 28.1% | -16.00% | $-152.18 |
| 50-55c | 35 | 42.9% | -5.46% | $-57.53 |

## Assumptions and limits
- No historical order book: buys at hourly price + 1c, sells at price - 1c, plus each market's taker fee.
- 24h volume and spread can't be checked historically; markets with under $5,000 total volume are excluded.
- All stakes 3% (confidence needs 24h volume). A 5% run is shown for comparison.
- Same-hour signals taken in a fixed random order (the live bot uses 24h volume).
- Rules checked hourly; a stop can fill below -25% if the price jumps between hours.
- Hourly prices are Polymarket's price history series, not executed trades.
- Decisions at hour H use prices stamped H-1h or earlier (conservative, avoids any 1-hour lookahead).
- If a market has no fresh price when a time-based exit is due, it exits at the last known bid minus 1c.
- Only events that fully closed are included, and game times are their final values (postponements included).
- X5 (invalidation on wide spreads or disputes) is live-bot only; the backtest has no spread data.
- Break-even win rate is fixed in advance from each trade's entry price and fee rate (exit exactly at +50% / -25%).
