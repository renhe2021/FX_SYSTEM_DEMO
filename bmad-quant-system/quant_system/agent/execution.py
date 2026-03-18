"""
执行处理器 - BMAD Agent Layer
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import uuid
import logging

from .events import OrderEvent, FillEvent

logger = logging.getLogger(__name__)


class ExecutionHandler(ABC):
    """执行处理器基类"""
    
    @abstractmethod
    def execute_order(self, order: OrderEvent, current_price: float) -> Optional[FillEvent]:
        """执行订单"""
        pass


class SimulatedExecution(ExecutionHandler):
    """模拟执行器（回测用）"""
    
    def __init__(self, 
                 slippage: float = 0.0001,  # 滑点 (万分之一)
                 commission_rate: float = 0.0001,  # 手续费率
                 fill_ratio: float = 1.0):  # 成交比例
        self.slippage = slippage
        self.commission_rate = commission_rate
        self.fill_ratio = fill_ratio
        self._order_count = 0
    
    def execute_order(self, order: OrderEvent, current_price: float) -> Optional[FillEvent]:
        """执行订单"""
        # 计算成交价（含滑点）
        if order.direction == "BUY":
            fill_price = current_price * (1 + self.slippage)
        else:
            fill_price = current_price * (1 - self.slippage)
        
        # 限价单检查
        if order.order_type == "LIMIT" and order.price:
            if order.direction == "BUY" and current_price > order.price:
                logger.debug(f"限价买单未成交: 当前价{current_price} > 限价{order.price}")
                return None
            if order.direction == "SELL" and current_price < order.price:
                logger.debug(f"限价卖单未成交: 当前价{current_price} < 限价{order.price}")
                return None
            fill_price = order.price
        
        # 计算成交数量
        fill_quantity = order.quantity * self.fill_ratio
        
        # 计算手续费
        commission = fill_quantity * fill_price * self.commission_rate
        
        # 生成成交ID
        self._order_count += 1
        fill_id = f"FILL_{self._order_count}_{uuid.uuid4().hex[:8]}"
        
        fill = FillEvent(
            timestamp=order.timestamp,
            symbol=order.symbol,
            direction=order.direction,
            quantity=fill_quantity,
            fill_price=fill_price,
            commission=commission,
            order_id=order.order_id,
            fill_id=fill_id,
            data={}
        )
        
        logger.info(f"订单成交: {order.direction} {fill_quantity} {order.symbol} @ {fill_price:.5f}, 手续费: {commission:.2f}")
        
        return fill


class LiveExecution(ExecutionHandler):
    """实盘执行器（预留接口）"""
    
    def __init__(self, broker_api=None):
        self.broker_api = broker_api
    
    def execute_order(self, order: OrderEvent, current_price: float) -> Optional[FillEvent]:
        """执行订单 - 实盘需要实现具体的broker API调用"""
        raise NotImplementedError("实盘执行需要实现具体的broker API")
