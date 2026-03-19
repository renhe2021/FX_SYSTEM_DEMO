"""均线交叉策略"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, StrategyParameter, Signal


class MACrossStrategy(BaseStrategy):
    """
    均线交叉策略
    当短期均线上穿长期均线时买入，下穿时卖出
    """
    
    name = "MACrossStrategy"
    description = "均线交叉策略：短期均线上穿长期均线买入，下穿卖出"
    version = "1.0.0"
    author = "BMAD Team"
    
    parameters = [
        StrategyParameter(
            name="fast_period",
            type="int",
            default=10,
            description="快线周期",
            min_value=2,
            max_value=100
        ),
        StrategyParameter(
            name="slow_period",
            type="int",
            default=30,
            description="慢线周期",
            min_value=5,
            max_value=500
        ),
        StrategyParameter(
            name="ma_type",
            type="select",
            default="SMA",
            description="均线类型",
            options=["SMA", "EMA", "WMA"]
        ),
        StrategyParameter(
            name="position_size",
            type="float",
            default=100000,
            description="仓位大小",
            min_value=1000,
            max_value=10000000
        )
    ]
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        signals = []
        df = data.copy()
        
        fast_period = self.params['fast_period']
        slow_period = self.params['slow_period']
        ma_type = self.params['ma_type']
        position_size = self.params['position_size']
        
        # 计算均线
        if ma_type == "SMA":
            df['fast_ma'] = df['close'].rolling(fast_period).mean()
            df['slow_ma'] = df['close'].rolling(slow_period).mean()
        elif ma_type == "EMA":
            df['fast_ma'] = df['close'].ewm(span=fast_period).mean()
            df['slow_ma'] = df['close'].ewm(span=slow_period).mean()
        else:  # WMA
            weights_fast = range(1, fast_period + 1)
            weights_slow = range(1, slow_period + 1)
            df['fast_ma'] = df['close'].rolling(fast_period).apply(
                lambda x: sum(w * v for w, v in zip(weights_fast, x)) / sum(weights_fast)
            )
            df['slow_ma'] = df['close'].rolling(slow_period).apply(
                lambda x: sum(w * v for w, v in zip(weights_slow, x)) / sum(weights_slow)
            )
        
        # 计算交叉信号
        df['cross'] = 0
        df.loc[df['fast_ma'] > df['slow_ma'], 'cross'] = 1
        df.loc[df['fast_ma'] < df['slow_ma'], 'cross'] = -1
        df['cross_change'] = df['cross'].diff()
        
        # 生成信号
        position = 0
        
        for idx, row in df.iterrows():
            if pd.isna(row['cross_change']):
                continue
            
            # 金叉买入
            if row['cross_change'] == 2 and position <= 0:
                signals.append(Signal(
                    timestamp=idx,
                    action="BUY",
                    price=row['close'],
                    symbol="",
                    quantity=position_size,
                    reason=f"Golden cross: fast MA ({fast_period}) > slow MA ({slow_period})"
                ))
                position = 1
            
            # 死叉卖出
            elif row['cross_change'] == -2 and position >= 0:
                signals.append(Signal(
                    timestamp=idx,
                    action="SELL",
                    price=row['close'],
                    symbol="",
                    quantity=position_size,
                    reason=f"Death cross: fast MA ({fast_period}) < slow MA ({slow_period})"
                ))
                position = -1
        
        return signals
