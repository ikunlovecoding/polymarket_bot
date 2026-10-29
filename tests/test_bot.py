"""Tests for every component, using real Polymarket data saved on 2026-10-29.

Run:  python -m unittest discover -s tests -v
"""

import copy
import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from bot import data_feed as feed
from bot.fees import taker_fee
from bot.risk import check_new_trade, stake_for
from bot.run import load_config, run
from bot.simulator import simulate_buy, simulate_sell
from bot.strategy import exit_reason, select_entries

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
NOW = datetime(2026, 10, 29, 2, 0, tzinfo=timezone.utc)  # just before the saved book snapshot
BTC82K_YES = "60603152927209579761433288623268775004817185962857357305731410827159123984525"


def load_events():
    with open(os.path.join(FIX, "events_2026-10-29.json")) as fh:
        return json.load(fh)


def load_book():
    with open(os.path.join(FIX, "book_btc82k_yes.json")) as fh:
        return feed.parse_book(json.load(fh), BTC82K_YES)


def paper_cfg():
    cfg = load_config()
    cfg["mode"] = "paper"
    return cfg


class FakeApi:
    """Stands in for the network. Serves the saved real data; tests can change prices."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.events = load_events()
        self.book = load_book()

    def fetch_events(self, cfg, now):
        return self.events

    def fetch_book(self, token_id):
        return self.book

    def fetch_market_quotes(self, market_id, category, cfg):
        for ev in self.events:
            for m in ev["markets"]:
                if m["id"] == market_id:
                    return feed.quotes_from_event({**ev, "markets": [m]}, cfg, category)
        return []

    def set_quote(self, market_id, bid, ask):
        for ev in self.events:
            for m in ev["markets"]:
                if m["id"] == market_id:
                    m["bestBid"], m["bestAsk"] = bid, ask


# ------------------------------------------------------------------ fees

class TestFees(unittest.TestCase):
    def test_docs_examples(self):
        # Polymarket docs: 100 shares at 50c -> crypto $1.75, sports $1.25, tech $1.00
        self.assertAlmostEqual(taker_fee(100, 0.5, 0.07), 1.75)
        self.assertAlmostEqual(taker_fee(100, 0.5, 0.05), 1.25)
        self.assertAlmostEqual(taker_fee(100, 0.5, 0.04), 1.00)

    def test_symmetric_and_zero(self):
        self.assertAlmostEqual(taker_fee(100, 0.3, 0.05), taker_fee(100, 0.7, 0.05))
        self.assertEqual(taker_fee(100, 0.4, 0.0), 0.0)


# ------------------------------------------------------------------ data feed

class TestDataFeed(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()
        self.quotes = [q for ev in load_events() for q in feed.quotes_from_event(ev, self.cfg)]

    def test_second_outcome_is_mirror(self):
        no = next(q for q in self.quotes if q.market_id == "6236213" and q.outcome == "No")
        self.assertAlmostEqual(no.best_bid, 0.60)   # 1 - ask of Yes (0.40)
        self.assertAlmostEqual(no.best_ask, 0.61)   # 1 - bid of Yes (0.39)

    def test_categories(self):
        cats = {q.event_id: q.category for q in self.quotes}
        self.assertEqual(cats["1235147"], "sports")
        self.assertEqual(cats["1256935"], "crypto")
        self.assertNotIn("999001", cats)            # politics tag excludes the event

    def test_sports_event_time_is_game_start_not_end_date(self):
        q = next(q for q in self.quotes if q.market_id == "6041525")
        self.assertEqual(q.event_time, datetime(2026, 10, 29, 0, 0, tzinfo=timezone.utc))

    def test_market_fee_rate_used(self):
        q = next(q for q in self.quotes if q.market_id == "6236213")
        self.assertEqual(q.fee_rate, 0.07)
        q = next(q for q in self.quotes if q.market_id == "3499790")
        self.assertEqual(q.fee_rate, 0.0)           # zero_fees market

    def test_book_sorted_best_first(self):
        book = load_book()                         # raw file lists best prices LAST
        self.assertEqual(book.best_bid, 0.38)
        self.assertEqual(book.best_ask, 0.39)
        self.assertTrue(all(book.asks[i][0] < book.asks[i + 1][0] for i in range(len(book.asks) - 1)))


# ------------------------------------------------------------------ strategy

class TestStrategy(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()
        self.quotes = [q for ev in load_events() for q in feed.quotes_from_event(ev, self.cfg)]

    def test_only_btc_82k_yes_qualifies(self):
        signals, skipped = select_entries(self.quotes, NOW, self.cfg, set(), set())
        self.assertEqual(len(signals), 1)
        q, conf = signals[0]
        self.assertEqual((q.market_id, q.outcome), ("6236213", "Yes"))
        self.assertEqual(conf, "high")              # top 20% by volume among passing markets
        self.assertIn("F2 event too soon", skipped)  # games already started
        self.assertIn("F5 no resolution source named", skipped)

    def test_one_position_per_event_and_no_reentry(self):
        signals, _ = select_entries(self.quotes, NOW, self.cfg, {"1256935"}, set())
        self.assertEqual(signals, [])
        signals, _ = select_entries(self.quotes, NOW, self.cfg, set(), {"6236213", "6236215"})
        self.assertEqual(signals, [])

    def test_time_window(self):
        late = NOW + timedelta(days=2)               # BTC weekly is now < 3 days away
        signals, _ = select_entries(self.quotes, late, self.cfg, set(), set())
        self.assertEqual(signals, [])

    def _pos(self, **kw):
        p = {"entry_price": 0.40, "opened_at": NOW.isoformat()}
        p.update(kw)
        return p

    def _quote(self, bid, ask, **kw):
        q = copy.copy(next(q for q in self.quotes if q.market_id == "6236213" and q.outcome == "Yes"))
        q.best_bid, q.best_ask = bid, ask
        for k, v in kw.items():
            setattr(q, k, v)
        return q

    def test_exits(self):
        c = self.cfg
        self.assertIsNone(exit_reason(self._pos(), self._quote(0.45, 0.46), NOW + timedelta(hours=1), c))
        self.assertEqual(exit_reason(self._pos(), self._quote(0.60, 0.61), NOW, c), "X1 take profit")
        self.assertEqual(exit_reason(self._pos(), self._quote(0.30, 0.31), NOW, c), "X2 stop loss")
        self.assertEqual(exit_reason(self._pos(), self._quote(0.20, 0.21), NOW, c), "X2 stop loss")  # gap
        old = self._pos(opened_at=(NOW - timedelta(days=7)).isoformat())
        self.assertEqual(exit_reason(old, self._quote(0.45, 0.46), NOW, c), "X3 time stop")
        near = NOW.replace(day=1, month=11, hour=18)  # 11h before the Nov 2 05:00 end
        self.assertEqual(exit_reason(self._pos(opened_at=near.isoformat()), self._quote(0.45, 0.46), near, c),
                         "X4 pre-resolution exit")
        self.assertEqual(exit_reason(self._pos(), self._quote(0.30, 0.45), NOW, c), "X5 spread too wide")
        self.assertTrue(exit_reason(self._pos(), self._quote(0.45, 0.46, uma_status="proposed"), NOW, c)
                        .startswith("X5"))


# ------------------------------------------------------------------ simulator

class TestSimulator(unittest.TestCase):
    def test_buy_walks_real_asks_within_budget(self):
        fill = simulate_buy(load_book(), 50.0, 0.55, 0.07, 5)
        self.assertEqual(fill.shares, 122)           # 212 available at 0.39; budget allows 122
        self.assertAlmostEqual(fill.avg_price, 0.39)
        self.assertLessEqual(fill.net_cost, 50.0)
        self.assertAlmostEqual(fill.fee, taker_fee(122, 0.39, 0.07))

    def test_buy_spills_to_next_level(self):
        fill = simulate_buy(load_book(), 200.0, 0.55, 0.07, 5)
        self.assertEqual(fill.levels_used, 2)        # 212 @ 0.39 then the rest @ 0.40
        self.assertGreater(fill.avg_price, 0.39)
        self.assertLessEqual(fill.net_cost, 200.0)

    def test_buy_respects_price_cap(self):
        self.assertIsNone(simulate_buy(load_book(), 50.0, 0.38, 0.07, 5))

    def test_sell_walks_bids(self):
        fill = simulate_sell(load_book(), 122, 0.07)
        self.assertAlmostEqual(fill.avg_price, 0.38)
        self.assertAlmostEqual(fill.net_proceeds, 122 * 0.38 - taker_fee(122, 0.38, 0.07), places=5)


# ------------------------------------------------------------------ risk

class TestRisk(unittest.TestCase):
    def setUp(self):
        self.cfg = paper_cfg()
        self.state = {"cash": 1000.0, "day_start_equity": 1000.0, "positions": []}

    def test_stakes(self):
        self.assertEqual(stake_for("normal", 1000, self.cfg), 30.0)
        self.assertEqual(stake_for("high", 1000, self.cfg), 50.0)

    def test_allows_normal_trade(self):
        self.assertIsNone(check_new_trade(self.state, 50, 1000, self.cfg))

    def test_blocks(self):
        self.assertIn("kill switch", check_new_trade(self.state, 50, 1000, {**self.cfg, "kill_switch": True}))
        self.assertIn("signals only", check_new_trade(self.state, 50, 1000, {**self.cfg, "mode": "scan_only"}))
        self.assertIn("daily loss", check_new_trade(self.state, 30, 900, self.cfg))
        self.state["positions"] = [{"cost": 280.0}]
        self.assertIn("exposure cap", check_new_trade(self.state, 30, 1000, self.cfg))


# ------------------------------------------------------------------ whole bot

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = paper_cfg()
        self.api = FakeApi(self.cfg)

    def test_open_hold_take_profit(self):
        r = run(self.cfg, now=NOW, api=self.api, root=self.tmp)
        self.assertEqual(len(r["scan"]["opened"]), 1)
        pos = r["state"]["positions"][0]
        self.assertEqual(pos["shares"], 122)
        self.assertLessEqual(pos["cost"], 50.0)
        self.assertAlmostEqual(r["state"]["cash"], 1000 - pos["cost"], places=5)

        # Same scan again an hour later: no duplicate position, nothing to exit.
        r = run(self.cfg, now=NOW + timedelta(hours=1), api=self.api, root=self.tmp)
        self.assertEqual(len(r["scan"]["opened"]), 0)
        self.assertEqual(len(r["state"]["positions"]), 1)

        # Price jumps: bid 0.60 >= 0.39 x 1.5 -> take profit, sold into the bids of the book.
        self.api.set_quote("6236213", 0.60, 0.61)
        self.api.book = feed.Book(BTC82K_YES, bids=[(0.60, 1000)], asks=[(0.61, 1000)],
                                  min_order_size=5, timestamp_ms=0)
        r = run(self.cfg, now=NOW + timedelta(hours=2), api=self.api, root=self.tmp)
        self.assertEqual(len(r["scan"]["closed"]), 1)
        t = r["state"]["closed"][0]
        self.assertEqual(t["exit_reason"], "X1 take profit")
        self.assertEqual(t["result"], "WIN")
        self.assertAlmostEqual(t["pnl"], 122 * 0.60 - taker_fee(122, 0.60, 0.07) - pos["cost"], places=4)
        # Market may not be traded again (E5).
        self.assertIn("6236213", r["state"]["traded_market_ids"])
        for f in ("Trade_Ledger.md", "reports/brief.md", "reports/last_scan.md", "data/state.json"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, f)), f)
        with open(os.path.join(self.tmp, "Trade_Ledger.md")) as fh:
            self.assertIn("X1 take profit", fh.read())

    def test_settles_if_market_resolved(self):
        run(self.cfg, now=NOW, api=self.api, root=self.tmp)
        for ev in self.api.events:
            for m in ev["markets"]:
                if m["id"] == "6236213":
                    m["closed"], m["outcomePrices"] = True, '["0", "1"]'
        r = run(self.cfg, now=NOW + timedelta(hours=1), api=self.api, root=self.tmp)
        t = r["state"]["closed"][0]
        self.assertEqual(t["exit_reason"], "Settled at resolution")
        self.assertEqual(t["result"], "LOSS")

    def test_scan_only_and_dry_run_never_trade(self):
        r = run({**self.cfg, "mode": "scan_only"}, now=NOW, api=self.api, root=self.tmp)
        self.assertEqual(r["scan"]["opened"], [])
        self.assertEqual(len(r["scan"]["signals"]), 1)
        r = run(self.cfg, now=NOW, api=self.api, root=self.tmp, dry_run=True)
        self.assertEqual(r["scan"]["opened"], [])

    def test_feed_failure_does_not_crash(self):
        class Broken(FakeApi):
            def fetch_events(self, cfg, now):
                raise RuntimeError("network down")
        r = run(self.cfg, now=NOW, api=Broken(self.cfg), root=self.tmp)
        self.assertTrue(any("network down" in e for e in r["scan"]["errors"]))


# ------------------------------------------------------------------ safety

class TestSafety(unittest.TestCase):
    def test_no_wallet_keys_or_order_sending_in_code(self):
        bot_dir = os.path.join(os.path.dirname(HERE), "bot")
        forbidden = [r"private_?key", r"mnemonic", r"seed_?phrase", r"py_clob_client", r"web3",
                     r"POST", r"\.post\(", r"post_order", r"create_order", r"api_secret", r"passphrase"]
        for name in os.listdir(bot_dir):
            if name.endswith(".py"):
                with open(os.path.join(bot_dir, name)) as fh:
                    src = fh.read()
                for pat in forbidden:
                    self.assertIsNone(re.search(pat, src), f"{pat} found in bot/{name}")


if __name__ == "__main__":
    unittest.main()
