"""
数据源抽象层 - BMAD Base Layer
支持: Excel, Bloomberg API, SQL
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
import logging

from .data_types import OHLCV, ohlcv_list_to_dataframe

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


class ExcelDataSource(BaseDataSource):
    """Excel数据源"""
    
    def __init__(self, file_path: str):
        super().__init__("Excel")
        self.file_path = file_path
        self._data_cache: Dict[str, pd.DataFrame] = {}
    
    def connect(self) -> bool:
        try:
            # 尝试读取Excel文件
            self._excel_file = pd.ExcelFile(self.file_path)
            self._connected = True
            logger.info(f"Excel数据源连接成功: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Excel数据源连接失败: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        self._data_cache.clear()
        self._connected = False
        logger.info("Excel数据源已断开")
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1D"
    ) -> pd.DataFrame:
        if not self._connected:
            raise ConnectionError("Excel数据源未连接")
        
        # 尝试从对应sheet读取数据
        try:
            if symbol not in self._data_cache:
                # 尝试读取以symbol命名的sheet
                df = pd.read_excel(
                    self._excel_file, 
                    sheet_name=symbol,
                    parse_dates=['timestamp'] if 'timestamp' in pd.read_excel(self._excel_file, sheet_name=symbol, nrows=0).columns else [0]
                )
                
                # 标准化列名
                df.columns = df.columns.str.lower()
                if 'date' in df.columns:
                    df.rename(columns={'date': 'timestamp'}, inplace=True)
                
                df.set_index('timestamp', inplace=True)
                self._data_cache[symbol] = df
            
            df = self._data_cache[symbol]
            
            # 过滤日期范围
            mask = (df.index >= start_date) & (df.index <= end_date)
            return df.loc[mask].copy()
            
        except Exception as e:
            logger.error(f"读取Excel数据失败 {symbol}: {e}")
            return pd.DataFrame()
    
    def list_symbols(self) -> List[str]:
        """列出所有可用的symbol (sheet名)"""
        if not self._connected:
            return []
        return self._excel_file.sheet_names


class BloombergDataSource(BaseDataSource):
    """Bloomberg API数据源"""
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        super().__init__("Bloomberg")
        self.host = host
        self.port = port
        self._session = None
        self._service = None
    
    def connect(self) -> bool:
        try:
            import blpapi
            
            # 创建Session选项
            sessionOptions = blpapi.SessionOptions()
            sessionOptions.setServerHost(self.host)
            sessionOptions.setServerPort(self.port)
            
            # 创建Session
            self._session = blpapi.Session(sessionOptions)
            
            if not self._session.start():
                logger.error("Bloomberg Session启动失败")
                return False
            
            if not self._session.openService("//blp/refdata"):
                logger.error("Bloomberg refdata服务打开失败")
                return False
            
            self._service = self._session.getService("//blp/refdata")
            self._connected = True
            logger.info("Bloomberg API连接成功")
            return True
            
        except ImportError:
            logger.error("blpapi库未安装，请运行: pip install blpapi")
            return False
        except Exception as e:
            logger.error(f"Bloomberg连接失败: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        if self._session:
            self._session.stop()
            self._session = None
        self._service = None
        self._connected = False
        logger.info("Bloomberg API已断开")
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1D"
    ) -> pd.DataFrame:
        if not self._connected:
            raise ConnectionError("Bloomberg API未连接")
        
        try:
            import blpapi
            
            # 频率映射
            freq_map = {
                "1M": "MINUTE",
                "5M": "5_MINUTES",
                "15M": "15_MINUTES",
                "30M": "30_MINUTES",
                "1H": "HOURLY",
                "1D": "DAILY",
                "1W": "WEEKLY",
                "1MO": "MONTHLY"
            }
            bbg_freq = freq_map.get(frequency.upper(), "DAILY")
            
            # 创建请求
            request = self._service.createRequest("HistoricalDataRequest")
            request.append("securities", symbol)
            request.append("fields", "PX_OPEN")
            request.append("fields", "PX_HIGH")
            request.append("fields", "PX_LOW")
            request.append("fields", "PX_LAST")
            request.append("fields", "VOLUME")
            
            request.set("startDate", start_date.strftime("%Y%m%d"))
            request.set("endDate", end_date.strftime("%Y%m%d"))
            request.set("periodicitySelection", bbg_freq)
            
            # 发送请求
            self._session.sendRequest(request)
            
            # 收集数据
            data = []
            while True:
                event = self._session.nextEvent(500)
                
                for msg in event:
                    if msg.hasElement("securityData"):
                        security_data = msg.getElement("securityData")
                        field_data = security_data.getElement("fieldData")
                        
                        for i in range(field_data.numValues()):
                            bar = field_data.getValue(i)
                            row = {
                                'timestamp': bar.getElementAsDatetime("date"),
                                'open': bar.getElementAsFloat("PX_OPEN") if bar.hasElement("PX_OPEN") else None,
                                'high': bar.getElementAsFloat("PX_HIGH") if bar.hasElement("PX_HIGH") else None,
                                'low': bar.getElementAsFloat("PX_LOW") if bar.hasElement("PX_LOW") else None,
                                'close': bar.getElementAsFloat("PX_LAST") if bar.hasElement("PX_LAST") else None,
                                'volume': bar.getElementAsFloat("VOLUME") if bar.hasElement("VOLUME") else 0
                            }
                            data.append(row)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            logger.info(f"Bloomberg获取数据成功: {symbol}, {len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"Bloomberg获取数据失败 {symbol}: {e}")
            return pd.DataFrame()
    
    def get_intraday_data(
        self,
        symbol: str,
        start_datetime: datetime,
        end_datetime: datetime,
        interval: int = 1  # 分钟
    ) -> pd.DataFrame:
        """获取日内分钟数据"""
        if not self._connected:
            raise ConnectionError("Bloomberg API未连接")
        
        try:
            import blpapi
            
            request = self._service.createRequest("IntradayBarRequest")
            request.set("security", symbol)
            request.set("eventType", "TRADE")
            request.set("startDateTime", start_datetime)
            request.set("endDateTime", end_datetime)
            request.set("interval", interval)
            
            self._session.sendRequest(request)
            
            data = []
            while True:
                event = self._session.nextEvent(500)
                
                for msg in event:
                    if msg.hasElement("barData"):
                        bar_data = msg.getElement("barData")
                        bar_tick_data = bar_data.getElement("barTickData")
                        
                        for i in range(bar_tick_data.numValues()):
                            bar = bar_tick_data.getValue(i)
                            row = {
                                'timestamp': bar.getElementAsDatetime("time"),
                                'open': bar.getElementAsFloat("open"),
                                'high': bar.getElementAsFloat("high"),
                                'low': bar.getElementAsFloat("low"),
                                'close': bar.getElementAsFloat("close"),
                                'volume': bar.getElementAsFloat("volume")
                            }
                            data.append(row)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Bloomberg日内数据获取失败 {symbol}: {e}")
            return pd.DataFrame()


class SQLDataSource(BaseDataSource):
    """SQL数据库数据源"""
    
    def __init__(self, connection_string: str):
        super().__init__("SQL")
        self.connection_string = connection_string
        self._engine = None
        self._connection = None
    
    def connect(self) -> bool:
        try:
            from sqlalchemy import create_engine
            
            self._engine = create_engine(self.connection_string)
            self._connection = self._engine.connect()
            self._connected = True
            logger.info("SQL数据库连接成功")
            return True
            
        except Exception as e:
            logger.error(f"SQL数据库连接失败: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
        if self._engine:
            self._engine.dispose()
        self._connected = False
        logger.info("SQL数据库已断开")
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = "1D",
        table_name: str = "market_data"
    ) -> pd.DataFrame:
        if not self._connected:
            raise ConnectionError("SQL数据库未连接")
        
        try:
            query = f"""
                SELECT timestamp, open, high, low, close, volume
                FROM {table_name}
                WHERE symbol = :symbol
                AND timestamp >= :start_date
                AND timestamp <= :end_date
                ORDER BY timestamp
            """
            
            df = pd.read_sql(
                query,
                self._connection,
                params={
                    'symbol': symbol,
                    'start_date': start_date,
                    'end_date': end_date
                },
                parse_dates=['timestamp']
            )
            
            if not df.empty:
                df.set_index('timestamp', inplace=True)
            
            logger.info(f"SQL获取数据成功: {symbol}, {len(df)}条")
            return df
            
        except Exception as e:
            logger.error(f"SQL获取数据失败 {symbol}: {e}")
            return pd.DataFrame()
    
    def execute_query(self, query: str, params: dict = None) -> pd.DataFrame:
        """执行自定义SQL查询"""
        if not self._connected:
            raise ConnectionError("SQL数据库未连接")
        
        try:
            return pd.read_sql(query, self._connection, params=params)
        except Exception as e:
            logger.error(f"SQL查询执行失败: {e}")
            return pd.DataFrame()
