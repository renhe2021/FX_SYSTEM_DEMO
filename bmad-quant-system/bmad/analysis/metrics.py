"""绩效指标计算"""
import numpy as np
import pandas as pd
from typing import Union


def calculate_sharpe(returns: Union[pd.Series, np.ndarray], 
                     risk_free_rate: float = 0.0,
                     periods_per_year: int = 252) -> float:
    """计算夏普比率
    
    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率（年化）
        periods_per_year: 每年交易周期数
    
    Returns:
        夏普比率
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    returns = returns[~np.isnan(returns)]
    
    if len(returns) == 0 or np.std(returns) == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate / periods_per_year
    return np.sqrt(periods_per_year) * np.mean(excess_returns) / np.std(returns)


def calculate_max_drawdown(equity_curve: Union[pd.Series, np.ndarray]) -> float:
    """计算最大回撤
    
    Args:
        equity_curve: 权益曲线
    
    Returns:
        最大回撤（负数）
    """
    if isinstance(equity_curve, pd.Series):
        equity_curve = equity_curve.values
    
    if len(equity_curve) == 0:
        return 0.0
    
    cummax = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - cummax) / cummax
    return np.min(drawdown)


def calculate_win_rate(trades: pd.DataFrame, pnl_column: str = 'pnl') -> float:
    """计算胜率
    
    Args:
        trades: 交易记录DataFrame
        pnl_column: PnL列名
    
    Returns:
        胜率 (0-1)
    """
    if trades.empty or pnl_column not in trades.columns:
        return 0.0
    
    winning = len(trades[trades[pnl_column] > 0])
    total = len(trades)
    
    return winning / total if total > 0 else 0.0


def calculate_profit_factor(trades: pd.DataFrame, pnl_column: str = 'pnl') -> float:
    """计算盈亏比
    
    Args:
        trades: 交易记录DataFrame
        pnl_column: PnL列名
    
    Returns:
        盈亏比
    """
    if trades.empty or pnl_column not in trades.columns:
        return 0.0
    
    gross_profit = trades[trades[pnl_column] > 0][pnl_column].sum()
    gross_loss = abs(trades[trades[pnl_column] < 0][pnl_column].sum())
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss


def calculate_sortino(returns: Union[pd.Series, np.ndarray],
                      risk_free_rate: float = 0.0,
                      periods_per_year: int = 252) -> float:
    """计算索提诺比率
    
    只考虑下行波动率
    """
    if isinstance(returns, pd.Series):
        returns = returns.values
    
    returns = returns[~np.isnan(returns)]
    
    if len(returns) == 0:
        return 0.0
    
    excess_returns = returns - risk_free_rate / periods_per_year
    downside_returns = returns[returns < 0]
    
    if len(downside_returns) == 0 or np.std(downside_returns) == 0:
        return float('inf') if np.mean(excess_returns) > 0 else 0.0
    
    return np.sqrt(periods_per_year) * np.mean(excess_returns) / np.std(downside_returns)


def calculate_calmar(annual_return: float, max_drawdown: float) -> float:
    """计算卡玛比率
    
    Args:
        annual_return: 年化收益率
        max_drawdown: 最大回撤（负数）
    
    Returns:
        卡玛比率
    """
    if max_drawdown == 0:
        return float('inf') if annual_return > 0 else 0.0
    
    return annual_return / abs(max_drawdown)
