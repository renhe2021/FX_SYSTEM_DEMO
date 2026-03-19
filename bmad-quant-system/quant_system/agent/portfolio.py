"""
投资组合管理 - BMAD Agent Layer
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import logging

from .events import FillEvent, SignalEvent, OrderEvent

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        return self.quantity * (self.current_price - self.avg_price)
    
    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl


@dataclass
class Trade:
    """交易记录"""
    timestamp: datetime
    symbol: str
    direction: str
    quantity: float
    price: float
    commission: float
    pnl: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'direction': self.direction,
            'quantity': self.quantity,
            'price': self.price,
            'commission': self.commission,
            'pnl': self.pnl
        }


class Portfolio:
    """投资组合"""
    
    def __init__(self, initial_capital: float = 1000000.0,
                 commission_rate: float = 0.0001):  # 万分之一
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        
        self._positions: Dict[str, Position] = {}
        self._trades: List[Trade] = []
        self._equity_curve: List[Dict] = []
        self._current_time: datetime = None
    
    def update_time(self, timestamp: datetime) -> None:
        """更新当前时间"""
        self._current_time = timestamp
    
    def update_market_price(self, symbol: str, price: float) -> None:
        """更新市场价格"""
        if symbol in self._positions:
            self._positions[symbol].current_price = price
    
    def process_fill(self, fill: FillEvent) -> None:
        """处理成交"""
        symbol = fill.symbol
        quantity = fill.quantity
        price = fill.fill_price
        direction = fill.direction
        commission = fill.commission
        
        # 计算交易成本
        trade_value = quantity * price
        
        if symbol not in self._positions:
            self._positions[symbol] = Position(symbol=symbol)
        
        position = self._positions[symbol]
        pnl = 0.0
        
        if direction == "BUY":
            # 买入
            if position.quantity >= 0:
                # 加仓
                total_cost = position.quantity * position.avg_price + trade_value
                position.quantity += quantity
                position.avg_price = total_cost / position.quantity if position.quantity > 0 else 0
            else:
                # 平空仓
                pnl = -quantity * (price - position.avg_price)
                position.realized_pnl += pnl
                position.quantity += quantity
                if position.quantity > 0:
                    position.avg_price = price
            
            self.cash -= trade_value + commission
            
        else:  # SELL
            # 卖出
            if position.quantity <= 0:
                # 加空仓
                total_cost = abs(position.quantity) * position.avg_price + trade_value
                position.quantity -= quantity
                position.avg_price = total_cost / abs(position.quantity) if position.quantity != 0 else 0
            else:
                # 平多仓
                pnl = quantity * (price - position.avg_price)
                position.realized_pnl += pnl
                position.quantity -= quantity
                if position.quantity < 0:
                    position.avg_price = price
            
            self.cash += trade_value - commission
        
        position.current_price = price
        
        # 记录交易
        trade = Trade(
            timestamp=fill.timestamp,
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            price=price,
            commission=commission,
            pnl=pnl
        )
        self._trades.append(trade)
        
        logger.info(f"成交: {direction} {quantity} {symbol} @ {price}, PnL: {pnl:.2f}")
    
    def record_equity(self) -> None:
        """记录权益曲线"""
        equity = self.total_equity
        self._equity_curve.append({
            'timestamp': self._current_time,
            'equity': equity,
            'cash': self.cash,
            'positions_value': self.positions_value
        })
    
    @property
    def positions_value(self) -> float:
        """持仓市值"""
        return sum(p.market_value for p in self._positions.values())
    
    @property
    def total_equity(self) -> float:
        """总权益"""
        return self.cash + self.positions_value
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return sum(p.unrealized_pnl for p in self._positions.values())
    
    @property
    def realized_pnl(self) -> float:
        """已实现盈亏"""
        return sum(p.realized_pnl for p in self._positions.values())
    
    @property
    def total_pnl(self) -> float:
        """总盈亏"""
        return self.total_equity - self.initial_capital
    
    @property
    def total_return(self) -> float:
        """总收益率"""
        return self.total_pnl / self.initial_capital
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self._positions.get(symbol)
    
    def get_position_quantity(self, symbol: str) -> float:
        """获取持仓数量"""
        pos = self._positions.get(symbol)
        return pos.quantity if pos else 0.0
    
    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self._positions.copy()
    
    def get_trades(self) -> List[Trade]:
        """获取所有交易"""
        return self._trades.copy()
    
    def trades_to_dataframe(self) -> pd.DataFrame:
        """交易记录转DataFrame"""
        if not self._trades:
            return pd.DataFrame()
        return pd.DataFrame([t.to_dict() for t in self._trades])
    
    def get_equity_curve(self) -> pd.DataFrame:
        """获取权益曲线"""
        if not self._equity_curve:
            return pd.DataFrame()
        df = pd.DataFrame(self._equity_curve)
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_summary(self) -> dict:
        """获取组合摘要"""
        return {
            'initial_capital': self.initial_capital,
            'current_equity': self.total_equity,
            'cash': self.cash,
            'positions_value': self.positions_value,
            'total_pnl': self.total_pnl,
            'total_return': f"{self.total_return:.2%}",
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'num_trades': len(self._trades),
            'positions': {s: {'qty': p.quantity, 'avg_price': p.avg_price, 'pnl': p.total_pnl} 
                         for s, p in self._positions.items() if p.quantity != 0}
        }
