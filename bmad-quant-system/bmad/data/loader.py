"""数据加载器"""
from pathlib import Path
from typing import Optional, Union
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """统一数据加载器
    
    支持多种数据格式和来源
    """
    
    @staticmethod
    def load_csv(file_path: str, 
                 date_column: str = None,
                 **kwargs) -> pd.DataFrame:
        """加载CSV文件
        
        Args:
            file_path: CSV文件路径
            date_column: 日期列名，默认使用第一列
            **kwargs: 传递给pd.read_csv的其他参数
        
        Returns:
            DataFrame with datetime index
        """
        try:
            if date_column:
                df = pd.read_csv(file_path, parse_dates=[date_column], **kwargs)
                df.set_index(date_column, inplace=True)
            else:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True, **kwargs)
            
            # 标准化列名
            df.columns = df.columns.str.lower()
            
            logger.info(f"加载CSV成功: {file_path}, {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"加载CSV失败 {file_path}: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def load_excel(file_path: str,
                   sheet_name: Union[str, int] = 0,
                   date_column: str = None,
                   **kwargs) -> pd.DataFrame:
        """加载Excel文件"""
        try:
            if date_column:
                df = pd.read_excel(file_path, sheet_name=sheet_name, 
                                   parse_dates=[date_column], **kwargs)
                df.set_index(date_column, inplace=True)
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name,
                                   index_col=0, parse_dates=True, **kwargs)
            
            df.columns = df.columns.str.lower()
            
            logger.info(f"加载Excel成功: {file_path}, {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"加载Excel失败 {file_path}: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def load_parquet(file_path: str) -> pd.DataFrame:
        """加载Parquet文件"""
        try:
            df = pd.read_parquet(file_path)
            
            # 如果index不是datetime，尝试转换
            if not isinstance(df.index, pd.DatetimeIndex):
                for col in ['timestamp', 'date', 'datetime', 'time']:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                        df.set_index(col, inplace=True)
                        break
            
            df.columns = df.columns.str.lower()
            
            logger.info(f"加载Parquet成功: {file_path}, {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"加载Parquet失败 {file_path}: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def load(file_path: str, **kwargs) -> pd.DataFrame:
        """自动识别格式并加载
        
        根据文件扩展名自动选择加载方法
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            return DataLoader.load_csv(file_path, **kwargs)
        elif suffix in ['.xlsx', '.xls']:
            return DataLoader.load_excel(file_path, **kwargs)
        elif suffix == '.parquet':
            return DataLoader.load_parquet(file_path)
        else:
            logger.error(f"不支持的文件格式: {suffix}")
            return pd.DataFrame()
    
    @staticmethod
    def resample(df: pd.DataFrame, 
                 freq: str,
                 ohlc_cols: bool = True) -> pd.DataFrame:
        """重采样数据
        
        Args:
            df: 原始数据
            freq: 目标频率 ('1H', '4H', '1D', '1W', etc.)
            ohlc_cols: 是否使用OHLC聚合方式
        
        Returns:
            重采样后的DataFrame
        """
        if ohlc_cols and all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            agg_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }
            if 'volume' in df.columns:
                agg_dict['volume'] = 'sum'
            
            return df.resample(freq).agg(agg_dict).dropna()
        else:
            return df.resample(freq).last().dropna()
