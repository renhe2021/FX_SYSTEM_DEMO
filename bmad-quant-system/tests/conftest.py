"""Pytest 配置文件

共享 fixtures 和配置
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


@pytest.fixture
def sample_ohlcv_data():
    """生成标准OHLCV测试数据"""
    dates = pd.date_range('2024-01-01', periods=1000, freq='15min')
    np.random.seed(42)
    
    base_price = 7.25
    returns = np.random.randn(1000) * 0.0005
    close = base_price * (1 + returns).cumprod()
    
    df = pd.DataFrame({
        'open': close * (1 + np.random.randn(1000) * 0.0001),
        'high': close * (1 + np.abs(np.random.randn(1000)) * 0.0002),
        'low': close * (1 - np.abs(np.random.randn(1000)) * 0.0002),
        'close': close,
        'volume': np.random.randint(1000, 10000, 1000)
    }, index=dates)
    
    return df


@pytest.fixture
def sample_daily_data():
    """生成日线测试数据"""
    dates = pd.date_range('2024-01-01', periods=252, freq='B')  # 一年交易日
    np.random.seed(42)
    
    base_price = 7.25
    returns = np.random.randn(252) * 0.005
    close = base_price * (1 + returns).cumprod()
    
    df = pd.DataFrame({
        'open': close * (1 + np.random.randn(252) * 0.001),
        'high': close * (1 + np.abs(np.random.randn(252)) * 0.002),
        'low': close * (1 - np.abs(np.random.randn(252)) * 0.002),
        'close': close,
        'volume': np.random.randint(10000, 100000, 252)
    }, index=dates)
    
    return df


@pytest.fixture
def sample_trades():
    """生成测试交易记录"""
    return pd.DataFrame({
        'entry_time': pd.date_range('2024-01-01', periods=20, freq='W'),
        'exit_time': pd.date_range('2024-01-02', periods=20, freq='W'),
        'symbol': ['USDCNH'] * 20,
        'direction': ['BUY'] * 10 + ['SELL'] * 10,
        'quantity': [100000] * 20,
        'entry_price': [7.25] * 20,
        'exit_price': 7.25 + np.random.randn(20) * 0.02,
        'pnl': np.random.randn(20) * 1000,
        'commission': [10] * 20
    })


@pytest.fixture
def sample_equity_curve():
    """生成测试权益曲线"""
    dates = pd.date_range('2024-01-01', periods=252, freq='B')
    np.random.seed(42)
    
    initial = 1000000
    returns = np.random.randn(252) * 0.01
    equity = initial * (1 + returns).cumprod()
    
    return pd.DataFrame({
        'equity': equity,
        'cash': equity * 0.3,
        'positions_value': equity * 0.7
    }, index=dates)
