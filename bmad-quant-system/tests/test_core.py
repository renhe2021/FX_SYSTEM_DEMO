"""核心模块测试

测试 portfolio, events, execution, risk 模块
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestPortfolio:
    """组合管理测试"""
    
    def test_portfolio_init(self):
        """测试组合初始化"""
        from bmad.core.portfolio import Portfolio
        
        portfolio = Portfolio(initial_capital=1000000)
        
        assert portfolio.initial_capital == 1000000
        assert portfolio.cash == 1000000
        assert portfolio.total_equity == 1000000
    
    def test_portfolio_position(self):
        """测试持仓管理"""
        from bmad.core.portfolio import Position
        
        # 创建持仓
        position = Position(
            symbol='USDCNH',
            quantity=100000,
            avg_price=7.25,
            current_price=7.26
        )
        
        assert position.symbol == 'USDCNH'
        assert position.quantity == 100000
        assert position.avg_price == 7.25
        assert position.unrealized_pnl == pytest.approx(1000, rel=0.01)
    
    def test_portfolio_trade(self):
        """测试交易记录"""
        from bmad.core.portfolio import Trade
        
        trade = Trade(
            timestamp=datetime.now(),
            symbol='USDCNH',
            direction='BUY',
            quantity=100000,
            price=7.25,
            commission=10,
            pnl=1000
        )
        
        assert trade.symbol == 'USDCNH'
        assert trade.pnl == 1000
        assert trade.direction == 'BUY'
    
    def test_trade_to_dict(self):
        """测试交易记录转字典"""
        from bmad.core.portfolio import Trade
        
        trade = Trade(
            timestamp=datetime.now(),
            symbol='USDCNH',
            direction='BUY',
            quantity=100000,
            price=7.25,
            commission=10
        )
        
        d = trade.to_dict()
        assert 'symbol' in d
        assert 'direction' in d
        assert d['quantity'] == 100000


class TestEvents:
    """事件系统测试"""
    
    def test_event_queue(self):
        """测试事件队列"""
        from bmad.core.events import EventQueue, EventType, SignalEvent
        
        queue = EventQueue()
        
        # 创建信号事件
        signal = SignalEvent(
            timestamp=datetime.now(),
            event_type=EventType.SIGNAL,
            symbol='USDCNH',
            signal_type='BUY',
            price=7.25,
            strength=1.0
        )
        
        queue.put(signal)
        assert not queue.empty()
    
    def test_signal_event(self):
        """测试信号事件"""
        from bmad.core.events import SignalEvent, EventType
        
        signal = SignalEvent(
            timestamp=datetime.now(),
            event_type=EventType.SIGNAL,
            symbol='USDCNH',
            signal_type='BUY',
            price=7.25,
            strength=0.8
        )
        
        assert signal.symbol == 'USDCNH'
        assert signal.signal_type == 'BUY'
        assert signal.strength == 0.8
    
    def test_order_event(self):
        """测试订单事件"""
        from bmad.core.events import OrderEvent, EventType
        
        order = OrderEvent(
            timestamp=datetime.now(),
            event_type=EventType.ORDER,
            symbol='USDCNH',
            order_type='MARKET',
            direction='BUY',
            quantity=100000,
            order_id='ORD_001'
        )
        
        assert order.symbol == 'USDCNH'
        assert order.direction == 'BUY'
        assert order.quantity == 100000
    
    def test_fill_event(self):
        """测试成交事件"""
        from bmad.core.events import FillEvent, EventType
        
        fill = FillEvent(
            timestamp=datetime.now(),
            event_type=EventType.FILL,
            symbol='USDCNH',
            direction='BUY',
            quantity=100000,
            fill_price=7.25,
            commission=10,
            order_id='ORD_001'
        )
        
        assert fill.fill_price == 7.25
        assert fill.commission == 10
    
    def test_event_queue_process(self):
        """测试事件队列处理"""
        from bmad.core.events import EventQueue, EventType, SignalEvent
        
        queue = EventQueue()
        processed = []
        
        def handler(event):
            processed.append(event)
        
        queue.register_handler(EventType.SIGNAL, handler)
        
        signal = SignalEvent(
            timestamp=datetime.now(),
            event_type=EventType.SIGNAL,
            symbol='USDCNH',
            signal_type='BUY',
            price=7.25
        )
        
        queue.put(signal)
        queue.process_events()
        
        assert len(processed) == 1


class TestExecution:
    """执行模块测试"""
    
    def test_simulated_execution(self):
        """测试模拟执行"""
        from bmad.core.execution import SimulatedExecution
        from bmad.core.events import OrderEvent, EventType
        
        execution = SimulatedExecution(slippage=0.0001, commission_rate=0.0001)
        
        order = OrderEvent(
            timestamp=datetime.now(),
            event_type=EventType.ORDER,
            symbol='USDCNH',
            order_type='MARKET',
            direction='BUY',
            quantity=100000,
            order_id='ORD_001'
        )
        
        fill = execution.execute_order(order, current_price=7.25)
        
        assert fill is not None
        assert fill.symbol == 'USDCNH'
        assert fill.quantity == 100000
        # 买入应该有滑点向上
        assert fill.fill_price >= 7.25
    
    def test_slippage_calculation(self):
        """测试滑点计算"""
        from bmad.core.execution import SimulatedExecution
        from bmad.core.events import OrderEvent, EventType
        
        execution = SimulatedExecution(slippage=0.001, commission_rate=0)
        
        # 买入订单
        buy_order = OrderEvent(
            timestamp=datetime.now(),
            event_type=EventType.ORDER,
            symbol='USDCNH',
            order_type='MARKET',
            direction='BUY',
            quantity=100000,
            order_id='ORD_001'
        )
        
        fill = execution.execute_order(buy_order, current_price=7.25)
        # 买入滑点向上: 7.25 * (1 + 0.001) = 7.25725
        assert fill.fill_price == pytest.approx(7.25725, rel=1e-4)


class TestRiskManager:
    """风控模块测试"""
    
    def test_risk_limits(self):
        """测试风控限制"""
        from bmad.core.risk import RiskLimits
        
        limits = RiskLimits(
            max_position_size=1000000,
            max_total_exposure=5000000,
            max_drawdown=0.1
        )
        
        assert limits.max_position_size == 1000000
        assert limits.max_total_exposure == 5000000
        assert limits.max_drawdown == 0.1
    
    def test_risk_manager_check_pass(self):
        """测试风控检查通过"""
        from bmad.core.risk import RiskManager, RiskLimits
        
        limits = RiskLimits(max_position_size=1000000)
        manager = RiskManager(limits, initial_capital=1000000)
        
        # 正常订单应该通过
        passed, reason = manager.check_order('USDCNH', 100000, 7.25, 'BUY')
        assert passed is True
    
    def test_risk_manager_check_fail(self):
        """测试风控检查拒绝"""
        from bmad.core.risk import RiskManager, RiskLimits
        
        limits = RiskLimits(max_position_size=500000)
        manager = RiskManager(limits, initial_capital=1000000)
        
        # 超大订单应该被拒绝 (100000 * 7.25 = 725000 > 500000)
        passed, reason = manager.check_order('USDCNH', 100000, 7.25, 'BUY')
        assert passed is False
    
    def test_position_size_calculation(self):
        """测试仓位计算"""
        from bmad.core.risk import RiskManager, RiskLimits
        
        limits = RiskLimits(position_size_pct=0.1)
        manager = RiskManager(limits, initial_capital=1000000)
        
        size = manager.calculate_position_size('USDCNH', 7.25)
        # 1000000 * 0.1 / 7.25 ≈ 13793
        assert size > 0
        assert size == pytest.approx(13793, rel=0.01)
    
    def test_update_capital(self):
        """测试资金更新"""
        from bmad.core.risk import RiskManager, RiskLimits
        
        limits = RiskLimits()
        manager = RiskManager(limits, initial_capital=1000000)
        
        manager.update_capital(10000)
        assert manager.current_capital == 1010000
        assert manager.peak_capital == 1010000


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
