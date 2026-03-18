# -*- coding: utf-8 -*-
"""
Weekend Pre-Lock Price Strategy Backtest
=========================================

Strategy Logic:
- Trading Window: Friday 22:00 - Saturday 01:30
- Use the LAST signal in the window for trading decision
- Reference Price: Saturday 02:00 ASK price (from Bloomberg)
- Trade Size: 55M USD per week
- Optimization: Grid search for best probability & confidence thresholds

Author: FX Strategy Team
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product
import warnings
warnings.filterwarnings('ignore')


class WeekendPrelockBacktest:
    """
    Weekend Pre-Lock Strategy Backtester
    """
    
    def __init__(
        self,
        signal_data_path: str,
        trade_size_usd: float = 55_000_000,
        trading_window_start: str = "22:00",
        trading_window_end: str = "01:30",
        reference_time: str = "02:00"
    ):
        """
        Initialize backtester
        
        Parameters:
        -----------
        signal_data_path : str
            Path to the signal CSV file
        trade_size_usd : float
            Weekly trade size in USD (default 55M)
        trading_window_start : str
            Start of trading window (Friday) HH:MM
        trading_window_end : str
            End of trading window (Saturday) HH:MM
        reference_time : str
            Reference price time (Saturday) HH:MM
        """
        self.trade_size_usd = trade_size_usd
        self.trading_window_start = trading_window_start
        self.trading_window_end = trading_window_end
        self.reference_time = reference_time
        
        # Load signal data
        print("Loading signal data...")
        self.signals_df = pd.read_csv(signal_data_path)
        self.signals_df['predict_time'] = pd.to_datetime(self.signals_df['predict_time'])
        print(f"Loaded {len(self.signals_df)} signals")
        
        # Price data (to be loaded from Bloomberg or file)
        self.price_data = None
        
    def load_price_data_from_file(self, price_file_path: str):
        """
        Load reference price data from CSV file
        
        Expected columns: date, ask_price, bid_price
        """
        self.price_data = pd.read_csv(price_file_path)
        self.price_data['date'] = pd.to_datetime(self.price_data['date'])
        print(f"Loaded {len(self.price_data)} price records")
        
    def load_price_data_from_bloomberg(self, start_date: str, end_date: str):
        """
        Load reference price data from Bloomberg API
        
        Requires: xbbg or blpapi
        """
        try:
            from xbbg import blp
            
            # Get Saturday 02:00 prices for USDCNH
            # Note: Need to adjust for your specific Bloomberg setup
            prices = blp.bdh(
                tickers='USDCNH Curncy',
                flds=['PX_ASK', 'PX_BID'],
                start_date=start_date,
                end_date=end_date
            )
            
            self.price_data = prices.reset_index()
            self.price_data.columns = ['date', 'ask_price', 'bid_price']
            print(f"Loaded {len(self.price_data)} prices from Bloomberg")
            
        except ImportError:
            print("Warning: xbbg not installed. Please install with 'pip install xbbg'")
            print("Or load price data from file using load_price_data_from_file()")
            
    def set_mock_price_data(self):
        """
        Generate mock price data for testing
        (Use actual Bloomberg data in production)
        """
        print("Generating mock price data for testing...")
        
        # Get unique dates from signals
        unique_dates = self.signals_df['fdate'].unique()
        
        # Generate mock Saturday 02:00 prices
        np.random.seed(42)
        base_price = 7.25
        
        mock_prices = []
        for fdate in unique_dates:
            date_str = str(fdate)
            date = datetime.strptime(date_str, '%Y%m%d')
            
            # Simulate price movement
            price_change = np.random.normal(0, 0.005)
            ask_price = base_price * (1 + price_change)
            bid_price = ask_price - 0.0002  # 2 pips spread
            
            mock_prices.append({
                'date': date,
                'fdate': fdate,
                'ask_price': ask_price,
                'bid_price': bid_price
            })
            
            base_price = ask_price  # Random walk
        
        self.price_data = pd.DataFrame(mock_prices)
        print(f"Generated {len(self.price_data)} mock price records")
        
    def filter_trading_window(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter signals within trading window (Friday 22:00 - Saturday 01:30)
        """
        df = df.copy()
        df['hour'] = df['predict_time'].dt.hour
        df['minute'] = df['predict_time'].dt.minute
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        df['weekday'] = df['predict_time'].dt.weekday  # Monday=0, Friday=4, Saturday=5
        
        # Trading window: Friday 22:00 - Saturday 01:30
        # Friday = weekday 4, Saturday = weekday 5
        
        # Friday 22:00-23:59
        friday_mask = (df['weekday'] == 4) & (df['time_decimal'] >= 22.0)
        
        # Saturday 00:00-01:30
        saturday_mask = (df['weekday'] == 5) & (df['time_decimal'] <= 1.5)
        
        return df[friday_mask | saturday_mask]
    
    def get_last_signal_per_week(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get the last signal for each trading week
        """
        df = df.sort_values('predict_time')
        
        # Group by week (using ISO week)
        df['year_week'] = df['predict_time'].dt.isocalendar().year.astype(str) + '_' + \
                          df['predict_time'].dt.isocalendar().week.astype(str).str.zfill(2)
        
        # Get last signal per week
        last_signals = df.groupby('year_week').last().reset_index()
        
        return last_signals
    
    def calculate_pnl(
        self,
        signal_row: pd.Series,
        entry_price: float,
        exit_price: float,
        trade_size: float
    ) -> float:
        """
        Calculate PnL for a single trade
        
        Parameters:
        -----------
        signal_row : pd.Series
            Signal data with is_positive, prediction, etc.
        entry_price : float
            Entry price (Friday evening)
        exit_price : float
            Exit price (Monday open or settlement)
        trade_size : float
            Trade size in USD
        
        Returns:
        --------
        float: PnL in USD
        """
        is_positive = signal_row['is_positive']
        
        # If is_positive = 1: Buy USD (Long USDCNH)
        # If is_positive = 0: Sell USD (Short USDCNH)
        
        if is_positive == 1:
            # Long USDCNH: profit if price goes up
            pnl = (exit_price - entry_price) / entry_price * trade_size
        else:
            # Short USDCNH: profit if price goes down
            pnl = (entry_price - exit_price) / entry_price * trade_size
            
        return pnl
    
    def run_backtest(
        self,
        prediction_threshold: float = 0.5,
        confidence_0_threshold: float = 0.0,
        confidence_1_threshold: float = 0.0,
        confidence_mode: str = 'or'  # 'or' or 'and'
    ) -> pd.DataFrame:
        """
        Run backtest with given thresholds
        
        Parameters:
        -----------
        prediction_threshold : float
            Minimum prediction value to trade (for is_positive=1)
        confidence_0_threshold : float
            Minimum confidence_0 value
        confidence_1_threshold : float
            Minimum confidence_1 value
        confidence_mode : str
            'or': either confidence must meet threshold
            'and': both confidences must meet threshold
        
        Returns:
        --------
        pd.DataFrame: Backtest results per week
        """
        if self.price_data is None:
            print("Warning: No price data loaded. Using mock data.")
            self.set_mock_price_data()
        
        # Filter trading window
        trading_signals = self.filter_trading_window(self.signals_df)
        
        # Get last signal per week
        weekly_signals = self.get_last_signal_per_week(trading_signals)
        
        results = []
        
        for _, row in weekly_signals.iterrows():
            week = row['year_week']
            fdate = row['fdate']
            
            # Get reference price for this date
            price_row = self.price_data[self.price_data['fdate'] == fdate]
            
            if len(price_row) == 0:
                continue
                
            ask_price = price_row['ask_price'].values[0]
            bid_price = price_row['bid_price'].values[0]
            
            # Apply thresholds to determine if we should trade
            prediction = row['prediction']
            conf_0 = row['confidence_0']
            conf_1 = row['confidence_1']
            is_positive = row['is_positive']
            
            # Confidence filter
            if confidence_mode == 'or':
                confidence_pass = (conf_0 >= confidence_0_threshold) or (conf_1 >= confidence_1_threshold)
            else:  # 'and'
                confidence_pass = (conf_0 >= confidence_0_threshold) and (conf_1 >= confidence_1_threshold)
            
            # Prediction filter (different logic for positive vs negative signals)
            if is_positive == 1:
                prediction_pass = prediction >= prediction_threshold
            else:
                prediction_pass = prediction <= (1 - prediction_threshold)
            
            # Determine if we trade
            should_trade = confidence_pass and prediction_pass
            
            if should_trade:
                # Entry price: use ask for long, bid for short
                entry_price = ask_price if is_positive == 1 else bid_price
                
                # Simulate exit price (for now, use entry + small random move)
                # In real backtest, use actual Monday open price
                exit_price = entry_price * (1 + np.random.normal(0, 0.002))
                
                pnl = self.calculate_pnl(row, entry_price, exit_price, self.trade_size_usd)
            else:
                pnl = 0
                entry_price = None
                exit_price = None
            
            results.append({
                'year_week': week,
                'fdate': fdate,
                'predict_time': row['predict_time'],
                'prediction': prediction,
                'confidence_0': conf_0,
                'confidence_1': conf_1,
                'is_positive': is_positive,
                'should_trade': should_trade,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl
            })
        
        return pd.DataFrame(results)
    
    def calculate_metrics(self, results_df: pd.DataFrame) -> dict:
        """
        Calculate performance metrics
        """
        pnl_series = results_df['pnl']
        trades = results_df[results_df['should_trade']]
        
        total_pnl = pnl_series.sum()
        num_trades = len(trades)
        num_weeks = len(results_df)
        win_rate = (trades['pnl'] > 0).mean() if num_trades > 0 else 0
        
        # Sharpe Ratio (annualized, assuming 52 weeks)
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
        confidence_0_thresholds: list = None,
        confidence_1_thresholds: list = None,
        confidence_mode: str = 'or',
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Grid search for optimal parameters
        
        Parameters:
        -----------
        prediction_thresholds : list
            List of prediction thresholds to test
        confidence_0_thresholds : list
            List of confidence_0 thresholds to test
        confidence_1_thresholds : list
            List of confidence_1 thresholds to test
        confidence_mode : str
            'or' or 'and'
        verbose : bool
            Print progress
        
        Returns:
        --------
        pd.DataFrame: Grid search results sorted by Sharpe Ratio
        """
        if prediction_thresholds is None:
            prediction_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        if confidence_0_thresholds is None:
            confidence_0_thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
        if confidence_1_thresholds is None:
            confidence_1_thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
        
        total_combinations = len(prediction_thresholds) * len(confidence_0_thresholds) * len(confidence_1_thresholds)
        
        if verbose:
            print(f"Running grid search with {total_combinations} combinations...")
        
        results = []
        count = 0
        
        for pred_th, conf_0_th, conf_1_th in product(
            prediction_thresholds, 
            confidence_0_thresholds, 
            confidence_1_thresholds
        ):
            count += 1
            
            # Run backtest
            backtest_results = self.run_backtest(
                prediction_threshold=pred_th,
                confidence_0_threshold=conf_0_th,
                confidence_1_threshold=conf_1_th,
                confidence_mode=confidence_mode
            )
            
            # Calculate metrics
            metrics = self.calculate_metrics(backtest_results)
            
            results.append({
                'prediction_threshold': pred_th,
                'confidence_0_threshold': conf_0_th,
                'confidence_1_threshold': conf_1_th,
                'confidence_mode': confidence_mode,
                **metrics
            })
            
            if verbose and count % 50 == 0:
                print(f"Progress: {count}/{total_combinations}")
        
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)
        
        if verbose:
            print("\n" + "=" * 60)
            print("Top 10 Parameter Combinations by Sharpe Ratio:")
            print("=" * 60)
            print(results_df.head(10).to_string(index=False))
        
        return results_df


def main():
    """
    Main function to run the backtest
    """
    # File paths
    signal_file = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\data\raw\USD_SIGNAL_V3.csv'
    
    # Initialize backtester
    bt = WeekendPrelockBacktest(
        signal_data_path=signal_file,
        trade_size_usd=55_000_000
    )
    
    # Use mock price data for now (replace with Bloomberg data)
    bt.set_mock_price_data()
    
    # Run grid search
    print("\n" + "=" * 60)
    print("Running Grid Search Optimization")
    print("=" * 60)
    
    grid_results = bt.grid_search(
        prediction_thresholds=[0.3, 0.4, 0.5, 0.6, 0.7],
        confidence_0_thresholds=[0.0, 0.2, 0.4, 0.6],
        confidence_1_thresholds=[0.0, 0.2, 0.4, 0.6],
        confidence_mode='or'
    )
    
    # Save results
    output_file = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\backtest\grid_search_results.csv'
    grid_results.to_csv(output_file, index=False)
    print(f"\nGrid search results saved to: {output_file}")
    
    # Show best parameters
    best = grid_results.iloc[0]
    print("\n" + "=" * 60)
    print("BEST PARAMETERS:")
    print("=" * 60)
    print(f"  Prediction Threshold: {best['prediction_threshold']}")
    print(f"  Confidence_0 Threshold: {best['confidence_0_threshold']}")
    print(f"  Confidence_1 Threshold: {best['confidence_1_threshold']}")
    print(f"  Total PnL: ${best['total_pnl']:,.2f}")
    print(f"  Sharpe Ratio: {best['sharpe_ratio']:.2f}")
    print(f"  Win Rate: {best['win_rate']*100:.1f}%")
    print(f"  Number of Trades: {best['num_trades']}")


if __name__ == "__main__":
    main()
