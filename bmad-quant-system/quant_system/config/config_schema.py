"""配置数据结构定义"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class DataSourceType(Enum):
    """数据源类型"""
    BLOOMBERG = "bloomberg"
    LOCAL_CSV = "local_csv"
    LOCAL_EXCEL = "local_excel"
    SQL = "sql"


class Frequency(Enum):
    """数据频率"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    DAILY = "1d"
    WEEKLY = "1w"


@dataclass
class BloombergConfig:
    """Bloomberg数据源配置"""
    host: str = "localhost"
    port: int = 8194
    timeout: int = 30000


@dataclass
class LocalFileConfig:
    """本地文件数据源配置"""
    path: str = ""
    date_column: str = "timestamp"
    date_format: Optional[str] = None


@dataclass
class SQLConfig:
    """SQL数据源配置"""
    connection_string: str = ""
    table_name: str = "market_data"


@dataclass
class DataSourceConfig:
    """数据源配置"""
    type: DataSourceType = DataSourceType.LOCAL_CSV
    symbol: str = ""
    frequency: Frequency = Frequency.MINUTE_1
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    days_back: int = 140  # 回溯天数
    
    # 各数据源特定配置
    bloomberg: BloombergConfig = field(default_factory=BloombergConfig)
    local_file: LocalFileConfig = field(default_factory=LocalFileConfig)
    sql: SQLConfig = field(default_factory=SQLConfig)


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str = ""
    type: str = ""  # FridayNightStrategy, MACrossStrategy, etc.
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskConfig:
    """风险管理配置"""
    max_position_size: float = 100000
    max_drawdown_pct: float = 0.2
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_trades_per_day: int = 10


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1000000
    commission_rate: float = 0.00005
    slippage: float = 0.0001
    position_size: float = 100000


@dataclass
class OutputConfig:
    """输出配置"""
    save_trades: bool = True
    save_equity_curve: bool = True
    output_dir: str = "./output"
    report_format: str = "html"  # html, pdf, json


@dataclass
class SystemConfig:
    """系统总配置"""
    name: str = "BMAD Quant System"
    version: str = "1.0.0"
    log_level: str = "INFO"
    
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
