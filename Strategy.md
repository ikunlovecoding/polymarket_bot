# Strategy.md: Version A "Price Range"
Chosen: 2026-10-29 (STRATEGY phase). Status: **untested.** The backtest decides whether this goes to paper trading.
Context: see Market_Context.md and Market_Notes.md.

---

## 1. Idea in one line
Buy outcomes priced 20–55¢ in liquid, clearly resolvable markets that settle within 3–14 days. Take profit at +50%, stop out at −25%, and never hold into the resolution moment.

## 2. Market filter (all must be true)
| # | Condition | Value |
|---|---|---|
| F1 | Category | Sports, Economics, Crypto, Tech/AI only |
| F2 | Time to resolution / event start | 3 to 14 days at entry. For sports the game start time is used, because a sports market's end date can be a week after the game |
| F3 | 24h volume | ≥ $5,000 |
| F4 | Bid–ask spread | ≤ 3¢ |
| F5 | Resolution rules | Objective source named (official score, BLS, Fed statement, exchange price, LMArena, etc.). Skip anything subjective or vague |
| F6 | Market status | Active, not closed, not in dispute |

## 3. Entry rule
| # | Condition | Value |
|---|---|---|
| E1 | Outcome ask price | 20¢ ≤ price ≤ 55¢ |
| E2 | Fill price | Simulated against the real order book (walk the asks for the full stake) |
| E3 | One position per event | No second position in the same event |
| E4 | No news signals | Version A uses price and volume only |
| E5 | No re-entry | Never trade a market that was already traded (added in BUILD so a stopped-out position isn't bought straight back) |

If several outcomes in the same event qualify, take the one with the highest 24h volume.

## 4. Stake size ("confidence")
| Confidence | Rule | Stake |
|---|---|---|
| High | Market's 24h volume is in the top 20% of all markets passing F1–F6 at scan time | **5%** of current bankroll |
| Normal | Everything else | **3%** of current bankroll |

Stakes are rounded down to whole shares. Max loss at stop ≈ 1.25% of bankroll (more if the price gaps).

## 5. Exit rules (first one hit wins)
| # | Exit | Rule |
|---|---|---|
| X1 | Take profit | Best bid ≥ entry × 1.50 |
| X2 | Stop loss | Best bid ≤ entry × 0.75 |
| X3 | Time stop | Position open 7 days |
| X4 | Pre-resolution exit | 12 hours before resolution time or event start |
| X5 | Invalidation | Market paused, rules changed, dispute opened, or spread > 10¢: exit at best available bid and log the reason |

Exits are simulated at the real bid side of the book, after fees.

## 6. Risk limits (checked before every simulated trade)
| Limit | Value | Action when hit |
|---|---|---|
| Daily loss | $100 realised + unrealised | No new trades until next day (UTC) |
| Total open exposure | 30% of current bankroll | No new trades until exposure drops |
| Kill switch | Manual flag in config | Stops all new trades immediately |
| Paper mode | ON | Real orders are impossible; there is no wallet or key in the code |

## 7. Costs assumed
- Taker fee: shares × rate × p × (1 − p). Each market publishes its own rate (`feeSchedule.rate`), and the bot uses it. Real data on 2026-10-29 showed sports games 0.05, World Series futures 0.03, crypto 0.07, and many economics/tech/AI markets at **0** ("zero_fees"). The docs' category rates (Sports 0.05, Economics 0.05, Crypto 0.07, Tech 0.04) are only a fallback.
- Slippage: from the real order book in paper mode; in the backtest, an extra 1¢ per side on top of fees.
- Break-even win rate after fees: about **38–45%** for sports/econ/tech and **40–50%** for crypto, depending on entry price (computed 2026-10-29).

## 8. What would prove this wrong (decided before the backtest)
- Out-of-sample win rate below break-even for its price/category mix, **or**
- Out-of-sample net P&L ≤ 0 after fees and slippage, **or**
- Max drawdown > 20% of bankroll.

If any of these happen, go back to the STRATEGY phase (Version B is the next candidate).

## 9. Parameters (fixed for the first backtest; no tuning on out-of-sample data)
| Parameter | Value |
|---|---|
| Price range | 20–55¢ |
| Resolution window | 3–14 days |
| Min 24h volume | $5,000 |
| Max spread | 3¢ |
| Take profit / stop | +50% / −25% |
| Max hold | 7 days |
| Pre-resolution exit | 12 hours |
| Stakes | 3% normal / 5% high |
