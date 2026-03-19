"""
数据探索器
==========

提供数据下载、分析和导出功能
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from .bbg_wrapper import BloombergWrapper, DataType

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False
    print("[Warning] pytz not installed, timezone features limited. Run: pip install pytz")


class DataExplorer:
    """
    数据探索器
    
    功能：
    - 连接Bloomberg
    - 下载K线/Tick/Bid-Ask数据
    - 数据统计和预览
    - 导出CSV/Excel
    - 时区转换支持
    """
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        self.bbg = BloombergWrapper(host, port)
        self._cache: Dict[str, pd.DataFrame] = {}
        self._output_dir = "output"
        self._default_timezone = "Asia/Shanghai"
        
        # 确保输出目录存在
        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir)
    
    def connect(self) -> bool:
        """连接Bloomberg"""
        return self.bbg.connect()
    
    def disconnect(self):
        """断开连接"""
        self.bbg.disconnect()
    
    @property
    def is_connected(self) -> bool:
        return self.bbg.is_connected
    
    def check_alive(self) -> bool:
        """检查Bloomberg连接是否真正可用"""
        return self.bbg.check_alive()
    
    def _convert_to_utc(self, dt: datetime, timezone: str) -> datetime:
        """将指定时区的时间转换为UTC"""
        if not HAS_PYTZ:
            # 简单处理：假设输入是北京时间，减8小时得到UTC
            if timezone == "Asia/Shanghai" or timezone == "Asia/Hong_Kong":
                return dt - timedelta(hours=8)
            elif timezone == "Asia/Tokyo":
                return dt - timedelta(hours=9)
            elif timezone == "America/New_York":
                return dt + timedelta(hours=5)  # EST
            elif timezone == "Europe/London":
                return dt  # GMT
            return dt
        
        try:
            tz = pytz.timezone(timezone)
            local_dt = tz.localize(dt)
            utc_dt = local_dt.astimezone(pytz.UTC)
            return utc_dt.replace(tzinfo=None)
        except Exception as e:
            print(f"[Timezone] Error: {e}, using original time")
            return dt
    
    def _convert_df_timezone(self, df: pd.DataFrame, timezone: str) -> pd.DataFrame:
        """将DataFrame的时间索引转换到指定时区"""
        if df is None or df.empty:
            return df
        
        if not HAS_PYTZ:
            # 简单处理
            offset_hours = {
                "Asia/Shanghai": 8,
                "Asia/Hong_Kong": 8,
                "Asia/Tokyo": 9,
                "America/New_York": -5,
                "Europe/London": 0,
                "UTC": 0
            }.get(timezone, 8)
            
            df = df.copy()
            df.index = df.index + pd.Timedelta(hours=offset_hours)
            return df
        
        try:
            df = df.copy()
            # 假设Bloomberg返回的是UTC时间
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert(timezone)
            # 移除时区信息以便后续处理
            df.index = df.index.tz_localize(None)
            return df
        except Exception as e:
            print(f"[Timezone] DataFrame conversion error: {e}")
            return df
    
    def _filter_daily_time(self, df: pd.DataFrame, daily_start: str, daily_end: str) -> pd.DataFrame:
        """
        过滤每日时段数据
        
        Args:
            df: 带有时间索引的DataFrame
            daily_start: 每日开始时间 (HH:MM)，如 "09:00"
            daily_end: 每日结束时间 (HH:MM)，如 "10:00"
        
        Returns:
            只包含每天指定时段的数据
        """
        if df is None or df.empty:
            return df
        
        try:
            # 解析时间
            start_hour, start_min = map(int, daily_start.split(':'))
            end_hour, end_min = map(int, daily_end.split(':'))
            
            start_time = start_hour * 100 + start_min  # e.g., 900 for 09:00
            end_time = end_hour * 100 + end_min        # e.g., 1000 for 10:00
            
            df = df.copy()
            
            # 获取每行的时间 (HHMM格式)
            time_of_day = df.index.hour * 100 + df.index.minute
            
            # 支持跨午夜的时段 (如 23:00 ~ 01:00)
            if start_time <= end_time:
                # 普通情况: 09:00 ~ 10:00
                mask = (time_of_day >= start_time) & (time_of_day < end_time)
            else:
                # 跨午夜: 23:00 ~ 01:00
                mask = (time_of_day >= start_time) | (time_of_day < end_time)
            
            filtered_df = df[mask]
            
            print(f"[DataExplorer] Daily time filter: {daily_start}~{daily_end}, kept {len(filtered_df)}/{len(df)} rows")
            
            return filtered_df
            
        except Exception as e:
            print(f"[DataExplorer] Daily filter error: {e}")
            return df

    # ========================================
    # K线数据下载
    # ========================================
    
    def download_bars(
        self,
        symbol: str,
        interval: str = "1m",
        days_back: int = 30,
        start_date: str = None,
        end_date: str = None,
        start_time: str = None,
        end_time: str = None,
        timezone: str = "Asia/Shanghai"
    ) -> Dict[str, Any]:
        """
        下载K线数据
        
        Args:
            symbol: Bloomberg代码
            interval: 时间间隔 (1m/5m/15m/30m/1h)
            days_back: 向前天数
            start_date: 起始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            start_time: 起始时间 (YYYY-MM-DDTHH:MM) - 优先级高于start_date
            end_time: 结束时间 (YYYY-MM-DDTHH:MM) - 优先级高于end_date
            timezone: 时区 (默认北京时间)
        
        Returns:
            {success, message, data, stats, cache_key}
        
        注意: 输入时间为北京时间，bbg_wrapper会自动转换为UTC发送给Bloomberg
        """
        try:
            # 解析日期时间 - start_time/end_time 优先
            # 输入时间为北京时间，bbg_wrapper内部会自动转换为UTC
            start_dt = None
            end_dt = None
            
            if start_time and end_time:
                # datetime-local 格式: YYYY-MM-DDTHH:MM (北京时间)
                start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
                end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
            elif start_date and end_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # 如果都没有指定，bbg_wrapper会使用当前北京时间
            
            df = self.bbg.get_bars(
                symbol=symbol,
                interval=interval,
                start_date=start_dt,
                end_date=end_dt,
                days_back=days_back,
                is_beijing_time=True  # 输入是北京时间
            )
            
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': '无数据返回，请检查品种代码或时间范围',
                    'data': None,
                    'stats': None
                }
            
            # 转换到目标时区（返回的数据是UTC，转换到北京时间显示）
            df = self._convert_df_timezone(df, timezone)
            
            # 缓存
            cache_key = f"{symbol.replace(' ', '_')}_{interval}"
            self._cache[cache_key] = df
            
            # 统计
            stats = self._compute_bar_stats(df)
            
            # 预览数据
            preview = self._df_to_preview(df, 100)
            
            return {
                'success': True,
                'message': f'成功加载 {len(df)} 行K线数据',
                'data': {
                    'rows': len(df),
                    'columns': list(df.columns),
                    'start': str(df.index[0]),
                    'end': str(df.index[-1]),
                    'preview': preview
                },
                'stats': stats,
                'cache_key': cache_key
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'下载失败: {str(e)}',
                'data': None,
                'stats': None
            }

    # ========================================
    # Tick数据下载
    # ========================================
    
    def download_ticks(
        self,
        symbol: str,
        hours_back: float = 1,
        start_time: str = None,
        end_time: str = None,
        timezone: str = "Asia/Shanghai"
    ) -> Dict[str, Any]:
        """
        下载Tick成交数据
        
        Args:
            symbol: Bloomberg代码
            hours_back: 向前小时数
            start_time: 起始时间 (YYYY-MM-DDTHH:MM) - 北京时间
            end_time: 结束时间 (YYYY-MM-DDTHH:MM) - 北京时间
            timezone: 时区 (默认北京时间)
        
        Returns:
            {success, message, data, cache_key}
        
        注意: 输入时间为北京时间，bbg_wrapper会自动转换为UTC发送给Bloomberg
        """
        try:
            # 解析时间（北京时间）
            start_dt = None
            end_dt = None
            
            if start_time and end_time:
                start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
                end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
            
            df = self.bbg.get_ticks(
                symbol=symbol,
                start_date=start_dt,
                end_date=end_dt,
                hours_back=hours_back,
                is_beijing_time=True  # 输入是北京时间
            )
            
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': '无Tick数据返回',
                    'data': None
                }
            
            # 转换到目标时区（返回的数据是UTC，转换到北京时间显示）
            df = self._convert_df_timezone(df, timezone)
            
            cache_key = f"{symbol.replace(' ', '_')}_tick"
            self._cache[cache_key] = df
            
            preview = self._df_to_preview(df, 100)
            
            # 统计
            stats = {
                'count': len(df),
                'avg_price': float(df['price'].mean()) if 'price' in df.columns else None,
                'min_price': float(df['price'].min()) if 'price' in df.columns else None,
                'max_price': float(df['price'].max()) if 'price' in df.columns else None,
                'total_size': int(df['size'].sum()) if 'size' in df.columns else None
            }
            
            return {
                'success': True,
                'message': f'成功加载 {len(df)} 条Tick数据',
                'data': {
                    'rows': len(df),
                    'start': str(df.index[0]),
                    'end': str(df.index[-1]),
                    'preview': preview
                },
                'stats': stats,
                'cache_key': cache_key
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'下载失败: {str(e)}',
                'data': None
            }

    # ========================================
    # Bid/Ask数据下载
    # ========================================
    
    def download_bid_ask(
        self,
        symbol: str,
        hours_back: float = 1,
        resample: str = None,
        start_time: str = None,
        end_time: str = None,
        timezone: str = "Asia/Shanghai",
        daily_start: str = None,
        daily_end: str = None
    ) -> Dict[str, Any]:
        """
        下载Bid/Ask报价数据
        
        Args:
            symbol: Bloomberg代码
            hours_back: 向前小时数
            resample: 重采样频率 (如 "1s", "5s", "1min")，None表示原始tick
            start_time: 起始时间 (YYYY-MM-DDTHH:MM) - 北京时间
            end_time: 结束时间 (YYYY-MM-DDTHH:MM) - 北京时间
            timezone: 时区 (默认北京时间)
            daily_start: 每日开始时间 (HH:MM)，如 "09:00" - 北京时间
            daily_end: 每日结束时间 (HH:MM)，如 "10:00" - 北京时间
        
        Returns:
            {success, message, data, stats, cache_key}
        
        注意: 输入时间为北京时间，bbg_wrapper会自动转换为UTC发送给Bloomberg
        """
        try:
            # 解析时间（北京时间）
            start_dt = None
            end_dt = None
            
            if start_time and end_time:
                start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
                end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
            
            print(f"[DataExplorer] download_bid_ask: symbol={symbol}, hours_back={hours_back}, resample={resample}")
            print(f"[DataExplorer] start_time={start_time}, end_time={end_time} (Beijing time)")
            print(f"[DataExplorer] daily_filter={daily_start}~{daily_end} (Beijing time)")
            
            if resample:
                # 重采样为bar格式
                df = self.bbg.get_bid_ask_bars(
                    symbol=symbol,
                    hours_back=hours_back,
                    resample=resample,
                    start_date=start_dt,
                    end_date=end_dt,
                    is_beijing_time=True  # 输入是北京时间
                )
                cache_key = f"{symbol.replace(' ', '_')}_bidask_{resample}"
            else:
                # 原始tick
                df = self.bbg.get_bid_ask(
                    symbol=symbol,
                    hours_back=hours_back,
                    start_date=start_dt,
                    end_date=end_dt,
                    is_beijing_time=True  # 输入是北京时间
                )
                cache_key = f"{symbol.replace(' ', '_')}_bidask"
            
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'No Bid/Ask data returned',
                    'data': None
                }
            
            # 转换到目标时区（返回的数据是UTC，转换到北京时间显示）
            df = self._convert_df_timezone(df, timezone)
            
            # 每日时段过滤（使用北京时间）
            original_rows = len(df)
            if daily_start and daily_end:
                df = self._filter_daily_time(df, daily_start, daily_end)
                print(f"[DataExplorer] Daily filter {daily_start}~{daily_end} (Beijing time): {original_rows} -> {len(df)} rows")
                
                if df.empty:
                    return {
                        'success': False,
                        'message': f'No data in daily time range {daily_start}~{daily_end} (Beijing time)',
                        'data': None
                    }
                
                cache_key += f"_{daily_start.replace(':','')}_{daily_end.replace(':','')}"
            
            self._cache[cache_key] = df
            
            preview = self._df_to_preview(df, 100)
            
            # 统计
            stats = self._compute_bidask_stats(df, resample is not None)
            
            filter_msg = f" (filtered {daily_start}~{daily_end} Beijing time)" if daily_start else ""
            return {
                'success': True,
                'message': f'Loaded {len(df)} Bid/Ask records{filter_msg}',
                'data': {
                    'rows': len(df),
                    'columns': list(df.columns),
                    'start': str(df.index[0]),
                    'end': str(df.index[-1]),
                    'preview': preview
                },
                'stats': stats,
                'cache_key': cache_key
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Download failed: {str(e)}',
                'data': None
            }

    # ========================================
    # 参考数据下载
    # ========================================
    
    def download_reference(
        self,
        symbols: List[str],
        fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        下载参考数据
        
        Args:
            symbols: Bloomberg代码列表
            fields: 字段列表
        
        Returns:
            {success, message, data}
        """
        try:
            if fields is None:
                fields = ["PX_LAST", "NAME", "CRNCY", "SECURITY_TYP"]
            
            df = self.bbg.get_reference(symbols, fields)
            
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': '无参考数据返回',
                    'data': None
                }
            
            return {
                'success': True,
                'message': f'成功加载 {len(df)} 条参考数据',
                'data': df.to_dict('records')
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'下载失败: {str(e)}',
                'data': None
            }

    # ========================================
    # 导出功能
    # ========================================
    
    def export_csv(self, cache_key: str, filepath: str = None) -> Dict[str, Any]:
        """导出为CSV"""
        try:
            if cache_key not in self._cache:
                return {'success': False, 'message': '数据不存在，请先下载'}
            
            df = self._cache[cache_key]
            
            if filepath is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = os.path.join(self._output_dir, f"{cache_key}_{timestamp}.csv")
            
            df.to_csv(filepath)
            
            return {
                'success': True,
                'message': f'已导出到 {filepath}',
                'filepath': filepath,
                'rows': len(df)
            }
            
        except Exception as e:
            return {'success': False, 'message': f'导出失败: {str(e)}'}
    
    def export_excel(self, cache_key: str, filepath: str = None) -> Dict[str, Any]:
        """导出为Excel"""
        try:
            if cache_key not in self._cache:
                return {'success': False, 'message': '数据不存在，请先下载'}
            
            df = self._cache[cache_key]
            
            if filepath is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = os.path.join(self._output_dir, f"{cache_key}_{timestamp}.xlsx")
            
            df.to_excel(filepath)
            
            return {
                'success': True,
                'message': f'已导出到 {filepath}',
                'filepath': filepath,
                'rows': len(df)
            }
            
        except Exception as e:
            return {'success': False, 'message': f'导出失败: {str(e)}'}

    # ========================================
    # 图表数据
    # ========================================
    
    def get_chart_data(self, cache_key: str, chart_type: str = "candlestick") -> Dict[str, Any]:
        """获取图表数据"""
        try:
            if cache_key not in self._cache:
                return {'success': False, 'message': '数据不存在'}
            
            df = self._cache[cache_key]
            
            if chart_type == "candlestick" and all(c in df.columns for c in ['open', 'high', 'low', 'close']):
                chart_df = df[['open', 'high', 'low', 'close']].tail(500).reset_index()
                chart_df['timestamp'] = chart_df['timestamp'].astype(str)
                return {
                    'success': True,
                    'type': 'candlestick',
                    'data': chart_df.to_dict('records')
                }
            
            elif chart_type == "line":
                # 自动选择价格列
                price_col = None
                for col in ['close', 'mid', 'price', 'bid']:
                    if col in df.columns:
                        price_col = col
                        break
                
                if price_col is None:
                    return {'success': False, 'message': '无可用价格列'}
                
                chart_df = df[[price_col]].tail(500).reset_index()
                chart_df['timestamp'] = chart_df['timestamp'].astype(str) if 'timestamp' in chart_df.columns else chart_df.index.astype(str)
                
                return {
                    'success': True,
                    'type': 'line',
                    'data': chart_df.to_dict('records'),
                    'price_col': price_col
                }
            
            elif chart_type == "bidask" and 'bid' in df.columns and 'ask' in df.columns:
                chart_df = df[['bid', 'ask', 'spread']].tail(500).reset_index()
                chart_df['timestamp'] = chart_df['timestamp'].astype(str) if 'timestamp' in chart_df.columns else chart_df.index.astype(str)
                
                return {
                    'success': True,
                    'type': 'bidask',
                    'data': chart_df.to_dict('records')
                }
            
            else:
                return {'success': False, 'message': f'不支持的图表类型或数据格式不匹配'}
            
        except Exception as e:
            return {'success': False, 'message': f'获取图表数据失败: {str(e)}'}

    # ========================================
    # 内部方法
    # ========================================
    
    def _df_to_preview(self, df: pd.DataFrame, n: int = 100) -> List[Dict]:
        """DataFrame转预览格式"""
        preview_df = df.tail(n).reset_index()
        
        # 转换时间列为字符串
        for col in preview_df.columns:
            if pd.api.types.is_datetime64_any_dtype(preview_df[col]):
                preview_df[col] = preview_df[col].astype(str)
        
        return preview_df.to_dict('records')
    
    def _compute_bar_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算K线统计"""
        stats = {}
        
        if 'close' in df.columns:
            stats['last_price'] = float(df['close'].iloc[-1])
            stats['first_price'] = float(df['close'].iloc[0])
            stats['high'] = float(df['high'].max()) if 'high' in df.columns else None
            stats['low'] = float(df['low'].min()) if 'low' in df.columns else None
            stats['avg'] = float(df['close'].mean())
            stats['std'] = float(df['close'].std())
            
            # 收益率
            stats['total_return'] = float((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100)
            
            # 波动率
            returns = df['close'].pct_change().dropna()
            stats['volatility'] = float(returns.std() * 100)
            
        if 'volume' in df.columns:
            stats['total_volume'] = int(df['volume'].sum())
            stats['avg_volume'] = float(df['volume'].mean())
        
        return stats
    
    def _compute_bidask_stats(self, df: pd.DataFrame, is_resampled: bool) -> Dict[str, Any]:
        """计算Bid/Ask统计"""
        stats = {}
        
        if is_resampled:
            # 重采样后的格式: bid, ask, spread, mid
            if 'bid' in df.columns:
                stats['avg_bid'] = float(df['bid'].mean())
                stats['last_bid'] = float(df['bid'].iloc[-1])
            if 'ask' in df.columns:
                stats['avg_ask'] = float(df['ask'].mean())
                stats['last_ask'] = float(df['ask'].iloc[-1])
            if 'spread' in df.columns:
                stats['avg_spread'] = float(df['spread'].mean())
                stats['min_spread'] = float(df['spread'].min())
                stats['max_spread'] = float(df['spread'].max())
            if 'mid' in df.columns:
                stats['last_mid'] = float(df['mid'].iloc[-1])
        else:
            # 原始tick格式: type, price, size
            if 'type' in df.columns and 'price' in df.columns:
                bids = df[df['type'] == 'BID']['price']
                asks = df[df['type'] == 'ASK']['price']
                
                if len(bids) > 0:
                    stats['bid_count'] = len(bids)
                    stats['avg_bid'] = float(bids.mean())
                    stats['last_bid'] = float(bids.iloc[-1])
                
                if len(asks) > 0:
                    stats['ask_count'] = len(asks)
                    stats['avg_ask'] = float(asks.mean())
                    stats['last_ask'] = float(asks.iloc[-1])
                
                if len(bids) > 0 and len(asks) > 0:
                    stats['avg_spread'] = stats['avg_ask'] - stats['avg_bid']
        
        return stats

    # ========================================
    # 缓存管理
    # ========================================
    
    def list_cache(self) -> List[Dict[str, Any]]:
        """列出缓存的数据"""
        result = []
        for key, df in self._cache.items():
            result.append({
                'key': key,
                'rows': len(df),
                'columns': list(df.columns),
                'start': str(df.index[0]) if len(df) > 0 else None,
                'end': str(df.index[-1]) if len(df) > 0 else None
            })
        return result
    
    def get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """获取缓存的DataFrame"""
        return self._cache.get(cache_key)
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
