"""数据探索工具

快速探索和分析数据的工具类
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path


class DataExplorer:
    """数据探索器
    
    用于快速加载、探索和分析数据
    
    示例:
    ------
    explorer = DataExplorer()
    explorer.load('usdcnh_intraday.csv')
    explorer.summary()
    explorer.describe()
    explorer.plot()
    """
    
    def __init__(self, data: pd.DataFrame = None):
        self.data = data
        self._file_path = None
    
    def load(self, file_path: str, **kwargs) -> 'DataExplorer':
        """加载数据文件
        
        自动识别CSV/Excel/Parquet格式
        """
        self._file_path = file_path
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            self.data = pd.read_csv(file_path, index_col=0, parse_dates=True, **kwargs)
        elif suffix in ['.xlsx', '.xls']:
            self.data = pd.read_excel(file_path, index_col=0, parse_dates=True, **kwargs)
        elif suffix == '.parquet':
            self.data = pd.read_parquet(file_path, **kwargs)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")
        
        self.data.columns = self.data.columns.str.lower()
        print(f"✓ 加载成功: {len(self.data)} 行, {len(self.data.columns)} 列")
        return self
    
    def summary(self) -> Dict[str, Any]:
        """数据摘要"""
        if self.data is None:
            print("请先加载数据")
            return {}
        
        df = self.data
        
        info = {
            '行数': len(df),
            '列数': len(df.columns),
            '列名': list(df.columns),
            '起始时间': str(df.index[0]) if len(df) > 0 else None,
            '结束时间': str(df.index[-1]) if len(df) > 0 else None,
            '时间跨度': str(df.index[-1] - df.index[0]) if len(df) > 1 else None,
            '缺失值': df.isnull().sum().to_dict()
        }
        
        print("\n" + "=" * 50)
        print("数据摘要")
        print("=" * 50)
        for key, value in info.items():
            print(f"{key}: {value}")
        
        return info
    
    def describe(self, columns: List[str] = None) -> pd.DataFrame:
        """统计描述"""
        if self.data is None:
            print("请先加载数据")
            return pd.DataFrame()
        
        if columns:
            return self.data[columns].describe()
        return self.data.describe()
    
    def head(self, n: int = 10) -> pd.DataFrame:
        """查看前n行"""
        if self.data is None:
            return pd.DataFrame()
        return self.data.head(n)
    
    def tail(self, n: int = 10) -> pd.DataFrame:
        """查看后n行"""
        if self.data is None:
            return pd.DataFrame()
        return self.data.tail(n)
    
    def filter_date(self, start: str = None, end: str = None) -> pd.DataFrame:
        """按日期筛选"""
        if self.data is None:
            return pd.DataFrame()
        
        df = self.data
        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]
        return df
    
    def filter_time(self, start_hour: int = None, end_hour: int = None) -> pd.DataFrame:
        """按时间筛选（小时）"""
        if self.data is None:
            return pd.DataFrame()
        
        df = self.data.copy()
        df['_hour'] = df.index.hour
        
        if start_hour is not None:
            df = df[df['_hour'] >= start_hour]
        if end_hour is not None:
            df = df[df['_hour'] <= end_hour]
        
        return df.drop('_hour', axis=1)
    
    def filter_weekday(self, weekdays: List[int]) -> pd.DataFrame:
        """按星期筛选 (0=周一, 6=周日)"""
        if self.data is None:
            return pd.DataFrame()
        
        return self.data[self.data.index.dayofweek.isin(weekdays)]
    
    def resample(self, freq: str) -> pd.DataFrame:
        """重采样
        
        freq: '1H', '4H', '1D', '1W' 等
        """
        if self.data is None:
            return pd.DataFrame()
        
        df = self.data
        
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            agg = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }
            if 'volume' in df.columns:
                agg['volume'] = 'sum'
            return df.resample(freq).agg(agg).dropna()
        
        return df.resample(freq).last().dropna()
    
    def returns(self, column: str = 'close', periods: int = 1) -> pd.Series:
        """计算收益率"""
        if self.data is None or column not in self.data.columns:
            return pd.Series()
        
        return self.data[column].pct_change(periods)
    
    def rolling_stats(self, column: str = 'close', window: int = 20) -> pd.DataFrame:
        """滚动统计"""
        if self.data is None or column not in self.data.columns:
            return pd.DataFrame()
        
        series = self.data[column]
        
        return pd.DataFrame({
            'mean': series.rolling(window).mean(),
            'std': series.rolling(window).std(),
            'min': series.rolling(window).min(),
            'max': series.rolling(window).max()
        })
    
    def plot(self, column: str = 'close', **kwargs):
        """快速绘图"""
        if self.data is None:
            print("请先加载数据")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            if column in self.data.columns:
                self.data[column].plot(figsize=(12, 6), **kwargs)
                plt.title(f'{column.upper()} - {self._file_path or "Data"}')
                plt.tight_layout()
                plt.show()
            else:
                print(f"列 '{column}' 不存在")
        except ImportError:
            print("请安装 matplotlib: pip install matplotlib")
    
    def to_csv(self, file_path: str, **kwargs):
        """导出CSV"""
        if self.data is not None:
            self.data.to_csv(file_path, **kwargs)
            print(f"✓ 已导出: {file_path}")
    
    def to_parquet(self, file_path: str, **kwargs):
        """导出Parquet"""
        if self.data is not None:
            self.data.to_parquet(file_path, **kwargs)
            print(f"✓ 已导出: {file_path}")


# 便捷函数
def explore(file_path: str) -> DataExplorer:
    """快速探索数据文件"""
    return DataExplorer().load(file_path)
