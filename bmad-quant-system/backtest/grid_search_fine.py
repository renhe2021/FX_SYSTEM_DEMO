# -*- coding: utf-8 -*-
"""
Fine-Grained Grid Search (step=0.01) for Weekend Pre-Lock Strategy
===================================================================
Exhaustive search over prediction and confidence thresholds.
Uses real Bloomberg prices only.
"""

import pandas as pd
import numpy as np
from itertools import product
import os
import time
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNAL_FILE = os.path.join(BASE_DIR, 'data', 'raw', 'USD_SIGNAL_V3_processed.csv')
PRICE_FILE = os.path.join(BASE_DIR, 'data', 'raw', 'weekend_prices_bbg.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'backtest', 'results')


def load_data():
    """Load and prepare signal + price data, return weekly decisions."""
    signals = pd.read_csv(SIGNAL_FILE)
    signals['predict_time'] = pd.to_datetime(signals['predict_time'])

    if 'confidence' not in signals.columns:
        signals['confidence'] = np.where(
            signals['prediction'] >= 0.5,
            signals['confidence_1'],
            signals['confidence_0']
        )

    prices = pd.read_csv(PRICE_FILE).dropna(subset=['entry_price', 'exit_price'])
    entry_prices = dict(zip(prices['year_week'], prices['entry_price']))
    exit_prices = dict(zip(prices['year_week'], prices['exit_price']))
    valid_weeks = set(prices['year_week'])

    # Filter trading window: Friday 22:00 ~ Saturday 01:30
    sig = signals.copy()
    sig['hour'] = sig['predict_time'].dt.hour
    sig['minute'] = sig['predict_time'].dt.minute
    sig['td'] = sig['hour'] + sig['minute'] / 60
    sig['wd'] = sig['predict_time'].dt.weekday

    friday = (sig['wd'] == 4) & (sig['td'] >= 22.0)
    saturday = (sig['wd'] == 5) & (sig['td'] <= 1.5)
    sig = sig[friday | saturday].copy()

    # Only valid weeks
    sig = sig[sig['year_week'].isin(valid_weeks)]

    # Last signal per week
    weekly = sig.sort_values('predict_time').groupby('year_week').last().reset_index()

    # Pre-compute arrays for speed
    weeks = weekly['year_week'].values
    preds = weekly['prediction'].values
    confs = weekly['confidence'].values
    entry_arr = np.array([entry_prices.get(w, np.nan) for w in weeks])
    exit_arr = np.array([exit_prices.get(w, np.nan) for w in weeks])

    # PnL if we trade = (exit - entry) / entry * 55M
    trade_size = 55_000_000
    pnl_if_trade = (exit_arr - entry_arr) / entry_arr * trade_size

    n_weeks = len(weeks)
    print(f"Data loaded: {n_weeks} weeks with valid signals + prices")
    print(f"Prediction range: {preds.min():.4f} ~ {preds.max():.4f}")
    print(f"Confidence range: {confs.min():.4f} ~ {confs.max():.4f}")

    return weeks, preds, confs, pnl_if_trade, n_weeks


def run_grid_search(preds, confs, pnl_if_trade, n_weeks):
    """Vectorized grid search with step=0.01"""
    pred_thresholds = np.round(np.arange(0.40, 0.86, 0.01), 2)
    conf_thresholds = np.round(np.arange(0.00, 1.01, 0.01), 2)

    total = len(pred_thresholds) * len(conf_thresholds)
    print(f"\nGrid search: {len(pred_thresholds)} pred x {len(conf_thresholds)} conf = {total} combinations")

    results = []
    count = 0
    t0 = time.time()

    for pred_th in pred_thresholds:
        for conf_th in conf_thresholds:
            count += 1

            # Vectorized: which weeks do we trade?
            mask = (preds >= pred_th) & (confs > conf_th)
            pnl_series = np.where(mask, pnl_if_trade, 0.0)

            total_pnl = pnl_series.sum()
            num_trades = mask.sum()

            if num_trades == 0:
                results.append({
                    'pred_threshold': pred_th,
                    'conf_threshold': conf_th,
                    'total_pnl': 0,
                    'num_trades': 0,
                    'num_weeks': n_weeks,
                    'trade_freq': 0,
                    'win_rate': 0,
                    'avg_pnl_trade': 0,
                    'avg_pnl_week': 0,
                    'sharpe': 0,
                    'max_drawdown': 0,
                    'profit_factor': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'max_win': 0,
                    'max_loss': 0,
                })
                continue

            trade_pnls = pnl_series[mask]
            wins = trade_pnls[trade_pnls > 0]
            losses = trade_pnls[trade_pnls < 0]

            win_rate = len(wins) / num_trades if num_trades > 0 else 0

            # Sharpe (annualized, 52 weeks)
            std = pnl_series.std()
            sharpe = (pnl_series.mean() / std) * np.sqrt(52) if std > 0 else 0

            # Max drawdown
            cum = np.cumsum(pnl_series)
            running_max = np.maximum.accumulate(cum)
            dd = cum - running_max
            max_dd = dd.min()

            # Profit factor
            gross_win = wins.sum() if len(wins) > 0 else 0
            gross_loss = abs(losses.sum()) if len(losses) > 0 else 0
            pf = gross_win / gross_loss if gross_loss > 0 else (float('inf') if gross_win > 0 else 0)

            results.append({
                'pred_threshold': pred_th,
                'conf_threshold': conf_th,
                'total_pnl': round(total_pnl, 2),
                'num_trades': int(num_trades),
                'num_weeks': n_weeks,
                'trade_freq': round(num_trades / n_weeks, 4),
                'win_rate': round(win_rate, 4),
                'avg_pnl_trade': round(total_pnl / num_trades, 2),
                'avg_pnl_week': round(total_pnl / n_weeks, 2),
                'sharpe': round(sharpe, 4),
                'max_drawdown': round(max_dd, 2),
                'profit_factor': round(pf, 4) if pf != float('inf') else 9999.0,
                'avg_win': round(wins.mean(), 2) if len(wins) > 0 else 0,
                'avg_loss': round(losses.mean(), 2) if len(losses) > 0 else 0,
                'max_win': round(wins.max(), 2) if len(wins) > 0 else 0,
                'max_loss': round(losses.min(), 2) if len(losses) > 0 else 0,
            })

        if count % 500 == 0:
            elapsed = time.time() - t0
            print(f"  Progress: {count}/{total} ({count/total*100:.0f}%) - {elapsed:.1f}s")

    elapsed = time.time() - t0
    print(f"  Completed {total} combinations in {elapsed:.1f}s")

    return pd.DataFrame(results)


def print_top_results(df, sort_by='sharpe', top_n=20, min_trades=0):
    """Print top results sorted by given metric"""
    filtered = df[df['num_trades'] >= min_trades].copy()
    filtered = filtered.sort_values(sort_by, ascending=False)

    print(f"\n{'='*120}")
    print(f"TOP {top_n} by {sort_by.upper()} (min trades >= {min_trades})")
    print(f"{'='*120}")
    print(f"{'#':>3} {'Pred':>6} {'Conf':>6} {'PnL($)':>14} {'Sharpe':>8} {'WinRate':>8} "
          f"{'Trades':>7} {'AvgPnL/Tr':>12} {'MaxDD($)':>12} {'PF':>8} {'AvgWin':>12} {'AvgLoss':>12}")
    print("-" * 120)

    for idx, (_, row) in enumerate(filtered.head(top_n).iterrows()):
        print(f"{idx+1:>3} {row['pred_threshold']:>6.2f} {row['conf_threshold']:>6.2f} "
              f"${row['total_pnl']:>12,.0f} {row['sharpe']:>8.2f} {row['win_rate']*100:>7.1f}% "
              f"{row['num_trades']:>4}/{row['num_weeks']} "
              f"${row['avg_pnl_trade']:>10,.0f} ${row['max_drawdown']:>10,.0f} "
              f"{row['profit_factor']:>8.2f} ${row['avg_win']:>10,.0f} ${row['avg_loss']:>10,.0f}")


def main():
    print("=" * 70)
    print("FINE-GRAINED GRID SEARCH (step=0.01)")
    print("=" * 70)

    weeks, preds, confs, pnl_if_trade, n_weeks = load_data()

    # Run grid search
    results = run_grid_search(preds, confs, pnl_if_trade, n_weeks)

    # Save all results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, 'grid_search_fine_001.csv')
    results.to_csv(output_file, index=False)
    print(f"\nAll {len(results)} combinations saved to: {output_file}")

    # --- Reports ---

    # Top by Sharpe
    print_top_results(results, sort_by='sharpe', top_n=20, min_trades=0)

    # Top by Total PnL
    print_top_results(results, sort_by='total_pnl', top_n=20, min_trades=0)

    # Top by Win Rate
    print_top_results(results, sort_by='win_rate', top_n=20, min_trades=0)

    # Top by Profit Factor
    print_top_results(results, sort_by='profit_factor', top_n=20, min_trades=0)

    # --- Summary statistics ---
    valid = results[results['num_trades'] >= 1]
    profitable = valid[valid['total_pnl'] > 0]
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total combinations tested:    {len(results):,}")
    print(f"Combinations with trades:     {len(valid):,}")
    print(f"Profitable combinations:      {len(profitable):,} ({len(profitable)/len(valid)*100:.1f}%)")
    print(f"Best PnL:                     ${valid['total_pnl'].max():,.0f}")
    print(f"Best Sharpe:                  {valid['sharpe'].max():.2f}")
    print(f"Best Win Rate (5+ trades):    {results[results['num_trades']>=5]['win_rate'].max()*100:.1f}%")

    # --- Heatmap data: pivot for pred vs conf ---
    print(f"\n{'='*70}")
    print("PnL HEATMAP (sampled pred x conf)")
    print(f"{'='*70}")
    sample_preds = np.arange(0.45, 0.81, 0.05)
    sample_confs = np.arange(0.0, 0.91, 0.10)

    header = "Pred\\Conf"
    print(f"\n{header:>10}", end="")
    for c in sample_confs:
        print(f" {c:>10.2f}", end="")
    print()
    print("-" * (10 + 11 * len(sample_confs)))

    for p in sample_preds:
        print(f"{p:>10.2f}", end="")
        for c in sample_confs:
            row = results[(abs(results['pred_threshold'] - p) < 0.001) &
                          (abs(results['conf_threshold'] - c) < 0.001)]
            if len(row) > 0:
                pnl = row.iloc[0]['total_pnl']
                print(f" ${pnl:>8,.0f}", end="")
            else:
                print(f" {'N/A':>9}", end="")
        print()

    # Sharpe heatmap
    print(f"\n{'='*70}")
    print("SHARPE HEATMAP (sampled pred x conf)")
    print(f"{'='*70}")

    print(f"\n{header:>10}", end="")
    for c in sample_confs:
        print(f" {c:>8.2f}", end="")
    print()
    print("-" * (10 + 9 * len(sample_confs)))

    for p in sample_preds:
        print(f"{p:>10.2f}", end="")
        for c in sample_confs:
            row = results[(abs(results['pred_threshold'] - p) < 0.001) &
                          (abs(results['conf_threshold'] - c) < 0.001)]
            if len(row) > 0:
                s = row.iloc[0]['sharpe']
                print(f" {s:>8.2f}", end="")
            else:
                print(f" {'N/A':>8}", end="")
        print()

    return results


if __name__ == "__main__":
    results = main()
