"""
信号生成器 - BMAD Model Layer
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


@dataclass
class Signal:
    """交易信号"""
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    price: float
    strength: float = 1.0  # 信号强度 0-1
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'price': self.price,
            'strength': self.strength,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'metadata': self.metadata
        }


class SignalGenerator:
    """信号生成器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._signals: List[Signal] = []
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """生成信号 - 子类实现"""
        raise NotImplementedError
    
    def get_signals(self) -> List[Signal]:
        """获取所有信号"""
        return self._signals.copy()
    
    def clear_signals(self) -> None:
        """清除信号"""
        self._signals.clear()
    
    def signals_to_dataframe(self) -> pd.DataFrame:
        """将信号转换为DataFrame"""
        if not self._signals:
            return pd.DataFrame()
        return pd.DataFrame([s.to_dict() for s in self._signals])


class MACrossoverSignal(SignalGenerator):
    """均线交叉信号"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20):
        super().__init__("MA_Crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        self.clear_signals()
        
        if len(data) < self.slow_period:
            return []
        
        # 计算均线
        fast_ma = data['close'].rolling(window=self.fast_period).mean()
        slow_ma = data['close'].rolling(window=self.slow_period).mean()
        
        # 生成信号
        for i in range(self.slow_period, len(data)):
            timestamp = data.index[i]
            price = data['close'].iloc[i]
            
            # 金叉
            if fast_ma.iloc[i] > slow_ma.iloc[i] and fast_ma.iloc[i-1] <= slow_ma.iloc[i-1]:
                signal = Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    strength=abs(fast_ma.iloc[i] - slow_ma.iloc[i]) / slow_ma.iloc[i],
                    metadata={'fast_ma': fast_ma.iloc[i], 'slow_ma': slow_ma.iloc[i]}
                )
                self._signals.append(signal)
            
            # 死叉
            elif fast_ma.iloc[i] < slow_ma.iloc[i] and fast_ma.iloc[i-1] >= slow_ma.iloc[i-1]:
                signal = Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=price,
                    strength=abs(fast_ma.iloc[i] - slow_ma.iloc[i]) / slow_ma.iloc[i],
                    metadata={'fast_ma': fast_ma.iloc[i], 'slow_ma': slow_ma.iloc[i]}
                )
                self._signals.append(signal)
        
        return self._signals


class RSISignal(SignalGenerator):
    """RSI超买超卖信号"""
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        super().__init__("RSI")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        self.clear_signals()
        
        if len(data) < self.period + 1:
            return []
        
        # 计算RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 生成信号
        for i in range(self.period + 1, len(data)):
            timestamp = data.index[i]
            price = data['close'].iloc[i]
            
            # 超卖反弹
            if rsi.iloc[i] > self.oversold and rsi.iloc[i-1] <= self.oversold:
                signal = Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    strength=(self.oversold - rsi.iloc[i-1]) / self.oversold,
                    metadata={'rsi': rsi.iloc[i]}
                )
                self._signals.append(signal)
            
            # 超买回落
            elif rsi.iloc[i] < self.overbought and rsi.iloc[i-1] >= self.overbought:
                signal = Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=price,
                    strength=(rsi.iloc[i-1] - self.overbought) / (100 - self.overbought),
                    metadata={'rsi': rsi.iloc[i]}
                )
                self._signals.append(signal)
        
        return self._signals


class TimeBasedSignal(SignalGenerator):
    """基于时间的信号生成器 - 用于周五夜盘策略"""
    
    def __init__(self, entry_day: int = 4, entry_hour: int = 22, 
                 exit_day: int = 5, exit_hour: int = 2):
        """
        entry_day: 入场日 (0=周一, 4=周五)
        entry_hour: 入场小时 (22 = 22:30 首次判断)
        exit_day: 出场日 (5=周六, 但实际是周五晚/周六凌晨)
        exit_hour: 出场小时 (2 = 02:00)
        """
        super().__init__("TimeBasedSignal")
        self.entry_day = entry_day
        self.entry_hour = entry_hour
        self.exit_day = exit_day
        self.exit_hour = exit_hour
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        self.clear_signals()
        
        for i in range(len(data)):
            timestamp = data.index[i]
            price = data['close'].iloc[i]
            
            # 检查是否是入场时间
            if timestamp.dayofweek == self.entry_day and timestamp.hour == self.entry_hour:
                signal = Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    strength=1.0,
                    metadata={'reason': 'Friday night entry'}
                )
                self._signals.append(signal)
            
            # 检查是否是出场时间 (周六凌晨实际上是周五的延续)
            elif (timestamp.dayofweek == self.exit_day and timestamp.hour == self.exit_hour) or \
                 (timestamp.dayofweek == 4 and timestamp.hour >= 24 + self.exit_hour - 24):
                signal = Signal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.CLOSE_LONG,
                    price=price,
                    strength=1.0,
                    metadata={'reason': 'Saturday morning exit'}
                )
                self._signals.append(signal)
        
        return self._signals
