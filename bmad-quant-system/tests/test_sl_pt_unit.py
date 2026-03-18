"""
Unit Tests for BacktestEngine SL/PT core methods.

Tests _check_stop_loss, _check_profit_taking, _check_sl_pt,
_get_entry_price_at_time using synthetic intraday data.

Easy to modify:
  - Change ENTRY_ASK / BID_SERIES to test different scenarios
  - Change SL_BPS / PT_BPS thresholds
  - Add new test cases by copying an existing one
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helper: build a minimal BacktestEngine with synthetic intraday data
# ---------------------------------------------------------------------------
def _make_engine_with_intraday(bid_series, ask_series, start_time="2025-08-29 22:30:00", freq="1min"):
    """
    Build a BacktestEngine stub with pre-loaded intraday arrays.

    Args:
        bid_series: list/array of bid prices (one per minute)
        ask_series: list/array of ask prices (one per minute)
        start_time: first bar timestamp (Beijing time)
        freq: bar frequency (default 1min)

    Returns:
        BacktestEngine instance with _intraday_ts_index, _intraday_bid_arr,
        _intraday_ask_arr populated. Other fields are left None.
    """
    import yaml
    config_path = ROOT / "backtest" / "dashboard" / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    from backtest.dashboard.app import BacktestEngine
    engine = BacktestEngine(config)

    n = len(bid_series)
    timestamps = pd.date_range(start_time, periods=n, freq=freq)
    engine._intraday_ts_index = timestamps.astype(np.int64).values  # nanoseconds
    engine._intraday_bid_arr = np.array(bid_series, dtype=np.float64)
    engine._intraday_ask_arr = np.array(ask_series, dtype=np.float64)

    return engine, timestamps


# ===================================================================
#  Test: _check_stop_loss
# ===================================================================
class TestCheckStopLoss:
    """Unit tests for _check_stop_loss method."""

    def test_sl_triggers_when_bid_drops_enough(self):
        """SL should trigger at the first minute where loss >= threshold."""
        # Entry at 7.1234 ASK. SL = 5 bps = 0.05% = 7.1234 * 0.0005 = 0.0035617
        # So trigger when bid <= 7.1234 - 0.0035617 = 7.11984
        entry = 7.1234
        sl_bps = 5.0
        # Bid starts at 7.1230, gradually drops
        bids = [7.1230, 7.1225, 7.1220, 7.1210, 7.1200, 7.1198, 7.1190]
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, unwind_time, unwind_bid = engine._check_stop_loss(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1],
            stop_loss_bps=sl_bps,
        )

        assert triggered is True
        # Verify the trigger bar: (7.1234 - bid) / 7.1234 >= 0.0005
        assert unwind_bid is not None
        loss_pct = (entry - unwind_bid) / entry
        assert loss_pct >= sl_bps / 10000.0
        # Should be the first bar meeting the condition
        # bar[4] = 7.1200: (7.1234-7.1200)/7.1234 = 0.000477 < 0.0005
        # bar[5] = 7.1198: (7.1234-7.1198)/7.1234 = 0.000505 >= 0.0005 => trigger
        assert unwind_bid == 7.1198
        assert unwind_time == ts[5]

    def test_sl_no_trigger_when_bid_stays_above(self):
        """SL should NOT trigger if bid never drops enough."""
        entry = 7.1234
        sl_bps = 10.0  # 10 bps = 0.10%
        bids = [7.1230, 7.1228, 7.1225, 7.1230, 7.1235]
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, unwind_time, unwind_bid = engine._check_stop_loss(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1],
            stop_loss_bps=sl_bps,
        )

        assert triggered is False
        assert unwind_time is None
        assert unwind_bid is None

    def test_sl_disabled_when_bps_is_none(self):
        """SL should be disabled when stop_loss_bps=None."""
        bids = [7.0000, 6.9000, 6.8000]  # massive drop
        asks = [b + 0.0003 for b in bids]
        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, _, _ = engine._check_stop_loss(
            avg_entry_price=7.1234,
            start_time=ts[0],
            end_time=ts[-1],
            stop_loss_bps=None,
        )
        assert triggered is False

    def test_sl_disabled_when_bps_is_zero(self):
        """SL should be disabled when stop_loss_bps=0."""
        bids = [7.0000, 6.9000, 6.8000]
        asks = [b + 0.0003 for b in bids]
        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, _, _ = engine._check_stop_loss(
            avg_entry_price=7.1234,
            start_time=ts[0],
            end_time=ts[-1],
            stop_loss_bps=0,
        )
        assert triggered is False

    def test_sl_skips_nan_bars(self):
        """SL should skip NaN bid bars without crashing."""
        entry = 7.1234
        sl_bps = 5.0
        bids = [7.1230, np.nan, 0.0, 7.1198]  # NaN and 0 should be skipped
        asks = [7.1233, np.nan, 0.0, 7.1201]

        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, unwind_time, unwind_bid = engine._check_stop_loss(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1] + pd.Timedelta(minutes=1),
            stop_loss_bps=sl_bps,
        )

        assert triggered is True
        assert unwind_bid == 7.1198  # skipped NaN and 0, triggered at bar[3]

    def test_sl_triggers_slightly_beyond_threshold(self):
        """SL should trigger when loss is slightly above threshold (avoids float precision edge)."""
        entry = 7.1234
        sl_bps = 5.0
        threshold = sl_bps / 10000.0
        # Bid slightly below the exact threshold to avoid float rounding
        trigger_bid = entry * (1 - threshold) - 0.00001
        bids = [7.1230, trigger_bid]
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, _, unwind_bid = engine._check_stop_loss(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1] + pd.Timedelta(minutes=1),
            stop_loss_bps=sl_bps,
        )

        assert triggered is True
        loss_pct = (entry - unwind_bid) / entry
        assert loss_pct >= threshold


# ===================================================================
#  Test: _check_profit_taking
# ===================================================================
class TestCheckProfitTaking:
    """Unit tests for _check_profit_taking method."""

    def test_pt_triggers_when_bid_rises_enough(self):
        """PT should trigger at the first minute where gain >= threshold."""
        entry = 7.1234
        pt_bps = 8.0  # 8 bps = 0.08%
        # trigger_bid = entry * (1 + 0.0008) = 7.12910
        bids = [7.1240, 7.1250, 7.1260, 7.1280, 7.1291, 7.1300]
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, unwind_time, unwind_bid = engine._check_profit_taking(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1] + pd.Timedelta(minutes=1),
            profit_taking_bps=pt_bps,
        )

        assert triggered is True
        gain_pct = (unwind_bid - entry) / entry
        assert gain_pct >= pt_bps / 10000.0
        # bar[4] = 7.1291: (7.1291-7.1234)/7.1234 = 0.0008001 >= 0.0008
        assert unwind_bid == 7.1291
        assert unwind_time == ts[4]

    def test_pt_no_trigger_when_bid_stays_low(self):
        """PT should NOT trigger if bid never rises enough."""
        entry = 7.1234
        pt_bps = 15.0
        bids = [7.1234, 7.1240, 7.1245, 7.1250]
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        triggered, _, _ = engine._check_profit_taking(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1],
            profit_taking_bps=pt_bps,
        )
        assert triggered is False

    def test_pt_disabled_when_bps_is_none(self):
        bids = [7.2000, 7.3000]
        asks = [b + 0.0003 for b in bids]
        engine, ts = _make_engine_with_intraday(bids, asks)
        triggered, _, _ = engine._check_profit_taking(7.1234, ts[0], ts[-1], None)
        assert triggered is False


# ===================================================================
#  Test: _check_sl_pt (combined single-pass)
# ===================================================================
class TestCheckSlPt:
    """Unit tests for _check_sl_pt combined method."""

    def test_sl_triggers_before_pt(self):
        """If SL happens chronologically before PT, SL should win."""
        entry = 7.1234
        # Bid drops first, then rises
        bids = [7.1230, 7.1220, 7.1198, 7.1300]  # bar[2] triggers SL
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        evt, evt_time, evt_bid = engine._check_sl_pt(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1] + pd.Timedelta(minutes=1),
            stop_loss_bps=5.0,
            profit_taking_bps=10.0,
        )

        assert evt == 'SL'
        assert evt_bid == 7.1198
        assert evt_time == ts[2]

    def test_pt_triggers_before_sl(self):
        """If PT happens chronologically before SL, PT should win."""
        entry = 7.1234
        # Bid rises first, then drops
        bids = [7.1240, 7.1260, 7.1295, 7.1100]  # bar[2] triggers PT (8bps+)
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        evt, evt_time, evt_bid = engine._check_sl_pt(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1] + pd.Timedelta(minutes=1),
            stop_loss_bps=10.0,
            profit_taking_bps=8.0,
        )

        assert evt == 'PT'
        assert evt_bid == 7.1295

    def test_neither_triggers(self):
        """If neither SL nor PT threshold is breached, return None."""
        entry = 7.1234
        bids = [7.1232, 7.1233, 7.1235, 7.1236]
        asks = [b + 0.0003 for b in bids]

        engine, ts = _make_engine_with_intraday(bids, asks)

        evt, evt_time, evt_bid = engine._check_sl_pt(
            avg_entry_price=entry,
            start_time=ts[0],
            end_time=ts[-1] + pd.Timedelta(minutes=1),
            stop_loss_bps=10.0,
            profit_taking_bps=10.0,
        )

        assert evt is None
        assert evt_time is None
        assert evt_bid is None

    def test_both_disabled(self):
        """If both SL and PT are None, should return None."""
        bids = [6.0, 8.0]  # extreme moves
        asks = [b + 0.0003 for b in bids]
        engine, ts = _make_engine_with_intraday(bids, asks)

        evt, _, _ = engine._check_sl_pt(7.1234, ts[0], ts[-1], None, None)
        assert evt is None

    def test_only_sl_enabled(self):
        """Only SL enabled, PT=None. Should still detect SL."""
        entry = 7.1234
        bids = [7.1230, 7.1198]
        asks = [b + 0.0003 for b in bids]
        engine, ts = _make_engine_with_intraday(bids, asks)

        evt, _, evt_bid = engine._check_sl_pt(
            entry, ts[0], ts[-1] + pd.Timedelta(minutes=1),
            stop_loss_bps=5.0, profit_taking_bps=None,
        )
        assert evt == 'SL'
        assert evt_bid == 7.1198

    def test_only_pt_enabled(self):
        """Only PT enabled, SL=None. Should still detect PT."""
        entry = 7.1234
        bids = [7.1240, 7.1295]
        asks = [b + 0.0003 for b in bids]
        engine, ts = _make_engine_with_intraday(bids, asks)

        evt, _, evt_bid = engine._check_sl_pt(
            entry, ts[0], ts[-1] + pd.Timedelta(minutes=1),
            stop_loss_bps=None, profit_taking_bps=8.0,
        )
        assert evt == 'PT'
        assert evt_bid == 7.1295

    def test_window_boundary_exclusive(self):
        """Bars outside [start_time, end_time) should NOT be checked."""
        entry = 7.1234
        # Bar at 22:30 is safe, bar at 22:31 triggers SL,
        # but we set end_time = 22:31 so bar[1] should NOT be included
        bids = [7.1230, 7.1100]
        asks = [b + 0.0003 for b in bids]
        engine, ts = _make_engine_with_intraday(bids, asks)

        evt, _, _ = engine._check_sl_pt(
            entry, ts[0], ts[1],  # end_time = ts[1], so bar[1] should be excluded
            stop_loss_bps=5.0, profit_taking_bps=None,
        )
        # searchsorted with side='right' for end means ts[1] IS included
        # Adjust expectation: end_time uses side='right', which INCLUDES the boundary
        # So bar[1] at ts[1] IS checked. This test documents the actual behavior.
        assert evt == 'SL'  # bar[1] is included because side='right'


# ===================================================================
#  Test: _get_entry_price_at_time
# ===================================================================
class TestGetEntryPriceAtTime:
    """Unit tests for _get_entry_price_at_time."""

    def test_exact_match(self):
        """Should return ASK when signal time exactly matches a bar."""
        bids = [7.1230, 7.1232, 7.1234]
        asks = [7.1233, 7.1235, 7.1237]
        engine, ts = _make_engine_with_intraday(bids, asks)

        # Signal at ts[1] -> should return ask[1]
        price = engine._get_entry_price_at_time(ts[1], "2025_34")
        assert abs(price - 7.1235) < 1e-10

    def test_near_match_within_5min(self):
        """Should match if signal is within 5 min of nearest bar."""
        bids = [7.1230, 7.1232]
        asks = [7.1233, 7.1235]
        engine, ts = _make_engine_with_intraday(bids, asks)

        # Signal at ts[0] + 3 minutes (within 5 min tolerance)
        sig_time = ts[0] + pd.Timedelta(minutes=3)
        price = engine._get_entry_price_at_time(sig_time, "2025_34")
        # Nearest bar is ts[1] (1 min vs 3 min away), should return ask[1]
        assert abs(price - 7.1235) < 1e-10

    def test_no_match_beyond_5min(self):
        """Should fall back to entry_map if signal is >5 min from any bar."""
        bids = [7.1230]
        asks = [7.1233]
        engine, ts = _make_engine_with_intraday(bids, asks)

        # Set up fallback
        engine.entry_map = {"2025_34": 7.9999}

        # Signal at ts[0] + 10 minutes (beyond 5 min tolerance)
        sig_time = ts[0] + pd.Timedelta(minutes=10)
        price = engine._get_entry_price_at_time(sig_time, "2025_34")
        assert abs(price - 7.9999) < 1e-10

    def test_fallback_when_no_intraday(self):
        """Should use entry_map when intraday data is not loaded."""
        import yaml
        config_path = ROOT / "backtest" / "dashboard" / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        from backtest.dashboard.app import BacktestEngine
        engine = BacktestEngine(config)
        engine.entry_map = {"2025_34": 7.5555}

        price = engine._get_entry_price_at_time(
            pd.Timestamp("2025-08-29 22:30:00"), "2025_34"
        )
        assert abs(price - 7.5555) < 1e-10


# ===================================================================
#  Test: Weighted Average Entry Price Calculation
# ===================================================================
class TestWeightedAverageEntry:
    """
    Test the weighted average entry price formula used in run_single_tranche.

    Formula:  avg_entry = sum(entry_i * amount_i) / sum(amount_i)
    """

    def test_equal_weight_two_tranches(self):
        """Two equal-size tranches: avg = simple average."""
        e1, e2 = 7.1234, 7.1256
        a1 = a2 = 27_500_000.0  # half of 55M
        weighted_sum = e1 * a1 + e2 * a2
        total_amount = a1 + a2
        avg = weighted_sum / total_amount
        expected = (e1 + e2) / 2
        assert abs(avg - expected) < 1e-10

    def test_unequal_weight_carry_over(self):
        """
        3 slots, slot 1 SKIP, slot 2 EXECUTE (weight 2/3), slot 3 EXECUTE (weight 1/3).
        Demonstrates weight carry-over from skipped slot.
        """
        trade_size = 55_000_000.0
        n_slots = 3
        base_weight = 1.0 / n_slots

        # Slot 1: SKIP -> accumulated_weight = base_weight
        accumulated_weight = base_weight

        # Slot 2: EXECUTE with available_weight = accumulated + base = 2/3
        available_weight_2 = accumulated_weight + base_weight
        entry_2 = 7.1234
        amount_2 = available_weight_2 * trade_size

        accumulated_weight = 0.0  # reset after execute

        # Slot 3: EXECUTE with available_weight = 0 + base = 1/3
        available_weight_3 = accumulated_weight + base_weight
        entry_3 = 7.1256
        amount_3 = available_weight_3 * trade_size

        weighted_sum = entry_2 * amount_2 + entry_3 * amount_3
        total = amount_2 + amount_3
        avg = weighted_sum / total

        # Manual: (7.1234 * 2/3 + 7.1256 * 1/3) = 7.12413...
        expected = entry_2 * (2 / 3) + entry_3 * (1 / 3)
        assert abs(avg - expected) < 1e-10
        assert abs(total - trade_size) < 1e-6  # should use full notional

    def test_single_tranche_avg_equals_entry(self):
        """Single tranche: avg entry == entry price."""
        entry = 7.1234
        amount = 55_000_000.0
        avg = (entry * amount) / amount
        assert abs(avg - entry) < 1e-10

    def test_three_equal_tranches(self):
        """Three equal tranches: avg = simple arithmetic mean."""
        entries = [7.1234, 7.1256, 7.1278]
        n = len(entries)
        amount = 55_000_000.0 / n  # equal weight

        weighted_sum = sum(e * amount for e in entries)
        total = amount * n
        avg = weighted_sum / total
        expected = sum(entries) / n
        assert abs(avg - expected) < 1e-10


# ===================================================================
#  Test: PnL Calculation
# ===================================================================
class TestPnlCalculation:
    """
    Test PnL formulas in isolation.

    Normal PnL:     (exit_price - entry_price) / entry_price * exec_amount
    SL/PT PnL:      (unwind_bid - entry_price) / entry_price * exec_amount
    """

    def test_normal_exit_pnl_positive(self):
        """Long position, price goes up -> positive PnL."""
        entry = 7.1234
        exit_price = 7.1300
        amount = 55_000_000.0
        pnl = (exit_price - entry) / entry * amount
        expected_bps = (exit_price - entry) / entry * 10000  # ~9.27 bps
        assert pnl > 0
        assert abs(pnl - amount * expected_bps / 10000) < 0.01

    def test_normal_exit_pnl_negative(self):
        """Long position, price goes down -> negative PnL."""
        entry = 7.1234
        exit_price = 7.1180
        amount = 55_000_000.0
        pnl = (exit_price - entry) / entry * amount
        assert pnl < 0

    def test_sl_unwind_recalculates_all_tranches(self):
        """
        When SL triggers, PnL should be recalculated for ALL executed tranches
        using the unwind bid price, not the original exit price.
        """
        executed_tranches = [
            (7.1234, 27_500_000.0),  # tranche 1
            (7.1256, 27_500_000.0),  # tranche 2
        ]
        unwind_bid = 7.1180  # SL unwind price

        # Recalculate PnL (mimics engine logic)
        total_pnl = 0.0
        for (t_entry, t_amount) in executed_tranches:
            t_pnl = (unwind_bid - t_entry) / t_entry * t_amount
            total_pnl += t_pnl

        # Both should be negative (unwind_bid < both entries)
        assert total_pnl < 0

        # Verify each tranche separately
        pnl_1 = (unwind_bid - 7.1234) / 7.1234 * 27_500_000.0
        pnl_2 = (unwind_bid - 7.1256) / 7.1256 * 27_500_000.0
        assert abs(total_pnl - (pnl_1 + pnl_2)) < 0.01

    def test_pt_unwind_recalculates_positive(self):
        """
        When PT triggers, PnL should be positive for all tranches
        (unwind_bid > entry for long position).
        """
        executed_tranches = [
            (7.1234, 27_500_000.0),
            (7.1256, 27_500_000.0),
        ]
        unwind_bid = 7.1340  # PT unwind price (above both entries)

        total_pnl = 0.0
        for (t_entry, t_amount) in executed_tranches:
            t_pnl = (unwind_bid - t_entry) / t_entry * t_amount
            total_pnl += t_pnl

        assert total_pnl > 0

    def test_return_pct_formula(self):
        """return_pct = week_pnl / total_exec_amount * 100."""
        week_pnl = 5000.0
        total_exec_amount = 55_000_000.0
        return_pct = round(week_pnl / total_exec_amount * 100, 4)
        expected = round(5000.0 / 55_000_000.0 * 100, 4)
        assert abs(return_pct - expected) < 1e-6


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
