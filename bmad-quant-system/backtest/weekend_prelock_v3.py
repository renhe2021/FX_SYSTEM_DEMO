# -*- coding: utf-8 -*-
"""
Weekend Pre-Lock Price Strategy Backtest V3
=============================================

Confidence Logic (Based on Model Output):
- confidence_0 = 下跌置信度 (bearish confidence)
- confidence_1 = 上涨置信度 (bullish confidence)

For Friday scenario (we want USDCNH to go UP):
- If prediction >= 0.5 (model predicts UP) → use confidence_1 (bullish confidence)
- If prediction < 0.5 (model predicts DOWN) → use confidence_0 (bearish confidence)

Trading Rule:
- BUY USDCNH when: prediction >= threshold AND confidence (confidence_1) > conf_threshold

Author: FX Strategy Team
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product
import warnings
warnings.filterwarnings('ignore')


class WeekendPrelockBacktestV3:
    """
    Weekend Pre-Lock Strategy Backtester
    
    Confidence Selection:
    - prediction >= 0.5 → use confidence_1 (bullish)
    - prediction < 0.5 → use confidence_0 (bearish)
    
    Trading: Only LONG when bullish signal is strong
    """
    
    def __init__(
        self,
        signal_data_path: str,
        trade_size_usd: float = 55_000_000,
        trading_window_start: str = "22:00",
        trading_window_end: str = "01:30"
    ):
        """Initialize backtester"""
        self.trade_size_usd = trade_size_usd
        self.trading_window_start = trading_window_start
        self.trading_window_end = trading_window_end
        
        # Load signal data
        print("Loading signal data...")
        self.signals_df = pd.read_csv(signal_data_path)
        self.signals_df['predict_time'] = pd.to_datetime(self.signals_df['predict_time'])
        print(f"Loaded {len(self.signals_df)} signals")
        
        # Analyze data
        print(f"Date range: {self.signals_df['predict_time'].min()} to {self.signals_df['predict_time'].max()}")
        print(f"Prediction range: {self.signals_df['prediction'].min():.4f} - {self.signals_df['prediction'].max():.4f}")
        
        # ========================================
        # KEY: Create unified confidence column
        # ========================================
        # For Friday (want USDCNH UP):
        # - prediction >= 0.5 (bullish) → use confidence_1
        # - prediction < 0.5 (bearish) → use confidence_0
        self.signals_df['confidence'] = np.where(
            self.signals_df['prediction'] >= 0.5,
            self.signals_df['confidence_1'],  # 上涨预测用 confidence_1
            self.signals_df['confidence_0']   # 下跌预测用 confidence_0
        )
        
        # Direction label
        self.signals_df['direction'] = np.where(
            self.signals_df['prediction'] >= 0.5, 
            'BULLISH', 
            'BEARISH'
        )
        
        # Analyze
        print(f"\n{'='*60}")
        print("DATA PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"confidence_0 range: {self.signals_df['confidence_0'].min():.4f} - {self.signals_df['confidence_0'].max():.4f}")
        print(f"confidence_1 range: {self.signals_df['confidence_1'].min():.4f} - {self.signals_df['confidence_1'].max():.4f}")
        print(f"Derived confidence range: {self.signals_df['confidence'].min():.4f} - {self.signals_df['confidence'].max():.4f}")
        
        direction_counts = self.signals_df['direction'].value_counts()
        print(f"\nSignal Direction Distribution:")
        print(f"  BULLISH (prediction >= 0.5): {direction_counts.get('BULLISH', 0)}")
        print(f"  BEARISH (prediction < 0.5): {direction_counts.get('BEARISH', 0)}")
        
        # Show sample data
        print(f"\nSample processed data:")
        sample = self.signals_df[['predict_time', 'prediction', 'confidence_0', 'confidence_1', 'confidence', 'direction']].head(10)
        print(sample.to_string(index=False))
        
        # Price data placeholder
        self.entry_prices = None
        self.exit_prices = None
        
    def set_mock_prices(self):
        """Generate mock entry and exit prices for testing"""
        print("\nGenerating mock price data...")
        
        self.signals_df['year_week'] = self.signals_df['predict_time'].dt.strftime('%Y_%W')
        unique_weeks = self.signals_df['year_week'].unique()
        
        np.random.seed(42)
        base_price = 7.2500
        
        entry_prices = {}
        exit_prices = {}
        
        for week in unique_weeks:
            entry_price = base_price + np.random.uniform(-0.02, 0.02)
            entry_prices[week] = entry_price
            
            # Exit price with small random move
            price_move = np.random.normal(0, 0.003)
            exit_prices[week] = entry_price * (1 + price_move)
            
            base_price = exit_prices[week]
        
        self.entry_prices = entry_prices
        self.exit_prices = exit_prices
        
        print(f"Generated prices for {len(unique_weeks)} weeks")
        
    def filter_trading_window(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter signals within trading window (Friday 22:00 - Saturday 01:30)"""
        df = df.copy()
        df['hour'] = df['predict_time'].dt.hour
        df['minute'] = df['predict_time'].dt.minute
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        df['weekday'] = df['predict_time'].dt.weekday
        
        # Friday 22:00-23:59
        friday_mask = (df['weekday'] == 4) & (df['time_decimal'] >= 22.0)
        
        # Saturday 00:00-01:30
        saturday_mask = (df['weekday'] == 5) & (df['time_decimal'] <= 1.5)
        
        filtered = df[friday_mask | saturday_mask].copy()
        
        return filtered
    
    def run_backtest(
        self,
        prediction_threshold: float = 0.5,
        confidence_threshold: float = 0.2
    ) -> pd.DataFrame:
        """
        Run backtest with given thresholds
        
        Trading Logic (Friday - want USDCNH UP):
        - BUY when: prediction >= pred_threshold AND confidence > conf_threshold
        
        Parameters:
        -----------
        prediction_threshold : float
            Minimum prediction value to trigger LONG (0-1)
        confidence_threshold : float
            Minimum confidence value to trigger trade (0-1)
        """
        if self.entry_prices is None:
            self.set_mock_prices()
        
        # Filter trading window
        trading_signals = self.filter_trading_window(self.signals_df)
        
        if len(trading_signals) == 0:
            print("Warning: No signals in trading window!")
            return pd.DataFrame()
        
        trading_signals['year_week'] = trading_signals['predict_time'].dt.strftime('%Y_%W')
        
        # Get last signal per week
        weekly_signals = trading_signals.sort_values('predict_time').groupby('year_week').last().reset_index()
        
        results = []
        
        for _, row in weekly_signals.iterrows():
            week = row['year_week']
            prediction = row['prediction']
            confidence = row['confidence']
            
            if week not in self.entry_prices:
                continue
                
            entry_price = self.entry_prices[week]
            exit_price = self.exit_prices[week]
            
            # BUY USDCNH when bullish and confident
            should_buy = (prediction >= prediction_threshold) and (confidence > confidence_threshold)
            
            pnl = 0
            if should_buy:
                # Long USDCNH: profit if price goes up
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
                'pnl': pnl
            })
        
        return pd.DataFrame(results)
    
    def calculate_metrics(self, results_df: pd.DataFrame) -> dict:
        """Calculate performance metrics"""
        if len(results_df) == 0:
            return {
                'total_pnl': 0, 'num_trades': 0, 'num_weeks': 0,
                'trade_frequency': 0, 'win_rate': 0,
                'avg_pnl_per_trade': 0, 'sharpe_ratio': 0, 'max_drawdown': 0
            }
        
        pnl_series = results_df['pnl']
        trades = results_df[results_df['should_buy']]
        
        total_pnl = pnl_series.sum()
        num_trades = len(trades)
        num_weeks = len(results_df)
        win_rate = (trades['pnl'] > 0).mean() if num_trades > 0 else 0
        
        # Sharpe Ratio (annualized)
        if pnl_series.std() > 0:
            sharpe = (pnl_series.mean() / pnl_series.std()) * np.sqrt(52)
        else:
            sharpe = 0
        
        # Max Drawdown
        cumulative_pnl = pnl_series.cumsum()
        rolling_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'total_pnl': total_pnl,
            'num_trades': num_trades,
            'num_weeks': num_weeks,
            'trade_frequency': num_trades / num_weeks if num_weeks > 0 else 0,
            'win_rate': win_rate,
            'avg_pnl_per_trade': total_pnl / num_trades if num_trades > 0 else 0,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown
        }
    
    def grid_search(
        self,
        prediction_thresholds: list = None,
        confidence_thresholds: list = None,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Grid search for optimal thresholds
        
        Parameters:
        -----------
        prediction_thresholds : list
            BUY when prediction >= threshold
        confidence_thresholds : list
            BUY when confidence > threshold
        """
        if prediction_thresholds is None:
            prediction_thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
        if confidence_thresholds is None:
            confidence_thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        
        total_combinations = len(prediction_thresholds) * len(confidence_thresholds)
        
        if verbose:
            print(f"\n{'='*70}")
            print("GRID SEARCH")
            print(f"{'='*70}")
            print(f"Prediction thresholds: {prediction_thresholds}")
            print(f"Confidence thresholds: {confidence_thresholds}")
            print(f"Total combinations: {total_combinations}")
            print(f"{'='*70}\n")
        
        results = []
        
        for pred_th, conf_th in product(prediction_thresholds, confidence_thresholds):
            backtest_results = self.run_backtest(
                prediction_threshold=pred_th,
                confidence_threshold=conf_th
            )
            
            metrics = self.calculate_metrics(backtest_results)
            
            results.append({
                'prediction_threshold': pred_th,
                'confidence_threshold': conf_th,
                **metrics
            })
        
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(
            ['sharpe_ratio', 'total_pnl'], 
            ascending=[False, False]
        )
        
        if verbose:
            print("\n" + "=" * 90)
            print("TOP 15 PARAMETER COMBINATIONS (by Sharpe Ratio)")
            print("=" * 90)
            
            top_15 = results_df.head(15)
            for idx, (i, row) in enumerate(top_15.iterrows()):
                print(f"\n#{idx+1}:")
                print(f"  Prediction >= {row['prediction_threshold']:.2f}")
                print(f"  Confidence > {row['confidence_threshold']:.2f}")
                print(f"  Sharpe: {row['sharpe_ratio']:.2f} | PnL: ${row['total_pnl']:,.0f}")
                print(f"  Win Rate: {row['win_rate']*100:.1f}% | Trades: {row['num_trades']}/{row['num_weeks']} weeks")
        
        return results_df


def main():
    """Main function"""
    signal_file = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\data\raw\USD_SIGNAL_V3.csv'
    
    print("=" * 70)
    print("WEEKEND PRE-LOCK STRATEGY BACKTEST V3")
    print("=" * 70)
    print("\nConfidence Logic:")
    print("  - prediction >= 0.5 (bullish) -> use confidence_1")
    print("  - prediction < 0.5 (bearish) -> use confidence_0")
    print("\nTrading Logic (Friday - want USDCNH UP):")
    print("  - BUY when: prediction >= threshold AND confidence > threshold")
    print("  - Entry: Last signal in Friday 22:00 - Saturday 01:30")
    print("  - Exit: Saturday 02:00 ASK price")
    print("  - Trade Size: $55M per week")
    
    # Initialize backtester
    bt = WeekendPrelockBacktestV3(
        signal_data_path=signal_file,
        trade_size_usd=55_000_000
    )
    
    # Use mock price data
    bt.set_mock_prices()
    
    # Run grid search
    grid_results = bt.grid_search(
        prediction_thresholds=[0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8],
        confidence_thresholds=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    )
    
    # Save results
    output_file = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\backtest\grid_search_v3_results.csv'
    grid_results.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    # Best parameters
    best = grid_results.iloc[0]
    print("\n" + "=" * 70)
    print("BEST PARAMETERS:")
    print("=" * 70)
    print(f"  Prediction Threshold: >= {best['prediction_threshold']:.2f}")
    print(f"  Confidence Threshold: > {best['confidence_threshold']:.2f}")
    print(f"  ---")
    print(f"  Total PnL: ${best['total_pnl']:,.2f}")
    print(f"  Sharpe Ratio: {best['sharpe_ratio']:.2f}")
    print(f"  Win Rate: {best['win_rate']*100:.1f}%")
    print(f"  Number of Trades: {best['num_trades']}/{best['num_weeks']} weeks")
    print(f"  Avg PnL per Trade: ${best['avg_pnl_per_trade']:,.2f}")
    print(f"  Max Drawdown: ${best['max_drawdown']:,.2f}")
    
    # Detailed results
    print("\n" + "=" * 70)
    print("DETAILED TRADE LIST (Best Parameters)")
    print("=" * 70)
    
    detailed_results = bt.run_backtest(
        prediction_threshold=best['prediction_threshold'],
        confidence_threshold=best['confidence_threshold']
    )
    
    trades = detailed_results[detailed_results['should_buy']]
    print(f"\nTotal weeks: {len(detailed_results)}")
    print(f"Trading weeks: {len(trades)}")
    
    if len(trades) > 0:
        print("\nTrade Details:")
        display_cols = ['year_week', 'predict_time', 'prediction', 'confidence', 
                        'direction', 'entry_price', 'exit_price', 'pnl']
        print(trades[display_cols].to_string(index=False))
    
    # Save processed data for verification
    processed_file = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\data\raw\USD_SIGNAL_V3_processed.csv'
    bt.signals_df.to_csv(processed_file, index=False)
    print(f"\nProcessed data saved to: {processed_file}")
    
    return grid_results, detailed_results


if __name__ == "__main__":
    grid_results, detailed_results = main()
