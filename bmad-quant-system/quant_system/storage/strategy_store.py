"""
策略配置存储管理
"""
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
import uuid


@dataclass
class StrategyConfig:
    """策略配置"""
    id: str
    name: str
    strategy_type: str  # FridayNightStrategy, MACrossStrategy, etc.
    description: str
    symbol: str
    parameters: Dict[str, Any]
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StrategyConfig':
        return cls(**data)


class StrategyStore:
    """策略配置存储管理器"""
    
    def __init__(self, storage_path: str = "./backtest_data"):
        self.storage_path = storage_path
        self.config_file = os.path.join(storage_path, "strategies.json")
        
        os.makedirs(storage_path, exist_ok=True)
        
        if not os.path.exists(self.config_file):
            self._save_all([])
    
    def _load_all(self) -> List[dict]:
        """加载所有策略配置"""
        if not os.path.exists(self.config_file):
            return []
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_all(self, strategies: List[dict]):
        """保存所有策略配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(strategies, f, ensure_ascii=False, indent=2)
    
    def save(self, config: StrategyConfig) -> str:
        """保存策略配置"""
        strategies = self._load_all()
        
        # 更新时间
        now = datetime.now().isoformat()
        if not config.created_at:
            config.created_at = now
        config.updated_at = now
        
        # 查找是否存在
        found = False
        for i, s in enumerate(strategies):
            if s['id'] == config.id:
                strategies[i] = config.to_dict()
                found = True
                break
        
        if not found:
            strategies.append(config.to_dict())
        
        self._save_all(strategies)
        return config.id
    
    def get(self, strategy_id: str) -> Optional[StrategyConfig]:
        """获取策略配置"""
        strategies = self._load_all()
        for s in strategies:
            if s['id'] == strategy_id:
                return StrategyConfig.from_dict(s)
        return None
    
    def get_by_name(self, name: str) -> Optional[StrategyConfig]:
        """按名称获取策略配置"""
        strategies = self._load_all()
        for s in strategies:
            if s['name'] == name:
                return StrategyConfig.from_dict(s)
        return None
    
    def list_all(self, active_only: bool = False) -> List[StrategyConfig]:
        """列出所有策略配置"""
        strategies = self._load_all()
        result = [StrategyConfig.from_dict(s) for s in strategies]
        if active_only:
            result = [s for s in result if s.is_active]
        return result
    
    def delete(self, strategy_id: str) -> bool:
        """删除策略配置"""
        strategies = self._load_all()
        new_strategies = [s for s in strategies if s['id'] != strategy_id]
        
        if len(new_strategies) < len(strategies):
            self._save_all(new_strategies)
            return True
        return False
    
    def create_default_strategies(self):
        """创建默认策略配置"""
        defaults = [
            StrategyConfig(
                id=str(uuid.uuid4())[:8],
                name="USDCNH周五夜盘",
                strategy_type="FridayNightStrategy",
                description="每周五21:00买入USDCNH，周六02:00卖出",
                symbol="USDCNH Curncy",
                parameters={
                    "entry_day": 4,
                    "entry_hour": 21,
                    "exit_hour": 2,
                    "position_size": 100000
                }
            ),
            StrategyConfig(
                id=str(uuid.uuid4())[:8],
                name="USDCNH均线交叉",
                strategy_type="MACrossStrategy",
                description="10/20日均线金叉买入，死叉卖出",
                symbol="USDCNH Curncy",
                parameters={
                    "fast_period": 10,
                    "slow_period": 20,
                    "position_size": 100000
                }
            ),
            StrategyConfig(
                id=str(uuid.uuid4())[:8],
                name="EURUSD周五夜盘",
                strategy_type="FridayNightStrategy",
                description="每周五21:00买入EURUSD，周六02:00卖出",
                symbol="EURUSD Curncy",
                parameters={
                    "entry_day": 4,
                    "entry_hour": 21,
                    "exit_hour": 2,
                    "position_size": 100000
                }
            )
        ]
        
        for config in defaults:
            if not self.get_by_name(config.name):
                self.save(config)
        
        return len(defaults)
