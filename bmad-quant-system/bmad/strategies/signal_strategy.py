"""
信号策略模块
提供基于信号函数的快速回测能力，适用于参数反算场景
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass, field
from .base import BaseStrategy, StrategyParameter, Signal


@dataclass
class SignalBacktestResult:
    """信号回测结果"""
    trades: List[Dict]
    equity_curve: pd.Series
    signals: pd.Series
    params: Dict[str, Any]
    
    # 统计指标
    total_pnl: float = 0.0
    total_pnl_pips: float = 0.0
    num_trades: int = 0
    win_rate: float = 0.0
    avg_pnl_per_trade: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    def calculate_stats(self):
        """计算统计指标"""
        if not self.trades:
            return
            
        self.num_trades = len(self.trades)
        self.total_pnl = sum(t['pnl'] for t in self.trades)
        self.total_pnl_pips = sum(t['pnl_pips'] for t in self.trades)
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        self.win_rate = len(winning_trades) / self.num_trades if self.num_trades > 0 else 0
        self.avg_pnl_per_trade = self.total_pnl / self.num_trades if self.num_trades > 0 else 0
        
        # 最大回撤
        if len(self.equity_curve) > 0:
            cummax = self.equity_curve.cummax()
            drawdown = (self.equity_curve - cummax)
            self.max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
            
            # 夏普比率
            if len(self.equity_curve) > 1:
                returns = self.equity_curve.diff().dropna()
                if returns.std() > 0:
                    # 假设10秒数据，一天约2160个点
                    annualize_factor = np.sqrt(252 * 2160)
                    self.sharpe_ratio = returns.mean() / returns.std() * annualize_factor
    
    def summary(self) -> Dict:
        """生成摘要"""
        return {
            '总交易次数': self.num_trades,
            '总PnL (USD)': f'{self.total_pnl:,.2f}',
            '总PnL (pips)': f'{self.total_pnl_pips:.1f}',
            '胜率': f'{self.win_rate*100:.1f}%',
            '平均每笔PnL': f'{self.avg_pnl_per_trade:,.2f}',
            '最大回撤': f'{self.max_drawdown:,.2f}',
            '夏普比率': f'{self.sharpe_ratio:.2f}',
            '参数': self.params
        }
    
    def print_summary(self):
        """打印摘要"""
        print("\n" + "="*50)
        print("信号回测结果")
        print("="*50)
        for key, value in self.summary().items():
            if key == '参数':
                print(f"\n策略参数:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")
        print("="*50)


class SignalStrategy(BaseStrategy):
    """
    信号策略基类
    
    支持函数式信号定义，简化回测流程
    适用于快速验证交易想法和参数反算
    
    使用方法:
    ---------
    1. 继承此类并实现 calculate_signal 方法
    2. 或直接使用 from_function 创建策略
    
    示例:
    -----
    # 方法1：继承
    class MySignalStrategy(SignalStrategy):
        def calculate_signal(self, data, **params):
            ma_fast = data['mid'].rolling(params['fast']).mean()
            ma_slow = data['mid'].rolling(params['slow']).mean()
            signal = pd.Series(0, index=data.index)
            signal[ma_fast > ma_slow] = 1
            signal[ma_fast < ma_slow] = -1
            return signal
    
    # 方法2：函数式
    def my_signal(data, fast=10, slow=30):
        ...
        return signal
    
    strategy = SignalStrategy.from_function(my_signal, fast=10, slow=30)
    """
    
    name = "SignalStrategy"
    description = "基于信号函数的快速回测策略"
    version = "1.0.0"
    
    def __init__(self, 
                 signal_func: Callable = None,
                 trade_size: float = 1000000,  # 默认100万美元
                 spread_cost: bool = True,
                 slippage_pips: float = 0.0,
                 **kwargs):
        super().__init__(**kwargs)
        self.signal_func = signal_func
        self.trade_size = trade_size
        self.spread_cost = spread_cost
        self.slippage_pips = slippage_pips
        self.signal_params = kwargs
    
    @classmethod
    def from_function(cls, 
                      signal_func: Callable,
                      trade_size: float = 1000000,
                      spread_cost: bool = True,
                      slippage_pips: float = 0.0,
                      **params) -> 'SignalStrategy':
        """
        从信号函数创建策略
        
        Args:
            signal_func: 信号函数，接收 (data, **params) 返回信号Series
            trade_size: 交易规模（美元）
            spread_cost: 是否考虑点差
            slippage_pips: 滑点（pips）
            **params: 信号函数参数
        """
        strategy = cls(
            signal_func=signal_func,
            trade_size=trade_size,
            spread_cost=spread_cost,
            slippage_pips=slippage_pips,
            **params
        )
        strategy.name = signal_func.__name__
        return strategy
    
    def calculate_signal(self, data: pd.DataFrame, **params) -> pd.Series:
        """
        计算信号（子类重写此方法）
        
        Args:
            data: 包含 bid, ask, mid 的DataFrame
            **params: 策略参数
            
        Returns:
            信号Series: 1=买入, -1=卖出, 0=无信号
        """
        if self.signal_func:
            return self.signal_func(data, **params)
        raise NotImplementedError("请实现 calculate_signal 方法或提供 signal_func")
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号（兼容bmad框架）"""
        signals_series = self.calculate_signal(data, **self.signal_params)
        
        signals = []
        prev_signal = 0
        
        for timestamp, signal_val in signals_series.items():
            if signal_val != prev_signal and signal_val != 0:
                # 信号变化，生成入场信号
                price = data.loc[timestamp, 'mid'] if 'mid' in data.columns else data.loc[timestamp, 'close']
                signals.append(Signal(
                    timestamp=timestamp,
                    action="BUY" if signal_val == 1 else "SELL",
                    price=price,
                    symbol="",
                    quantity=self.trade_size,
                    reason=f"信号={signal_val}",
                    metadata={'signal_value': signal_val}
                ))
            elif signal_val != prev_signal and signal_val == 0:
                # 信号归零，平仓
                price = data.loc[timestamp, 'mid'] if 'mid' in data.columns else data.loc[timestamp, 'close']
                action = "SELL" if prev_signal == 1 else "BUY"
                signals.append(Signal(
                    timestamp=timestamp,
                    action=action,
                    price=price,
                    symbol="",
                    quantity=self.trade_size,
                    reason="平仓",
                    metadata={'signal_value': 0}
                ))
            
            prev_signal = signal_val
        
        return signals
    
    def backtest(self, data: pd.DataFrame, **params) -> SignalBacktestResult:
        """
        直接运行信号回测（简化版，不需要完整的BacktestEngine）
        
        Args:
            data: Bid/Ask数据，需要包含 bid, ask, mid 列
            **params: 覆盖默认参数
            
        Returns:
            SignalBacktestResult
        """
        # 合并参数
        all_params = {**self.signal_params, **params}
        
        # 确保数据有必要的列
        if 'mid' not in data.columns and 'bid' in data.columns and 'ask' in data.columns:
            data = data.copy()
            data['mid'] = (data['bid'] + data['ask']) / 2
        
        # 生成信号
        signals = self.calculate_signal(data, **all_params)
        
        # 执行回测
        trades = []
        current_trade = None
        equity = [0.0]
        slippage = self.slippage_pips * 0.0001
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # 检查是否需要平仓
            if current_trade is not None:
                if signal != current_trade['direction']:
                    # 平仓
                    if current_trade['direction'] == 1:
                        exit_price = row['bid'] - slippage if self.spread_cost else row['mid']
                    else:
                        exit_price = row['ask'] + slippage if self.spread_cost else row['mid']
                    
                    pnl_pips = (exit_price - current_trade['entry_price']) * current_trade['direction'] * 10000
                    pnl = (exit_price - current_trade['entry_price']) * current_trade['direction'] * self.trade_size
                    
                    current_trade.update({
                        'exit_time': timestamp,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pips': pnl_pips
                    })
                    trades.append(current_trade)
                    equity.append(equity[-1] + pnl)
                    current_trade = None
            
            # 检查是否需要开仓
            if current_trade is None and signal != 0:
                if signal == 1:
                    entry_price = row['ask'] + slippage if self.spread_cost else row['mid']
                else:
                    entry_price = row['bid'] - slippage if self.spread_cost else row['mid']
                
                current_trade = {
                    'entry_time': timestamp,
                    'direction': signal,
                    'entry_price': entry_price,
                    'size': self.trade_size
                }
        
        # 收盘平仓
        if current_trade is not None:
            last_row = data.iloc[-1]
            last_time = data.index[-1]
            exit_price = last_row['bid'] if current_trade['direction'] == 1 else last_row['ask']
            
            pnl_pips = (exit_price - current_trade['entry_price']) * current_trade['direction'] * 10000
            pnl = (exit_price - current_trade['entry_price']) * current_trade['direction'] * self.trade_size
            
            current_trade.update({
                'exit_time': last_time,
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_pips': pnl_pips
            })
            trades.append(current_trade)
            equity.append(equity[-1] + pnl)
        
        # 构建权益曲线
        equity_index = data.index[:len(equity)-1] if len(equity) > 1 else data.index[:1]
        equity_curve = pd.Series(equity[1:] if len(equity) > 1 else [0], index=equity_index)
        
        result = SignalBacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            signals=signals,
            params=all_params
        )
        result.calculate_stats()
        
        return result
    
    def optimize(self, 
                 data: pd.DataFrame,
                 param_grid: Dict[str, List],
                 metric: str = 'total_pnl') -> Tuple[Dict, SignalBacktestResult]:
        """
        参数优化（网格搜索）
        
        Args:
            data: 回测数据
            param_grid: 参数网格，如 {'ma_fast': [5,10,20], 'ma_slow': [20,50,100]}
            metric: 优化目标
            
        Returns:
            (最优参数, 最优结果)
        """
        from itertools import product
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(product(*param_values))
        
        best_result = None
        best_params = None
        best_metric_value = float('-inf')
        
        results_log = []
        
        print(f"开始参数优化，共 {len(all_combinations)} 种组合...")
        
        for i, values in enumerate(all_combinations):
            params = dict(zip(param_names, values))
            result = self.backtest(data, **params)
            
            metric_value = getattr(result, metric, 0)
            results_log.append({**params, metric: metric_value})
            
            if metric_value > best_metric_value:
                best_metric_value = metric_value
                best_result = result
                best_params = params
            
            if (i + 1) % 10 == 0:
                print(f"进度: {i+1}/{len(all_combinations)}, 当前最优 {metric}: {best_metric_value:.2f}")
        
        print(f"\n优化完成！最优参数: {best_params}")
        print(f"最优 {metric}: {best_metric_value:.2f}")
        
        self.optimization_results = pd.DataFrame(results_log)
        
        return best_params, best_result


# ============ 内置信号函数 ============

def ma_cross_signal(data: pd.DataFrame, 
                    ma_fast: int = 10, 
                    ma_slow: int = 30,
                    price_col: str = 'mid') -> pd.Series:
    """
    均线交叉信号
    
    快线上穿慢线买入，下穿卖出
    """
    price = data[price_col]
    fast_ma = price.rolling(window=ma_fast).mean()
    slow_ma = price.rolling(window=ma_slow).mean()
    
    signal = pd.Series(0, index=data.index)
    signal[fast_ma > slow_ma] = 1
    signal[fast_ma < slow_ma] = -1
    
    return signal


def momentum_signal(data: pd.DataFrame,
                    lookback: int = 20,
                    threshold: float = 0.0001,
                    price_col: str = 'mid') -> pd.Series:
    """
    动量信号
    
    价格变化率超过阈值时产生信号
    """
    price = data[price_col]
    momentum = price.pct_change(periods=lookback)
    
    signal = pd.Series(0, index=data.index)
    signal[momentum > threshold] = 1
    signal[momentum < -threshold] = -1
    
    return signal


def mean_reversion_signal(data: pd.DataFrame,
                          ma_period: int = 50,
                          entry_std: float = 2.0,
                          exit_std: float = 0.5,
                          price_col: str = 'mid') -> pd.Series:
    """
    均值回归信号
    
    价格偏离均线超过N倍标准差时反向交易
    """
    price = data[price_col]
    ma = price.rolling(window=ma_period).mean()
    std = price.rolling(window=ma_period).std()
    
    z_score = (price - ma) / std
    
    signal = pd.Series(0, index=data.index)
    signal[z_score > entry_std] = -1   # 过高卖出
    signal[z_score < -entry_std] = 1   # 过低买入
    signal[(z_score > -exit_std) & (z_score < exit_std)] = 0  # 回归平仓
    
    return signal


def bollinger_signal(data: pd.DataFrame,
                     period: int = 20,
                     num_std: float = 2.0,
                     price_col: str = 'mid') -> pd.Series:
    """布林带信号"""
    price = data[price_col]
    ma = price.rolling(window=period).mean()
    std = price.rolling(window=period).std()
    
    upper = ma + num_std * std
    lower = ma - num_std * std
    
    signal = pd.Series(0, index=data.index)
    signal[price <= lower] = 1   # 触及下轨买入
    signal[price >= upper] = -1  # 触及上轨卖出
    
    return signal


def rsi_signal(data: pd.DataFrame,
               period: int = 14,
               oversold: float = 30,
               overbought: float = 70,
               price_col: str = 'mid') -> pd.Series:
    """RSI信号"""
    price = data[price_col]
    
    delta = price.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    signal = pd.Series(0, index=data.index)
    signal[rsi < oversold] = 1
    signal[rsi > overbought] = -1
    
    return signal
