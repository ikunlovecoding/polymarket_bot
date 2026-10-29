# Backtest: Strategy A
Generated 2026-10-29T08:12 UTC from data collected 2026-10-29T08:08 UTC.

## Verdict: FAILED
- out-of-sample win rate 19.2% < break-even 41.1%
- out-of-sample net P&L $-497.88 <= 0
- max drawdown 50.48% > 20%

## Data
- Events from 2026-04-28 to 2026-10-27; in-sample before 2026-08-28, out-of-sample from 2026-08-28.
- Resolved markets used: **16,805** with price history (of 16,924 collected).
- Usable markets found per category before sampling: {'sports': 76674, 'crypto': 4145, 'economics': 386, 'tech': 393}; cap 12000 per category.

## Results
| | Markets | Trades | Win rate | Break-even | Avg win | Avg loss | R:R | Net P&L | Return | Per month | Max drawdown |
|---|---|---|---|---|---|---|---|---|---|---|---|
| in-sample: $1,000 account, 3% stakes | 7,962 | 295 | 27.1% | 38.8% | $6.38 (+31.0%) | $-5.3 (-26.7%) | 1.2 | $-629.94 | -62.99% | -14.1% | 64.14% |
| in-sample: $1,000 account, 5% stakes | 7,962 | 165 | 26.7% | 38.7% | $7.86 (+23.9%) | $-8.29 (-26.0%) | 0.95 | $-657.50 | -65.75% | -14.72% | 65.89% |
| in-sample: every signal, $30 each | 7,962 | 5,288 | 21.0% | 39.6% | $9.24 (+31.0%) | $-8.32 (-28.0%) | 1.11 | $-24,482.10 | -2448.21% |  |  |
| in-sample: every signal, no liquidity filter | 7,962 | 6,267 | 21.8% | 39.6% | $10.81 (+36.4%) | $-9.57 (-32.2%) | 1.13 | $-32,080.25 | -3208.02% |  |  |
| out-of-sample: $1,000 account, 3% stakes | 8,843 | 137 | 15.3% | 40.2% | $4.64 (+22.7%) | $-5.13 (-23.6%) | 0.9 | $-497.88 | -49.79% | -20.22% | 50.48% |
| out-of-sample: $1,000 account, 5% stakes | 8,843 | 77 | 15.6% | 40.1% | $5.11 (+13.9%) | $-8.96 (-24.7%) | 0.57 | $-520.89 | -52.09% | -21.15% | 52.1% |
| out-of-sample: every signal, $30 each | 8,843 | 5,123 | 19.2% | 41.1% | $10.48 (+35.2%) | $-8.36 (-28.1%) | 1.25 | $-24,205.85 | -2420.59% |  |  |
| out-of-sample: every signal, no liquidity filter | 8,843 | 6,513 | 19.7% | 40.9% | $12.02 (+40.4%) | $-10.14 (-34.1%) | 1.19 | $-37,522.51 | -3752.25% |  |  |

### in-sample: every signal, broken down
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 473 | 25.8% | -20.17% | $-2,845.16 |
| economics | 46 | 37.0% | -5.72% | $-78.78 |
| sports | 4760 | 20.4% | -15.19% | $-21,513.44 |
| tech | 9 | 22.2% | -16.62% | $-44.72 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 2 | 100.0% | +4.24% | $+2.53 |
| X1 | 469 | 100.0% | +54.85% | $+7,663.89 |
| X2 | 2254 | 0.0% | -42.24% | $-28,336.97 |
| X3 | 1415 | 25.4% | -4.44% | $-1,874.30 |
| X4 | 1148 | 24.6% | -5.66% | $-1,937.24 |

| Entry price | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| 20-25c | 409 | 20.5% | -12.63% | $-1,545.14 |
| 25-30c | 402 | 25.9% | -6.86% | $-823.29 |
| 30-35c | 406 | 20.2% | -13.03% | $-1,578.67 |
| 35-40c | 467 | 18.0% | -15.01% | $-2,087.60 |
| 40-45c | 648 | 17.3% | -17.81% | $-3,438.94 |
| 45-50c | 1745 | 19.1% | -19.78% | $-10,268.45 |
| 50-55c | 1211 | 25.8% | -13.19% | $-4,740.01 |

### out-of-sample: every signal, broken down
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 816 | 31.2% | -10.92% | $-2,650.33 |
| economics | 122 | 19.7% | -20.79% | $-757.76 |
| sports | 4078 | 16.8% | -16.60% | $-20,134.03 |
| tech | 107 | 18.7% | -20.77% | $-663.73 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 5 | 80.0% | +88.36% | $+132.27 |
| X1 | 457 | 100.0% | +59.73% | $+8,142.50 |
| X2 | 2003 | 0.0% | -45.68% | $-27,235.53 |
| X3 | 1290 | 22.8% | -5.37% | $-2,064.17 |
| X4 | 1368 | 16.9% | -7.80% | $-3,180.93 |

| Entry price | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| 20-25c | 744 | 21.9% | -10.12% | $-2,250.21 |
| 25-30c | 542 | 21.4% | -11.62% | $-1,881.65 |
| 30-35c | 440 | 18.6% | -10.18% | $-1,336.76 |
| 35-40c | 412 | 16.0% | -11.88% | $-1,457.44 |
| 40-45c | 480 | 18.5% | -13.36% | $-1,909.18 |
| 45-50c | 1233 | 15.2% | -21.43% | $-7,867.72 |
| 50-55c | 1272 | 22.2% | -19.90% | $-7,502.90 |

## Assumptions and limits
- No historical order book: buys at hourly price + 1c, sells at price - 1c, plus each market's taker fee.
- 24h volume and spread can't be checked historically; markets with under $5,000 total volume are excluded.
- All stakes 3% (confidence needs 24h volume). A 5% run is shown for comparison.
- Same-hour signals taken in a fixed random order (the live bot uses 24h volume).
- In place of F3/F4, an entry needs the price to have changed >= 3 times in the past 24h with no single-hour jump > 8c (only past prices are used). The run without this filter is shown for comparison.
- Rules checked hourly; a stop can fill below -25% if the price jumps between hours.
- Hourly prices are Polymarket's price history series, not executed trades.
- Decisions at hour H use only prices stamped at or before H; checked on live markets that a stamp is the time of its price.
- If a market has no fresh price when a time-based exit is due, it exits at the last known bid minus 1c.
- Only events that fully closed are included, and game times are their final values (postponements included).
- X5 (invalidation on wide spreads or disputes) is live-bot only; the backtest has no spread data.
- Break-even win rate is fixed in advance from each trade's entry price and fee rate (exit exactly at +50% / -25%).
