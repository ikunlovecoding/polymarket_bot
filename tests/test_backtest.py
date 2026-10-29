"""Backtest simulator tests on small made-up price paths with known answers."""

import unittest
from datetime import datetime, timezone

from bot.backtest import HOUR, SLIP, Series, simulate, summarize
from bot.fees import taker_fee
from bot.run import load_config

T0 = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp())
DAY = 86400


def market(mid, path, event_day=10, fee=0.05, final=(1.0, 0.0), event=None, closed_day=None):
    """path: list of (hours after T0, price of outcome 0)."""
    return {"market_id": mid, "event_id": event or ("ev" + mid), "event_title": "", "question": mid,
            "category": "sports", "outcomes": ["Yes", "No"], "token0": "t",
            "final_prices": list(final), "fee_rate": fee, "volume": 10000,
            "event_time": datetime.fromtimestamp(T0 + event_day * DAY, timezone.utc).isoformat(),
            "opened": datetime.fromtimestamp(T0, timezone.utc).isoformat(),
            "closed_at": datetime.fromtimestamp(T0 + (closed_day or event_day) * DAY, timezone.utc).isoformat(),
            "history": [[T0 + h * HOUR, int(p * 1000)] for h, p in path]}


def flat(p, hours):
    return [(h, p) for h in range(hours)]


class TestBacktest(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def run_one(self, rec, unlimited=True):
        s = Series(rec)
        return simulate([s], self.cfg, 0.03, T0, T0 + 12 * DAY, unlimited=unlimited,
                        use_liquidity_filter=False)["trades"]

    def test_take_profit(self):
        # Yes trades at 0.30 (ask 0.31). At hour 10 it jumps to 0.60 -> bid 0.59 >= 0.31*1.5=0.465.
        path = flat(0.30, 10) + [(h, 0.60) for h in range(10, 240)]
        t = self.run_one(market("a", path))[0]
        self.assertEqual(t["reason"], "X1 take profit")
        self.assertAlmostEqual(t["entry"], 0.30 + SLIP)
        self.assertAlmostEqual(t["exit"], 0.60 - SLIP)
        shares = t["shares"]
        expect = shares * 0.59 - taker_fee(shares, 0.59, 0.05) - t["cost"]
        self.assertAlmostEqual(t["pnl"], expect, places=6)

    def test_stop_loss_with_gap(self):
        path = flat(0.40, 5) + [(h, 0.10) for h in range(5, 240)]
        t = self.run_one(market("b", path))[0]
        self.assertEqual(t["reason"], "X2 stop loss")
        self.assertAlmostEqual(t["exit"], 0.09)       # gapped well below the stop
        self.assertLess(t["pnl_pct"], -70)

    def test_pre_resolution_exit(self):
        # Event 5 days out: entered ~5d before, must leave 12h before the event (before the 7-day stop).
        t = self.run_one(market("c", flat(0.40, 240), event_day=5))[0]
        self.assertEqual(t["reason"], "X4 pre-resolution exit")
        self.assertLess(t["pnl"], 0)                   # flat price still loses slippage + fees
        self.assertEqual(t["closed"], T0 + 5 * DAY - 12 * HOUR)

    def test_time_stop(self):
        # Event 10 days out: the 7-day time stop comes first.
        t = self.run_one(market("c2", flat(0.40, 240), event_day=10))[0]
        self.assertEqual(t["reason"], "X3 time stop")
        self.assertEqual(t["closed"] - t["opened"], 7 * DAY)

    def test_entry_waits_until_14_days_and_needs_3(self):
        # event in 20 days: no entry before day 6; price 0.40 throughout
        t = self.run_one(market("d", flat(0.40, 20 * 24), event_day=20))
        self.assertTrue(t)
        self.assertGreaterEqual(t[0]["opened"], T0 + 6 * DAY)

    def test_no_entry_outside_price_range(self):
        # Yes at 0.80 -> ask 0.81 (too dear) but No at 0.20 -> ask 0.21 (inside): the No side is bought.
        self.assertEqual(self.run_one(market("e", flat(0.80, 240)))[0]["outcome"], "No")
        # Yes 0.90 -> ask 0.91, No 0.10 -> ask 0.11: both outside, no trade.
        self.assertEqual(self.run_one(market("f", flat(0.90, 240))), [])

    def test_early_resolution_settles(self):
        # Market closes on day 5 (e.g. a "hit price" market) at 1.0 for Yes, before X4 could act
        path = flat(0.40, 4 * 24 + 23)
        t = self.run_one(market("g", path, closed_day=5))[0]
        self.assertEqual(t["reason"], "Settled at resolution")
        self.assertAlmostEqual(t["exit"], 1.0)

    def test_portfolio_one_per_event_and_exposure(self):
        recs = [market(str(i), flat(0.40, 240), event="same" if i < 3 else None) for i in range(20)]
        out = simulate([Series(r) for r in recs], self.cfg, 0.03, T0, T0 + 12 * DAY, use_liquidity_filter=False)
        opened_same = [t for t in out["trades"] if t["market_id"] in ("0", "1", "2")]
        self.assertEqual(len(opened_same), 1)          # one position per event
        # 30% cap with 3% stakes -> at most 10 open at once
        first_hour = min(t["opened"] for t in out["trades"])
        self.assertLessEqual(sum(1 for t in out["trades"] if t["opened"] == first_hour), 10)
        s = summarize(out["trades"], out["curve"], 1000)
        self.assertGreater(s["max_drawdown_pct"], 0)

    def test_no_lookahead_price_used_only_up_to_now(self):
        # Price is 0.40 until hour 100, then 0.95. A lookahead bug would avoid or exploit the jump
        # at entry; the bot must enter at 0.41 in the first eligible hour.
        path = flat(0.40, 100) + [(h, 0.95) for h in range(100, 240)]
        t = self.run_one(market("h", path))[0]
        self.assertAlmostEqual(t["entry"], 0.41)
        self.assertEqual(t["reason"], "X1 take profit")
        self.assertGreaterEqual(t["closed"], T0 + 100 * HOUR)


if __name__ == "__main__":
    unittest.main()


class TestReviewFixesBacktest(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def test_price_gap_still_exits_before_event(self):           # finding 1
        # entry on day 0 (event day 5); prices stop on day 3 -> must exit at 12h before event,
        # NOT ride to resolution.
        path = flat(0.40, 3 * 24)
        rec = market("gap", path, event_day=5, final=(1.0, 0.0))
        t = simulate([Series(rec)], self.cfg, 0.03, T0, T0 + 8 * DAY, unlimited=True,
                     use_liquidity_filter=False)["trades"][0]
        self.assertEqual(t["reason"], "X4 pre-resolution exit (no fresh price)")
        self.assertEqual(t["closed"], T0 + 5 * DAY - 12 * HOUR)
        self.assertLess(abs(t["pnl_pct"]), 15)

    def test_planned_breakeven_matches_strategy_table(self):    # finding 5
        from bot.backtest import planned_breakeven
        # Strategy.md: sports ~41.8% at 35c, crypto ~45.2% at 35c (computed with the same formula)
        self.assertAlmostEqual(planned_breakeven(0.35, 0.05) * 100, 41.8, delta=0.3)
        self.assertAlmostEqual(planned_breakeven(0.35, 0.07) * 100, 45.2, delta=0.3)
        self.assertAlmostEqual(planned_breakeven(0.35, 0.0) * 100, 33.3, delta=0.2)

    def test_cheaper_outcome_first_within_market(self):           # finding 9
        t = simulate([Series(market("tie", flat(0.52, 240), event_day=5))], self.cfg, 0.03,
                     T0, T0 + 8 * DAY, unlimited=True, use_liquidity_filter=False)["trades"][0]
        self.assertEqual(t["outcome"], "No")                  # No ask 0.49 < Yes ask 0.53


class TestLiquidityFilter(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def _trades(self, path):
        return simulate([Series(market("q", path, event_day=6))], self.cfg, 0.03, T0, T0 + 8 * DAY,
                        unlimited=True)["trades"]

    def test_stuck_placeholder_price_is_skipped(self):
        self.assertEqual(self._trades(flat(0.50, 200)), [])     # 0.50 for days = empty book

    def test_flip_flopping_price_is_skipped(self):
        path = [(h, 0.45 if h % 2 else 0.15) for h in range(200)]   # wide-book noise
        self.assertEqual(self._trades(path), [])

    def test_normal_trading_market_is_entered(self):
        path = [(h, 0.40 + 0.01 * ((h // 3) % 3)) for h in range(200)]  # small real moves
        t = self._trades(path)
        self.assertTrue(t)
        # price changes every 3h, so the 3rd change (the minimum) is at hour 9
        self.assertGreaterEqual(t[0]["opened"], T0 + 9 * HOUR)
