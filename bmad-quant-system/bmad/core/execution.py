"""订单执行"""
from datetime import datetime
from typing import Optional
import uuid
import logging

from .events import OrderEvent, FillEvent, EventType

logger = logging.getLogger(__name__)


class SimulatedExecution:
    """模拟执行器"""
    
    def __init__(self, slippage: float = 0.0001, commission_rate: float = 0.0001):
        self.slippage = slippage
        self.commission_rate = commission_rate
    
    def execute_order(self, order: OrderEvent, current_price: float) -> Optional[FillEvent]:
        """执行订单"""
        if current_price <= 0:
            logger.warning(f"无效价格: {current_price}")
            return None
        
        # 计算滑点
        if order.direction == "BUY":
            fill_price = current_price * (1 + self.slippage)
        else:
            fill_price = current_price * (1 - self.slippage)
        
        # 计算手续费
        commission = order.quantity * fill_price * self.commission_rate
        
        # 创建成交事件
        fill = FillEvent(
            timestamp=order.timestamp,
            event_type=EventType.FILL,
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            fill_price=fill_price,
            commission=commission,
            order_id=order.order_id,
            fill_id=f"FILL_{uuid.uuid4().hex[:8]}",
            data={}
        )
        
        logger.debug(f"订单执行: {order.direction} {order.quantity} {order.symbol} @ {fill_price}")
        
        return fill
