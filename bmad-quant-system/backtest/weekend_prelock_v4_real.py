# -*- coding: utf-8 -*-
"""
Weekend Pre-Lock Price Strategy Backtest V4 (Real Bloomberg Prices)
====================================================================

Key Rules:
- Trading Window: Friday 22:30 - Saturday 01:30 (Beijing Time)
- Signal every 30min: 22:30, 23:00, 23:30, 00:00, 00:30, 01:00, 01:30
- Entry Price: mid = (bid + ask) / 2 at signal time (from weekend_prices_bbg.csv)
- Exit/Reference Price: Saturday 02:00 ASK price (from weekend_prices_bbg.csv)
- Trade Size: 55M USD per week
- Direction: LONG USDCNH when bullish signal, NO TRADE when bearish

Confidence Logic (V3):
- prediction >= 0.5 (bullish) -> use confidence_1
- prediction < 0.5 (bearish) -> use confidence_0

PnL = (exit_price - entry_price) / entry_price * trade_size_usd

Author: FX Strategy Team
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product
import warnings
import os

warnings.filterwarnings('ignore')

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNAL_FILE = os.path.join(BASE_DIR, 'data', 'raw', 'USD_SIGNAL_V3_processed.csv')
PRICE_FILE = os.path.join(BASE_DIR, 'data', 'raw', 'weekend_prices_bbg.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'backtest', 'results')


class WeekendPrelockBacktestV4:
    """
    Weekend Pre-Lock Strategy Backtester with REAL Bloomberg prices.
    No mock data allowed.
    """

    def __init__(
        self,
        signal_data_path: str = SIGNAL_FILE,
        price_data_path: str = PRICE_FILE,
        trade_size_usd: float = 55_000_000,
    ):
        self.trade_size_usd = trade_size_usd

        # Load signal data
        print("=" * 70)
        print("LOADING DATA")
        print("=" * 70)

        self.signals_df = pd.read_csv(signal_data_path)
        self.signals_df['predict_time'] = pd.to_datetime(self.signals_df['predict_time'])
        print(f"[Signal] Loaded {len(self.signals_df)} signals, "
              f"{self.signals_df['year_week'].nunique()} weeks")
        print(f"[Signal] Date range: {self.signals_df['predict_time'].min()} ~ "
              f"{self.signals_df['predict_time'].max()}")

        # Ensure confidence / direction columns exist
        if 'confidence' not in self.signals_df.columns:
            self.signals_df['confidence'] = np.where(
                self.signals_df['prediction'] >= 0.5,
                self.signals_df['confidence_1'],
                self.signals_df['confidence_0']
            )
        if 'direction' not in self.signals_df.columns:
            self.signals_df['direction'] = np.where(
                self.signals_df['prediction'] >= 0.5, 'BULLISH', 'BEARISH'
            )

        # Load REAL price data
        self.prices_df = pd.read_csv(price_data_path)
        valid_prices = self.prices_df.dropna(subset=['entry_price', 'exit_price'])
        print(f"[Price]  Loaded {len(self.prices_df)} weeks, "
              f"{len(valid_prices)} with valid prices")
        print(f"[Price]  Weeks: {valid_prices['year_week'].tolist()}")

        # Build price lookup
        self.entry_prices = dict(zip(valid_prices['year_week'], valid_prices['entry_price']))
        self.exit_prices = dict(zip(valid_prices['year_week'], valid_prices['exit_price']))

        # Intersect weeks
        signal_weeks = set(self.signals_df['year_week'].unique())
        price_weeks = set(valid_prices['year_week'].unique())
        self.valid_weeks = sorted(signal_weeks & price_weeks)
        print(f"\n[Match] {len(self.valid_weeks)} weeks with BOTH signal AND real price data")
        print(f"        {self.valid_weeks}")

    def filter_trading_window(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter signals within Friday 22:30 - Saturday 01:30 (Beijing Time)"""
        df = df.copy()
        df['hour'] = df['predict_time'].dt.hour
        df['minute'] = df['predict_time'].dt.minute
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        df['weekday'] = df['predict_time'].dt.weekday

        # Friday 22:30-23:59
        friday_mask = (df['weekday'] == 4) & (df['time_decimal'] >= 22.5)
        # Saturday 00:00-01:30
        saturday_mask = (df['weekday'] == 5) & (df['time_decimal'] <= 1.5)

        filtered = df[friday_mask | saturday_mask].copy()
        return filtered

    def get_weekly_last_signal(self, trading_signals: pd.DataFrame) -> pd.DataFrame:
        """Get the LAST signal per week within trading window"""
        return (trading_signals
                .sort_values('predict_time')
                .groupby('year_week')
                .last()
                .reset_index())

    def run_backtest(
        self,
        prediction_threshold: float = 0.5,
        confidence_threshold: float = 0.0,
        use_all_signals: bool = False,
    ) -> pd.DataFrame:
        """
        Run backtest with given thresholds.

        Trading Logic:
        - BUY (Long USDCNH) when:
            prediction >= prediction_threshold AND confidence > confidence_threshold
        - Otherwise: NO TRADE (PnL = 0)

        Parameters
        ----------
        prediction_threshold : float
            Minimum prediction to trigger LONG
        confidence_threshold : float
            Minimum confidence to trigger LONG
        use_all_signals : bool
            If True, use ALL signals (not just trading window).
            If False, only use signals in Friday 22:00 - Saturday 01:30.
        """
        if use_all_signals:
            working_signals = self.signals_df.copy()
        else:
            working_signals = self.filter_trading_window(self.signals_df)

        # Only keep valid weeks
        working_signals = working_signals[
            working_signals['year_week'].isin(self.valid_weeks)
        ]

        if len(working_signals) == 0:
            return pd.DataFrame()

        # Get last signal per week
        weekly_signals = self.get_weekly_last_signal(working_signals)

        results = []
        for _, row in weekly_signals.iterrows():
            week = row['year_week']
            if week not in self.entry_prices:
                continue

            prediction = row['prediction']
            confidence = row['confidence']
            entry_price = self.entry_prices[week]
            exit_price = self.exit_prices[week]

            # Decision: BUY only when bullish & confident
            should_buy = (
                prediction >= prediction_threshold
                and confidence > confidence_threshold
            )

            pnl = 0.0
            if should_buy:
                # Long USDCNH: profit when price goes up
                pnl = (exit_price - entry_price) / entry_price * self.trade_size_usd

            results.append({
                'year_week': week,
                'predict_time': row['predict_time'],
                'prediction': prediction,
                'confidence_0': row['confidence_0'],
                'confidence_1': row['confidence_1'],
                'confidence': confidence,
                'direction': row['direction'],
                'should_buy': should_buy,
                'entry_price': entry_price if should_buy else None,
                'exit_price': exit_price if should_buy else None,
                'price_move_pips': (exit_price - entry_price) * 10000,
                'pnl': pnl,
            })

        return pd.DataFrame(results)

    def calculate_metrics(self, results_df: pd.DataFrame) -> dict:
        """Calculate comprehensive performance metrics"""
        if len(results_df) == 0:
            return {k: 0 for k in [
                'total_pnl', 'num_trades', 'num_weeks', 'trade_frequency',
                'win_rate', 'avg_pnl_per_trade', 'avg_pnl_per_week',
                'sharpe_ratio', 'max_drawdown', 'profit_factor',
                'avg_win', 'avg_loss',
            ]}

        pnl_series = results_df['pnl']
        trades = results_df[results_df['should_buy']]

        total_pnl = pnl_series.sum()
        num_trades = len(trades)
        num_weeks = len(results_df)
        win_rate = (trades['pnl'] > 0).mean() if num_trades > 0 else 0

        # Sharpe (annualized, 52 weeks)
        sharpe = 0
        if pnl_series.std() > 0:
            sharpe = (pnl_series.mean() / pnl_series.std()) * np.sqrt(52)

        # Max Drawdown
        cum_pnl = pnl_series.cumsum()
        rolling_max = cum_pnl.cummax()
        drawdown = cum_pnl - rolling_max
        max_drawdown = drawdown.min()

        # Profit Factor
        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum() if num_trades > 0 else 0
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum()) if num_trades > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Average win / loss
        wins = trades[trades['pnl'] > 0]
        losses = trades[trades['pnl'] < 0]
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0

        return {
            'total_pnl': total_pnl,
            'num_trades': num_trades,
            'num_weeks': num_weeks,
            'trade_frequency': num_trades / num_weeks if num_weeks > 0 else 0,
            'win_rate': win_rate,
            'avg_pnl_per_trade': total_pnl / num_trades if num_trades > 0 else 0,
            'avg_pnl_per_week': total_pnl / num_weeks if num_weeks > 0 else 0,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
        }

    def grid_search(
        self,
        prediction_thresholds: list = None,
        confidence_thresholds: list = None,
        use_all_signals: bool = False,
        verbose: bool = True,
    ) -> pd.DataFrame:
        """Grid search for optimal thresholds"""
        if prediction_thresholds is None:
            prediction_thresholds = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
        if confidence_thresholds is None:
            confidence_thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

        total = len(prediction_thresholds) * len(confidence_thresholds)

        if verbose:
            print(f"\n{'='*70}")
            print(f"GRID SEARCH ({total} combinations)")
            print(f"{'='*70}")
            print(f"Prediction thresholds: {prediction_thresholds}")
            print(f"Confidence thresholds: {confidence_thresholds}")
            print(f"Use all signals: {use_all_signals}")

        results = []
        for pred_th, conf_th in product(prediction_thresholds, confidence_thresholds):
            bt_results = self.run_backtest(
                prediction_threshold=pred_th,
                confidence_threshold=conf_th,
                use_all_signals=use_all_signals,
            )
            metrics = self.calculate_metrics(bt_results)
            results.append({
                'prediction_threshold': pred_th,
                'confidence_threshold': conf_th,
                **metrics,
            })

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(
            ['sharpe_ratio', 'total_pnl'], ascending=[False, False]
        )

        if verbose:
            print(f"\n{'='*70}")
            print("TOP 10 PARAMETER COMBINATIONS (by Sharpe)")
            print(f"{'='*70}")
            for idx, (_, row) in enumerate(results_df.head(10).iterrows()):
                print(f"\n  #{idx+1}: pred>={row['prediction_threshold']:.2f}, "
                      f"conf>{row['confidence_threshold']:.2f}")
                print(f"      PnL=${row['total_pnl']:>12,.0f}  |  "
                      f"Sharpe={row['sharpe_ratio']:>6.2f}  |  "
                      f"WinRate={row['win_rate']*100:>5.1f}%  |  "
                      f"Trades={row['num_trades']:>2}/{row['num_weeks']} weeks  |  "
                      f"MaxDD=${row['max_drawdown']:>10,.0f}")

        return results_df

    def print_detailed_report(
        self,
        prediction_threshold: float = 0.5,
        confidence_threshold: float = 0.0,
        use_all_signals: bool = False,
    ):
        """Print a detailed backtest report"""
        results = self.run_backtest(
            prediction_threshold=prediction_threshold,
            confidence_threshold=confidence_threshold,
            use_all_signals=use_all_signals,
        )
        metrics = self.calculate_metrics(results)

        print(f"\n{'='*70}")
        print("DETAILED BACKTEST REPORT")
        print(f"{'='*70}")
        print(f"Parameters:")
        print(f"  Prediction threshold: >= {prediction_threshold}")
        print(f"  Confidence threshold: > {confidence_threshold}")
        print(f"  Trading window: {'All signals' if use_all_signals else 'Fri 22:00 ~ Sat 01:30'}")
        print(f"  Trade size: ${self.trade_size_usd:,.0f}")

        print(f"\n--- Performance Summary ---")
        print(f"  Total PnL:          ${metrics['total_pnl']:>12,.2f}")
        print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:>12.2f}")
        print(f"  Win Rate:           {metrics['win_rate']*100:>11.1f}%")
        print(f"  Profit Factor:      {metrics['profit_factor']:>12.2f}")
        print(f"  Trades:             {metrics['num_trades']:>12d} / {metrics['num_weeks']} weeks")
        print(f"  Trade Frequency:    {metrics['trade_frequency']*100:>11.1f}%")
        print(f"  Avg PnL/Trade:      ${metrics['avg_pnl_per_trade']:>12,.2f}")
        print(f"  Avg PnL/Week:       ${metrics['avg_pnl_per_week']:>12,.2f}")
        print(f"  Avg Win:            ${metrics['avg_win']:>12,.2f}")
        print(f"  Avg Loss:           ${metrics['avg_loss']:>12,.2f}")
        print(f"  Max Drawdown:       ${metrics['max_drawdown']:>12,.2f}")

        # Weekly detail
        print(f"\n--- Weekly Trade Detail ---")
        if len(results) > 0:
            print(f"{'Week':<10} {'Time':<20} {'Pred':>6} {'Conf':>6} {'Dir':<8} "
                  f"{'Trade':>5} {'Entry':>9} {'Exit':>9} {'Move(pips)':>10} {'PnL($)':>14}")
            print("-" * 110)

            cum_pnl = 0
            for _, row in results.iterrows():
                cum_pnl += row['pnl']
                trade_str = "BUY" if row['should_buy'] else "-"
                entry_str = f"{row['entry_price']:.4f}" if row['should_buy'] else "-"
                exit_str = f"{row['exit_price']:.4f}" if row['should_buy'] else "-"
                move_str = f"{row['price_move_pips']:>+.1f}" if row['should_buy'] else "-"
                pnl_str = f"${row['pnl']:>+12,.2f}" if row['should_buy'] else "$0"

                time_str = str(row['predict_time'])[:16] if pd.notna(row['predict_time']) else '-'

                print(f"{row['year_week']:<10} {time_str:<20} "
                      f"{row['prediction']:>6.3f} {row['confidence']:>6.3f} "
                      f"{row['direction']:<8} {trade_str:>5} "
                      f"{entry_str:>9} {exit_str:>9} {move_str:>10} {pnl_str:>14}")

            print("-" * 110)
            print(f"{'CUMULATIVE PnL':>88} ${cum_pnl:>+14,.2f}")

        return results, metrics


def main():
    print("=" * 70)
    print("WEEKEND PRE-LOCK STRATEGY BACKTEST V4 (REAL BLOOMBERG PRICES)")
    print("=" * 70)
    print()
    print("Trading Rules:")
    print("  - Signal Window: Friday 22:00 ~ Saturday 01:30 (Beijing)")
    print("  - Entry: mid = (bid + ask) / 2 at signal time")
    print("  - Exit:  Saturday 02:00 ASK price")
    print("  - Direction: LONG USDCNH only (BUY USD)")
    print("  - Decision: BUY when prediction >= threshold AND confidence > threshold")
    print("  - Trade Size: $55M per week")
    print("  - confidence = confidence_1 if prediction>=0.5 else confidence_0")
    print()

    # Initialize
    bt = WeekendPrelockBacktestV4()

    # ============================================
    # Part 1: Baseline - no filter (all signals trade)
    # ============================================
    print("\n" + "=" * 70)
    print("PART 1: BASELINE (pred>=0.5, conf>0.0 - all bullish signals trade)")
    print("=" * 70)
    bt.print_detailed_report(
        prediction_threshold=0.5,
        confidence_threshold=0.0,
    )

    # ============================================
    # Part 2: Grid Search
    # ============================================
    print("\n" + "=" * 70)
    print("PART 2: GRID SEARCH OPTIMIZATION")
    print("=" * 70)
    grid_results = bt.grid_search(
        prediction_thresholds=[0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80],
        confidence_thresholds=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    )

    # Save grid search results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    grid_file = os.path.join(OUTPUT_DIR, 'grid_search_v4_real.csv')
    grid_results.to_csv(grid_file, index=False)
    print(f"\nGrid search results saved to: {grid_file}")

    # ============================================
    # Part 3: Best parameters detail
    # ============================================
    best = grid_results.iloc[0]
    print("\n" + "=" * 70)
    print(f"PART 3: BEST PARAMETERS DETAIL")
    print(f"  pred >= {best['prediction_threshold']:.2f}, conf > {best['confidence_threshold']:.2f}")
    print("=" * 70)

    best_results, best_metrics = bt.print_detailed_report(
        prediction_threshold=best['prediction_threshold'],
        confidence_threshold=best['confidence_threshold'],
    )

    # Save detailed results
    detail_file = os.path.join(OUTPUT_DIR, 'best_trades_v4_real.csv')
    best_results.to_csv(detail_file, index=False)
    print(f"\nBest parameter trades saved to: {detail_file}")

    # ============================================
    # Part 4: Compare all signals vs trading window only
    # ============================================
    print("\n" + "=" * 70)
    print("PART 4: ALL SIGNALS vs TRADING WINDOW ONLY (pred>=0.5, conf>0.0)")
    print("=" * 70)

    print("\n--- Using ALL signals (last signal of the week) ---")
    bt.print_detailed_report(
        prediction_threshold=0.5,
        confidence_threshold=0.0,
        use_all_signals=True,
    )

    return grid_results, best_results


if __name__ == "__main__":
    grid_results, best_results = main()
