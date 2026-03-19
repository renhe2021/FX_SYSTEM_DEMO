"""
数据类型定义 - BMAD Base Layer
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pandas as pd


@dataclass
class OHLCV:
    """K线数据结构"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'symbol': self.symbol
        }


@dataclass
class Trade:
    """成交数据结构"""
    timestamp: datetime
    price: float
    size: float
    symbol: str
    side: str  # 'BUY' or 'SELL'
    trade_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'price': self.price,
            'size': self.size,
            'symbol': self.symbol,
            'side': self.side,
            'trade_id': self.trade_id
        }


@dataclass
class Quote:
    """报价数据结构"""
    timestamp: datetime
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    symbol: str
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'bid': self.bid,
            'ask': self.ask,
            'bid_size': self.bid_size,
            'ask_size': self.ask_size,
            'symbol': self.symbol,
            'mid': self.mid,
            'spread': self.spread
        }


@dataclass
class Position:
    """持仓数据结构"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    timestamp: datetime
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        return self.quantity * (self.current_price - self.avg_price)
    
    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_price == 0:
            return 0
        return (self.current_price - self.avg_price) / self.avg_price * 100


def ohlcv_list_to_dataframe(ohlcv_list: list) -> pd.DataFrame:
    """将OHLCV列表转换为DataFrame"""
    if not ohlcv_list:
        return pd.DataFrame()
    
    data = [o.to_dict() for o in ohlcv_list]
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


def dataframe_to_ohlcv_list(df: pd.DataFrame, symbol: str = "") -> list:
    """将DataFrame转换为OHLCV列表"""
    ohlcv_list = []
    for idx, row in df.iterrows():
        ohlcv = OHLCV(
            timestamp=idx if isinstance(idx, datetime) else pd.to_datetime(idx),
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row.get('volume', 0),
            symbol=symbol
        )
        ohlcv_list.append(ohlcv)
    return ohlcv_list
