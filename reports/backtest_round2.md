# Backtest round 2: variants A-D
Data: 16,924 resolved markets, events 2026-04-28 to 2026-10-27. In-sample before 2026-08-28, out-of-sample from 2026-08-28.
Rules fixed before running: a variant must make money in-sample (account AND per-trade average) to be tested out-of-sample, then meet Strategy.md section 8 out-of-sample. A variant that passes both still needs the untouched Jan-Apr 2026 data before paper trading.

## Verdicts
| Variant | Status |
|---|---|
| A: price range 20-55c, +50% / -25% | **FAILED in-sample (not run out-of-sample)** |
| B: A + momentum (up >= 5c in 24h) | **FAILED in-sample (not run out-of-sample)** |
| C: favourites 75-92c, 1-7 days out, hold to resolution, -25% stop | **FAILED in-sample (not run out-of-sample)** |
| D: A with a wider -50% stop | **FAILED in-sample (not run out-of-sample)** |

## A: price range 20-55c, +50% / -25%
- in-sample average P&L per trade -15.56% <= 0
- in-sample account P&L $-629.94 <= 0

| Period | Run | Trades | Win rate | Break-even | Avg win | Avg loss | Avg per trade | Net P&L | Per month | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| in-sample | $1,000 account, 3% | 295 | 27.1% | 38.8% | +31.0% | -26.7% | -11.03% | $-629.94 | -14.1% | 64.14% |
| in-sample | every signal, $30 | 5,288 | 21.0% | 39.6% | +31.0% | -28.0% | -15.56% | $-24,482.10 |  |  |

in-sample, every signal:
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 473 | 25.8% | -20.17% | $-2,845.16 |
| economics | 46 | 37.0% | -5.72% | $-78.78 |
| sports | 4760 | 20.4% | -15.19% | $-21,513.44 |
| tech | 9 | 22.2% | -16.62% | $-44.72 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 2 | 100.0% | +4.24% | $+2.53 |
| X1 take profit | 469 | 100.0% | +54.85% | $+7,663.89 |
| X2 stop loss | 2254 | 0.0% | -42.24% | $-28,336.97 |
| X3 time stop | 1415 | 25.4% | -4.44% | $-1,874.30 |
| X4 pre-resolution exit | 1148 | 24.6% | -5.66% | $-1,937.24 |

## B: A + momentum (up >= 5c in 24h)
- in-sample average P&L per trade -16.94% <= 0
- in-sample account P&L $-824.13 <= 0

| Period | Run | Trades | Win rate | Break-even | Avg win | Avg loss | Avg per trade | Net P&L | Per month | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| in-sample | $1,000 account, 3% | 352 | 21.9% | 39.0% | +27.0% | -28.5% | -16.35% | $-824.13 | -18.45% | 82.42% |
| in-sample | every signal, $30 | 2,083 | 21.0% | 39.8% | +30.6% | -29.6% | -16.94% | $-10,502.60 |  |  |

in-sample, every signal:
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 324 | 30.9% | -11.64% | $-1,126.15 |
| economics | 30 | 30.0% | -13.97% | $-124.29 |
| sports | 1725 | 19.0% | -18.02% | $-9,251.39 |
| tech | 4 | 50.0% | -0.71% | $-0.76 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 2 | 0.0% | -5.13% | $-3.06 |
| X1 take profit | 193 | 100.0% | +51.95% | $+2,986.92 |
| X2 stop loss | 1062 | 0.0% | -39.33% | $-12,437.35 |
| X3 time stop | 370 | 35.4% | -2.67% | $-294.57 |
| X4 pre-resolution exit | 456 | 25.0% | -5.56% | $-754.54 |

## C: favourites 75-92c, 1-7 days out, hold to resolution, -25% stop
- in-sample average P&L per trade -8.93% <= 0
- in-sample account P&L $-490.78 <= 0

| Period | Run | Trades | Win rate | Break-even | Avg win | Avg loss | Avg per trade | Net P&L | Per month | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| in-sample | $1,000 account, 3% | 295 | 67.1% | 57.4% | +20.0% | -62.7% | -7.18% | $-490.78 | -10.98% | 57.2% |
| in-sample | every signal, $30 | 2,184 | 60.1% | 56.9% | +21.1% | -54.1% | -8.93% | $-5,767.80 |  |  |

in-sample, every signal:
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 337 | 54.9% | -8.78% | $-875.72 |
| economics | 24 | 66.7% | -7.51% | $-53.32 |
| sports | 1812 | 61.0% | -8.90% | $-4,770.94 |
| tech | 11 | 45.5% | -20.65% | $-67.82 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 1356 | 96.8% | +17.19% | $+6,902.45 |
| X2 stop loss | 828 | 0.0% | -51.71% | $-12,670.25 |

## D: A with a wider -50% stop
- in-sample average P&L per trade -14.69% <= 0
- in-sample account P&L $-614.00 <= 0

| Period | Run | Trades | Win rate | Break-even | Avg win | Avg loss | Avg per trade | Net P&L | Per month | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| in-sample | $1,000 account, 3% | 251 | 25.5% | 53.9% | +26.6% | -25.8% | -12.47% | $-614.00 | -13.74% | 62.89% |
| in-sample | every signal, $30 | 5,126 | 24.2% | 54.5% | +31.6% | -29.5% | -14.69% | $-22,410.62 |  |  |

in-sample, every signal:
| Category | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| crypto | 401 | 40.6% | -16.82% | $-2,009.08 |
| economics | 43 | 41.9% | -2.32% | $-29.37 |
| sports | 4673 | 22.6% | -14.68% | $-20,411.01 |
| tech | 9 | 44.4% | +14.48% | $+38.85 |

| Exit | Trades | Win rate | Avg P&L per trade | Total P&L ($30 stakes) |
|---|---|---|---|---|
| Settled at resolution | 5 | 100.0% | +100.67% | $+150.47 |
| X1 take profit | 518 | 100.0% | +55.95% | $+8,636.78 |
| X2 stop loss | 1043 | 0.0% | -63.51% | $-19,718.67 |
| X3 time stop | 2016 | 19.4% | -11.57% | $-6,941.38 |
| X4 pre-resolution exit | 1544 | 21.2% | -9.87% | $-4,537.82 |

Same assumptions as reports/backtest.md (1c slippage per side, market fees, past-only liquidity filter, hourly checks). Variant C holds through resolution: a win pays $1 with no exit fee; prices more than 12h after the event are not in the data, so a stop can't fire in that last stretch.
