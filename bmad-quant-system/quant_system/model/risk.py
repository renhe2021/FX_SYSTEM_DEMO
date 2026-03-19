"""
风险管理 - BMAD Model Layer
"""
from dataclasses import dataclass, field
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """风险限制参数"""
    max_position_size: float = 100000  # 最大持仓金额
    max_position_pct: float = 0.1  # 最大持仓占比 (10%)
    max_drawdown_pct: float = 0.2  # 最大回撤 (20%)
    max_daily_loss: float = 5000  # 每日最大亏损
    max_single_loss_pct: float = 0.02  # 单笔最大亏损 (2%)
    stop_loss_pct: float = 0.02  # 默认止损比例 (2%)
    take_profit_pct: float = 0.05  # 默认止盈比例 (5%)
    max_leverage: float = 1.0  # 最大杠杆
    min_trade_interval: int = 60  # 最小交易间隔(秒)


class RiskManager:
    """风险管理器"""
    
    def __init__(self, limits: RiskLimits = None, initial_capital: float = 1000000):
        self.limits = limits or RiskLimits()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.daily_pnl = 0.0
        self._positions: Dict[str, float] = {}
        self._trade_history = []
    
    def check_order(self, symbol: str, quantity: float, price: float, side: str) -> tuple:
        """
        检查订单是否符合风险限制
        返回: (是否通过, 原因)
        """
        order_value = abs(quantity * price)
        
        # 检查单笔交易金额
        if order_value > self.limits.max_position_size:
            return False, f"订单金额{order_value}超过最大限制{self.limits.max_position_size}"
        
        # 检查持仓占比
        position_pct = order_value / self.current_capital
        if position_pct > self.limits.max_position_pct:
            return False, f"持仓占比{position_pct:.2%}超过限制{self.limits.max_position_pct:.2%}"
        
        # 检查每日亏损
        if self.daily_pnl < -self.limits.max_daily_loss:
            return False, f"每日亏损{-self.daily_pnl}已超限制{self.limits.max_daily_loss}"
        
        # 检查回撤
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown > self.limits.max_drawdown_pct:
            return False, f"当前回撤{current_drawdown:.2%}超过限制{self.limits.max_drawdown_pct:.2%}"
        
        return True, "通过风险检查"
    
    def calculate_position_size(self, symbol: str, price: float, 
                                 volatility: float = None) -> float:
        """
        计算建议仓位大小
        使用凯利公式或固定比例
        """
        # 基于最大持仓比例计算
        max_value = self.current_capital * self.limits.max_position_pct
        
        # 如果有波动率，调整仓位
        if volatility:
            # 波动率越高，仓位越小
            vol_adjustment = min(1.0, 0.02 / volatility)  # 假设目标波动率2%
            max_value *= vol_adjustment
        
        # 计算数量
        quantity = max_value / price
        
        return quantity
    
    def calculate_stop_loss(self, entry_price: float, side: str, 
                            atr: float = None) -> float:
        """计算止损价"""
        if atr:
            # 基于ATR的止损
            stop_distance = atr * 2
        else:
            # 固定比例止损
            stop_distance = entry_price * self.limits.stop_loss_pct
        
        if side == "BUY":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def calculate_take_profit(self, entry_price: float, side: str,
                               atr: float = None) -> float:
        """计算止盈价"""
        if atr:
            # 基于ATR的止盈 (风险回报比 1:2.5)
            profit_distance = atr * 5
        else:
            # 固定比例止盈
            profit_distance = entry_price * self.limits.take_profit_pct
        
        if side == "BUY":
            return entry_price + profit_distance
        else:
            return entry_price - profit_distance
    
    def update_capital(self, pnl: float) -> None:
        """更新资金"""
        self.current_capital += pnl
        self.daily_pnl += pnl
        
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        logger.debug(f"资金更新: PnL={pnl}, 当前={self.current_capital}, 峰值={self.peak_capital}")
    
    def reset_daily_pnl(self) -> None:
        """重置每日盈亏"""
        self.daily_pnl = 0.0
    
    def update_position(self, symbol: str, quantity: float) -> None:
        """更新持仓"""
        if symbol in self._positions:
            self._positions[symbol] += quantity
            if abs(self._positions[symbol]) < 1e-8:
                del self._positions[symbol]
        else:
            self._positions[symbol] = quantity
    
    def get_position(self, symbol: str) -> float:
        """获取持仓"""
        return self._positions.get(symbol, 0.0)
    
    def get_all_positions(self) -> Dict[str, float]:
        """获取所有持仓"""
        return self._positions.copy()
    
    @property
    def current_drawdown(self) -> float:
        """当前回撤"""
        if self.peak_capital == 0:
            return 0
        return (self.peak_capital - self.current_capital) / self.peak_capital
    
    @property
    def total_return(self) -> float:
        """总收益率"""
        return (self.current_capital - self.initial_capital) / self.initial_capital
    
    def get_risk_report(self) -> dict:
        """获取风险报告"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'total_return': f"{self.total_return:.2%}",
            'current_drawdown': f"{self.current_drawdown:.2%}",
            'daily_pnl': self.daily_pnl,
            'positions': self._positions.copy(),
            'risk_limits': {
                'max_position_size': self.limits.max_position_size,
                'max_position_pct': f"{self.limits.max_position_pct:.2%}",
                'max_drawdown_pct': f"{self.limits.max_drawdown_pct:.2%}",
                'max_daily_loss': self.limits.max_daily_loss
            }
        }
