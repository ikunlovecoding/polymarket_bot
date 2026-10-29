# Market_Notes.md
Market research for the prediction market bot (MARKET RESEARCH phase).
Compiled: 2026-10-29. Every line has a source and the time the data was observed.
Rule: nothing here is invented. Anything not confirmed from a primary or dated source is marked **UNVERIFIED**.

---

## 0. Research limits (read first)
| Item | Status |
|---|---|
| Polymarket public API (gamma-api.polymarket.com) | **Blocked from Claude's cloud workspace** (proxy refused, 2026-10-29). Live prices below come from third-party pages that track Polymarket, not from the API directly. |
| X (Twitter) research | **Done 2026-10-29** via the Claude app's built-in browser (X "Top" search, posts since Oct 22–26). See section 7. X posts are individual opinions or claims, so every X figure is **UNVERIFIED** unless it matches another source. |
| Prices in general | Snapshots only. Prediction market prices move by the minute; treat every price here as stale after a few hours. |

**Build implication:** the bot's data feed cannot run in Claude's cloud workspace as-is. Options to settle in the ARCHITECTURE phase: run the bot on your own computer, or find a data path the cloud can reach.

---

## 1. Where the volume is (Polymarket, last 30 days)
Source: [DeFi Rate – Polymarket volume](https://defirate.com/prediction-markets/volume/polymarket/), page updated 2026-10-28, data through 2026-10-27.

| Category | 30-day volume | Share | vs prior 30 days |
|---|---|---|---|
| **Sports** | $2.9B | 58.2% | +7.8% |
| **Crypto** | $738M | 14.7% | −7.6% |
| Politics (out of scope) | $434M | 8.7% | +68.6% |
| **Economics** | $92M | 1.8% | −50.5% |
| **Tech** | $51M | 1.0% | +71.2% |

- Platform total: $195M on 2026-10-27; $1.4B last 7 days; $4.8B last 30 days; $76.5B year to date.
- **Takeaway:** sports and crypto are where liquidity is. Economics and tech are thin, so slippage on a $30–50 order will matter more there.

## 2. Trading fees (needed for the backtest)
Source: [Polymarket docs – Fees](https://docs.polymarket.com/trading/fees?via=xp), read 2026-10-29. Effective date not stated on the page.

- Formula (takers only, makers pay 0): **fee = shares × feeRate × p × (1 − p)**
- Fee rates for your categories: **Crypto 0.07 · Sports 0.05 · Economics 0.05 · Tech 0.04**
- Fees are highest at 50¢ and symmetric (30¢ and 70¢ cost the same).
- Worked example, sports YES bought at 40¢: fee ≈ 1.2¢/share = **3% of cost on entry**; selling at 60¢ costs another ≈ 1.2¢/share. Crypto is ~40% more expensive. This eats into the +50% / −25% rule and must be in the backtest.

## 3. Sports
| Finding | Detail | Source / observed |
|---|---|---|
| World Series 2026 | Brewers vs Rays. Game 5 Oct 28; Games 6–7 (if needed) Oct 30 and Oct 31, 8 p.m. ET | [MLB.com FAQ](https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more), article dated 2026-10-20. Current series score **UNVERIFIED** |
| World Series Game 1 | Brewers beat Rays | [FOX 13](https://www.fox13news.com/news/world-series-2026-game-1) (search result headline) |
| Super Bowl LXI futures | 49ers +641, Bills +733, Chiefs +890, Rams/Seahawks +1150 (top 5) | [RG.org Polymarket Daily](https://rg.org/news/prediction-markets/polymarket-daily-texas-senate-netanyahu-bills-super-bowl-october-28-2026), prices as of 2026-10-28 00:13 ET |
| NFL volume trend | Polymarket NFL/college football volume reported sharply up | [Crypto Briefing](https://cryptobriefing.com/polymarket-nfl-college-football-volume-surge/) (date **UNVERIFIED**) |

## 4. Economics
| Finding | Detail | Source / observed |
|---|---|---|
| Fed funds target | 3.75%–4.00%; raised 25bp at the Sep 15–16 meeting | [FedRateCalc](https://fedratecalc.com/fomc-meeting-schedule/), read 2026-10-29 |
| October FOMC (Oct 27–28) | Polymarket "No change" at 96% before the decision; $83.2M volume. Outcome reported on X: **held, 10–2 vote** (see 7.1; not yet confirmed from the Fed) | RG.org, 2026-10-28 00:13 ET; X, 2026-10-29 |
| Next FOMC | **Dec 8–9, 2026** (last of the year) | FedRateCalc |
| December hike market | "25bp increase in December" at 77% | RG.org, 2026-10-28 (**UNVERIFIED**: wording as reported by RG, not checked on Polymarket) |
| CPI releases | Oct CPI → **Nov 10, 2026**, 8:30 a.m. ET · Nov CPI → **Dec 10, 2026** · Dec CPI → Jan 13, 2027 | [BLS schedule](https://www.bls.gov/schedule/news_release/cpi.htm), read 2026-10-29 |
| Largest company end of 2026 | NVIDIA 69%, $9.0M volume | RG.org, 2026-10-28 |

## 5. Crypto
| Finding | Detail | Source / observed |
|---|---|---|
| BTC October range markets | Dip to $80K: 68% · Hit $82.5K: 57% · Dip to $77.5K: 21%. Resolve Oct 31 | RG.org, 2026-10-28 00:13 ET |
| ETH October markets | Hit $2,400: 68% · Dip to $2,300: 61% · Dip to $2,200: 19% | RG.org, 2026-10-28 |
| "What price will Bitcoin hit in 2026?" | ↑$90K at **45%** with $78.8M volume (Oct 28). Earlier snapshot showed ↑$90K at 76% (Oct 4). Sources disagree; **UNVERIFIED** which is current | RG.org 2026-10-28; [DeFi Rate BTC 2026](https://defirate.com/prediction-markets/bitcoin-price-2026), observed 2026-10-04 |
| BTC spot price | ~$81.1K per one X post (7.1). Consistent with the October range markets above, but not confirmed from an exchange. **UNVERIFIED** | X, 2026-10-29 |

## 6. Tech / AI
| Finding | Detail | Source / observed |
|---|---|---|
| Best AI model end of October | Google 96%, resolves Oct 31 | RG.org, 2026-10-28 |
| Best AI model end of 2026 | Anthropic 56%, Google 36%, OpenAI ~6%. Resolves on the LMArena text leaderboard (style control off) at 12:00 p.m. ET, Dec 31, 2026. Only ~$10K traded in 24h | [DeFi Rate](https://defirate.com/odds/best-ai-model-2026/), prices observed 2026-10-28 |
| Next Fable model (5.2+) by Oct 31 | 10% (down from 33%) | RG.org, 2026-10-28 |
| Acquisitions before 2027 | Conductor 28%, $18.4M volume | RG.org, 2026-10-28 |

## 7. What traders are watching (X)
Read 2026-10-29 from X search (Top). Ages ("7h") are relative to the read time. All items **UNVERIFIED** unless noted.

### 7.1 Economics: the Fed is the hottest in-scope topic
| Post | What it says | Note |
|---|---|---|
| [@polytutor](https://x.com/polytutor), ~6h | Fed **held at 3.75–4.00% on Oct 28, vote 10–2**, Cook and Hammack dissenting for a hike. Hold was priced at ~95.5% on Kalshi/Polymarket US, 94% on CME. "December hike odds are the market to watch now." | Hold matches the 96% pre-decision price in section 4. Two X accounts report the same 10–2 vote. Not yet confirmed from the Fed's own statement |
| [@foom_trade](https://x.com/foom_trade), ~6h | December hike market at **79.5¢**; one trader holds $194K bought at 64.7¢. Same trader lost $59.4K betting on an October hike. Mentions BTC at **$81.1K** | Shows how a "right idea, wrong meeting" bet loses |
| [@MrktMovingStats](https://x.com/MrktMovingStats), ~7h | December "no change" odds fell to **16%** (from 22%); volume spiked 10x | Consistent with ~80% hike odds above |
| [@PolyAlertHub](https://x.com/PolyAlertHub), ~11h | A wallet put **$1.05M on "No" for a 50+bp hike at 99.7¢** to make $3,150 | Example of "near-certain" trades with tiny upside; a bad fit for your +50% target |
| [@PredictionsScan](https://x.com/PredictionsScan), ~7h | "Will no Fed rate cuts happen in 2026?" traded $37.9K in 1h, ~198x its hourly average | Volume spikes cluster right after the decision |
| [@0xlunasterling](https://x.com/0xlunasterling) (中文), ~12h | Pre-decision: hold 94.8%, +25bp 4.9%. **September PCE due Oct 29** | PCE date not checked against BEA |

### 7.2 Crypto: mostly bot promotion
| Post | What it says | Note |
|---|---|---|
| [@maqxbt](https://x.com/maqxbt) (paid partnership) and [@nuwjxx](https://x.com/nuwjxx), Oct 27–28 | A bot reportedly made $2.1–2.4M buying at ~99¢ on **5-minute BTC Up/Down** markets seconds before close | Two accounts give different profit figures. This is a speed game; your multi-day holds can't compete there |
| [@ninedol](https://x.com/ninedol), Oct 28 | Trader made $23.9K on 5-min BTC markets at a 50.5% win rate by buying the cheap side (11–27¢) | Same idea as your +50%/−25% rule: low win rate is fine if wins are bigger than losses |
| [@RetroValix](https://x.com/RetroValix), [@Argona0x](https://x.com/Argona0x), [@immortalhowwl](https://x.com/immortalhowwl) | "Built a bot with Grok Bot, made $200K–$700K" style posts | **Marketing, not evidence.** No verifiable track records; ignore for strategy |

### 7.3 Sports
| Post | What it says | Note |
|---|---|---|
| X scoreboard widget, read 2026-10-29 | World Series: finals shown MIL 5–4 TB, MIL 10–1 TB, TB 4–3 MIL (12 inn.), a game live (MIL 2–0, bottom 5th); games still scheduled **Oct 30 and Oct 31** | Widget dates are in your local time and one game may have been cut off. Series score **UNVERIFIED** |
| [@0x_exit](https://x.com/0x_exit), ~12h | Trader up $158K with a ~50% win rate by **only buying longshot season futures** (NFL/NBA/MLB/NHL champions) | Futures last weeks to months, longer than your "days" holding period |
| [@ninedol](https://x.com/ninedol), Oct 24 | Trader up $766K in a year buying underdogs (NBA, football draws, UFC) at **12–40¢** | Supports testing a "price range" entry rule in the backtest |
| [@0xTengen_](https://x.com/0xTengen_), [@crbpite8](https://x.com/crbpite8), Oct 27–28 | "breakthebank" made $2.56M in one night on NBA + Monday Night Football, with $1M+ bets; lost $664K the day before | Whale-sized one-off results; no lesson for $30–50 stakes |
| [@sonsakripto](https://x.com/sonsakripto), ~20h | Polymarket said to be a "Preferred Prediction Market Partner" of the NBA | Promotional post; **UNVERIFIED** |

### 7.4 Tech / AI
| Post | What it says | Note |
|---|---|---|
| [@_Chain_Duck_](https://x.com/_Chain_Duck_), ~3h | "Best AI model end of 2026": **Google 50%, Anthropic 42%, OpenAI 5.6%**, $3.4M volume | **Conflicts** with section 6 (Anthropic 56%, Google 36% on Oct 28). The market may have flipped within a day; check live before trading |
| [@Polymarket](https://x.com/Polymarket), Oct 26 | Reports Anthropic's IPO filing | Related markets exist: "Anthropic IPO by…" and "IPO closing market cap" (~44% above $2T per [@SofiaTachExpert](https://x.com/SofiaTachExpert)) |
| [@Brainmaster](https://x.com/Brainmaster), Oct 24 | Rumor of an Anthropic IPO in **mid-November 2026**; buying "IPO by Nov 25/30" outcomes | Rumor; **UNVERIFIED** |
| [@kar4arodon](https://x.com/kar4arodon), Oct 25 | "Largest company end of month": Apple ~39% at the time | Conflicts with NVIDIA 69% in section 4, but those are different markets (end of month vs end of year) |

### 7.5 What this means for the strategy
- **Main theme in scope:** the December FOMC (Dec 8–9) hike market. It has high attention and volume, and it resolves inside the year.
- **The strategies X promotes most** (5-minute BTC bots, arbitrage) need speed and a live wallet. They don't fit a paper bot that holds for days.
- **One repeated pattern worth testing:** buying cheap outcomes (12–40¢) and accepting a ~50% or lower win rate. It matches your 2:1 reward/risk rule.
- **Prices move quickly:** "best AI model" moved about 14 points in a day. The bot must re-check the live price before every paper trade.

## 8. Key dates ahead (in scope)
| Date | Event | Category |
|---|---|---|
| Oct 30–31 | World Series Games 6–7 (if needed) | Sports |
| Oct 31 | BTC/ETH October range markets and "best AI model end of October" resolve | Crypto, Tech |
| Nov 10 | October CPI release | Economics |
| Dec 8–9 | FOMC meeting | Economics |
| Dec 10 | November CPI release | Economics |
| Dec 31 | "Best AI model end of 2026" and BTC 2026 price markets resolve | Tech, Crypto |
| Feb 2027 | Super Bowl LXI (futures trading now) | Sports |

## 9. Notes for the STRATEGY phase
- Sports has ~58% of volume: best liquidity for a $30–50 stake and a multi-day hold.
- Economics and tech are thin; set a minimum-liquidity filter before trading them.
- Fees (3–4% per side near mid-prices) make small edges unprofitable; the backtest must include them.
- Crypto range markets resolve monthly and are the costliest category for fees.
