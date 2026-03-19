"""动量策略"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, StrategyParameter, Signal


class MomentumStrategy(BaseStrategy):
    """
    动量策略
    基于价格动量和RSI指标进行交易
    """
    
    name = "MomentumStrategy"
    description = "动量策略：基于价格动量和RSI指标，追踪趋势"
    version = "1.0.0"
    author = "BMAD Team"
    
    parameters = [
        StrategyParameter(
            name="momentum_period",
            type="int",
            default=20,
            description="动量计算周期",
            min_value=5,
            max_value=100
        ),
        StrategyParameter(
            name="rsi_period",
            type="int",
            default=14,
            description="RSI周期",
            min_value=5,
            max_value=50
        ),
        StrategyParameter(
            name="rsi_oversold",
            type="int",
            default=30,
            description="RSI超卖阈值",
            min_value=10,
            max_value=40
        ),
        StrategyParameter(
            name="rsi_overbought",
            type="int",
            default=70,
            description="RSI超买阈值",
            min_value=60,
            max_value=90
        ),
        StrategyParameter(
            name="momentum_threshold",
            type="float",
            default=0.02,
            description="动量阈值（百分比）",
            min_value=0.001,
            max_value=0.1
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
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        signals = []
        df = data.copy()
        
        momentum_period = self.params['momentum_period']
        rsi_period = self.params['rsi_period']
        rsi_oversold = self.params['rsi_oversold']
        rsi_overbought = self.params['rsi_overbought']
        momentum_threshold = self.params['momentum_threshold']
        position_size = self.params['position_size']
        
        # 计算指标
        df['momentum'] = df['close'].pct_change(momentum_period)
        df['rsi'] = self._calculate_rsi(df['close'], rsi_period)
        
        # 生成信号
        position = 0
        
        for idx, row in df.iterrows():
            if pd.isna(row['momentum']) or pd.isna(row['rsi']):
                continue
            
            # 买入条件：正动量 + RSI超卖反弹
            if (row['momentum'] > momentum_threshold and 
                row['rsi'] > rsi_oversold and 
                row['rsi'] < 50 and
                position <= 0):
                
                signals.append(Signal(
                    timestamp=idx,
                    action="BUY",
                    price=row['close'],
                    symbol="",
                    quantity=position_size,
                    reason=f"Momentum: {row['momentum']:.2%}, RSI: {row['rsi']:.1f}"
                ))
                position = 1
            
            # 卖出条件：负动量 + RSI超买回落
            elif (row['momentum'] < -momentum_threshold and 
                  row['rsi'] < rsi_overbought and 
                  row['rsi'] > 50 and
                  position >= 0):
                
                signals.append(Signal(
                    timestamp=idx,
                    action="SELL",
                    price=row['close'],
                    symbol="",
                    quantity=position_size,
                    reason=f"Momentum: {row['momentum']:.2%}, RSI: {row['rsi']:.1f}"
                ))
                position = -1
        
        return signals
