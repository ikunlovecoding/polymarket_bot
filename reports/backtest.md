# Backtest: Strategy A
Generated 2026-10-29T08:09 UTC from data collected 2026-10-29T08:08 UTC.

## Verdict: FAILED
- out-of-sample win rate 19.7% < break-even 40.9%
- out-of-sample net P&L $-405.96 <= 0
- max drawdown 40.96% > 20%

## Data
- Events from 2026-04-28 to 2026-10-27; in-sample before 2026-08-28, out-of-sample from 2026-08-28.
- Resolved markets used: **16,805** with price history (of 16,924 collected).
- Usable markets found per category before sampling: {'sports': 76674, 'crypto': 4145, 'economics': 386, 'tech': 393}; cap 12000 per category.

## Results
| | Markets | Trades | Win rate | Break-even | Avg win | Avg loss | R:R | Net P&L | Return | Per month | Max drawdown |
|---|---|---|---|---|---|---|---|---|---|---|---|
| in-sample: $1,000 account, 3% stakes | 7,962 | 292 | 21.6% | 38.8% | $5.21 (+31.2%) | $-4.46 (-25.6%) | 1.17 | $-693.77 | -69.38% | -15.53% | 70.17% |
| in-sample: $1,000 account, 5% stakes | 7,962 | 151 | 19.9% | 38.8% | $5.9 (+23.8%) | $-7.21 (-25.1%) | 0.82 | $-695.72 | -69.57% | -15.57% | 69.83% |
| in-sample: every signal, $30 each | 7,962 | 6,267 | 21.8% | 39.6% | $10.81 (+36.4%) | $-9.57 (-32.2%) | 1.13 | $-32,080.25 | -3208.02% |  |  |
| out-of-sample: $1,000 account, 3% stakes | 8,843 | 128 | 20.3% | 40.5% | $6.03 (+28.8%) | $-5.52 (-24.2%) | 1.09 | $-405.96 | -40.6% | -16.49% | 40.96% |
| out-of-sample: $1,000 account, 5% stakes | 8,843 | 83 | 20.5% | 40.5% | $11.67 (+34.1%) | $-9.65 (-25.8%) | 1.21 | $-438.30 | -43.83% | -17.8% | 45.27% |
| out-of-sample: every signal, $30 each | 8,843 | 6,513 | 19.7% | 40.9% | $12.02 (+40.4%) | $-10.14 (-34.1%) | 1.19 | $-37,522.51 | -3752.25% |  |  |

### in-sample: every signal, broken down
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 815 | 25.9% | -26.17% | $-6,338.11 |
| economics | 50 | 26.0% | -12.53% | $-186.80 |
| sports | 5386 | 21.2% | -15.89% | $-25,440.86 |
| tech | 16 | 18.8% | -24.01% | $-114.48 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 5 | 80.0% | +66.59% | $+98.53 |
| X1 | 652 | 100.0% | +59.58% | $+11,557.12 |
| X2 | 2945 | 0.0% | -46.07% | $-40,332.67 |
| X3 | 1510 | 23.5% | -4.67% | $-2,101.09 |
| X4 | 1155 | 30.9% | -3.78% | $-1,302.14 |

| Entry price | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| 20-25c | 411 | 24.3% | -9.75% | $-1,198.38 |
| 25-30c | 396 | 26.5% | -7.85% | $-929.56 |
| 30-35c | 378 | 23.8% | -11.25% | $-1,269.20 |
| 35-40c | 394 | 16.2% | -18.51% | $-2,169.44 |
| 40-45c | 528 | 15.2% | -18.25% | $-2,870.63 |
| 45-50c | 1559 | 17.0% | -22.10% | $-10,254.32 |
| 50-55c | 2601 | 25.5% | -17.37% | $-13,388.72 |

### out-of-sample: every signal, broken down
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 1363 | 27.8% | -21.52% | $-8,720.15 |
| economics | 133 | 18.0% | -22.85% | $-906.55 |
| sports | 4870 | 17.6% | -18.52% | $-26,799.50 |
| tech | 147 | 17.7% | -24.97% | $-1,096.31 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 4 | 50.0% | +74.43% | $+89.74 |
| X1 | 705 | 100.0% | +61.18% | $+12,849.09 |
| X2 | 3039 | 0.0% | -50.54% | $-45,673.31 |
| X3 | 1730 | 19.2% | -5.99% | $-3,085.61 |
| X4 | 1035 | 23.7% | -5.52% | $-1,702.43 |

| Entry price | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| 20-25c | 695 | 26.0% | -7.36% | $-1,527.25 |
| 25-30c | 546 | 22.5% | -13.39% | $-2,184.74 |
| 30-35c | 415 | 21.4% | -11.87% | $-1,470.61 |
| 35-40c | 385 | 21.8% | -13.02% | $-1,492.23 |
| 40-45c | 484 | 18.8% | -16.30% | $-2,350.94 |
| 45-50c | 1068 | 15.7% | -24.32% | $-7,735.93 |
| 50-55c | 2920 | 18.8% | -23.97% | $-20,760.82 |

## Assumptions and limits
- No historical order book: buys at hourly price + 1c, sells at price - 1c, plus each market's taker fee.
- 24h volume and spread can't be checked historically; markets with under $5,000 total volume are excluded.
- All stakes 3% (confidence needs 24h volume). A 5% run is shown for comparison.
- Same-hour signals taken in a fixed random order (the live bot uses 24h volume).
- Rules checked hourly; a stop can fill below -25% if the price jumps between hours.
- Hourly prices are Polymarket's price history series, not executed trades.
- Decisions at hour H use only prices stamped at or before H; checked on live markets that a stamp is the time of its price.
- If a market has no fresh price when a time-based exit is due, it exits at the last known bid minus 1c.
- Only events that fully closed are included, and game times are their final values (postponements included).
- X5 (invalidation on wide spreads or disputes) is live-bot only; the backtest has no spread data.
- Break-even win rate is fixed in advance from each trade's entry price and fee rate (exit exactly at +50% / -25%).
