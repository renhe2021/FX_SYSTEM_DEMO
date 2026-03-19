"""周五夜盘策略"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base import BaseStrategy, Signal


class FridayNightStrategy(BaseStrategy):
    """
    周五夜盘策略
    
    逻辑：周五21:00开仓，周六02:00平仓
    基于USDCNH在周末前的波动特性
    """
    
    name = "FridayNightStrategy"
    version = "1.0.0"
    description = "周五夜盘USDCNH交易策略，利用周末前的汇率波动"
    
    def __init__(
        self,
        entry_day: int = 4,      # 周五 (0=周一)
        entry_hour: int = 21,    # 21:00
        exit_day: int = 5,       # 周六
        exit_hour: int = 2,      # 02:00
        direction: str = "long", # long/short
        **kwargs
    ):
        super().__init__(
            entry_day=entry_day,
            entry_hour=entry_hour,
            exit_day=exit_day,
            exit_hour=exit_hour,
            direction=direction,
            **kwargs
        )
        self.entry_day = entry_day
        self.entry_hour = entry_hour
        self.exit_day = exit_day
        self.exit_hour = exit_hour
        self.direction = direction
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        signals = []
        df = data.copy()
        
        # 确保有时间索引
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
        
        df['dayofweek'] = df.index.dayofweek
        df['hour'] = df.index.hour
        
        # 找入场点
        entry_mask = (df['dayofweek'] == self.entry_day) & (df['hour'] == self.entry_hour)
        entry_points = df[entry_mask]
        
        # 找出场点
        exit_mask = (df['dayofweek'] == self.exit_day) & (df['hour'] == self.exit_hour)
        exit_points = df[exit_mask]
        
        # 配对信号
        for entry_time in entry_points.index:
            # 找最近的出场点
            future_exits = exit_points[exit_points.index > entry_time]
            if len(future_exits) > 0:
                exit_time = future_exits.index[0]
                
                entry_price = df.loc[entry_time, 'close']
                exit_price = df.loc[exit_time, 'close']
                
                if self.direction == "long":
                    signals.append(Signal(
                        timestamp=entry_time,
                        action="BUY",
                        price=entry_price,
                        reason=f"周五{self.entry_hour}:00开多"
                    ))
                    signals.append(Signal(
                        timestamp=exit_time,
                        action="SELL",
                        price=exit_price,
                        reason=f"周六{self.exit_hour}:00平仓"
                    ))
                else:
                    signals.append(Signal(
                        timestamp=entry_time,
                        action="SELL",
                        price=entry_price,
                        reason=f"周五{self.entry_hour}:00开空"
                    ))
                    signals.append(Signal(
                        timestamp=exit_time,
                        action="BUY",
                        price=exit_price,
                        reason=f"周六{self.exit_hour}:00平仓"
                    ))
        
        self.signals = signals
        return signals
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析策略表现"""
        signals = self.generate_signals(data)
        
        if not signals:
            return {'error': '没有生成信号', 'trades': []}
        
        trades = []
        returns = []
        
        # 配对交易
        for i in range(0, len(signals) - 1, 2):
            entry = signals[i]
            exit_sig = signals[i + 1]
            
            if self.direction == "long":
                ret = (exit_sig.price - entry.price) / entry.price * 100
            else:
                ret = (entry.price - exit_sig.price) / entry.price * 100
            
            returns.append(ret)
            trades.append({
                'entry_time': str(entry.timestamp),
                'exit_time': str(exit_sig.timestamp),
                'entry_price': entry.price,
                'exit_price': exit_sig.price,
                'return_pct': round(ret, 4),
                'direction': self.direction
            })
        
        # 统计
        returns = np.array(returns)
        wins = returns[returns > 0]
        losses = returns[returns <= 0]
        
        analysis = {
            'strategy': self.name,
            'total_trades': len(trades),
            'win_rate': round(len(wins) / len(trades) * 100, 2) if trades else 0,
            'total_return': round(returns.sum(), 4),
            'avg_return': round(returns.mean(), 4) if len(returns) > 0 else 0,
            'max_return': round(returns.max(), 4) if len(returns) > 0 else 0,
            'min_return': round(returns.min(), 4) if len(returns) > 0 else 0,
            'std_return': round(returns.std(), 4) if len(returns) > 1 else 0,
            'sharpe_ratio': round(returns.mean() / returns.std() * np.sqrt(52), 2) if len(returns) > 1 and returns.std() > 0 else 0,
            'trades': trades,
            'returns': returns.tolist(),
            # 用于绑定图表
            'chart_data': {
                'cumulative_returns': np.cumsum(returns).tolist(),
                'trade_dates': [t['entry_time'] for t in trades]
            }
        }
        
        return analysis
    
    @classmethod
    def get_param_schema(cls) -> List[Dict]:
        return [
            {'name': 'entry_day', 'type': 'int', 'default': 4, 'min': 0, 'max': 6, 'description': '入场星期(0=周一)'},
            {'name': 'entry_hour', 'type': 'int', 'default': 21, 'min': 0, 'max': 23, 'description': '入场小时'},
            {'name': 'exit_day', 'type': 'int', 'default': 5, 'min': 0, 'max': 6, 'description': '出场星期'},
            {'name': 'exit_hour', 'type': 'int', 'default': 2, 'min': 0, 'max': 23, 'description': '出场小时'},
            {'name': 'direction', 'type': 'select', 'default': 'long', 'options': ['long', 'short'], 'description': '方向'}
        ]
