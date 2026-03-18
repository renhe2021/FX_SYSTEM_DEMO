"""
BMAD量化交易系统
================

基于BMAD架构的量化交易回测系统:
- Base: 数据层 (数据源抽象、数据管理)
- Model: 模型层 (技术指标、信号生成、风险管理、策略)
- Agent: 执行层 (事件系统、回测引擎、组合管理)
- Display: 展示层 (绩效分析、可视化)

支持数据源:
- Excel本地文件
- Bloomberg API
- SQL数据库

示例用法:
---------
from quant_system import BacktestEngine, BloombergDataSource, FridayNightStrategy

# 创建数据源
data_source = BloombergDataSource()
data_source.connect()

# 获取数据
data = data_source.get_historical_data("USDCNH Curncy", start_date, end_date)

# 创建回测引擎
engine = BacktestEngine(initial_capital=1000000)
engine.add_data("USDCNH", data)
engine.add_strategy(FridayNightStrategy())

# 运行回测
results = engine.run()
"""

__version__ = "1.0.0"
__author__ = "BMAD Quant System"

# Base Layer
from .base import (
    BaseDataSource, ExcelDataSource, BloombergDataSource, SQLDataSource,
    DataManager, OHLCV, Trade, Quote
)

# Model Layer
from .model import (
    TechnicalIndicators,
    SignalGenerator, Signal, SignalType,
    RiskManager, RiskLimits,
    BaseStrategy, FridayNightStrategy
)

# Agent Layer
from .agent import (
    Event, EventType, EventQueue,
    MarketDataEvent, SignalEvent, OrderEvent, FillEvent,
    BacktestEngine, Portfolio,
    ExecutionHandler, SimulatedExecution
)

# Display Layer
from .display import (
    PerformanceAnalyzer,
    QuantVisualizer
)

__all__ = [
    # Base
    'BaseDataSource', 'ExcelDataSource', 'BloombergDataSource', 'SQLDataSource',
    'DataManager', 'OHLCV', 'Trade', 'Quote',
    # Model
    'TechnicalIndicators',
    'SignalGenerator', 'Signal', 'SignalType',
    'RiskManager', 'RiskLimits',
    'BaseStrategy', 'FridayNightStrategy',
    # Agent
    'Event', 'EventType', 'EventQueue',
    'MarketDataEvent', 'SignalEvent', 'OrderEvent', 'FillEvent',
    'BacktestEngine', 'Portfolio',
    'ExecutionHandler', 'SimulatedExecution',
    # Display
    'PerformanceAnalyzer', 'QuantVisualizer'
]
