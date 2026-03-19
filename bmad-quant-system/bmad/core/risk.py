"""风险管理"""
from dataclasses import dataclass
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """风险限制"""
    max_position_size: float = 1000000  # 单品种最大仓位
    max_total_exposure: float = 5000000  # 总敞口上限
    max_drawdown: float = 0.2  # 最大回撤限制
    position_size_pct: float = 0.1  # 单次仓位占比


class RiskManager:
    """风险管理器"""
    
    def __init__(self, limits: RiskLimits, initial_capital: float):
        self.limits = limits
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self._positions: Dict[str, float] = {}
    
    def check_order(self, symbol: str, quantity: float, 
                    price: float, direction: str) -> Tuple[bool, str]:
        """检查订单是否符合风险限制"""
        order_value = quantity * price
        
        # 检查单品种仓位限制
        if order_value > self.limits.max_position_size:
            return False, f"超过单品种仓位限制: {order_value} > {self.limits.max_position_size}"
        
        # 检查总敞口
        total_exposure = sum(abs(v) for v in self._positions.values()) + order_value
        if total_exposure > self.limits.max_total_exposure:
            return False, f"超过总敞口限制: {total_exposure} > {self.limits.max_total_exposure}"
        
        # 检查回撤
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown > self.limits.max_drawdown:
            return False, f"超过最大回撤限制: {current_drawdown:.2%} > {self.limits.max_drawdown:.2%}"
        
        return True, "通过"
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        """计算建议仓位大小"""
        max_value = self.current_capital * self.limits.position_size_pct
        return max_value / price if price > 0 else 0
    
    def update_capital(self, pnl: float) -> None:
        """更新资金"""
        self.current_capital += pnl
        self.peak_capital = max(self.peak_capital, self.current_capital)
    
    def update_position(self, symbol: str, quantity_change: float) -> None:
        """更新持仓"""
        current = self._positions.get(symbol, 0)
        self._positions[symbol] = current + quantity_change
