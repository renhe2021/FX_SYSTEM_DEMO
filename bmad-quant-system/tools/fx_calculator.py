"""外汇计算器

外汇交易相关的计算工具
"""
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FXPosition:
    """外汇持仓"""
    pair: str
    direction: str  # 'long' or 'short'
    size: float  # 名义金额
    entry_price: float
    current_price: float = 0.0
    
    @property
    def pnl_pips(self) -> float:
        """盈亏点数"""
        if self.direction == 'long':
            return (self.current_price - self.entry_price) * 10000
        else:
            return (self.entry_price - self.current_price) * 10000
    
    @property
    def pnl_amount(self) -> float:
        """盈亏金额"""
        pip_value = self.size * 0.0001
        return self.pnl_pips * pip_value


class FXCalculator:
    """外汇计算器
    
    提供外汇交易常用计算功能
    
    示例:
    ------
    calc = FXCalculator()
    
    # 计算点值
    pip_value = calc.pip_value('USDCNH', 100000)
    
    # 计算保证金
    margin = calc.margin_required('USDCNH', 100000, 7.25, leverage=50)
    
    # 计算仓位大小
    size = calc.position_size(account=100000, risk_pct=0.02, stop_pips=50)
    """
    
    # 货币对配置
    PAIR_CONFIG = {
        'USDCNH': {'pip_size': 0.0001, 'base': 'USD', 'quote': 'CNH'},
        'EURUSD': {'pip_size': 0.0001, 'base': 'EUR', 'quote': 'USD'},
        'USDJPY': {'pip_size': 0.01, 'base': 'USD', 'quote': 'JPY'},
        'GBPUSD': {'pip_size': 0.0001, 'base': 'GBP', 'quote': 'USD'},
        'AUDUSD': {'pip_size': 0.0001, 'base': 'AUD', 'quote': 'USD'},
    }
    
    def pip_value(self, pair: str, size: float, 
                  account_currency: str = 'USD',
                  current_rate: float = None) -> float:
        """计算点值
        
        Args:
            pair: 货币对
            size: 交易规模（名义金额）
            account_currency: 账户货币
            current_rate: 当前汇率（用于转换）
        
        Returns:
            每点价值
        """
        config = self.PAIR_CONFIG.get(pair.upper(), {'pip_size': 0.0001})
        pip_size = config['pip_size']
        
        # 基础点值 = 规模 * 点大小
        base_pip_value = size * pip_size
        
        # 如果报价货币不是账户货币，需要转换
        quote = config.get('quote', 'USD')
        if quote != account_currency and current_rate:
            base_pip_value = base_pip_value / current_rate
        
        return base_pip_value
    
    def margin_required(self, pair: str, size: float, 
                        price: float, leverage: float = 100) -> float:
        """计算所需保证金
        
        Args:
            pair: 货币对
            size: 交易规模
            price: 当前价格
            leverage: 杠杆倍数
        
        Returns:
            所需保证金
        """
        notional = size * price
        return notional / leverage
    
    def position_size(self, account: float, risk_pct: float,
                      stop_pips: float, pip_value: float = None,
                      pair: str = None, price: float = None) -> float:
        """根据风险计算仓位大小
        
        Args:
            account: 账户金额
            risk_pct: 风险比例 (如 0.02 = 2%)
            stop_pips: 止损点数
            pip_value: 每点价值（每标准手）
            pair: 货币对（用于自动计算pip_value）
            price: 当前价格
        
        Returns:
            建议仓位大小
        """
        risk_amount = account * risk_pct
        
        if pip_value is None and pair:
            # 假设1标准手 = 100000
            pip_value = self.pip_value(pair, 100000)
        elif pip_value is None:
            pip_value = 10  # 默认USD pairs
        
        # 仓位 = 风险金额 / (止损点数 * 点值)
        lots = risk_amount / (stop_pips * pip_value)
        
        return lots * 100000  # 转换为名义金额
    
    def pips_to_price(self, pips: float, pair: str = None) -> float:
        """点数转价格变动"""
        config = self.PAIR_CONFIG.get(pair.upper() if pair else '', {'pip_size': 0.0001})
        return pips * config['pip_size']
    
    def price_to_pips(self, price_change: float, pair: str = None) -> float:
        """价格变动转点数"""
        config = self.PAIR_CONFIG.get(pair.upper() if pair else '', {'pip_size': 0.0001})
        return price_change / config['pip_size']
    
    def spread_cost(self, spread_pips: float, size: float,
                    pair: str = None) -> float:
        """计算点差成本"""
        pip_value = self.pip_value(pair or 'USDCNH', size)
        return spread_pips * pip_value
    
    def breakeven_pips(self, spread_pips: float, 
                       commission_per_lot: float = 0,
                       size: float = 100000) -> float:
        """计算盈亏平衡点数
        
        考虑点差和手续费后需要多少点才能盈利
        """
        # 点差成本
        spread_cost = spread_pips
        
        # 手续费转换为点数
        if commission_per_lot > 0:
            lots = size / 100000
            commission_pips = (commission_per_lot * lots * 2) / (size * 0.0001)
            spread_cost += commission_pips
        
        return spread_cost
    
    def calculate_pnl(self, entry_price: float, exit_price: float,
                      size: float, direction: str = 'long',
                      pair: str = 'USDCNH') -> Dict:
        """计算盈亏
        
        Returns:
            包含点数盈亏、金额盈亏、收益率的字典
        """
        if direction == 'long':
            price_change = exit_price - entry_price
        else:
            price_change = entry_price - exit_price
        
        pips = self.price_to_pips(price_change, pair)
        pip_value = self.pip_value(pair, size)
        pnl_amount = pips * pip_value
        
        return {
            'pips': round(pips, 1),
            'amount': round(pnl_amount, 2),
            'return_pct': round(price_change / entry_price * 100, 4),
            'direction': direction
        }
    
    def swap_cost(self, size: float, days: int,
                  long_swap: float, short_swap: float,
                  direction: str = 'long') -> float:
        """计算隔夜利息成本
        
        Args:
            size: 仓位大小
            days: 持仓天数
            long_swap: 多头隔夜利息（点）
            short_swap: 空头隔夜利息（点）
            direction: 方向
        
        Returns:
            总隔夜利息（可正可负）
        """
        swap_rate = long_swap if direction == 'long' else short_swap
        pip_value = self.pip_value('USDCNH', size)
        
        # 周三三倍
        wednesday_count = days // 7
        regular_days = days - wednesday_count * 2  # 周三算3天
        
        total_swap = (regular_days + wednesday_count * 3) * swap_rate * pip_value
        return round(total_swap, 2)


# 便捷实例
fx = FXCalculator()
