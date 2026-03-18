"""数据源基类"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BaseDataSource(ABC):
    """数据源基类"""
    
    def __init__(self, name: str):
        self.name = name
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1D"
    ) -> pd.DataFrame:
        """获取历史数据"""
        pass
    
    @property
    def is_connected(self) -> bool:
        return self._connected
