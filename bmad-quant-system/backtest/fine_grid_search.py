# -*- coding: utf-8 -*-
"""
Weekend Pre-Lock Strategy - Fine-Grained Grid Search
====================================================

Objective: Maximize Total PnL
Grid: 0.01 granularity for both prediction and confidence thresholds

Author: FX Strategy Team
"""

import pandas as pd
import numpy as np
from datetime import datetime
from itertools import product
import warnings
warnings.filterwarnings('ignore')


class FineTuneBacktest:
    """Fine-grained Grid Search for Maximum PnL"""
    
    def __init__(self, signal_data_path: str, trade_size_usd: float = 55_000_000):
        self.trade_size_usd = trade_size_usd
        
        # Load and process data
        print("Loading signal data...")
        self.signals_df = pd.read_csv(signal_data_path)
        self.signals_df['predict_time'] = pd.to_datetime(self.signals_df['predict_time'])
        
        # Confidence logic: pred >= 0.5 -> use conf_1, pred < 0.5 -> use conf_0
        self.signals_df['confidence'] = np.where(
            self.signals_df['prediction'] >= 0.5,
            self.signals_df['confidence_1'],
            self.signals_df['confidence_0']
        )
        
        print(f"Loaded {len(self.signals_df)} signals")
        
        # Generate mock prices
        self.signals_df['year_week'] = self.signals_df['predict_time'].dt.strftime('%Y_%W')
        unique_weeks = self.signals_df['year_week'].unique()
        
        np.random.seed(42)
        base_price = 7.2500
        self.entry_prices = {}
        self.exit_prices = {}
        
        for week in unique_weeks:
            entry_price = base_price + np.random.uniform(-0.02, 0.02)
            self.entry_prices[week] = entry_price
            price_move = np.random.normal(0, 0.003)
            self.exit_prices[week] = entry_price * (1 + price_move)
            base_price = self.exit_prices[week]
        
        # Pre-filter trading window signals
        self._prepare_weekly_signals()
        
    def _prepare_weekly_signals(self):
        """Pre-compute weekly signals for faster grid search"""
        df = self.signals_df.copy()
        df['hour'] = df['predict_time'].dt.hour
        df['minute'] = df['predict_time'].dt.minute
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        df['weekday'] = df['predict_time'].dt.weekday
        
        # Friday 22:00-23:59 or Saturday 00:00-01:30
        friday_mask = (df['weekday'] == 4) & (df['time_decimal'] >= 22.0)
        saturday_mask = (df['weekday'] == 5) & (df['time_decimal'] <= 1.5)
        
        trading_signals = df[friday_mask | saturday_mask].copy()
        
        # Get last signal per week
        self.weekly_signals = trading_signals.sort_values('predict_time').groupby('year_week').last().reset_index()
        print(f"Weekly signals in trading window: {len(self.weekly_signals)}")
        
    def run_backtest(self, pred_th: float, conf_th: float) -> dict:
        """Fast backtest for grid search"""
        total_pnl = 0
        num_trades = 0
        pnl_list = []
        
        for _, row in self.weekly_signals.iterrows():
            week = row['year_week']
            if week not in self.entry_prices:
                pnl_list.append(0)
                continue
                
            should_buy = (row['prediction'] >= pred_th) and (row['confidence'] > conf_th)
            
            if should_buy:
                entry = self.entry_prices[week]
                exit_p = self.exit_prices[week]
                pnl = (exit_p - entry) / entry * self.trade_size_usd
                total_pnl += pnl
                num_trades += 1
                pnl_list.append(pnl)
            else:
                pnl_list.append(0)
        
        # Calculate metrics
        pnl_arr = np.array(pnl_list)
        sharpe = (pnl_arr.mean() / pnl_arr.std() * np.sqrt(52)) if pnl_arr.std() > 0 else 0
        win_rate = (np.array([p for p in pnl_list if p != 0]) > 0).mean() if num_trades > 0 else 0
        
        return {
            'total_pnl': total_pnl,
            'num_trades': num_trades,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate
        }
    
    def fine_grid_search(self):
        """Run fine-grained grid search (0.01 granularity)"""
        
        # Define search ranges
        pred_range = np.arange(0.50, 0.86, 0.01)  # 0.50 to 0.85
        conf_range = np.arange(0.00, 1.01, 0.01)  # 0.00 to 1.00
        
        total_combinations = len(pred_range) * len(conf_range)
        
        print(f"\n{'='*70}")
        print("FINE-GRAINED GRID SEARCH (Maximize PnL)")
        print(f"{'='*70}")
        print(f"Prediction range: {pred_range.min():.2f} - {pred_range.max():.2f} (step: 0.01)")
        print(f"Confidence range: {conf_range.min():.2f} - {conf_range.max():.2f} (step: 0.01)")
        print(f"Total combinations: {total_combinations:,}")
        print(f"{'='*70}\n")
        
        results = []
        count = 0
        
        for pred_th in pred_range:
            for conf_th in conf_range:
                count += 1
                metrics = self.run_backtest(pred_th, conf_th)
                results.append({
                    'prediction_threshold': round(pred_th, 2),
                    'confidence_threshold': round(conf_th, 2),
                    **metrics
                })
                
            # Progress update per prediction threshold
            if count % 100 == 0:
                print(f"Progress: {count:,}/{total_combinations:,} ({count/total_combinations*100:.1f}%)")
        
        results_df = pd.DataFrame(results)
        
        # Sort by Total PnL (primary objective)
        results_df_by_pnl = results_df.sort_values('total_pnl', ascending=False)
        
        print("\n" + "=" * 90)
        print("TOP 20 PARAMETER COMBINATIONS (by Total PnL)")
        print("=" * 90)
        
        for idx, row in results_df_by_pnl.head(20).iterrows():
            print(f"\n#{results_df_by_pnl.index.get_loc(idx)+1}:")
            print(f"  Prediction >= {row['prediction_threshold']:.2f}, Confidence > {row['confidence_threshold']:.2f}")
            print(f"  Total PnL: ${row['total_pnl']:,.0f} | Sharpe: {row['sharpe_ratio']:.2f} | Win Rate: {row['win_rate']*100:.1f}% | Trades: {row['num_trades']}")
        
        return results_df_by_pnl


def main():
    signal_file = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\data\raw\USD_SIGNAL_V3.csv'
    
    print("=" * 70)
    print("FINE-GRAINED GRID SEARCH FOR MAXIMUM PnL")
    print("=" * 70)
    
    bt = FineTuneBacktest(signal_data_path=signal_file, trade_size_usd=55_000_000)
    
    # Run fine grid search
    results = bt.fine_grid_search()
    
    # Save all results
    output_file = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\backtest\fine_grid_search_results.csv'
    results.to_csv(output_file, index=False)
    print(f"\nAll results saved to: {output_file}")
    
    # Best parameters
    best = results.iloc[0]
    print("\n" + "=" * 70)
    print("OPTIMAL PARAMETERS FOR MAXIMUM PnL:")
    print("=" * 70)
    print(f"  Prediction Threshold: >= {best['prediction_threshold']:.2f}")
    print(f"  Confidence Threshold: > {best['confidence_threshold']:.2f}")
    print(f"  ---")
    print(f"  Total PnL: ${best['total_pnl']:,.2f}")
    print(f"  Sharpe Ratio: {best['sharpe_ratio']:.2f}")
    print(f"  Win Rate: {best['win_rate']*100:.1f}%")
    print(f"  Number of Trades: {best['num_trades']}")
    
    # Also show top results with good trade frequency
    print("\n" + "=" * 70)
    print("TOP RESULTS WITH >= 5 TRADES (for statistical significance)")
    print("=" * 70)
    
    good_freq = results[results['num_trades'] >= 5].head(10)
    for idx, row in good_freq.iterrows():
        print(f"  Pred >= {row['prediction_threshold']:.2f}, Conf > {row['confidence_threshold']:.2f}")
        print(f"    PnL: ${row['total_pnl']:,.0f} | Sharpe: {row['sharpe_ratio']:.2f} | WR: {row['win_rate']*100:.1f}% | Trades: {row['num_trades']}")
    
    return results


if __name__ == "__main__":
    results = main()
