"""数据加载器 - 默认从Bloomberg加载，失败则提示用户使用本地文件"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from .config_schema import (
    DataSourceConfig,
    DataSourceType,
    Frequency
)


class DataLoader:
    """
    数据加载器
    
    加载顺序：
    1. 默认尝试从Bloomberg API加载
    2. 如果BBG失败，打印日志，提示用户可以使用本地文件
    3. 如果配置了本地文件路径，尝试从本地文件加载
    4. 都失败则报错
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._data: Optional[pd.DataFrame] = None
    
    def load(self) -> pd.DataFrame:
        """
        加载数据
        
        默认先尝试Bloomberg，失败则尝试本地文件
        """
        # 如果明确指定了local_csv或local_excel，直接用本地文件
        if self.config.type == DataSourceType.LOCAL_CSV:
            return self._load_from_csv()
        elif self.config.type == DataSourceType.LOCAL_EXCEL:
            return self._load_from_excel()
        elif self.config.type == DataSourceType.SQL:
            return self._load_from_sql()
        
        # 默认：先尝试Bloomberg
        print(f"[DataLoader] 尝试从Bloomberg加载数据: {self.config.symbol}")
        
        try:
            data = self._load_from_bloomberg()
            print(f"[DataLoader] Bloomberg加载成功: {len(data)} 行")
            return data
        except Exception as e:
            print(f"\n" + "=" * 60)
            print(f"[DataLoader] Bloomberg连接失败: {e}")
            print(f"=" * 60)
            print(f"[DataLoader] 请确保:")
            print(f"  1. Bloomberg Terminal已启动并登录")
            print(f"  2. blpapi已安装: pip install blpapi")
            print(f"  3. 网络连接正常")
            
            # 检查是否有本地文件可用
            local_path = self.config.local_file.path if self.config.local_file else None
            
            if local_path and Path(local_path).exists():
                print(f"\n[DataLoader] 检测到本地文件: {local_path}")
                print(f"[DataLoader] 将使用本地文件作为替代数据源...")
                print(f"=" * 60 + "\n")
                
                return self._load_from_csv()
            else:
                print(f"\n[DataLoader] 未找到本地备份文件")
                if local_path:
                    print(f"[DataLoader] 配置的路径: {local_path} (文件不存在)")
                print(f"[DataLoader] 请先运行 fetch_bbg_data.py 下载数据，或手动准备CSV文件")
                print(f"=" * 60 + "\n")
                
                raise RuntimeError(
                    f"无法加载数据: Bloomberg连接失败且无本地文件可用。\n"
                    f"请先启动Bloomberg Terminal，或准备本地CSV文件。"
                )
    
    def _get_date_range(self) -> tuple:
        """获取日期范围"""
        end_date = datetime.now()
        
        if self.config.end_date:
            end_date = datetime.strptime(self.config.end_date, "%Y-%m-%d")
        
        if self.config.start_date:
            start_date = datetime.strptime(self.config.start_date, "%Y-%m-%d")
        else:
            start_date = end_date - timedelta(days=self.config.days_back)
        
        return start_date, end_date
    
    def _load_from_bloomberg(self) -> pd.DataFrame:
        """从Bloomberg加载数据"""
        from quant_system.base import BloombergDataSource
        
        bbg_config = self.config.bloomberg
        start_date, end_date = self._get_date_range()
        
        print(f"[BBG] 连接Bloomberg: {bbg_config.host}:{bbg_config.port}")
        print(f"[BBG] 品种: {self.config.symbol}")
        print(f"[BBG] 日期范围: {start_date.date()} ~ {end_date.date()}")
        
        bbg = BloombergDataSource(
            host=bbg_config.host,
            port=bbg_config.port
        )
        
        if not bbg.connect():
            raise ConnectionError("Bloomberg连接失败")
        
        try:
            freq = self.config.frequency
            
            # 分钟级数据使用IntradayBarRequest
            if freq in [Frequency.MINUTE_1, Frequency.MINUTE_5, Frequency.MINUTE_15, Frequency.MINUTE_30]:
                interval_map = {
                    Frequency.MINUTE_1: 1,
                    Frequency.MINUTE_5: 5,
                    Frequency.MINUTE_15: 15,
                    Frequency.MINUTE_30: 30
                }
                data = bbg.get_intraday_data(
                    self.config.symbol,
                    start_date,
                    end_date,
                    interval=interval_map[freq]
                )
            else:
                # 日线及以上使用HistoricalDataRequest
                freq_map = {
                    Frequency.HOUR_1: "1H",
                    Frequency.DAILY: "1D",
                    Frequency.WEEKLY: "1W"
                }
                data = bbg.get_historical_data(
                    self.config.symbol,
                    start_date,
                    end_date,
                    frequency=freq_map.get(freq, "1D")
                )
            
            print(f"[BBG] 加载完成: {len(data)} 行")
            return data
            
        finally:
            bbg.disconnect()
    
    def _load_from_csv(self) -> pd.DataFrame:
        """从CSV文件加载数据"""
        file_config = self.config.local_file
        
        if not file_config.path:
            raise ValueError("CSV文件路径未指定")
        
        path = Path(file_config.path)
        if not path.exists():
            raise FileNotFoundError(f"CSV文件不存在: {file_config.path}")
        
        print(f"[CSV] 加载文件: {file_config.path}")
        
        # 读取CSV
        try:
            data = pd.read_csv(
                file_config.path,
                parse_dates=[file_config.date_column],
                index_col=file_config.date_column
            )
        except (KeyError, ValueError):
            # 如果指定的列不存在，尝试用第一列
            data = pd.read_csv(file_config.path, index_col=0, parse_dates=True)
        
        # 确保索引是datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        # 标准化列名
        data.columns = data.columns.str.lower()
        
        # 移除时区信息
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
        
        # 过滤日期范围
        start_date, end_date = self._get_date_range()
        data = data[(data.index >= pd.Timestamp(start_date)) & (data.index <= pd.Timestamp(end_date))]
        
        print(f"[CSV] 加载完成: {len(data)} 行")
        print(f"[CSV] 日期范围: {data.index[0]} ~ {data.index[-1]}")
        
        return data
    
    def _load_from_excel(self) -> pd.DataFrame:
        """从Excel文件加载数据"""
        file_config = self.config.local_file
        
        if not file_config.path:
            raise ValueError("Excel文件路径未指定")
        
        print(f"[Excel] 加载文件: {file_config.path}")
        
        data = pd.read_excel(
            file_config.path,
            parse_dates=[file_config.date_column]
        )
        
        if file_config.date_column in data.columns:
            data.set_index(file_config.date_column, inplace=True)
        
        data.columns = data.columns.str.lower()
        
        start_date, end_date = self._get_date_range()
        data = data[(data.index >= start_date) & (data.index <= end_date)]
        
        print(f"[Excel] 加载完成: {len(data)} 行")
        return data
    
    def _load_from_sql(self) -> pd.DataFrame:
        """从SQL数据库加载数据"""
        from quant_system.base import SQLDataSource
        
        sql_config = self.config.sql
        start_date, end_date = self._get_date_range()
        
        print(f"[SQL] 连接数据库...")
        
        sql = SQLDataSource(sql_config.connection_string)
        
        if not sql.connect():
            raise ConnectionError("SQL数据库连接失败")
        
        try:
            data = sql.get_historical_data(
                self.config.symbol,
                start_date,
                end_date,
                table_name=sql_config.table_name
            )
            
            print(f"[SQL] 加载完成: {len(data)} 行")
            return data
            
        finally:
            sql.disconnect()


def load_data(config: DataSourceConfig) -> pd.DataFrame:
    """便捷函数：加载数据"""
    loader = DataLoader(config)
    return loader.load()
