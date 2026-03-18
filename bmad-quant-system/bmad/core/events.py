"""事件系统"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Callable
from queue import Queue


class EventType(Enum):
    """事件类型"""
    MARKET_DATA = "MARKET_DATA"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"


@dataclass
class Event:
    """事件基类"""
    timestamp: datetime
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketDataEvent(Event):
    """市场数据事件"""
    symbol: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    
    def __post_init__(self):
        self.event_type = EventType.MARKET_DATA


@dataclass
class SignalEvent(Event):
    """信号事件"""
    symbol: str = ""
    signal_type: str = ""  # BUY, SELL, CLOSE_LONG, CLOSE_SHORT
    price: float = 0.0
    strength: float = 1.0
    stop_loss: float = None
    take_profit: float = None
    
    def __post_init__(self):
        self.event_type = EventType.SIGNAL


@dataclass
class OrderEvent(Event):
    """订单事件"""
    symbol: str = ""
    order_type: str = "MARKET"  # MARKET, LIMIT
    direction: str = ""  # BUY, SELL
    quantity: float = 0.0
    price: float = None  # for LIMIT orders
    order_id: str = ""
    
    def __post_init__(self):
        self.event_type = EventType.ORDER


@dataclass
class FillEvent(Event):
    """成交事件"""
    symbol: str = ""
    direction: str = ""
    quantity: float = 0.0
    fill_price: float = 0.0
    commission: float = 0.0
    order_id: str = ""
    fill_id: str = ""
    
    def __post_init__(self):
        self.event_type = EventType.FILL


class EventQueue:
    """事件队列"""
    
    def __init__(self):
        self._queue = Queue()
        self._handlers: Dict[EventType, List[Callable]] = {
            et: [] for et in EventType
        }
    
    def put(self, event: Event) -> None:
        """添加事件"""
        self._queue.put(event)
    
    def get(self) -> Event:
        """获取事件"""
        return self._queue.get()
    
    def empty(self) -> bool:
        """队列是否为空"""
        return self._queue.empty()
    
    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """注册事件处理器"""
        self._handlers[event_type].append(handler)
    
    def process_events(self) -> None:
        """处理所有事件"""
        while not self.empty():
            event = self.get()
            for handler in self._handlers.get(event.event_type, []):
                handler(event)
