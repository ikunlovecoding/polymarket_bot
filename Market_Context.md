# Market_Context.md
Long-term operating context for the prediction market bot.
Created: 2026-10-29 (ORIENT phase)

---

## 1. Trader profile
- Experience: a few months trading on Polymarket
- Platform: **Polymarket** (public data feeds only: no wallet, no keys, no login)

## 2. Allowed categories
- Sports
- Economics (e.g. Fed rates, CPI, jobs data)
- Crypto price markets
- Tech / AI

Anything outside these four is out of scope.

## 3. Holding period
- **Days**: enter ahead of an event, exit on target/stop, typically before or around resolution

## 4. Entry approaches (current, informal)
Trader uses all of the following today:
- Mispricing (own probability estimate vs. market price)
- News (headlines, data releases, injury reports)
- Momentum (riding price direction)
- Price range (buying within a set price zone)
- Gut feel

Notes:
- **Gut feel is excluded from the bot**; it can't be turned into a rule.
- Best past result: World Cup final trade (entry/exit details not recalled).
- Worst source of losses: **news-based trades**.
- Which signal actually has an edge is unknown; the backtest decides, not memory.

## 5. Exits
- **Take profit: +50%** from entry price
- **Stop loss: −25%** from entry price
- Reward/risk = 2:1 → break-even win rate ≈ 33% before fees and slippage

## 6. Stake sizing
- **Confidence-based, % of current bankroll**
  - Low confidence: **3%** (≈ $30 at start)
  - High confidence: **5%** (≈ $50 at start)
- Max risk per trade at stop: 5% × 25% ≈ **1.25% of bankroll**
- How "confidence" is measured is defined in the STRATEGY phase (likely: gap between estimated probability and market price)

## 7. Bankroll and risk limits
| Limit | Value |
|---|---|
| Starting bankroll (paper) | **$1,000** |
| Daily loss limit | **$100**: no new trades for the rest of the day once hit |
| Max total open exposure | **30% of current bankroll** (≈ $300 at start) |
| Kill switch | Required: stops all trading immediately |

## 8. Goal
- Primary: **steady returns**
- Stated target: **10%+ per month**
- ⚠️ Reality check: 10%+/month is very hard to sustain at these stake sizes. The backtest will show what's realistic, and paper results are judged against the backtest, not just the target. Do not raise risk to chase the target.

## 9. Autonomy
- **Paper mode: full auto.** Bot scans, checks risk, places paper trades, and reports in the morning brief.
- **Real money: not automated.** Claude never places real bets, moves funds, or connects a wallet. Going live is a manual step done by the trader.

## 10. Non-negotiable rules
- Paper mode ON by default
- Never invent prices, data, or results; mark unverified info as UNVERIFIED
- Never handle seed phrases or private keys
- Check risk (bankroll, exposure, stake, stop, target, resolution rules) before every signal
- Never change the strategy automatically after one trade; changes only from accumulated evidence (10/25-trade reviews)

## 11. Open items for later phases
- Define the "confidence" metric and the 3%→5% scaling (STRATEGY)
- Pick 1–2 entry signals for version one; news-based likely deferred (STRATEGY)
- Define when NOT to trade, e.g. low liquidity, unclear resolution rules, wide spreads (STRATEGY)
- Confirm scan schedule and morning-brief time (SHIP)
