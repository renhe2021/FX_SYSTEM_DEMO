"""
数据管理器 - BMAD Base Layer
统一管理多数据源
"""
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
import logging

from .data_source import BaseDataSource

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理器 - 统一管理多数据源"""
    
    def __init__(self):
        self._sources: Dict[str, BaseDataSource] = {}
        self._primary_source: Optional[str] = None
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_enabled = True
    
    def register_source(self, name: str, source: BaseDataSource, primary: bool = False) -> None:
        """注册数据源"""
        self._sources[name] = source
        if primary or self._primary_source is None:
            self._primary_source = name
        logger.info(f"数据源已注册: {name}, primary={primary}")
    
    def unregister_source(self, name: str) -> None:
        """注销数据源"""
        if name in self._sources:
            self._sources[name].disconnect()
            del self._sources[name]
            if self._primary_source == name:
                self._primary_source = next(iter(self._sources), None)
            logger.info(f"数据源已注销: {name}")
    
    def connect_all(self) -> Dict[str, bool]:
        """连接所有数据源"""
        results = {}
        for name, source in self._sources.items():
            results[name] = source.connect()
        return results
    
    def disconnect_all(self) -> None:
        """断开所有数据源"""
        for source in self._sources.values():
            source.disconnect()
        self._cache.clear()
    
    def get_source(self, name: str = None) -> Optional[BaseDataSource]:
        """获取数据源"""
        if name is None:
            name = self._primary_source
        return self._sources.get(name)
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1D",
        source_name: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """获取历史数据"""
        
        # 生成缓存键
        cache_key = f"{symbol}_{start_date}_{end_date}_{frequency}_{source_name}"
        
        # 检查缓存
        if use_cache and self._cache_enabled and cache_key in self._cache:
            logger.debug(f"从缓存获取数据: {cache_key}")
            return self._cache[cache_key].copy()
        
        # 确定数据源
        source = self.get_source(source_name)
        if source is None:
            raise ValueError(f"数据源不存在: {source_name or self._primary_source}")
        
        if not source.is_connected:
            if not source.connect():
                raise ConnectionError(f"数据源连接失败: {source.name}")
        
        # 获取数据
        df = source.get_historical_data(symbol, start_date, end_date, frequency)
        
        # 缓存数据
        if self._cache_enabled and not df.empty:
            self._cache[cache_key] = df.copy()
        
        return df
    
    def get_multiple_symbols(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1D",
        source_name: str = None
    ) -> Dict[str, pd.DataFrame]:
        """获取多个symbol的数据"""
        result = {}
        for symbol in symbols:
            try:
                df = self.get_historical_data(
                    symbol, start_date, end_date, frequency, source_name
                )
                result[symbol] = df
            except Exception as e:
                logger.error(f"获取{symbol}数据失败: {e}")
                result[symbol] = pd.DataFrame()
        return result
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        logger.info("数据缓存已清除")
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """设置缓存开关"""
        self._cache_enabled = enabled
    
    @property
    def available_sources(self) -> List[str]:
        """获取所有可用数据源名称"""
        return list(self._sources.keys())
    
    @property
    def primary_source_name(self) -> Optional[str]:
        """获取主数据源名称"""
        return self._primary_source
