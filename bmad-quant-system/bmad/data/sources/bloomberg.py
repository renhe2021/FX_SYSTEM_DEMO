"""Bloomberg数据源"""
from datetime import datetime
from typing import Optional
import pandas as pd
import logging

from .base import BaseDataSource

logger = logging.getLogger(__name__)


class BloombergDataSource(BaseDataSource):
    """Bloomberg API数据源"""
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        super().__init__("Bloomberg")
        self.host = host
        self.port = port
        self._session = None
        self._service = None
    
    def connect(self) -> bool:
        """连接Bloomberg API"""
        try:
            import blpapi
            
            sessionOptions = blpapi.SessionOptions()
            sessionOptions.setServerHost(self.host)
            sessionOptions.setServerPort(self.port)
            
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
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
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
        """获取历史数据"""
        if not self._connected:
            raise ConnectionError("Bloomberg API未连接")
        
        try:
            import blpapi
            
            freq_map = {
                "1M": "MINUTE", "5M": "5_MINUTES", "15M": "15_MINUTES",
                "30M": "30_MINUTES", "1H": "HOURLY", "1D": "DAILY",
                "1W": "WEEKLY", "1MO": "MONTHLY"
            }
            bbg_freq = freq_map.get(frequency.upper(), "DAILY")
            
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
            
            self._session.sendRequest(request)
            
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
        interval: int = 1
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
