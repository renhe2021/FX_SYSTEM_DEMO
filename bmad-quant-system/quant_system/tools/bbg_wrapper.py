"""
Bloomberg API 统一封装
======================

支持数据类型：
- Bar Data (K线 OHLCV) - IntradayBarRequest
- Tick Data (逐笔成交) - IntradayTickRequest  
- Bid/Ask (买卖盘报价) - IntradayTickRequest with BID/ASK events
- Reference Data (参考数据) - ReferenceDataRequest
- Historical Data (历史日线) - HistoricalDataRequest

时区说明：
- 所有输入时间默认为北京时间（Asia/Shanghai）
- 发送给Bloomberg API之前自动转换为UTC
- 返回的数据时间戳为UTC（由调用方转换为目标时区）
"""

import pandas as pd
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# 北京时间与UTC的时差（小时）
BEIJING_UTC_OFFSET = 8


def beijing_now() -> datetime:
    """获取当前北京时间"""
    return datetime.utcnow() + timedelta(hours=BEIJING_UTC_OFFSET)


def beijing_to_utc(dt: datetime) -> datetime:
    """将北京时间转换为UTC时间"""
    return dt - timedelta(hours=BEIJING_UTC_OFFSET)


def utc_to_beijing(dt: datetime) -> datetime:
    """将UTC时间转换为北京时间"""
    return dt + timedelta(hours=BEIJING_UTC_OFFSET)


class DataType(Enum):
    """数据类型枚举"""
    BAR_1M = "1m"
    BAR_5M = "5m"
    BAR_15M = "15m"
    BAR_30M = "30m"
    BAR_1H = "1h"
    BAR_1D = "1d"
    TICK = "tick"
    BID_ASK = "bid_ask"
    REFERENCE = "reference"


@dataclass
class DownloadRequest:
    """下载请求"""
    symbol: str
    data_type: DataType
    start_date: datetime
    end_date: datetime
    fields: Optional[List[str]] = None


class BloombergWrapper:
    """
    Bloomberg API 统一封装
    
    使用方法：
    ---------
    bbg = BloombergWrapper()
    bbg.connect()
    
    # K线数据
    bars = bbg.get_bars("USDCNH Curncy", interval="1m", days_back=7)
    
    # Tick数据
    ticks = bbg.get_ticks("USDCNH Curncy", hours_back=1)
    
    # Bid/Ask数据
    quotes = bbg.get_bid_ask("USDCNH Curncy", hours_back=1)
    
    bbg.disconnect()
    """
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        self.host = host
        self.port = port
        self._session = None
        self._refdata_service = None
        self._connected = False
    
    def connect(self) -> bool:
        """连接Bloomberg Terminal"""
        try:
            import blpapi
            
            sessionOptions = blpapi.SessionOptions()
            sessionOptions.setServerHost(self.host)
            sessionOptions.setServerPort(self.port)
            
            self._session = blpapi.Session(sessionOptions)
            
            if not self._session.start():
                print(f"[BBG] Cannot start Session")
                return False
            
            if not self._session.openService("//blp/refdata"):
                print(f"[BBG] Cannot open refdata service")
                return False
            
            self._refdata_service = self._session.getService("//blp/refdata")
            self._connected = True
            print(f"[BBG] Connected: {self.host}:{self.port}")
            return True
            
        except ImportError:
            print("[BBG] Error: blpapi not installed, run: pip install blpapi")
            return False
        except Exception as e:
            print(f"[BBG] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self._session:
            self._session.stop()
            self._session = None
            self._refdata_service = None
            self._connected = False
            print("[BBG] Disconnected")
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def check_alive(self) -> bool:
        """检查Bloomberg连接是否真正可用（活性检查）
        
        不仅检查内部标记，还验证session是否仍在运行。
        如果Bloomberg Terminal已关闭，会更新内部状态并返回False。
        """
        if not self._connected or self._session is None:
            self._connected = False
            return False
        
        try:
            # 尝试发送一个轻量级的参考数据请求来验证连接
            import blpapi
            request = self._refdata_service.createRequest("ReferenceDataRequest")
            request.append("securities", "USD Curncy")
            request.append("fields", "ID_BB_GLOBAL")
            
            cid = self._session.sendRequest(request)
            
            # 等待响应，设置超时5秒
            import time
            start_time = time.time()
            while True:
                event = self._session.nextEvent(3000)  # 3秒超时
                if event.eventType() in (blpapi.Event.RESPONSE, blpapi.Event.PARTIAL_RESPONSE):
                    return True  # 收到响应，连接正常
                if event.eventType() == blpapi.Event.TIMEOUT:
                    break
                if time.time() - start_time > 5:
                    break
            
            # 超时或无响应，连接可能已断开
            print("[BBG] Connection check: no response, marking as disconnected")
            self._connected = False
            return False
            
        except Exception as e:
            print(f"[BBG] Connection check failed: {e}")
            self._connected = False
            self._session = None
            self._refdata_service = None
            return False
    
    def _ensure_connected(self) -> bool:
        """确保已连接"""
        if not self._connected:
            return self.connect()
        return True

    # ========================================
    # K线数据 (IntradayBarRequest)
    # ========================================
    
    def get_bars(
        self,
        symbol: str,
        interval: str = "1m",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = 30,
        is_beijing_time: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取K线数据 (OHLCV)
        
        Args:
            symbol: Bloomberg代码，如 "USDCNH Curncy"
            interval: 时间间隔 (1m/5m/15m/30m/1h)
            start_date: 起始时间（默认北京时间）
            end_date: 结束时间（默认北京时间）
            days_back: 向前天数（如果未指定start_date）
            is_beijing_time: 输入时间是否为北京时间（默认True）
        
        Returns:
            DataFrame: timestamp(index), open, high, low, close, volume, num_events
            注意：返回的时间戳为UTC，由调用方转换为目标时区
        """
        if not self._ensure_connected():
            return None
        
        try:
            import blpapi
            
            # 处理日期 - 默认使用北京时间
            if end_date is None:
                end_date = beijing_now()  # 当前北京时间
            if start_date is None:
                start_date = end_date - timedelta(days=days_back)
            
            # 如果输入是北京时间，转换为UTC
            if is_beijing_time:
                start_date_utc = beijing_to_utc(start_date)
                end_date_utc = beijing_to_utc(end_date)
            else:
                start_date_utc = start_date
                end_date_utc = end_date
            
            # interval映射到分钟数
            interval_map = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60}
            interval_minutes = interval_map.get(interval, 1)
            
            request = self._refdata_service.createRequest("IntradayBarRequest")
            request.set("security", symbol)
            request.set("eventType", "TRADE")
            request.set("interval", interval_minutes)
            request.set("startDateTime", start_date_utc)
            request.set("endDateTime", end_date_utc)
            
            print(f"[BBG] Request bars: {symbol}, {interval}")
            print(f"[BBG]   Beijing time: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"[BBG]   UTC time: {start_date_utc.strftime('%Y-%m-%d %H:%M')} ~ {end_date_utc.strftime('%Y-%m-%d %H:%M')}")
            
            self._session.sendRequest(request)
            
            data = []
            while True:
                event = self._session.nextEvent(5000)
                
                for msg in event:
                    if msg.hasElement("barData"):
                        barData = msg.getElement("barData")
                        if barData.hasElement("barTickData"):
                            tickData = barData.getElement("barTickData")
                            for i in range(tickData.numValues()):
                                bar = tickData.getValueAsElement(i)
                                data.append({
                                    'timestamp': bar.getElementAsDatetime("time"),
                                    'open': bar.getElementAsFloat("open"),
                                    'high': bar.getElementAsFloat("high"),
                                    'low': bar.getElementAsFloat("low"),
                                    'close': bar.getElementAsFloat("close"),
                                    'volume': bar.getElementAsInteger("volume") if bar.hasElement("volume") else 0,
                                    'num_events': bar.getElementAsInteger("numEvents") if bar.hasElement("numEvents") else 0
                                })
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                print(f"[BBG] Bar data is empty")
                return None
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            print(f"[BBG] Bars loaded: {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"[BBG] Get bars failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ========================================
    # Tick数据 (IntradayTickRequest - TRADE)
    # ========================================
    
    def get_ticks(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        hours_back: float = 1,
        include_condition_codes: bool = True,
        is_beijing_time: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取逐笔成交Tick数据
        
        Args:
            symbol: Bloomberg代码
            start_date: 起始时间（默认北京时间）
            end_date: 结束时间（默认北京时间）
            hours_back: 向前小时数
            include_condition_codes: 是否包含条件代码
            is_beijing_time: 输入时间是否为北京时间（默认True）
        
        Returns:
            DataFrame: timestamp(index), price, size, condition_code
            注意：返回的时间戳为UTC
        """
        if not self._ensure_connected():
            return None
        
        try:
            import blpapi
            
            # 处理日期 - 默认使用北京时间
            if end_date is None:
                end_date = beijing_now()  # 当前北京时间
            if start_date is None:
                start_date = end_date - timedelta(hours=hours_back)
            
            # 如果输入是北京时间，转换为UTC
            if is_beijing_time:
                start_date_utc = beijing_to_utc(start_date)
                end_date_utc = beijing_to_utc(end_date)
            else:
                start_date_utc = start_date
                end_date_utc = end_date
            
            print(f"[BBG] get_ticks called: symbol={symbol}")
            print(f"[BBG]   Beijing time: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"[BBG]   UTC time: {start_date_utc.strftime('%Y-%m-%d %H:%M')} ~ {end_date_utc.strftime('%Y-%m-%d %H:%M')}")
            
            request = self._refdata_service.createRequest("IntradayTickRequest")
            request.set("security", symbol)
            
            # eventTypes - 只要TRADE
            eventTypes = request.getElement("eventTypes")
            eventTypes.appendValue("TRADE")
            
            request.set("startDateTime", start_date_utc)
            request.set("endDateTime", end_date_utc)
            request.set("includeConditionCodes", include_condition_codes)
            
            self._session.sendRequest(request)
            
            data = []
            while True:
                event = self._session.nextEvent(5000)
                
                for msg in event:
                    if msg.hasElement("tickData"):
                        tickData = msg.getElement("tickData")
                        if tickData.hasElement("tickData"):
                            ticks = tickData.getElement("tickData")
                            for i in range(ticks.numValues()):
                                tick = ticks.getValueAsElement(i)
                                row = {
                                    'timestamp': tick.getElementAsDatetime("time"),
                                    'price': tick.getElementAsFloat("value") if tick.hasElement("value") else None,
                                    'size': tick.getElementAsInteger("size") if tick.hasElement("size") else 0,
                                }
                                if include_condition_codes and tick.hasElement("conditionCodes"):
                                    row['condition_code'] = tick.getElementAsString("conditionCodes")
                                data.append(row)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                print(f"[BBG] Tick data is empty")
                return None
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            print(f"[BBG] Tick loaded: {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"[BBG] Get Tick failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ========================================
    # Bid/Ask数据 (IntradayTickRequest - BID/ASK) - 优化版
    # ========================================
    
    def get_bid_ask(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        hours_back: float = 1,
        is_beijing_time: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取Bid/Ask报价数据 (优化版: 预分配内存, 批量处理)
        
        Args:
            symbol: Bloomberg代码
            start_date: 起始时间（默认北京时间）
            end_date: 结束时间（默认北京时间）
            hours_back: 向前小时数
            is_beijing_time: 输入时间是否为北京时间（默认True）
        
        Returns:
            DataFrame: timestamp(index), type(BID/ASK), price, size
            注意：返回的时间戳为UTC
        """
        if not self._ensure_connected():
            return None
        
        try:
            import blpapi
            
            # 处理日期 - 默认使用北京时间
            if end_date is None:
                end_date = beijing_now()  # 当前北京时间
            if start_date is None:
                start_date = end_date - timedelta(hours=hours_back)
            
            # 如果输入是北京时间，转换为UTC
            if is_beijing_time:
                start_date_utc = beijing_to_utc(start_date)
                end_date_utc = beijing_to_utc(end_date)
            else:
                start_date_utc = start_date
                end_date_utc = end_date
            
            print(f"[BBG] Requesting Bid/Ask ticks: {symbol}")
            print(f"[BBG]   Beijing time: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"[BBG]   UTC time: {start_date_utc.strftime('%Y-%m-%d %H:%M')} ~ {end_date_utc.strftime('%Y-%m-%d %H:%M')}")
            
            request = self._refdata_service.createRequest("IntradayTickRequest")
            request.set("security", symbol)
            
            # eventTypes - BID和ASK
            eventTypes = request.getElement("eventTypes")
            eventTypes.appendValue("BID")
            eventTypes.appendValue("ASK")
            
            request.set("startDateTime", start_date_utc)
            request.set("endDateTime", end_date_utc)
            
            self._session.sendRequest(request)
            
            # 优化: 预分配列表, 批量收集数据
            timestamps = []
            types = []
            prices = []
            sizes = []
            
            total_ticks = 0
            while True:
                event = self._session.nextEvent(5000)
                
                for msg in event:
                    if msg.hasElement("tickData"):
                        tickData = msg.getElement("tickData")
                        if tickData.hasElement("tickData"):
                            ticks = tickData.getElement("tickData")
                            num_ticks = ticks.numValues()
                            total_ticks += num_ticks
                            
                            # 批量提取数据
                            for i in range(num_ticks):
                                tick = ticks.getValueAsElement(i)
                                timestamps.append(tick.getElementAsDatetime("time"))
                                types.append(tick.getElementAsString("type") if tick.hasElement("type") else "")
                                prices.append(tick.getElementAsFloat("value") if tick.hasElement("value") else None)
                                sizes.append(tick.getElementAsInteger("size") if tick.hasElement("size") else 0)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not timestamps:
                print(f"[BBG] Bid/Ask data is empty")
                return None
            
            # 优化: 直接从列表构建DataFrame (比逐行append快很多)
            df = pd.DataFrame({
                'type': types,
                'price': prices,
                'size': sizes
            }, index=pd.to_datetime(timestamps))
            df.index.name = 'timestamp'
            
            bid_count = (df['type'] == 'BID').sum()
            ask_count = (df['type'] == 'ASK').sum()
            print(f"[BBG] Bid/Ask loaded: {len(df)} ticks (BID: {bid_count}, ASK: {ask_count})")
            
            return df
            
        except Exception as e:
            print(f"[BBG] Get Bid/Ask failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ========================================
    # Bid/Ask Bar数据 (智能选择: 秒级用tick重采样, 分钟级用Bar请求)
    # ========================================
    
    def get_bid_ask_bars(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        hours_back: float = 1,
        resample: str = "1min",
        is_beijing_time: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取Bid/Ask Bar数据
        
        策略: 优先尝试 IntradayBarRequest, 失败则回退到 tick 重采样
        
        Args:
            symbol: Bloomberg代码
            start_date: 起始时间（默认北京时间）
            end_date: 结束时间（默认北京时间）
            hours_back: 向前小时数
            resample: 重采样频率 (1s/5s/10s/30s/1min/5min/...)
            is_beijing_time: 输入时间是否为北京时间（默认True）
        
        Returns:
            DataFrame: timestamp(index), bid, ask, spread, mid
            注意：返回的时间戳为UTC
        """
        if not self._ensure_connected():
            return None
        
        # 处理日期 - 默认使用北京时间
        if end_date is None:
            end_date = beijing_now()  # 当前北京时间
        if start_date is None:
            start_date = end_date - timedelta(hours=hours_back)
        
        # 如果输入是北京时间，转换为UTC
        if is_beijing_time:
            start_date_utc = beijing_to_utc(start_date)
            end_date_utc = beijing_to_utc(end_date)
        else:
            start_date_utc = start_date
            end_date_utc = end_date
        
        print(f"[BBG] Bid/Ask Bars: {symbol}")
        print(f"[BBG]   Beijing time: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"[BBG]   UTC time: {start_date_utc.strftime('%Y-%m-%d %H:%M')} ~ {end_date_utc.strftime('%Y-%m-%d %H:%M')}")
        
        # 解析间隔
        interval_seconds = self._parse_interval_to_seconds(resample)
        
        # 优先尝试 IntradayBarRequest (Excel BDH 支持秒级 BarSize)
        print(f"[BBG] Bid/Ask Bars: trying Bar request, interval={interval_seconds}s")
        result = self._get_bid_ask_bars_from_bar_request_seconds(symbol, start_date_utc, end_date_utc, interval_seconds)
        
        if result is not None and not result.empty:
            return result
        
        # Bar 请求失败, 回退到 tick 重采样
        print(f"[BBG] Bar request failed or wrong interval, fallback to tick resample")
        return self._get_bid_ask_bars_from_ticks(symbol, start_date_utc, end_date_utc, hours_back, resample)
    
    def _parse_interval_to_seconds(self, interval: str) -> int:
        """将间隔字符串转换为秒数"""
        interval = interval.lower().strip()
        
        # 秒级映射
        if interval.endswith('s'):
            try:
                return int(interval[:-1])
            except ValueError:
                pass
        
        # 分钟级映射
        interval_map = {
            "1m": 60, "1min": 60,
            "2m": 120, "2min": 120,
            "5m": 300, "5min": 300,
            "10m": 600, "10min": 600,
            "15m": 900, "15min": 900,
            "30m": 1800, "30min": 1800,
            "1h": 3600, "60m": 3600, "60min": 3600,
        }
        
        if interval in interval_map:
            return interval_map[interval]
        
        # 尝试解析分钟数
        if 'min' in interval:
            try:
                minutes = int(interval.replace('min', ''))
                return minutes * 60
            except ValueError:
                pass
        
        # 默认1分钟
        return 60
    
    def _get_bid_ask_bars_from_ticks(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        hours_back: float,
        resample: str
    ) -> Optional[pd.DataFrame]:
        """
        从tick数据重采样生成Bid/Ask Bars (优化版: 更高效的重采样)
        
        注意：此方法接收UTC时间参数
        """
        import time
        t0 = time.time()
        
        # 传递 is_beijing_time=False 因为已经是UTC时间
        df = self.get_bid_ask(symbol, start_date, end_date, hours_back, is_beijing_time=False)
        t1 = time.time()
        print(f"[BBG] Tick download time: {t1-t0:.2f}s")
        
        if df is None or df.empty:
            return None
        
        try:
            t2 = time.time()
            
            # 优化: 使用更高效的方式处理
            # 创建bid和ask的Series (避免创建多余的DataFrame)
            is_bid = df['type'] == 'BID'
            is_ask = df['type'] == 'ASK'
            
            bid_prices = df.loc[is_bid, 'price']
            ask_prices = df.loc[is_ask, 'price']
            
            # 重采样 - 使用 last() 取最后一个值
            bids_resampled = bid_prices.resample(resample).last()
            asks_resampled = ask_prices.resample(resample).last()
            
            # 合并为DataFrame
            result = pd.DataFrame({
                'bid': bids_resampled,
                'ask': asks_resampled
            })
            
            # 前向填充
            result = result.ffill()
            
            # 计算spread和mid (向量化操作)
            result['spread'] = result['ask'] - result['bid']
            result['mid'] = (result['ask'] + result['bid']) * 0.5
            
            # 删除空行
            result = result.dropna()
            
            t3 = time.time()
            print(f"[BBG] Resample time: {t3-t2:.2f}s | Total: {t3-t0:.2f}s")
            print(f"[BBG] Bid/Ask Bars (from ticks): {len(result)} rows, resample={resample}")
            return result
            
        except Exception as e:
            print(f"[BBG] Process Bid/Ask Bars from ticks failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_bid_ask_bars_from_bar_request_seconds(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval_seconds: int
    ) -> Optional[pd.DataFrame]:
        """
        尝试使用IntradayBarRequest获取Bid/Ask Bars (秒级/分钟级)
        
        Excel BDH 支持秒级 BarSize, 尝试直接传秒数给 interval 参数
        如果返回的数据间隔不对, 返回 None 让调用方回退到 tick 重采样
        """
        try:
            print(f"[BBG] Request Bid/Ask Bars: {symbol}, interval={interval_seconds}s, {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
            
            # 分别请求 BID 和 ASK 的 bar 数据
            bid_df = self._get_intraday_bars_with_interval(symbol, "BID", interval_seconds, start_date, end_date)
            ask_df = self._get_intraday_bars_with_interval(symbol, "ASK", interval_seconds, start_date, end_date)
            
            if bid_df is None and ask_df is None:
                print(f"[BBG] Bid/Ask Bar data is empty")
                return None
            
            # 验证返回的数据间隔是否正确
            check_df = bid_df if bid_df is not None else ask_df
            if check_df is None or len(check_df) < 2:
                # 数据不足，无法验证间隔，回退到 tick 重采样
                print(f"[BBG] Too few bars returned ({0 if check_df is None else len(check_df)} rows), fallback to tick resample")
                return None
            
            actual_interval = (check_df.index[1] - check_df.index[0]).total_seconds()
            expected_interval = interval_seconds
            
            # 如果实际间隔和期望间隔相差太大 (超过 50%), 说明 API 没有按预期处理
            if actual_interval > expected_interval * 1.5 or actual_interval < expected_interval * 0.5:
                print(f"[BBG] Interval mismatch! expected: {expected_interval}s, actual: {actual_interval}s")
                return None  # fallback to tick resample
            
            print(f"[BBG] Interval OK: expected={expected_interval}s, actual={actual_interval}s")
            
            # 合并 bid 和 ask
            result = pd.DataFrame()
            
            if bid_df is not None:
                result['bid'] = bid_df['close']
                result['bid_high'] = bid_df['high']
                result['bid_low'] = bid_df['low']
            
            if ask_df is not None:
                result['ask'] = ask_df['close']
                result['ask_high'] = ask_df['high']
                result['ask_low'] = ask_df['low']
            
            # 前向填充缺失值
            result = result.ffill()
            
            # 计算 spread 和 mid
            if 'bid' in result.columns and 'ask' in result.columns:
                result['spread'] = result['ask'] - result['bid']
                result['mid'] = (result['ask'] + result['bid']) / 2
            
            # 删除空行
            result = result.dropna()
            
            print(f"[BBG] Bid/Ask Bars (from bar request): {len(result)} rows, interval={interval_seconds}s")
            return result
            
        except Exception as e:
            print(f"[BBG] Get Bid/Ask Bars from bar request failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_intraday_bars_with_interval(
        self,
        symbol: str,
        event_type: str,
        interval_seconds: int,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        内部方法: 尝试获取指定间隔的 Intraday Bar 数据
        
        注意: Bloomberg IntradayBarRequest 的 interval 参数单位是**分钟**,
        最小值为1分钟。如果请求间隔小于1分钟，应回退到 tick 重采样。
        """
        try:
            import blpapi
            
            # Bloomberg API interval 单位是分钟，最小1分钟
            interval_minutes = max(1, interval_seconds // 60)
            
            request = self._refdata_service.createRequest("IntradayBarRequest")
            request.set("security", symbol)
            request.set("eventType", event_type)
            request.set("interval", interval_minutes)  # 单位: 分钟
            request.set("startDateTime", start_date)
            request.set("endDateTime", end_date)
            
            print(f"[BBG] {event_type} bar request: interval={interval_minutes}min (from {interval_seconds}s)")
            
            self._session.sendRequest(request)
            
            data = []
            error_msg = None
            
            while True:
                event = self._session.nextEvent(5000)
                
                for msg in event:
                    if msg.hasElement("responseError"):
                        error_elem = msg.getElement("responseError")
                        error_msg = error_elem.getElementAsString("message") if error_elem.hasElement("message") else str(error_elem)
                        print(f"[BBG] {event_type} bar request error: {error_msg}")
                    
                    if msg.hasElement("barData"):
                        barData = msg.getElement("barData")
                        if barData.hasElement("barTickData"):
                            tickData = barData.getElement("barTickData")
                            for i in range(tickData.numValues()):
                                bar = tickData.getValueAsElement(i)
                                data.append({
                                    'timestamp': bar.getElementAsDatetime("time"),
                                    'open': bar.getElementAsFloat("open"),
                                    'high': bar.getElementAsFloat("high"),
                                    'low': bar.getElementAsFloat("low"),
                                    'close': bar.getElementAsFloat("close"),
                                    'volume': bar.getElementAsInteger("volume") if bar.hasElement("volume") else 0,
                                    'num_events': bar.getElementAsInteger("numEvents") if bar.hasElement("numEvents") else 0
                                })
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                if error_msg:
                    print(f"[BBG] {event_type} bars empty due to error: {error_msg}")
                return None
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            print(f"[BBG] {event_type} bars loaded: {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"[BBG] Get {event_type} bars failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_bid_ask_bars_from_bar_request(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval_minutes: int
    ) -> Optional[pd.DataFrame]:
        """
        使用IntradayBarRequest获取Bid/Ask Bars (分钟级)
        
        注意: Bloomberg IntradayBarRequest 的 interval 参数单位是分钟, 最小值为 1
        """
        try:
            print(f"[BBG] Request Bid/Ask Bars: {symbol}, interval={interval_minutes}min, {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
            
            # 分别请求 BID 和 ASK 的 bar 数据
            bid_df = self._get_intraday_bars(symbol, "BID", interval_minutes, start_date, end_date)
            ask_df = self._get_intraday_bars(symbol, "ASK", interval_minutes, start_date, end_date)
            
            if bid_df is None and ask_df is None:
                print(f"[BBG] Bid/Ask Bar data is empty")
                return None
            
            # 合并 bid 和 ask
            result = pd.DataFrame()
            
            if bid_df is not None:
                result['bid'] = bid_df['close']
                result['bid_high'] = bid_df['high']
                result['bid_low'] = bid_df['low']
            
            if ask_df is not None:
                result['ask'] = ask_df['close']
                result['ask_high'] = ask_df['high']
                result['ask_low'] = ask_df['low']
            
            # 前向填充缺失值
            result = result.ffill()
            
            # 计算 spread 和 mid
            if 'bid' in result.columns and 'ask' in result.columns:
                result['spread'] = result['ask'] - result['bid']
                result['mid'] = (result['ask'] + result['bid']) / 2
            
            # 删除空行
            result = result.dropna()
            
            print(f"[BBG] Bid/Ask Bars (from bar request): {len(result)} rows, interval={interval_minutes}min")
            return result
            
        except Exception as e:
            print(f"[BBG] Get Bid/Ask Bars from bar request failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_intraday_bars(
        self,
        symbol: str,
        event_type: str,
        interval_minutes: int,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        内部方法: 获取指定事件类型的Intraday Bar数据
        
        注意: Bloomberg IntradayBarRequest 的 interval 参数单位是分钟, 最小值为 1
        
        Args:
            symbol: Bloomberg代码
            event_type: 事件类型 (TRADE/BID/ASK/BEST_BID/BEST_ASK)
            interval_minutes: 间隔分钟数 (最小 1)
            start_date: 起始时间
            end_date: 结束时间
        
        Returns:
            DataFrame: timestamp(index), open, high, low, close, volume, num_events
        """
        try:
            import blpapi
            
            request = self._refdata_service.createRequest("IntradayBarRequest")
            request.set("security", symbol)
            request.set("eventType", event_type)
            request.set("interval", interval_minutes)  # 单位: 分钟
            request.set("startDateTime", start_date)
            request.set("endDateTime", end_date)
            
            print(f"[BBG] {event_type} bar request: interval={interval_minutes}min")
            
            self._session.sendRequest(request)
            
            data = []
            error_msg = None
            
            while True:
                event = self._session.nextEvent(5000)
                
                for msg in event:
                    # 检查是否有错误
                    if msg.hasElement("responseError"):
                        error_elem = msg.getElement("responseError")
                        error_msg = error_elem.getElementAsString("message") if error_elem.hasElement("message") else str(error_elem)
                        print(f"[BBG] {event_type} bar request error: {error_msg}")
                    
                    if msg.hasElement("barData"):
                        barData = msg.getElement("barData")
                        if barData.hasElement("barTickData"):
                            tickData = barData.getElement("barTickData")
                            for i in range(tickData.numValues()):
                                bar = tickData.getValueAsElement(i)
                                data.append({
                                    'timestamp': bar.getElementAsDatetime("time"),
                                    'open': bar.getElementAsFloat("open"),
                                    'high': bar.getElementAsFloat("high"),
                                    'low': bar.getElementAsFloat("low"),
                                    'close': bar.getElementAsFloat("close"),
                                    'volume': bar.getElementAsInteger("volume") if bar.hasElement("volume") else 0,
                                    'num_events': bar.getElementAsInteger("numEvents") if bar.hasElement("numEvents") else 0
                                })
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                if error_msg:
                    print(f"[BBG] {event_type} bars empty due to error: {error_msg}")
                return None
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            print(f"[BBG] {event_type} bars loaded: {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"[BBG] Get {event_type} bars failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ========================================
    # 参考数据 (ReferenceDataRequest)
    # ========================================
    
    def get_reference(
        self,
        symbols: List[str],
        fields: List[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取参考数据（静态数据）
        
        Args:
            symbols: Bloomberg代码列表
            fields: 字段列表，如 ["PX_LAST", "NAME", "CRNCY"]
        
        Returns:
            DataFrame: symbol, field1, field2, ...
        """
        if not self._ensure_connected():
            return None
        
        try:
            import blpapi
            
            if fields is None:
                fields = ["PX_LAST", "NAME", "CRNCY", "SECURITY_TYP"]
            
            request = self._refdata_service.createRequest("ReferenceDataRequest")
            
            for symbol in symbols:
                request.append("securities", symbol)
            for field in fields:
                request.append("fields", field)
            
            print(f"[BBG] Request reference data: {symbols}, {fields}")
            
            self._session.sendRequest(request)
            
            data = []
            while True:
                event = self._session.nextEvent(5000)
                
                for msg in event:
                    if msg.hasElement("securityData"):
                        secData = msg.getElement("securityData")
                        for i in range(secData.numValues()):
                            sec = secData.getValueAsElement(i)
                            row = {'symbol': sec.getElementAsString("security")}
                            
                            if sec.hasElement("fieldData"):
                                fieldData = sec.getElement("fieldData")
                                for field in fields:
                                    if fieldData.hasElement(field):
                                        try:
                                            row[field] = fieldData.getElementValue(field)
                                        except:
                                            row[field] = None
                                    else:
                                        row[field] = None
                            
                            data.append(row)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                return None
            
            df = pd.DataFrame(data)
            print(f"[BBG] Reference data loaded: {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"[BBG] Get reference data failed: {e}")
            return None

    # ========================================
    # 历史日线数据 (HistoricalDataRequest)
    # ========================================
    
    def get_historical(
        self,
        symbol: str,
        fields: List[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = 365,
        frequency: str = "DAILY"
    ) -> Optional[pd.DataFrame]:
        """
        获取历史日线数据
        
        Args:
            symbol: Bloomberg代码
            fields: 字段列表
            start_date: 起始日期
            end_date: 结束日期
            days_back: 向前天数
            frequency: 频率 (DAILY/WEEKLY/MONTHLY)
        
        Returns:
            DataFrame with historical data
        """
        if not self._ensure_connected():
            return None
        
        try:
            import blpapi
            
            if fields is None:
                fields = ["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME"]
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=days_back)
            
            request = self._refdata_service.createRequest("HistoricalDataRequest")
            
            request.append("securities", symbol)
            for field in fields:
                request.append("fields", field)
            request.set("startDate", start_date.strftime("%Y%m%d"))
            request.set("endDate", end_date.strftime("%Y%m%d"))
            request.set("periodicitySelection", frequency)
            
            print(f"[BBG] Request historical data: {symbol}, {frequency}, {start_date.date()} ~ {end_date.date()}")
            
            self._session.sendRequest(request)
            
            data = []
            while True:
                event = self._session.nextEvent(5000)
                
                for msg in event:
                    if msg.hasElement("securityData"):
                        secData = msg.getElement("securityData")
                        if secData.hasElement("fieldData"):
                            fieldData = secData.getElement("fieldData")
                            for i in range(fieldData.numValues()):
                                row_elem = fieldData.getValueAsElement(i)
                                row = {'date': row_elem.getElementAsDatetime("date")}
                                for field in fields:
                                    if row_elem.hasElement(field):
                                        try:
                                            row[field] = row_elem.getElementValue(field)
                                        except:
                                            row[field] = None
                                data.append(row)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            if not data:
                return None
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 重命名列
            rename_map = {
                'PX_OPEN': 'open',
                'PX_HIGH': 'high', 
                'PX_LOW': 'low',
                'PX_LAST': 'close',
                'PX_VOLUME': 'volume'
            }
            df.rename(columns=rename_map, inplace=True)
            
            print(f"[BBG] Historical data loaded: {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"[BBG] Get historical data failed: {e}")
            return None

    # ========================================
    # 便捷方法
    # ========================================
    
    def download(self, request: DownloadRequest) -> Optional[pd.DataFrame]:
        """统一下载接口"""
        if request.data_type == DataType.TICK:
            return self.get_ticks(request.symbol, request.start_date, request.end_date)
        elif request.data_type == DataType.BID_ASK:
            return self.get_bid_ask(request.symbol, request.start_date, request.end_date)
        elif request.data_type == DataType.REFERENCE:
            return self.get_reference([request.symbol], request.fields or ["PX_LAST", "NAME"])
        else:
            return self.get_bars(request.symbol, request.data_type.value, request.start_date, request.end_date)
    
    def quick_bars(self, symbol: str, days: int = 7, interval: str = "1m") -> Optional[pd.DataFrame]:
        """快速获取K线"""
        return self.get_bars(symbol, interval=interval, days_back=days)
    
    def quick_ticks(self, symbol: str, hours: float = 1) -> Optional[pd.DataFrame]:
        """快速获取Tick"""
        return self.get_ticks(symbol, hours_back=hours)
    
    def quick_quotes(self, symbol: str, hours: float = 1) -> Optional[pd.DataFrame]:
        """快速获取Bid/Ask"""
        return self.get_bid_ask(symbol, hours_back=hours)
