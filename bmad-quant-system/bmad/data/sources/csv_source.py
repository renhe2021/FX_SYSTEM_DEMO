"""CSV数据源"""
from datetime import datetime
from typing import Optional, Dict
import pandas as pd
import logging
from pathlib import Path

from .base import BaseDataSource

logger = logging.getLogger(__name__)


class CSVDataSource(BaseDataSource):
    """CSV文件数据源"""
    
    def __init__(self, file_path: str = None, data_dir: str = None):
        super().__init__("CSV")
        self.file_path = file_path
        self.data_dir = Path(data_dir) if data_dir else None
        self._data_cache: Dict[str, pd.DataFrame] = {}
    
    def connect(self) -> bool:
        """连接（验证文件存在）"""
        try:
            if self.file_path and Path(self.file_path).exists():
                self._connected = True
                logger.info(f"CSV数据源连接成功: {self.file_path}")
                return True
            elif self.data_dir and self.data_dir.exists():
                self._connected = True
                logger.info(f"CSV数据目录连接成功: {self.data_dir}")
                return True
            else:
                logger.error("CSV文件或目录不存在")
                return False
        except Exception as e:
            logger.error(f"CSV数据源连接失败: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self._data_cache.clear()
        self._connected = False
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime = None,
        end_date: datetime = None,
        frequency: str = "1D"
    ) -> pd.DataFrame:
        """获取历史数据"""
        # 确定文件路径
        if self.file_path:
            file_path = self.file_path
        elif self.data_dir:
            # 尝试多种文件名格式
            possible_names = [
                f"{symbol}.csv",
                f"{symbol.lower()}.csv",
                f"{symbol.replace(' ', '_')}.csv",
                f"{symbol.replace(' ', '_').lower()}.csv"
            ]
            file_path = None
            for name in possible_names:
                p = self.data_dir / name
                if p.exists():
                    file_path = str(p)
                    break
            
            if not file_path:
                logger.error(f"找不到 {symbol} 的数据文件")
                return pd.DataFrame()
        else:
            return pd.DataFrame()
        
        # 读取数据
        try:
            if file_path not in self._data_cache:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                
                # 标准化列名
                df.columns = df.columns.str.lower()
                
                # 确保有必要的列
                required_cols = ['open', 'high', 'low', 'close']
                if not all(col in df.columns for col in required_cols):
                    # 尝试重命名
                    rename_map = {
                        'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close',
                        'px_open': 'open', 'px_high': 'high', 
                        'px_low': 'low', 'px_last': 'close'
                    }
                    df.rename(columns=rename_map, inplace=True)
                
                self._data_cache[file_path] = df
            
            df = self._data_cache[file_path]
            
            # 过滤日期范围
            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]
            
            logger.info(f"CSV加载成功: {symbol}, {len(df)}条")
            return df.copy()
            
        except Exception as e:
            logger.error(f"CSV读取失败: {e}")
            return pd.DataFrame()
    
    def load_file(self, file_path: str, **kwargs) -> pd.DataFrame:
        """直接加载CSV文件"""
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True, **kwargs)
            df.columns = df.columns.str.lower()
            return df
        except Exception as e:
            logger.error(f"加载文件失败 {file_path}: {e}")
            return pd.DataFrame()
