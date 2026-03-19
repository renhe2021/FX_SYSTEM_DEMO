"""回测引擎"""
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import logging
import uuid

from .events import (
    EventQueue, EventType,
    SignalEvent, OrderEvent, FillEvent
)
from .portfolio import Portfolio
from .execution import SimulatedExecution
from .risk import RiskManager, RiskLimits

logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎
    
    使用示例:
    ---------
    engine = BacktestEngine(initial_capital=1000000)
    engine.add_data('USDCNH', data)
    engine.add_strategy(FridayNightStrategy())
    results = engine.run()
    """
    
    def __init__(self,
                 initial_capital: float = 1000000.0,
                 commission_rate: float = 0.0001,
                 slippage: float = 0.0001):
        
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        # 核心组件
        self.event_queue = EventQueue()
        self.portfolio = Portfolio(initial_capital, commission_rate)
        self.execution = SimulatedExecution(slippage, commission_rate)
        self.risk_manager = RiskManager(RiskLimits(), initial_capital)
        
        # 策略
        self._strategies: Dict[str, Any] = {}
        
        # 数据
        self._data: Dict[str, pd.DataFrame] = {}
        self._current_prices: Dict[str, float] = {}
        
        # 结果
        self._signals: List[SignalEvent] = []
        self._orders: List[OrderEvent] = []
        self._fills: List[FillEvent] = []
        
        # 注册事件处理器
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        self.event_queue.register_handler(EventType.SIGNAL, self._handle_signal)
        self.event_queue.register_handler(EventType.ORDER, self._handle_order)
        self.event_queue.register_handler(EventType.FILL, self._handle_fill)
    
    def add_strategy(self, strategy) -> None:
        """添加策略"""
        self._strategies[strategy.name] = strategy
        logger.info(f"策略已添加: {strategy.name}")
    
    def add_data(self, symbol: str, data: pd.DataFrame) -> None:
        """添加数据"""
        self._data[symbol] = data.copy()
        logger.info(f"数据已添加: {symbol}, {len(data)}条")
    
    def run(self) -> Dict[str, Any]:
        """运行回测"""
        if not self._data:
            raise ValueError("没有数据")
        if not self._strategies:
            raise ValueError("没有策略")
        
        logger.info("=" * 50)
        logger.info("回测开始")
        logger.info("=" * 50)
        
        # 获取所有时间戳并排序
        all_timestamps = set()
        for df in self._data.values():
            all_timestamps.update(df.index.tolist())
        timestamps = sorted(all_timestamps)
        
        logger.info(f"回测区间: {timestamps[0]} ~ {timestamps[-1]}")
        logger.info(f"数据点数: {len(timestamps)}")
        
        # 遍历每个时间点
        for timestamp in timestamps:
            self.portfolio.update_time(timestamp)
            
            # 更新市场数据
            for symbol, df in self._data.items():
                if timestamp in df.index:
                    row = df.loc[timestamp]
                    price = row['close']
                    self._current_prices[symbol] = price
                    self.portfolio.update_market_price(symbol, price)
            
            # 运行策略生成信号
            for strategy in self._strategies.values():
                for symbol, df in self._data.items():
                    if timestamp in df.index:
                        idx = df.index.get_loc(timestamp)
                        
                        # 支持两种信号生成方式
                        if hasattr(strategy, 'generate_signal'):
                            signal = strategy.generate_signal(df, symbol, idx)
                            if signal:
                                self._process_signal(signal)
                        elif hasattr(strategy, 'generate_signals'):
                            # 批量信号模式 - 只在第一个时间点运行一次
                            if idx == 0:
                                signals = strategy.generate_signals(df)
                                for sig in signals:
                                    sig.symbol = symbol
                                self._batch_signals = {s.timestamp: s for s in signals}
                            
                            # 检查当前时间是否有信号
                            if hasattr(self, '_batch_signals') and timestamp in self._batch_signals:
                                self._process_signal(self._batch_signals[timestamp])
            
            # 处理所有事件
            self.event_queue.process_events()
            
            # 记录权益
            self.portfolio.record_equity()
        
        # 生成结果
        results = self._generate_results()
        
        logger.info("=" * 50)
        logger.info("回测完成")
        logger.info("=" * 50)
        
        return results
    
    def _process_signal(self, signal) -> None:
        """处理信号"""
        signal_event = SignalEvent(
            timestamp=signal.timestamp,
            event_type=EventType.SIGNAL,
            symbol=signal.symbol,
            signal_type=signal.action,
            price=signal.price,
            strength=1.0,
            data=signal.metadata or {}
        )
        self.event_queue.put(signal_event)
    
    def _handle_signal(self, signal: SignalEvent) -> None:
        """处理信号事件"""
        self._signals.append(signal)
        
        symbol = signal.symbol
        signal_type = signal.signal_type
        price = signal.price
        
        # 获取当前持仓
        current_position = self.portfolio.get_position_quantity(symbol)
        
        # 根据信号类型生成订单
        order = None
        
        if signal_type == "BUY" and current_position <= 0:
            quantity = self._calculate_position_size(symbol, price)
            if quantity > 0:
                order = self._create_order(signal.timestamp, symbol, "BUY", quantity)
        
        elif signal_type == "SELL" and current_position >= 0:
            quantity = self._calculate_position_size(symbol, price)
            if quantity > 0:
                order = self._create_order(signal.timestamp, symbol, "SELL", quantity)
        
        elif signal_type == "CLOSE_LONG" and current_position > 0:
            order = self._create_order(signal.timestamp, symbol, "SELL", abs(current_position))
        
        elif signal_type == "CLOSE_SHORT" and current_position < 0:
            order = self._create_order(signal.timestamp, symbol, "BUY", abs(current_position))
        
        if order:
            self.event_queue.put(order)
    
    def _handle_order(self, order: OrderEvent) -> None:
        """处理订单事件"""
        self._orders.append(order)
        
        # 风险检查
        current_price = self._current_prices.get(order.symbol, 0)
        passed, reason = self.risk_manager.check_order(
            order.symbol, order.quantity, current_price, order.direction
        )
        
        if not passed:
            logger.warning(f"订单被拒绝: {reason}")
            return
        
        # 执行订单
        fill = self.execution.execute_order(order, current_price)
        
        if fill:
            self.event_queue.put(fill)
    
    def _handle_fill(self, fill: FillEvent) -> None:
        """处理成交事件"""
        self._fills.append(fill)
        
        # 更新组合
        self.portfolio.process_fill(fill)
        
        # 更新风险管理器
        self.risk_manager.update_capital(0)
        
        if fill.direction == "BUY":
            self.risk_manager.update_position(fill.symbol, fill.quantity)
        else:
            self.risk_manager.update_position(fill.symbol, -fill.quantity)
    
    def _calculate_position_size(self, symbol: str, price: float) -> float:
        """计算仓位大小"""
        return self.risk_manager.calculate_position_size(symbol, price)
    
    def _create_order(self, timestamp: datetime, symbol: str,
                      direction: str, quantity: float) -> OrderEvent:
        """创建订单"""
        return OrderEvent(
            timestamp=timestamp,
            event_type=EventType.ORDER,
            symbol=symbol,
            order_type="MARKET",
            direction=direction,
            quantity=quantity,
            order_id=f"ORD_{uuid.uuid4().hex[:8]}",
            data={}
        )
    
    def _generate_results(self) -> Dict[str, Any]:
        """生成回测结果"""
        equity_curve = self.portfolio.get_equity_curve()
        trades_df = self.portfolio.trades_to_dataframe()
        
        # 计算绩效指标
        if not equity_curve.empty:
            returns = equity_curve['equity'].pct_change().dropna()
            
            total_days = (equity_curve.index[-1] - equity_curve.index[0]).days
            total_return = self.portfolio.total_return
            annual_return = (1 + total_return) ** (365 / max(total_days, 1)) - 1 if total_days > 0 else 0
            
            sharpe = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
            
            cummax = equity_curve['equity'].cummax()
            drawdown = (equity_curve['equity'] - cummax) / cummax
            max_drawdown = drawdown.min()
            
            if not trades_df.empty and 'pnl' in trades_df.columns:
                winning_trades = len(trades_df[trades_df['pnl'] > 0])
                total_trades = len(trades_df)
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
            else:
                win_rate = 0
                total_trades = 0
        else:
            annual_return = 0
            sharpe = 0
            max_drawdown = 0
            win_rate = 0
            total_trades = 0
        
        results = {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_equity': self.portfolio.total_equity,
                'total_return': f"{self.portfolio.total_return:.2%}",
                'annual_return': f"{annual_return:.2%}",
                'sharpe_ratio': round(sharpe, 2),
                'max_drawdown': f"{max_drawdown:.2%}",
                'total_trades': total_trades,
                'win_rate': f"{win_rate:.2%}",
                'total_pnl': round(self.portfolio.total_pnl, 2),
                'total_commission': round(sum(f.commission for f in self._fills), 2)
            },
            'equity_curve': equity_curve,
            'trades': trades_df,
            'signals': pd.DataFrame([{
                'timestamp': s.timestamp,
                'symbol': s.symbol,
                'signal_type': s.signal_type,
                'price': s.price
            } for s in self._signals]) if self._signals else pd.DataFrame(),
            'portfolio': self.portfolio.get_summary()
        }
        
        logger.info("\n回测结果摘要:")
        for key, value in results['summary'].items():
            logger.info(f"  {key}: {value}")
        
        return results
    
    def get_equity_curve(self) -> pd.DataFrame:
        """获取权益曲线"""
        return self.portfolio.get_equity_curve()
    
    def get_trades(self) -> pd.DataFrame:
        """获取交易记录"""
        return self.portfolio.trades_to_dataframe()
