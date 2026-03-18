"""
事件系统 - BMAD Agent Layer
事件驱动回测架构的核心
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict, List
from queue import Queue, Empty
import threading


class EventType(Enum):
    """事件类型"""
    MARKET_DATA = "MARKET_DATA"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"
    PORTFOLIO = "PORTFOLIO"
    RISK = "RISK"


@dataclass
class Event:
    """事件基类"""
    event_type: EventType
    timestamp: datetime
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
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def __post_init__(self):
        self.event_type = EventType.SIGNAL


@dataclass
class OrderEvent(Event):
    """订单事件"""
    symbol: str = ""
    order_type: str = "MARKET"  # MARKET, LIMIT, STOP
    direction: str = ""  # BUY, SELL
    quantity: float = 0.0
    price: Optional[float] = None  # 限价单价格
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
    
    @property
    def cost(self) -> float:
        """交易成本（含手续费）"""
        return self.quantity * self.fill_price + self.commission


class EventQueue:
    """事件队列"""
    
    def __init__(self):
        self._queue: Queue = Queue()
        self._handlers: Dict[EventType, List[callable]] = {
            event_type: [] for event_type in EventType
        }
        self._running = False
        self._lock = threading.Lock()
    
    def put(self, event: Event) -> None:
        """放入事件"""
        self._queue.put(event)
    
    def get(self, timeout: float = None) -> Optional[Event]:
        """获取事件"""
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None
    
    def empty(self) -> bool:
        """队列是否为空"""
        return self._queue.empty()
    
    def register_handler(self, event_type: EventType, handler: callable) -> None:
        """注册事件处理器"""
        with self._lock:
            self._handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: EventType, handler: callable) -> None:
        """注销事件处理器"""
        with self._lock:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
    
    def dispatch(self, event: Event) -> None:
        """分发事件到处理器"""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"事件处理错误: {e}")
    
    def process_events(self) -> int:
        """处理所有待处理事件，返回处理数量"""
        count = 0
        while not self._queue.empty():
            event = self._queue.get_nowait()
            self.dispatch(event)
            count += 1
        return count
    
    def clear(self) -> None:
        """清空队列"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break
    
    def size(self) -> int:
        """队列大小"""
        return self._queue.qsize()
