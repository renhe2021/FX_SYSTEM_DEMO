"""配置管理器 - 加载和验证YAML配置"""
import os
import yaml
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from .config_schema import (
    SystemConfig,
    DataSourceConfig,
    DataSourceType,
    Frequency,
    BloombergConfig,
    LocalFileConfig,
    SQLConfig,
    StrategyConfig,
    RiskConfig,
    BacktestConfig,
    OutputConfig
)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: SystemConfig = SystemConfig()
        
        if config_path and os.path.exists(config_path):
            self.load(config_path)
    
    def load(self, config_path: str) -> SystemConfig:
        """从YAML文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        self.config = self._parse_config(data)
        self.config_path = config_path
        return self.config
    
    def save(self, config_path: Optional[str] = None) -> None:
        """保存配置到YAML文件"""
        path = config_path or self.config_path
        if not path:
            raise ValueError("No config path specified")
        
        data = self._config_to_dict(self.config)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def _parse_config(self, data: Dict[str, Any]) -> SystemConfig:
        """解析配置字典"""
        config = SystemConfig()
        
        # 基础信息
        config.name = data.get('name', config.name)
        config.version = data.get('version', config.version)
        config.log_level = data.get('log_level', config.log_level)
        
        # 数据源配置
        if 'data_source' in data:
            config.data_source = self._parse_data_source(data['data_source'])
        
        # 策略配置
        if 'strategy' in data:
            config.strategy = self._parse_strategy(data['strategy'])
        
        # 风险配置
        if 'risk' in data:
            config.risk = self._parse_risk(data['risk'])
        
        # 回测配置
        if 'backtest' in data:
            config.backtest = self._parse_backtest(data['backtest'])
        
        # 输出配置
        if 'output' in data:
            config.output = self._parse_output(data['output'])
        
        return config
    
    def _parse_data_source(self, data: Dict[str, Any]) -> DataSourceConfig:
        """解析数据源配置"""
        ds = DataSourceConfig()
        
        # 数据源类型
        type_str = data.get('type', 'local_csv').lower()
        type_map = {
            'bloomberg': DataSourceType.BLOOMBERG,
            'bbg': DataSourceType.BLOOMBERG,
            'local_csv': DataSourceType.LOCAL_CSV,
            'csv': DataSourceType.LOCAL_CSV,
            'local_excel': DataSourceType.LOCAL_EXCEL,
            'excel': DataSourceType.LOCAL_EXCEL,
            'sql': DataSourceType.SQL
        }
        ds.type = type_map.get(type_str, DataSourceType.LOCAL_CSV)
        
        ds.symbol = data.get('symbol', '')
        
        # 频率
        freq_str = data.get('frequency', '1m').lower()
        freq_map = {
            '1m': Frequency.MINUTE_1,
            '5m': Frequency.MINUTE_5,
            '15m': Frequency.MINUTE_15,
            '30m': Frequency.MINUTE_30,
            '1h': Frequency.HOUR_1,
            '1d': Frequency.DAILY,
            '1w': Frequency.WEEKLY
        }
        ds.frequency = freq_map.get(freq_str, Frequency.MINUTE_1)
        
        ds.start_date = data.get('start_date')
        ds.end_date = data.get('end_date')
        ds.days_back = data.get('days_back', 140)
        
        # Bloomberg配置
        if 'bloomberg' in data:
            bbg = data['bloomberg']
            ds.bloomberg = BloombergConfig(
                host=bbg.get('host', 'localhost'),
                port=bbg.get('port', 8194),
                timeout=bbg.get('timeout', 30000)
            )
        
        # 本地文件配置
        if 'local_file' in data:
            lf = data['local_file']
            ds.local_file = LocalFileConfig(
                path=lf.get('path', ''),
                date_column=lf.get('date_column', 'timestamp'),
                date_format=lf.get('date_format')
            )
        
        # SQL配置
        if 'sql' in data:
            sql = data['sql']
            ds.sql = SQLConfig(
                connection_string=sql.get('connection_string', ''),
                table_name=sql.get('table_name', 'market_data')
            )
        
        return ds
    
    def _parse_strategy(self, data: Dict[str, Any]) -> StrategyConfig:
        """解析策略配置"""
        return StrategyConfig(
            name=data.get('name', ''),
            type=data.get('type', ''),
            enabled=data.get('enabled', True),
            parameters=data.get('parameters', {})
        )
    
    def _parse_risk(self, data: Dict[str, Any]) -> RiskConfig:
        """解析风险配置"""
        return RiskConfig(
            max_position_size=data.get('max_position_size', 100000),
            max_drawdown_pct=data.get('max_drawdown_pct', 0.2),
            stop_loss_pct=data.get('stop_loss_pct'),
            take_profit_pct=data.get('take_profit_pct'),
            max_trades_per_day=data.get('max_trades_per_day', 10)
        )
    
    def _parse_backtest(self, data: Dict[str, Any]) -> BacktestConfig:
        """解析回测配置"""
        return BacktestConfig(
            initial_capital=data.get('initial_capital', 1000000),
            commission_rate=data.get('commission_rate', 0.00005),
            slippage=data.get('slippage', 0.0001),
            position_size=data.get('position_size', 100000)
        )
    
    def _parse_output(self, data: Dict[str, Any]) -> OutputConfig:
        """解析输出配置"""
        return OutputConfig(
            save_trades=data.get('save_trades', True),
            save_equity_curve=data.get('save_equity_curve', True),
            output_dir=data.get('output_dir', './output'),
            report_format=data.get('report_format', 'html')
        )
    
    def _config_to_dict(self, config: SystemConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            'name': config.name,
            'version': config.version,
            'log_level': config.log_level,
            
            'data_source': {
                'type': config.data_source.type.value,
                'symbol': config.data_source.symbol,
                'frequency': config.data_source.frequency.value,
                'start_date': config.data_source.start_date,
                'end_date': config.data_source.end_date,
                'days_back': config.data_source.days_back,
                'bloomberg': {
                    'host': config.data_source.bloomberg.host,
                    'port': config.data_source.bloomberg.port,
                    'timeout': config.data_source.bloomberg.timeout
                },
                'local_file': {
                    'path': config.data_source.local_file.path,
                    'date_column': config.data_source.local_file.date_column,
                    'date_format': config.data_source.local_file.date_format
                },
                'sql': {
                    'connection_string': config.data_source.sql.connection_string,
                    'table_name': config.data_source.sql.table_name
                }
            },
            
            'strategy': {
                'name': config.strategy.name,
                'type': config.strategy.type,
                'enabled': config.strategy.enabled,
                'parameters': config.strategy.parameters
            },
            
            'risk': {
                'max_position_size': config.risk.max_position_size,
                'max_drawdown_pct': config.risk.max_drawdown_pct,
                'stop_loss_pct': config.risk.stop_loss_pct,
                'take_profit_pct': config.risk.take_profit_pct,
                'max_trades_per_day': config.risk.max_trades_per_day
            },
            
            'backtest': {
                'initial_capital': config.backtest.initial_capital,
                'commission_rate': config.backtest.commission_rate,
                'slippage': config.backtest.slippage,
                'position_size': config.backtest.position_size
            },
            
            'output': {
                'save_trades': config.output.save_trades,
                'save_equity_curve': config.output.save_equity_curve,
                'output_dir': config.output.output_dir,
                'report_format': config.output.report_format
            }
        }
    
    def validate(self) -> bool:
        """验证配置有效性"""
        errors = []
        
        # 验证数据源
        ds = self.config.data_source
        if ds.type == DataSourceType.LOCAL_CSV and not ds.local_file.path:
            errors.append("Local CSV data source requires 'local_file.path'")
        
        if ds.type == DataSourceType.SQL and not ds.sql.connection_string:
            errors.append("SQL data source requires 'sql.connection_string'")
        
        if not ds.symbol:
            errors.append("Data source requires 'symbol'")
        
        # 验证策略
        if not self.config.strategy.type:
            errors.append("Strategy requires 'type'")
        
        # 验证回测
        if self.config.backtest.initial_capital <= 0:
            errors.append("Initial capital must be positive")
        
        if errors:
            for e in errors:
                print(f"Config Error: {e}")
            return False
        
        return True


def load_config(config_path: str) -> SystemConfig:
    """便捷函数：加载配置文件"""
    manager = ConfigManager(config_path)
    return manager.config


def create_default_config(output_path: str) -> None:
    """创建默认配置文件"""
    manager = ConfigManager()
    
    # 设置默认值
    manager.config.name = "BMAD Quant System"
    manager.config.data_source.type = DataSourceType.BLOOMBERG
    manager.config.data_source.symbol = "USDCNH Curncy"
    manager.config.data_source.frequency = Frequency.MINUTE_1
    manager.config.strategy.name = "Friday Night Strategy"
    manager.config.strategy.type = "FridayNightStrategy"
    manager.config.strategy.parameters = {
        'entry_hour': 21,
        'entry_minute': 0,
        'exit_hour': 2,
        'exit_minute': 0,
        'hold_hours': 5
    }
    
    manager.save(output_path)
