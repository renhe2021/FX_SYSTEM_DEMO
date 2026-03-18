"""策略基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class StrategyParameter:
    """策略参数定义"""
    name: str
    type: str  # int, float, str, bool, select
    default: Any
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: List[Any] = field(default_factory=list)


@dataclass 
class Signal:
    """交易信号"""
    timestamp: pd.Timestamp
    action: str  # BUY, SELL, HOLD
    price: float
    symbol: str
    quantity: float = 0
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """策略基类
    
    所有策略需要继承此类并实现 generate_signals 方法
    
    示例:
    ------
    class MyStrategy(BaseStrategy):
        name = "MyStrategy"
        description = "我的策略"
        
        parameters = [
            StrategyParameter(name="threshold", type="float", default=0.01)
        ]
        
        def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
            signals = []
            # 策略逻辑
            return signals
    """
    
    # 子类需要定义这些类属性
    name: str = "BaseStrategy"
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    
    # 参数定义
    parameters: List[StrategyParameter] = []
    
    def __init__(self, **kwargs):
        """初始化策略"""
        self.params = {}
        
        # 构建参数类型映射
        param_types = {p.name: p.type for p in self.parameters}
        
        # 设置默认值
        for param in self.parameters:
            self.params[param.name] = param.default
        
        # 覆盖传入的参数
        for key, value in kwargs.items():
            if key in self.params:
                expected_type = param_types.get(key, 'str')
                self.params[key] = self._convert_type(value, expected_type)
    
    def _convert_type(self, value, expected_type: str):
        """转换参数类型"""
        if value is None:
            return value
        
        try:
            if expected_type == 'int':
                return int(value)
            elif expected_type == 'float':
                return float(value)
            elif expected_type == 'bool':
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes')
            elif expected_type == 'select':
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return value
            else:
                return str(value)
        except (ValueError, TypeError):
            return value
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """生成交易信号
        
        Args:
            data: OHLCV数据，index为datetime
        
        Returns:
            信号列表
        """
        pass
    
    @classmethod
    def get_parameter_schema(cls) -> List[Dict[str, Any]]:
        """获取参数schema"""
        return [
            {
                'name': p.name,
                'type': p.type,
                'default': p.default,
                'description': p.description,
                'min': p.min_value,
                'max': p.max_value,
                'options': p.options
            }
            for p in cls.parameters
        ]
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': cls.name,
            'description': cls.description,
            'version': cls.version,
            'author': cls.author,
            'parameters': cls.get_parameter_schema()
        }
    
    def validate_params(self) -> bool:
        """验证参数"""
        for param in self.parameters:
            value = self.params.get(param.name)
            
            if param.min_value is not None and value < param.min_value:
                return False
            if param.max_value is not None and value > param.max_value:
                return False
            if param.options and value not in param.options:
                return False
        
        return True
