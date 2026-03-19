"""周五夜盘策略"""
import pandas as pd
from typing import List
from .base_strategy import BaseStrategy, StrategyParameter, Signal


class FridayNightStrategy(BaseStrategy):
    """
    周五夜盘策略
    在每周五指定时间买入，指定时间卖出
    适用于外汇市场的周末效应
    
    支持跨日交易：如周五21:00买入，周六02:00卖出
    """
    
    name = "FridayNightStrategy"
    description = "周五夜盘策略：在周五晚间买入，指定时间卖出，捕捉周末效应"
    version = "1.2.0"
    author = "BMAD Team"
    
    parameters = [
        StrategyParameter(
            name="entry_day",
            type="select",
            default=4,
            description="入场日期（0=周一，4=周五）",
            options=[0, 1, 2, 3, 4]
        ),
        StrategyParameter(
            name="entry_hour",
            type="int",
            default=21,
            description="入场时间（小时，北京时间）",
            min_value=0,
            max_value=23
        ),
        StrategyParameter(
            name="entry_minute",
            type="int",
            default=0,
            description="入场时间（分钟）",
            min_value=0,
            max_value=59
        ),
        StrategyParameter(
            name="exit_day",
            type="select",
            default=5,
            description="出场日期（5=周六，6=周日，0=周一）",
            options=[0, 5, 6]
        ),
        StrategyParameter(
            name="exit_hour",
            type="int",
            default=2,
            description="出场时间（小时，北京时间）",
            min_value=0,
            max_value=23
        ),
        StrategyParameter(
            name="exit_minute",
            type="int",
            default=0,
            description="出场时间（分钟）",
            min_value=0,
            max_value=59
        ),
        StrategyParameter(
            name="direction",
            type="select",
            default="long",
            description="交易方向",
            options=["long", "short"]
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
        
        # 添加辅助列
        df = data.copy()
        df['dayofweek'] = df.index.dayofweek
        df['hour'] = df.index.hour
        df['minute'] = df.index.minute
        
        # 获取参数
        entry_day = self.params['entry_day']
        entry_hour = self.params['entry_hour']
        entry_minute = self.params.get('entry_minute', 0)
        exit_day = self.params.get('exit_day', 5)  # 默认周六
        exit_hour = self.params.get('exit_hour', 2)  # 默认2点
        exit_minute = self.params.get('exit_minute', 0)
        direction = self.params['direction']
        position_size = self.params['position_size']
        
        day_names = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
        
        # 找入场点
        entry_mask = (
            (df['dayofweek'] == entry_day) & 
            (df['hour'] == entry_hour) & 
            (df['minute'] == entry_minute)
        )
        
        entry_points = df[entry_mask]
        
        for entry_time in entry_points.index:
            entry_price = df.loc[entry_time, 'close']
            
            # 生成入场信号
            signals.append(Signal(
                timestamp=entry_time,
                action="BUY" if direction == "long" else "SELL",
                price=entry_price,
                symbol="",
                quantity=position_size,
                reason=f"周{day_names[entry_day]} {entry_hour}:{entry_minute:02d} 入场",
                metadata={'direction': direction}
            ))
            
            # 找出场点
            future_data = df[df.index > entry_time]
            if future_data.empty:
                continue
            
            exit_time = None
            
            # 精确匹配出场时间
            exit_mask = (
                (future_data['dayofweek'] == exit_day) & 
                (future_data['hour'] == exit_hour) & 
                (future_data['minute'] == exit_minute)
            )
            
            exit_candidates = future_data[exit_mask]
            
            if not exit_candidates.empty:
                exit_time = exit_candidates.index[0]
            else:
                # 找最接近的时间点
                day_data = future_data[future_data['dayofweek'] == exit_day]
                if not day_data.empty:
                    # 找 >= exit_hour 的数据
                    hour_mask = day_data['hour'] >= exit_hour
                    if hour_mask.any():
                        exit_time = day_data[hour_mask].index[0]
                    else:
                        exit_time = day_data.index[0]
                else:
                    # 找下一个交易日
                    next_trading = future_data[~future_data['dayofweek'].isin([5, 6])]
                    if not next_trading.empty:
                        exit_time = next_trading.index[0]
            
            if exit_time is None:
                continue
                
            exit_price = df.loc[exit_time, 'close']
            
            # 生成出场信号
            signals.append(Signal(
                timestamp=exit_time,
                action="SELL" if direction == "long" else "BUY",
                price=exit_price,
                symbol="",
                quantity=position_size,
                reason=f"周{day_names[exit_time.dayofweek]} {exit_time.hour}:{exit_time.minute:02d} 出场",
                metadata={'direction': direction, 'entry_time': entry_time}
            ))
        
        return signals
