"""策略模块测试

测试 base, friday_night, registry 模块
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestBaseStrategy:
    """策略基类测试"""
    
    def test_strategy_parameter(self):
        """测试策略参数"""
        from bmad.strategies.base import StrategyParameter
        
        param = StrategyParameter(
            name='position_size',
            type='float',
            default=100000,
            min_value=10000,
            max_value=1000000,
            description='仓位大小'
        )
        
        assert param.name == 'position_size'
        assert param.default == 100000
        assert param.type == 'float'
    
    def test_signal(self):
        """测试信号对象"""
        from bmad.strategies.base import Signal
        
        signal = Signal(
            timestamp=pd.Timestamp.now(),
            symbol='USDCNH',
            action='BUY',
            price=7.25,
            quantity=100000,
            metadata={'reason': 'friday_entry'}
        )
        
        assert signal.action == 'BUY'
        assert signal.price == 7.25
        assert signal.symbol == 'USDCNH'


class TestFridayNightStrategy:
    """周五策略测试"""
    
    @pytest.fixture
    def sample_data(self):
        """创建包含多个周五的测试数据"""
        # 生成一个月的15分钟数据
        dates = pd.date_range('2024-01-01', periods=4000, freq='15min')
        
        df = pd.DataFrame({
            'open': 7.25,
            'high': 7.26,
            'low': 7.24,
            'close': 7.25,
            'volume': 1000
        }, index=dates)
        
        return df
    
    def test_strategy_init(self):
        """测试策略初始化"""
        from bmad.strategies.friday_night import FridayNightStrategy
        
        strategy = FridayNightStrategy(
            entry_day=4,
            entry_hour=21,
            exit_day=5,
            exit_hour=2,
            position_size=100000
        )
        
        # 参数通过 params 字典访问
        assert strategy.params['entry_day'] == 4
        assert strategy.params['entry_hour'] == 21
        assert strategy.params['position_size'] == 100000
    
    def test_strategy_name(self):
        """测试策略名称"""
        from bmad.strategies.friday_night import FridayNightStrategy
        
        strategy = FridayNightStrategy()
        
        assert strategy.name is not None
        assert len(strategy.name) > 0
    
    def test_generate_signals(self, sample_data):
        """测试信号生成"""
        from bmad.strategies.friday_night import FridayNightStrategy
        
        strategy = FridayNightStrategy(
            entry_day=4,
            entry_hour=21,
            exit_day=5,
            exit_hour=2
        )
        
        signals = strategy.generate_signals(sample_data)
        
        # 应该生成一些信号
        assert isinstance(signals, list)
    
    def test_entry_signal_timing(self, sample_data):
        """测试入场信号时机"""
        from bmad.strategies.friday_night import FridayNightStrategy
        
        strategy = FridayNightStrategy(
            entry_day=4,  # 周五
            entry_hour=21
        )
        
        signals = strategy.generate_signals(sample_data)
        
        # 检查入场信号是否在周五21点
        entry_signals = [s for s in signals if s.action == 'BUY']
        for signal in entry_signals:
            assert signal.timestamp.dayofweek == 4  # 周五
            assert signal.timestamp.hour == 21
    
    def test_strategy_info(self):
        """测试策略信息"""
        from bmad.strategies.friday_night import FridayNightStrategy
        
        info = FridayNightStrategy.get_info()
        
        assert 'name' in info
        assert 'parameters' in info


class TestStrategyRegistry:
    """策略注册器测试"""
    
    def test_register_strategy(self):
        """测试策略注册"""
        from bmad.strategies.registry import StrategyRegistry
        from bmad.strategies.friday_night import FridayNightStrategy
        
        # 使用类方法注册
        StrategyRegistry.register(FridayNightStrategy)
        
        assert FridayNightStrategy.name in StrategyRegistry.get_names()
    
    def test_get_strategy(self):
        """测试获取策略"""
        from bmad.strategies.registry import StrategyRegistry
        from bmad.strategies.friday_night import FridayNightStrategy
        
        StrategyRegistry.register(FridayNightStrategy)
        
        strategy_class = StrategyRegistry.get(FridayNightStrategy.name)
        assert strategy_class == FridayNightStrategy
    
    def test_create_strategy(self):
        """测试创建策略实例"""
        from bmad.strategies.registry import StrategyRegistry
        from bmad.strategies.friday_night import FridayNightStrategy
        
        StrategyRegistry.register(FridayNightStrategy)
        
        strategy = StrategyRegistry.create(FridayNightStrategy.name, position_size=200000)
        
        assert isinstance(strategy, FridayNightStrategy)
        assert strategy.params['position_size'] == 200000
    
    def test_list_all(self):
        """测试列出所有策略"""
        from bmad.strategies.registry import StrategyRegistry
        from bmad.strategies.friday_night import FridayNightStrategy
        
        StrategyRegistry.register(FridayNightStrategy)
        
        all_strategies = StrategyRegistry.list_all()
        assert len(all_strategies) > 0


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
