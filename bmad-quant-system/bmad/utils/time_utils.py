"""时间工具函数"""
from datetime import datetime, timedelta
from typing import List, Union
import pandas as pd


def is_trading_day(date: datetime, market: str = 'forex') -> bool:
    """判断是否为交易日
    
    Args:
        date: 日期
        market: 市场类型 ('forex', 'stock_cn', 'stock_us')
    
    Returns:
        是否为交易日
    """
    weekday = date.weekday()
    
    if market == 'forex':
        # 外汇市场周一到周五交易，周六凌晨收盘
        if weekday == 6:  # 周日
            return False
        if weekday == 5 and date.hour >= 5:  # 周六5点后
            return False
        return True
    
    elif market in ['stock_cn', 'stock_us']:
        # 股票市场周一到周五
        return weekday < 5
    
    return weekday < 5


def get_trading_days(start_date: datetime, 
                     end_date: datetime,
                     market: str = 'forex') -> List[datetime]:
    """获取交易日列表"""
    days = []
    current = start_date
    
    while current <= end_date:
        if is_trading_day(current, market):
            days.append(current)
        current += timedelta(days=1)
    
    return days


def to_beijing_time(dt: datetime, from_tz: str = 'UTC') -> datetime:
    """转换为北京时间
    
    Args:
        dt: 原始时间
        from_tz: 原始时区
    
    Returns:
        北京时间
    """
    try:
        import pytz
        
        tz_map = {
            'UTC': pytz.UTC,
            'US/Eastern': pytz.timezone('US/Eastern'),
            'Europe/London': pytz.timezone('Europe/London')
        }
        
        beijing = pytz.timezone('Asia/Shanghai')
        
        if from_tz in tz_map:
            if dt.tzinfo is None:
                dt = tz_map[from_tz].localize(dt)
            return dt.astimezone(beijing).replace(tzinfo=None)
        
        return dt
        
    except ImportError:
        # 简单的UTC到北京时间转换
        if from_tz == 'UTC':
            return dt + timedelta(hours=8)
        return dt


def parse_datetime(value: Union[str, datetime, pd.Timestamp]) -> datetime:
    """解析日期时间
    
    支持多种格式输入
    """
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    
    if isinstance(value, str):
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%Y%m%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        # 尝试pandas解析
        return pd.to_datetime(value).to_pydatetime()
    
    raise ValueError(f"无法解析日期: {value}")


def get_week_boundaries(date: datetime) -> tuple:
    """获取周的起止时间
    
    Returns:
        (周一00:00, 周日23:59)
    """
    weekday = date.weekday()
    monday = date - timedelta(days=weekday)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return monday, sunday
