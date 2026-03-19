"""
策略模块 - BMAD Model Layer
"""
from abc import ABC, abstractmethod
from datetime import datetime, time
from typing import List, Optional, Dict, Any
import pandas as pd
import logging

from .signals import Signal, SignalType

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}
        self._signals: List[Signal] = []
        self._position = 0  # 当前持仓
        self._entry_price = 0  # 入场价格
    
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, symbol: str, 
                        current_idx: int) -> Optional[Signal]:
        """生成单个信号"""
        pass
    
    def run(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """运行策略生成所有信号"""
        self._signals.clear()
        self._position = 0
        self._entry_price = 0
        
        for i in range(len(data)):
            signal = self.generate_signal(data, symbol, i)
            if signal:
                self._signals.append(signal)
        
        return self._signals
    
    def get_signals(self) -> List[Signal]:
        return self._signals.copy()
    
    def signals_to_dataframe(self) -> pd.DataFrame:
        if not self._signals:
            return pd.DataFrame()
        return pd.DataFrame([s.to_dict() for s in self._signals])


class FridayNightStrategy(BaseStrategy):
    """
    周五夜盘策略
    每周五22:30开始判断，每半小时一次至周六01:30，周六02:00出场
    """
    
    def __init__(self, 
                 entry_day: int = 4,      # 周五
                 entry_hour: int = 22,    # 22:30
                 entry_minute: int = 30,
                 exit_hour: int = 2,      # 02:00 (次日凌晨)
                 exit_minute: int = 0,
                 position_size: float = 100000):
        
        super().__init__("FridayNightStrategy", {
            'entry_day': entry_day,
            'entry_hour': entry_hour,
            'entry_minute': entry_minute,
            'exit_hour': exit_hour,
            'exit_minute': exit_minute,
            'position_size': position_size
        })
        
        self.entry_day = entry_day
        self.entry_hour = entry_hour
        self.entry_minute = entry_minute
        self.exit_hour = exit_hour
        self.exit_minute = exit_minute
        self.position_size = position_size
    
    def _is_entry_time(self, dt: datetime) -> bool:
        """判断是否是入场时间"""
        return (dt.weekday() == self.entry_day and 
                dt.hour == self.entry_hour and 
                dt.minute >= self.entry_minute)
    
    def _is_exit_time(self, dt: datetime) -> bool:
        """判断是否是出场时间"""
        # 周六凌晨
        if dt.weekday() == 5 and dt.hour == self.exit_hour:
            return True
        # 或者周五深夜过了午夜
        if dt.weekday() == 4 and dt.hour >= 24:  # 理论上不会发生
            return True
        return False
    
    def _should_exit_on_day_close(self, dt: datetime, next_dt: datetime = None) -> bool:
        """判断是否应该在日终平仓（用于日线数据）"""
        # 如果是周五，且下一个交易日是周一，说明周末要平仓
        if dt.weekday() == 4:  # 周五
            if next_dt is None or next_dt.weekday() == 0:  # 下一个是周一
                return True
        return False
    
    def generate_signal(self, data: pd.DataFrame, symbol: str, 
                        current_idx: int) -> Optional[Signal]:
        """生成信号"""
        if current_idx >= len(data):
            return None
        
        current_time = data.index[current_idx]
        current_price = data['close'].iloc[current_idx]
        
        # 检查数据频率（日线 vs 分钟线）
        is_daily = False
        if current_idx > 0:
            time_diff = (data.index[current_idx] - data.index[current_idx-1]).total_seconds()
            is_daily = time_diff >= 86400  # 大于等于1天
        
        if is_daily:
            # 日线数据逻辑
            return self._generate_daily_signal(data, symbol, current_idx, current_time, current_price)
        else:
            # 分钟/小时数据逻辑
            return self._generate_intraday_signal(data, symbol, current_idx, current_time, current_price)
    
    def _generate_daily_signal(self, data: pd.DataFrame, symbol: str,
                                current_idx: int, current_time: datetime,
                                current_price: float) -> Optional[Signal]:
        """日线数据信号生成"""
        # 周五买入
        if current_time.weekday() == self.entry_day and self._position == 0:
            self._position = self.position_size
            self._entry_price = current_price
            
            logger.info(f"[{current_time}] 周五买入信号: {symbol} @ {current_price}")
            
            return Signal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=current_price,
                strength=1.0,
                metadata={
                    'reason': 'Friday entry',
                    'position_size': self.position_size
                }
            )
        
        # 周一平仓（因为日线数据没有周六凌晨的数据点）
        if current_time.weekday() == 0 and self._position > 0:  # 周一
            pnl = (current_price - self._entry_price) * self._position
            
            logger.info(f"[{current_time}] 周一平仓信号: {symbol} @ {current_price}, PnL: {pnl}")
            
            signal = Signal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.CLOSE_LONG,
                price=current_price,
                strength=1.0,
                metadata={
                    'reason': 'Monday exit (proxy for Saturday 2am)',
                    'entry_price': self._entry_price,
                    'pnl': pnl
                }
            )
            
            self._position = 0
            self._entry_price = 0
            
            return signal
        
        return None
    
    def _generate_intraday_signal(self, data: pd.DataFrame, symbol: str,
                                   current_idx: int, current_time: datetime,
                                   current_price: float) -> Optional[Signal]:
        """日内数据信号生成"""
        # 入场
        if self._is_entry_time(current_time) and self._position == 0:
            self._position = self.position_size
            self._entry_price = current_price
            
            logger.info(f"[{current_time}] 入场信号: {symbol} @ {current_price}")
            
            return Signal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=current_price,
                strength=1.0,
                metadata={
                    'reason': f'Entry at {self.entry_hour}:{self.entry_minute:02d}',
                    'position_size': self.position_size
                }
            )
        
        # 出场
        if self._is_exit_time(current_time) and self._position > 0:
            pnl = (current_price - self._entry_price) * self._position
            
            logger.info(f"[{current_time}] 出场信号: {symbol} @ {current_price}, PnL: {pnl}")
            
            signal = Signal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.CLOSE_LONG,
                price=current_price,
                strength=1.0,
                metadata={
                    'reason': f'Exit at {self.exit_hour}:{self.exit_minute:02d}',
                    'entry_price': self._entry_price,
                    'pnl': pnl
                }
            )
            
            self._position = 0
            self._entry_price = 0
            
            return signal
        
        return None


class MACrossStrategy(BaseStrategy):
    """均线交叉策略"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20, 
                 position_size: float = 100000):
        super().__init__("MACrossStrategy", {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'position_size': position_size
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.position_size = position_size
    
    def generate_signal(self, data: pd.DataFrame, symbol: str,
                        current_idx: int) -> Optional[Signal]:
        if current_idx < self.slow_period:
            return None
        
        current_time = data.index[current_idx]
        current_price = data['close'].iloc[current_idx]
        
        # 计算均线
        fast_ma = data['close'].iloc[current_idx-self.fast_period+1:current_idx+1].mean()
        slow_ma = data['close'].iloc[current_idx-self.slow_period+1:current_idx+1].mean()
        
        prev_fast_ma = data['close'].iloc[current_idx-self.fast_period:current_idx].mean()
        prev_slow_ma = data['close'].iloc[current_idx-self.slow_period:current_idx].mean()
        
        # 金叉买入
        if fast_ma > slow_ma and prev_fast_ma <= prev_slow_ma and self._position == 0:
            self._position = self.position_size
            self._entry_price = current_price
            
            return Signal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=current_price,
                strength=abs(fast_ma - slow_ma) / slow_ma,
                metadata={'fast_ma': fast_ma, 'slow_ma': slow_ma}
            )
        
        # 死叉卖出
        if fast_ma < slow_ma and prev_fast_ma >= prev_slow_ma and self._position > 0:
            pnl = (current_price - self._entry_price) * self._position
            
            signal = Signal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.CLOSE_LONG,
                price=current_price,
                strength=abs(fast_ma - slow_ma) / slow_ma,
                metadata={
                    'fast_ma': fast_ma, 
                    'slow_ma': slow_ma,
                    'entry_price': self._entry_price,
                    'pnl': pnl
                }
            )
            
            self._position = 0
            self._entry_price = 0
            
            return signal
        
        return None
