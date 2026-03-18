"""策略基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class Signal:
    """交易信号"""
    timestamp: datetime
    action: str  # BUY, SELL, HOLD
    price: float
    quantity: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': str(self.timestamp),
            'action': self.action,
            'price': self.price,
            'quantity': self.quantity,
            'reason': self.reason
        }


class BaseStrategy(ABC):
    """策略基类"""
    
    name: str = "BaseStrategy"
    version: str = "1.0.0"
    description: str = ""
    
    def __init__(self, **params):
        self.params = params
        self.signals: List[Signal] = []
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号"""
        pass
    
    @abstractmethod
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析数据，返回分析结果（用于可视化）"""
        pass
    
    def get_info(self) -> Dict:
        """获取策略信息"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'parameters': self.params
        }
    
    @classmethod
    def get_param_schema(cls) -> List[Dict]:
        """获取参数定义（子类覆盖）"""
        return []
