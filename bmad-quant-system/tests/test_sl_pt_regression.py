"""
Regression Tests for run_single_tranche with SL/PT scenarios.

Uses a fully mocked BacktestEngine with synthetic signals + intraday data.
Each test scenario is self-contained and easy to modify.

HOW TO ADD A NEW TEST:
  1. Copy an existing test method
  2. Modify signals (predict_time, prediction, confidence)
  3. Modify intraday bid/ask data
  4. Modify SL/PT thresholds
  5. Update expected assertions

Key parameters you can tweak:
  - TRADE_SIZE: total USD notional per week
  - pred_th / conf_th: signal thresholds
  - stop_loss_bps / profit_taking_bps: risk thresholds
  - Intraday bid/ask prices: controls when SL/PT triggers
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import pytest
import yaml
import copy


# ---------------------------------------------------------------------------
# Shared setup: build a fully-functional engine from synthetic data
# ---------------------------------------------------------------------------
TRADE_SIZE = 55_000_000.0
CONFIG_PATH = ROOT / "backtest" / "dashboard" / "config.yaml"


def _load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _build_engine(
    signal_rows,
    intraday_bids,
    intraday_asks,
    intraday_start="2025-08-29 22:00:00",
    intraday_freq="1min",
    exit_price=None,
    year_week="2025_34",
):
    """
    Build a BacktestEngine with all internal state pre-populated.

    Args:
        signal_rows: list of dicts with keys:
            predict_time, prediction, confidence, confidence_1, confidence_0, year_week
        intraday_bids: list of bid prices (one per bar)
        intraday_asks: list of ask prices (one per bar)
        intraday_start: first bar timestamp
        intraday_freq: bar frequency
        exit_price: Saturday 02:00 exit price (ASK). If None, uses last ask.
        year_week: the week key

    Returns:
        BacktestEngine instance ready to call run_single_tranche()
    """
    from backtest.dashboard.app import BacktestEngine

    config = _load_config()
    config['trading']['trade_size_usd'] = TRADE_SIZE
    engine = BacktestEngine(config)

    # ----- Build signals -----
    sig_df = pd.DataFrame(signal_rows)
    sig_df['predict_time'] = pd.to_datetime(sig_df['predict_time'])
    sig_df['year_week'] = year_week
    if 'direction' not in sig_df.columns:
        sig_df['direction'] = sig_df['prediction'].apply(lambda p: 'BULLISH' if p >= 0.5 else 'BEARISH')

    # weekly_signals: one row per week (last signal)
    last_sig = sig_df.iloc[-1:].copy()
    last_sig = last_sig.reset_index(drop=True)
    engine.weekly_signals = last_sig

    # _weekly_all_signals: all signals for this week
    engine._weekly_all_signals = {year_week: sig_df}

    # Numpy arrays (one element per week)
    engine._weeks = np.array([year_week])
    engine._preds = np.array([float(last_sig['prediction'].iloc[0])])
    engine._confs = np.array([float(last_sig['confidence'].iloc[0])])

    # ----- Build intraday data -----
    n_bars = len(intraday_bids)
    intraday_ts = pd.date_range(intraday_start, periods=n_bars, freq=intraday_freq)
    engine._intraday_ts_index = intraday_ts.astype(np.int64).values
    engine._intraday_bid_arr = np.array(intraday_bids, dtype=np.float64)
    engine._intraday_ask_arr = np.array(intraday_asks, dtype=np.float64)

    # ----- Build entry/exit maps -----
    # Entry price per signal is looked up from intraday ASK via _get_entry_price_at_time
    # Exit price: Saturday 02:00
    if exit_price is None:
        exit_price = float(intraday_asks[-1])
    engine._entry = np.array([float(intraday_asks[0])])  # fallback
    engine._exit = np.array([exit_price])
    engine.entry_map = {year_week: float(intraday_asks[0])}
    engine.exit_map = {year_week: exit_price}

    # Mark as ready
    engine.signals = sig_df
    engine.prices = pd.DataFrame({'year_week': [year_week], 'entry_price': [intraday_asks[0]], 'exit_price': [exit_price]})
    engine.valid_weeks = [year_week]

    return engine


# ---------------------------------------------------------------------------
# Helper: generate 1-min intraday bars from a price path
# ---------------------------------------------------------------------------
def make_intraday(start_time, n_minutes, base_bid, bid_offsets, spread=0.0003):
    """
    Generate synthetic intraday data.

    Args:
        start_time: first bar time
        n_minutes: number of bars
        base_bid: base bid price
        bid_offsets: list of offsets from base_bid for each minute,
                     OR a single callable(minute_idx) -> offset
        spread: bid-ask spread

    Returns:
        (bids, asks) lists
    """
    if callable(bid_offsets):
        bids = [base_bid + bid_offsets(i) for i in range(n_minutes)]
    else:
        assert len(bid_offsets) == n_minutes
        bids = [base_bid + o for o in bid_offsets]
    asks = [b + spread for b in bids]
    return bids, asks


# ===========================================================================
#  SCENARIO 1: Normal exit, no SL/PT triggers
# ===========================================================================
class TestNormalExit:
    """
    3 signals, all executed, bid stays in range, no SL/PT triggers.
    Expected: PnL = sum of (exit - entry_i) / entry_i * amount_i
    """

    def _make_scenario(self):
        # Signals: Fri 22:30, 23:00, 23:30 — all BULLISH with high pred/conf
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
            {'predict_time': '2025-08-29 23:30:00', 'prediction': 0.60, 'confidence': 0.70,
             'confidence_1': 0.70, 'confidence_0': 0.30},
        ]

        # Intraday: 22:00 to 02:00 next day (480 min), bid ~7.1230, slight uptrend
        n_min = 480
        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=7.1230,
            bid_offsets=lambda i: i * 0.00001,  # very gentle rise
        )
        exit_ask = asks[-1]

        engine = _build_engine(signals, bids, asks, exit_price=exit_ask)
        return engine, signals, bids, asks, exit_ask

    def test_no_sl_pt_pnl_positive(self):
        """Without SL/PT, a rising market should give positive PnL."""
        engine, signals, bids, asks, exit_ask = self._make_scenario()

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=None, profit_taking_bps=None,
        )

        assert result is not None
        trade = result['trades'][0]
        assert trade['should_buy'] is True
        assert trade['n_executed'] == 3
        assert trade['pnl'] > 0  # uptrend -> positive
        assert trade['stop_loss_triggered'] is False
        assert trade['profit_taking_triggered'] is False

    def test_with_sl_pt_no_trigger(self):
        """With loose SL/PT thresholds, neither should trigger on calm data."""
        engine, _, _, _, _ = self._make_scenario()

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=50.0,  # 50 bps is very loose
            profit_taking_bps=50.0,
        )

        trade = result['trades'][0]
        assert trade['stop_loss_triggered'] is False
        assert trade['profit_taking_triggered'] is False

    def test_tranche_details_correct(self):
        """Verify tranche detail counts and actions."""
        engine, signals, _, _, _ = self._make_scenario()

        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)
        detail = result['tranche_details'][0]

        assert detail['n_signals'] == 3
        assert len(detail['tranches']) == 3
        for td in detail['tranches']:
            assert td['action'] == 'EXECUTE'
            assert td['amount_usd'] > 0

    def test_equal_weight_distribution(self):
        """3 equal-weight tranches should each get ~1/3 of notional."""
        engine, _, _, _, _ = self._make_scenario()
        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)
        detail = result['tranche_details'][0]

        for td in detail['tranches']:
            assert abs(td['available_weight'] - 1.0 / 3) < 0.01
            expected_amount = TRADE_SIZE / 3
            assert abs(td['amount_usd'] - expected_amount) < 100


# ===========================================================================
#  SCENARIO 2: Stop Loss triggers on first tranche
# ===========================================================================
class TestStopLossTrigger:
    """
    3 signals, slot 1 executes, then SL triggers before slot 2.
    Expected: slot 1 = EXECUTE -> SL UNWIND, slots 2-3 = STOPPED (SL)
    """

    def _make_scenario(self, sl_bps=5.0):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
            {'predict_time': '2025-08-29 23:30:00', 'prediction': 0.60, 'confidence': 0.70,
             'confidence_1': 0.70, 'confidence_0': 0.30},
        ]

        # Entry at 22:30: ask ~7.1233
        # Bid drops sharply at 22:45 (minute 45 from 22:00 start)
        n_min = 480
        entry_bid = 7.1230

        def bid_path(i):
            if i <= 30:  # 22:00-22:30: stable
                return 0
            elif i <= 45:  # 22:30-22:45: drop
                return -(i - 30) * 0.0004  # drops fast
            else:  # 22:45+: stays low
                return -0.0060  # ~60 pips below entry

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=entry_bid,
            bid_offsets=bid_path,
        )
        exit_ask = asks[-1]

        engine = _build_engine(signals, bids, asks, exit_price=exit_ask)
        return engine, signals, bids, asks, sl_bps

    def test_sl_triggers_and_stops_night(self):
        """SL triggers after slot 1, remaining slots should be STOPPED."""
        engine, _, _, _, sl_bps = self._make_scenario(sl_bps=5.0)

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=sl_bps,
        )

        trade = result['trades'][0]
        assert trade['stop_loss_triggered'] is True
        assert trade['profit_taking_triggered'] is False
        assert trade['pnl'] < 0  # loss

        detail = result['tranche_details'][0]
        actions = [td['action'] for td in detail['tranches']]
        # First slot should be EXECUTE -> SL UNWIND
        assert 'SL UNWIND' in actions[0]
        # Remaining slots should be STOPPED
        for action in actions[1:]:
            assert action == 'STOPPED (SL)'

    def test_sl_info_fields(self):
        """Verify stop_loss_info has correct fields."""
        engine, _, _, _, sl_bps = self._make_scenario(sl_bps=5.0)

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=sl_bps,
        )

        trade = result['trades'][0]
        sl_info = trade['stop_loss']
        assert sl_info['triggered'] is True
        assert sl_info['loss_bps'] >= sl_bps
        assert sl_info['threshold_bps'] == sl_bps
        assert sl_info['unwind_bid'] < sl_info['avg_entry']

    def test_sl_pnl_bounded_by_threshold(self):
        """SL loss in bps should be approximately equal to (or slightly above) threshold."""
        engine, _, _, _, sl_bps = self._make_scenario(sl_bps=5.0)

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=sl_bps,
        )

        sl_info = result['trades'][0]['stop_loss']
        # Loss should be >= threshold but not wildly more (max 1 bar gap = ~0.4 bps in our data)
        assert sl_info['loss_bps'] >= sl_bps
        assert sl_info['loss_bps'] < sl_bps + 5.0  # reasonable upper bound

    def test_loose_sl_no_trigger(self):
        """With a very loose SL (100 bps), it should NOT trigger on modest drop."""
        engine, _, _, _, _ = self._make_scenario()

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=100.0,  # 100 bps = 1%, very loose
        )

        trade = result['trades'][0]
        assert trade['stop_loss_triggered'] is False


# ===========================================================================
#  SCENARIO 3: Profit Taking triggers
# ===========================================================================
class TestProfitTakingTrigger:
    """
    3 signals, bid rises sharply after slot 1, PT triggers before slot 2.
    """

    def _make_scenario(self, pt_bps=8.0):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
            {'predict_time': '2025-08-29 23:30:00', 'prediction': 0.60, 'confidence': 0.70,
             'confidence_1': 0.70, 'confidence_0': 0.30},
        ]

        n_min = 480
        entry_bid = 7.1230

        def bid_path(i):
            if i <= 30:  # 22:00-22:30: stable
                return 0
            elif i <= 45:  # 22:30-22:45: sharp rise
                return (i - 30) * 0.0005  # rises fast
            else:
                return 0.0075  # stays high

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=entry_bid,
            bid_offsets=bid_path,
        )
        exit_ask = asks[-1]
        engine = _build_engine(signals, bids, asks, exit_price=exit_ask)
        return engine, pt_bps

    def test_pt_triggers_and_stops_night(self):
        """PT triggers after slot 1, remaining slots STOPPED (PT)."""
        engine, pt_bps = self._make_scenario(pt_bps=8.0)

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            profit_taking_bps=pt_bps,
        )

        trade = result['trades'][0]
        assert trade['profit_taking_triggered'] is True
        assert trade['stop_loss_triggered'] is False
        assert trade['pnl'] > 0  # profit

        detail = result['tranche_details'][0]
        actions = [td['action'] for td in detail['tranches']]
        assert 'PT UNWIND' in actions[0]
        for action in actions[1:]:
            assert action == 'STOPPED (PT)'

    def test_pt_info_fields(self):
        """Verify profit_taking_info has correct fields."""
        engine, pt_bps = self._make_scenario(pt_bps=8.0)

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            profit_taking_bps=pt_bps,
        )

        pt_info = result['trades'][0]['profit_taking']
        assert pt_info['triggered'] is True
        assert pt_info['gain_bps'] >= pt_bps
        assert pt_info['threshold_bps'] == pt_bps
        assert pt_info['unwind_bid'] > pt_info['avg_entry']


# ===========================================================================
#  SCENARIO 4: SL triggers during a SKIP slot
# ===========================================================================
class TestSlDuringSkipSlot:
    """
    3 signals: slot 1 EXECUTE, slot 2 SKIP (low confidence), slot 3 pending.
    SL triggers during slot 2's monitoring window.
    """

    def _make_scenario(self):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            # Slot 2: below confidence threshold (will be SKIPped if conf_th=0.5)
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.30,
             'confidence_1': 0.30, 'confidence_0': 0.70},
            {'predict_time': '2025-08-29 23:30:00', 'prediction': 0.60, 'confidence': 0.70,
             'confidence_1': 0.70, 'confidence_0': 0.30},
        ]

        n_min = 480
        entry_bid = 7.1230

        def bid_path(i):
            if i <= 30:  # 22:00-22:30: stable
                return 0
            elif i <= 60:  # 22:30-23:00: stable (slot 1 window)
                return -0.0001
            elif i <= 75:  # 23:00-23:15: sharp drop (during SKIP slot 2 window)
                return -(i - 60) * 0.0004
            else:
                return -0.0060

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=entry_bid,
            bid_offsets=bid_path,
        )
        exit_ask = asks[-1]
        engine = _build_engine(signals, bids, asks, exit_price=exit_ask)
        return engine

    def test_sl_triggers_during_skip_slot(self):
        """SL should still be monitored even when a slot is SKIPped."""
        engine = self._make_scenario()

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.5,  # conf_th=0.5 makes slot 2 a SKIP
            stop_loss_bps=5.0,
        )

        trade = result['trades'][0]
        assert trade['stop_loss_triggered'] is True

        detail = result['tranche_details'][0]
        actions = [td['action'] for td in detail['tranches']]
        # Slot 1: EXECUTE -> SL UNWIND (relabeled after SL during slot 2)
        assert 'SL UNWIND' in actions[0]
        # Slot 2 should be SKIP (it was already appended before SL triggers)
        # But subsequent processing relabels earlier EXECUTEs
        # Slot 3: STOPPED (SL)
        assert 'STOPPED (SL)' in actions[2]


# ===========================================================================
#  SCENARIO 5: Multiple tranches before SL
# ===========================================================================
class TestMultipleTranchesBeforeSl:
    """
    3 signals, slots 1 and 2 execute, then SL triggers during slot 3's window.
    Weighted avg entry should be used for SL check.
    All executed tranches' PnL recalculated at unwind bid.
    """

    def _make_scenario(self):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
            {'predict_time': '2025-08-29 23:30:00', 'prediction': 0.60, 'confidence': 0.70,
             'confidence_1': 0.70, 'confidence_0': 0.30},
        ]

        n_min = 480
        entry_bid = 7.1230

        def bid_path(i):
            if i <= 60:  # 22:00-23:00: stable
                return 0
            elif i <= 90:  # 23:00-23:30: still OK
                return -0.0001
            elif i <= 105:  # 23:30-23:45: sharp drop
                return -(i - 90) * 0.0004
            else:
                return -0.0060

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=entry_bid,
            bid_offsets=bid_path,
        )
        exit_ask = asks[-1]
        engine = _build_engine(signals, bids, asks, exit_price=exit_ask)
        return engine

    def test_multiple_tranches_then_sl(self):
        """All 3 slots execute, SL triggers after slot 3 (in slot 3's post-check window).
        All executed tranches should be relabeled to SL UNWIND."""
        engine = self._make_scenario()

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=5.0,
        )

        trade = result['trades'][0]
        assert trade['stop_loss_triggered'] is True
        # All 3 slots execute before SL triggers (drop happens after slot 3 at 23:30)
        assert trade['n_executed'] == 3

        detail = result['tranche_details'][0]
        actions = [td['action'] for td in detail['tranches']]
        # All 3 executed tranches should be relabeled to SL UNWIND
        sl_unwind_count = sum(1 for a in actions if 'SL UNWIND' in a)
        assert sl_unwind_count == 3

    def test_pnl_recalculated_for_all_tranches(self):
        """Total PnL should reflect unwind_bid for ALL executed tranches."""
        engine = self._make_scenario()

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=5.0,
        )

        trade = result['trades'][0]
        sl_info = trade['stop_loss']
        unwind_bid = sl_info['unwind_bid']

        # Manually compute expected PnL
        detail = result['tranche_details'][0]
        expected_pnl = 0.0
        for td in detail['tranches']:
            if 'SL UNWIND' in td['action']:
                expected_pnl += td['pnl']

        assert abs(trade['pnl'] - expected_pnl) < 1.0  # within $1 rounding

    def test_weighted_avg_entry_used(self):
        """SL should use weighted avg of both tranches, not just the last one."""
        engine = self._make_scenario()

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=5.0,
        )

        sl_info = result['trades'][0]['stop_loss']
        avg_entry = sl_info['avg_entry']

        # avg_entry should be between the two entry prices
        detail = result['tranche_details'][0]
        entries = [td['entry_price'] for td in detail['tranches'] if td['entry_price'] is not None]
        if len(entries) >= 2:
            assert min(entries) <= avg_entry <= max(entries)


# ===========================================================================
#  SCENARIO 6: Weight carry-over from SKIP slots
# ===========================================================================
class TestWeightCarryOver:
    """
    3 signals: slot 1 SKIP (low pred), slot 2 EXECUTE (gets slot 1 weight too), slot 3 EXECUTE.
    """

    def _make_scenario(self):
        signals = [
            # Slot 1: below prediction threshold
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.40, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
            {'predict_time': '2025-08-29 23:30:00', 'prediction': 0.60, 'confidence': 0.70,
             'confidence_1': 0.70, 'confidence_0': 0.30},
        ]

        n_min = 480
        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=7.1230,
            bid_offsets=lambda i: i * 0.00001,  # gentle rise
        )
        exit_ask = asks[-1]
        engine = _build_engine(signals, bids, asks, exit_price=exit_ask)
        return engine

    def test_skip_then_execute_carries_weight(self):
        """Slot 2 should execute with 2/3 of total notional (its own + slot 1's)."""
        engine = self._make_scenario()

        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)
        detail = result['tranche_details'][0]

        tranches = detail['tranches']
        assert tranches[0]['action'] == 'SKIP'
        assert tranches[1]['action'] == 'EXECUTE'
        assert tranches[2]['action'] == 'EXECUTE'

        # Slot 2 available_weight should be ~2/3
        assert abs(tranches[1]['available_weight'] - 2.0 / 3) < 0.01
        expected_amount_2 = TRADE_SIZE * 2 / 3
        assert abs(tranches[1]['amount_usd'] - expected_amount_2) < 100

        # Slot 3 available_weight should be ~1/3
        assert abs(tranches[2]['available_weight'] - 1.0 / 3) < 0.01

    def test_total_executed_is_full_notional(self):
        """Even with SKIPs, total executed amount should equal trade_size."""
        engine = self._make_scenario()

        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)
        detail = result['tranche_details'][0]

        total = sum(td['amount_usd'] for td in detail['tranches'])
        assert abs(total - TRADE_SIZE) < 100


# ===========================================================================
#  SCENARIO 7: All signals SKIPped (no trade)
# ===========================================================================
class TestAllSkipped:
    """All signals below threshold -> no trade, PnL = 0."""

    def test_no_execution(self):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.30, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.35, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
        ]

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', 480, base_bid=7.1230,
            bid_offsets=lambda i: 0,
        )
        engine = _build_engine(signals, bids, asks)

        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)
        trade = result['trades'][0]
        assert trade['should_buy'] is False
        assert trade['pnl'] == 0.0
        assert trade['n_executed'] == 0


# ===========================================================================
#  SCENARIO 8: Fixed tranche_size mode
# ===========================================================================
class TestFixedTrancheSize:
    """Use tranche_size parameter instead of equal weight."""

    def test_fixed_size_amounts(self):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
        ]

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', 480, base_bid=7.1230,
            bid_offsets=lambda i: i * 0.00001,
        )
        engine = _build_engine(signals, bids, asks)

        tranche_size = 20_000_000.0
        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            tranche_size=tranche_size,
        )

        detail = result['tranche_details'][0]
        for td in detail['tranches']:
            if td['action'] == 'EXECUTE':
                assert abs(td['amount_usd'] - tranche_size) < 100


# ===========================================================================
#  SCENARIO 9: Metrics computation validation
# ===========================================================================
class TestMetrics:
    """Verify aggregate metrics formulas."""

    def _make_two_week_engine(self):
        """Build engine with 2 weeks of data for metric testing."""
        from backtest.dashboard.app import BacktestEngine

        config = _load_config()
        config['trading']['trade_size_usd'] = TRADE_SIZE
        engine = BacktestEngine(config)

        # Week 1: bullish, uptrend
        week1_signals = pd.DataFrame([
            {'predict_time': pd.Timestamp('2025-08-29 22:30:00'), 'prediction': 0.70,
             'confidence': 0.80, 'confidence_1': 0.80, 'confidence_0': 0.20,
             'year_week': '2025_34', 'direction': 'BULLISH'},
        ])
        # Week 2: bullish, downtrend
        week2_signals = pd.DataFrame([
            {'predict_time': pd.Timestamp('2025-09-05 22:30:00'), 'prediction': 0.65,
             'confidence': 0.75, 'confidence_1': 0.75, 'confidence_0': 0.25,
             'year_week': '2025_35', 'direction': 'BULLISH'},
        ])

        all_signals = pd.concat([week1_signals, week2_signals], ignore_index=True)
        engine.signals = all_signals

        # Weekly signals (last per week)
        engine.weekly_signals = pd.concat([
            week1_signals.iloc[-1:].reset_index(drop=True),
            week2_signals.iloc[-1:].reset_index(drop=True),
        ], ignore_index=True)

        engine._weekly_all_signals = {
            '2025_34': week1_signals,
            '2025_35': week2_signals,
        }

        engine._weeks = np.array(['2025_34', '2025_35'])
        engine._preds = np.array([0.70, 0.65])
        engine._confs = np.array([0.80, 0.75])

        # Intraday for week 1
        n_min = 480
        bids1, asks1 = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=7.1230,
            bid_offsets=lambda i: i * 0.00002,
        )
        # Intraday for week 2
        bids2, asks2 = make_intraday(
            '2025-09-05 22:00:00', n_min, base_bid=7.1230,
            bid_offsets=lambda i: -i * 0.00001,
        )

        all_bids = bids1 + bids2
        all_asks = asks1 + asks2
        all_ts = list(pd.date_range('2025-08-29 22:00:00', periods=n_min, freq='1min')) + \
                 list(pd.date_range('2025-09-05 22:00:00', periods=n_min, freq='1min'))
        all_ts = pd.DatetimeIndex(all_ts)

        engine._intraday_ts_index = all_ts.astype(np.int64).values
        engine._intraday_bid_arr = np.array(all_bids, dtype=np.float64)
        engine._intraday_ask_arr = np.array(all_asks, dtype=np.float64)

        engine._entry = np.array([asks1[30], asks2[30]])  # entry at min 30 (22:30)
        engine._exit = np.array([asks1[-1], asks2[-1]])

        engine.entry_map = {'2025_34': asks1[30], '2025_35': asks2[30]}
        engine.exit_map = {'2025_34': asks1[-1], '2025_35': asks2[-1]}

        engine.prices = pd.DataFrame({
            'year_week': ['2025_34', '2025_35'],
            'entry_price': [asks1[30], asks2[30]],
            'exit_price': [asks1[-1], asks2[-1]],
        })
        engine.valid_weeks = ['2025_34', '2025_35']

        return engine

    def test_total_pnl_is_sum(self):
        engine = self._make_two_week_engine()
        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)

        pnls = [t['pnl'] for t in result['trades']]
        assert abs(result['metrics']['total_pnl'] - sum(pnls)) < 1.0

    def test_win_rate(self):
        engine = self._make_two_week_engine()
        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)

        traded = [t for t in result['trades'] if t['should_buy']]
        wins = sum(1 for t in traded if t['pnl'] > 0)
        expected_wr = wins / len(traded) if traded else 0
        assert abs(result['metrics']['win_rate'] - expected_wr) < 0.01

    def test_cumulative_pnl(self):
        engine = self._make_two_week_engine()
        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)

        cum = 0.0
        for t in result['trades']:
            cum += t['pnl']
            assert abs(t['cum_pnl'] - cum) < 1.0

    def test_max_drawdown_non_positive(self):
        engine = self._make_two_week_engine()
        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)
        assert result['metrics']['max_drawdown'] <= 0


# ===========================================================================
#  SCENARIO 10: Edge case — single signal week
# ===========================================================================
class TestSingleSignalWeek:
    """Week with only 1 signal slot."""

    def test_single_slot_execute(self):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
        ]

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', 480, base_bid=7.1230,
            bid_offsets=lambda i: i * 0.00001,
        )
        engine = _build_engine(signals, bids, asks)

        result = engine.run_single_tranche(pred_th=0.5, conf_th=0.0)
        trade = result['trades'][0]
        assert trade['should_buy'] is True
        assert trade['n_executed'] == 1
        assert trade['executed_pct'] == 100.0

    def test_single_slot_sl(self):
        """Even with 1 slot, SL should work."""
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
        ]

        n_min = 480
        def bid_path(i):
            if i <= 30:
                return 0
            elif i <= 45:
                return -(i - 30) * 0.0005
            else:
                return -0.0075
        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=7.1230,
            bid_offsets=bid_path,
        )
        engine = _build_engine(signals, bids, asks)

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=5.0,
        )
        trade = result['trades'][0]
        assert trade['stop_loss_triggered'] is True
        assert trade['pnl'] < 0


# ===========================================================================
#  SCENARIO 11: PT and SL both active, PT wins
# ===========================================================================
class TestPtWinsOverSl:
    """Both thresholds active, bid rises -> PT triggers first."""

    def test_pt_wins_when_bid_rises(self):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
            {'predict_time': '2025-08-29 23:00:00', 'prediction': 0.65, 'confidence': 0.75,
             'confidence_1': 0.75, 'confidence_0': 0.25},
        ]

        n_min = 480
        def bid_path(i):
            if i <= 30:
                return 0
            else:
                return (i - 30) * 0.00003  # steady rise

        bids, asks = make_intraday(
            '2025-08-29 22:00:00', n_min, base_bid=7.1230,
            bid_offsets=bid_path,
        )
        engine = _build_engine(signals, bids, asks)

        result = engine.run_single_tranche(
            pred_th=0.5, conf_th=0.0,
            stop_loss_bps=10.0,
            profit_taking_bps=5.0,  # tight PT
        )

        trade = result['trades'][0]
        assert trade['profit_taking_triggered'] is True
        assert trade['stop_loss_triggered'] is False
        assert trade['pnl'] > 0


# ===========================================================================
#  SCENARIO 12: Regression — verify params are recorded correctly
# ===========================================================================
class TestParamsRecording:
    """Verify that result['params'] matches what was passed in."""

    def test_params_recorded(self):
        signals = [
            {'predict_time': '2025-08-29 22:30:00', 'prediction': 0.70, 'confidence': 0.80,
             'confidence_1': 0.80, 'confidence_0': 0.20},
        ]
        bids, asks = make_intraday('2025-08-29 22:00:00', 480, 7.1230, lambda i: 0)
        engine = _build_engine(signals, bids, asks)

        result = engine.run_single_tranche(
            pred_th=0.55, conf_th=0.10,
            tranche_size=20_000_000.0,
            stop_loss_bps=7.5,
            profit_taking_bps=12.0,
        )

        params = result['params']
        assert params['pred_threshold'] == 0.55
        assert params['conf_threshold'] == 0.10
        assert params['tranche_size'] == 20_000_000.0
        assert params['stop_loss_bps'] == 7.5
        assert params['profit_taking_bps'] == 12.0
        assert params['execution_mode'] == 'tranche'
        assert params['weighting'] == 'fixed_size'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
