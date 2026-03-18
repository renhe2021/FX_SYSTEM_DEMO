"""均线交叉策略"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base import BaseStrategy, Signal


class MACrossStrategy(BaseStrategy):
    """
    均线交叉策略
    
    逻辑：短期均线上穿长期均线买入，下穿卖出
    """
    
    name = "MACrossStrategy"
    version = "1.0.0"
    description = "均线交叉策略，短期均线上穿长期均线买入"
    
    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 20,
        **kwargs
    ):
        super().__init__(
            fast_period=fast_period,
            slow_period=slow_period,
            **kwargs
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        signals = []
        df = data.copy()
        
        # 确保有时间索引
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
        
        # 计算均线
        df['ma_fast'] = df['close'].rolling(self.fast_period).mean()
        df['ma_slow'] = df['close'].rolling(self.slow_period).mean()
        
        # 交叉信号
        df['cross'] = 0
        df.loc[df['ma_fast'] > df['ma_slow'], 'cross'] = 1
        df.loc[df['ma_fast'] < df['ma_slow'], 'cross'] = -1
        df['cross_change'] = df['cross'].diff()
        
        position = 0
        for idx, row in df.iterrows():
            if pd.isna(row['cross_change']):
                continue
            
            if row['cross_change'] == 2 and position == 0:  # 金叉
                signals.append(Signal(
                    timestamp=idx,
                    action="BUY",
                    price=row['close'],
                    reason=f"金叉: MA{self.fast_period}上穿MA{self.slow_period}"
                ))
                position = 1
            elif row['cross_change'] == -2 and position == 1:  # 死叉
                signals.append(Signal(
                    timestamp=idx,
                    action="SELL",
                    price=row['close'],
                    reason=f"死叉: MA{self.fast_period}下穿MA{self.slow_period}"
                ))
                position = 0
        
        self.signals = signals
        return signals
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析策略表现"""
        df = data.copy()
        
        # 确保有时间索引
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
        
        # 计算均线
        df['ma_fast'] = df['close'].rolling(self.fast_period).mean()
        df['ma_slow'] = df['close'].rolling(self.slow_period).mean()
        
        signals = self.generate_signals(data)
        
        if len(signals) < 2:
            return {
                'error': '信号不足',
                'trades': [],
                'chart_data': {
                    'dates': df.index.strftime('%Y-%m-%d %H:%M').tolist(),
                    'close': df['close'].tolist(),
                    'ma_fast': df['ma_fast'].tolist(),
                    'ma_slow': df['ma_slow'].tolist()
                }
            }
        
        trades = []
        returns = []
        
        # 配对交易
        for i in range(0, len(signals) - 1, 2):
            if i + 1 >= len(signals):
                break
            entry = signals[i]
            exit_sig = signals[i + 1]
            
            ret = (exit_sig.price - entry.price) / entry.price * 100
            returns.append(ret)
            trades.append({
                'entry_time': str(entry.timestamp),
                'exit_time': str(exit_sig.timestamp),
                'entry_price': entry.price,
                'exit_price': exit_sig.price,
                'return_pct': round(ret, 4)
            })
        
        returns = np.array(returns) if returns else np.array([0])
        wins = returns[returns > 0]
        
        analysis = {
            'strategy': self.name,
            'parameters': {'fast_period': self.fast_period, 'slow_period': self.slow_period},
            'total_trades': len(trades),
            'win_rate': round(len(wins) / len(trades) * 100, 2) if trades else 0,
            'total_return': round(returns.sum(), 4),
            'avg_return': round(returns.mean(), 4),
            'max_return': round(returns.max(), 4),
            'min_return': round(returns.min(), 4),
            'sharpe_ratio': round(returns.mean() / returns.std() * np.sqrt(252), 2) if len(returns) > 1 and returns.std() > 0 else 0,
            'trades': trades,
            'chart_data': {
                'dates': df.index.strftime('%Y-%m-%d %H:%M').tolist(),
                'close': df['close'].tolist(),
                'ma_fast': df['ma_fast'].tolist(),
                'ma_slow': df['ma_slow'].tolist(),
                'cumulative_returns': np.cumsum(returns).tolist() if len(returns) > 0 else [],
                'signals': [s.to_dict() for s in signals]
            }
        }
        
        return analysis
    
    @classmethod
    def get_param_schema(cls) -> List[Dict]:
        return [
            {'name': 'fast_period', 'type': 'int', 'default': 5, 'min': 2, 'max': 50, 'description': '快线周期'},
            {'name': 'slow_period', 'type': 'int', 'default': 20, 'min': 5, 'max': 200, 'description': '慢线周期'}
        ]
