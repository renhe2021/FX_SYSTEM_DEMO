"""策略注册器"""
from typing import Dict, Any, List, Optional, Type

from .base import BaseStrategy


class StrategyRegistry:
    """策略注册器
    
    用于管理和创建策略实例
    """
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    
    @classmethod
    def register(cls, strategy_class: Type[BaseStrategy]) -> None:
        """注册策略"""
        cls._strategies[strategy_class.name] = strategy_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseStrategy]]:
        """获取策略类"""
        return cls._strategies.get(name)
    
    @classmethod
    def create(cls, name: str, **kwargs) -> Optional[BaseStrategy]:
        """创建策略实例"""
        strategy_class = cls.get(name)
        if strategy_class:
            return strategy_class(**kwargs)
        return None
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """列出所有策略"""
        return [s.get_info() for s in cls._strategies.values()]
    
    @classmethod
    def get_names(cls) -> List[str]:
        """获取所有策略名称"""
        return list(cls._strategies.keys())
