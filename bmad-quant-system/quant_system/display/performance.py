"""
绩效分析 - BMAD Display Layer
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime


class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self, equity_curve: pd.DataFrame, trades: pd.DataFrame,
                 initial_capital: float = 1000000.0,
                 risk_free_rate: float = 0.02):
        """
        equity_curve: 权益曲线 DataFrame (index=timestamp, columns=['equity', 'cash', ...])
        trades: 交易记录 DataFrame
        initial_capital: 初始资金
        risk_free_rate: 无风险利率 (年化)
        """
        self.equity_curve = equity_curve
        self.trades = trades
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        
        # 计算收益率序列
        if not equity_curve.empty:
            self.returns = equity_curve['equity'].pct_change().dropna()
        else:
            self.returns = pd.Series()
    
    def calculate_all_metrics(self) -> Dict[str, Any]:
        """计算所有绩效指标"""
        metrics = {}
        
        # 基础指标
        metrics['total_return'] = self.total_return()
        metrics['annual_return'] = self.annual_return()
        metrics['volatility'] = self.volatility()
        metrics['sharpe_ratio'] = self.sharpe_ratio()
        metrics['sortino_ratio'] = self.sortino_ratio()
        metrics['calmar_ratio'] = self.calmar_ratio()
        
        # 风险指标
        metrics['max_drawdown'] = self.max_drawdown()
        metrics['max_drawdown_duration'] = self.max_drawdown_duration()
        metrics['var_95'] = self.value_at_risk(0.95)
        metrics['cvar_95'] = self.conditional_var(0.95)
        
        # 交易指标
        metrics['total_trades'] = self.total_trades()
        metrics['win_rate'] = self.win_rate()
        metrics['profit_factor'] = self.profit_factor()
        metrics['avg_win'] = self.average_win()
        metrics['avg_loss'] = self.average_loss()
        metrics['win_loss_ratio'] = self.win_loss_ratio()
        metrics['expectancy'] = self.expectancy()
        
        # 其他指标
        metrics['avg_holding_period'] = self.average_holding_period()
        metrics['trade_frequency'] = self.trade_frequency()
        
        return metrics
    
    def total_return(self) -> float:
        """总收益率"""
        if self.equity_curve.empty:
            return 0.0
        final_equity = self.equity_curve['equity'].iloc[-1]
        return (final_equity - self.initial_capital) / self.initial_capital
    
    def annual_return(self) -> float:
        """年化收益率"""
        if self.equity_curve.empty:
            return 0.0
        
        total_days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
        if total_days <= 0:
            return 0.0
        
        total_ret = self.total_return()
        return (1 + total_ret) ** (365 / total_days) - 1
    
    def volatility(self) -> float:
        """年化波动率"""
        if self.returns.empty:
            return 0.0
        return self.returns.std() * np.sqrt(252)
    
    def sharpe_ratio(self) -> float:
        """夏普比率"""
        if self.returns.empty or self.returns.std() == 0:
            return 0.0
        
        excess_returns = self.returns - self.risk_free_rate / 252
        return np.sqrt(252) * excess_returns.mean() / self.returns.std()
    
    def sortino_ratio(self) -> float:
        """索提诺比率 (只考虑下行风险)"""
        if self.returns.empty:
            return 0.0
        
        excess_returns = self.returns - self.risk_free_rate / 252
        downside_returns = self.returns[self.returns < 0]
        
        if downside_returns.empty or downside_returns.std() == 0:
            return 0.0
        
        return np.sqrt(252) * excess_returns.mean() / downside_returns.std()
    
    def calmar_ratio(self) -> float:
        """卡玛比率 (年化收益/最大回撤)"""
        max_dd = self.max_drawdown()
        if max_dd == 0:
            return 0.0
        return self.annual_return() / abs(max_dd)
    
    def max_drawdown(self) -> float:
        """最大回撤"""
        if self.equity_curve.empty:
            return 0.0
        
        equity = self.equity_curve['equity']
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        return drawdown.min()
    
    def max_drawdown_duration(self) -> int:
        """最大回撤持续时间（天）"""
        if self.equity_curve.empty:
            return 0
        
        equity = self.equity_curve['equity']
        cummax = equity.cummax()
        
        # 找到回撤期间
        in_drawdown = equity < cummax
        
        if not in_drawdown.any():
            return 0
        
        # 计算最长回撤持续时间
        max_duration = 0
        current_duration = 0
        
        for is_dd in in_drawdown:
            if is_dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return max_duration
    
    def value_at_risk(self, confidence: float = 0.95) -> float:
        """风险价值 (VaR)"""
        if self.returns.empty:
            return 0.0
        return self.returns.quantile(1 - confidence)
    
    def conditional_var(self, confidence: float = 0.95) -> float:
        """条件风险价值 (CVaR/ES)"""
        if self.returns.empty:
            return 0.0
        var = self.value_at_risk(confidence)
        return self.returns[self.returns <= var].mean()
    
    def total_trades(self) -> int:
        """总交易次数"""
        return len(self.trades) if not self.trades.empty else 0
    
    def win_rate(self) -> float:
        """胜率"""
        if self.trades.empty or 'pnl' not in self.trades.columns:
            return 0.0
        
        winning = len(self.trades[self.trades['pnl'] > 0])
        total = len(self.trades)
        return winning / total if total > 0 else 0.0
    
    def profit_factor(self) -> float:
        """盈亏比 (总盈利/总亏损)"""
        if self.trades.empty or 'pnl' not in self.trades.columns:
            return 0.0
        
        gross_profit = self.trades[self.trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(self.trades[self.trades['pnl'] < 0]['pnl'].sum())
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def average_win(self) -> float:
        """平均盈利"""
        if self.trades.empty or 'pnl' not in self.trades.columns:
            return 0.0
        
        winning_trades = self.trades[self.trades['pnl'] > 0]
        return winning_trades['pnl'].mean() if not winning_trades.empty else 0.0
    
    def average_loss(self) -> float:
        """平均亏损"""
        if self.trades.empty or 'pnl' not in self.trades.columns:
            return 0.0
        
        losing_trades = self.trades[self.trades['pnl'] < 0]
        return losing_trades['pnl'].mean() if not losing_trades.empty else 0.0
    
    def win_loss_ratio(self) -> float:
        """盈亏比 (平均盈利/平均亏损)"""
        avg_win = self.average_win()
        avg_loss = abs(self.average_loss())
        return avg_win / avg_loss if avg_loss > 0 else float('inf')
    
    def expectancy(self) -> float:
        """期望值 (每笔交易的预期收益)"""
        win_rate = self.win_rate()
        avg_win = self.average_win()
        avg_loss = abs(self.average_loss())
        
        return win_rate * avg_win - (1 - win_rate) * avg_loss
    
    def average_holding_period(self) -> float:
        """平均持仓时间（天）"""
        # 需要更详细的交易数据来计算
        return 0.0
    
    def trade_frequency(self) -> float:
        """交易频率 (每天交易次数)"""
        if self.trades.empty or self.equity_curve.empty:
            return 0.0
        
        total_days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
        return len(self.trades) / max(total_days, 1)
    
    def generate_report(self) -> str:
        """生成绩效报告"""
        metrics = self.calculate_all_metrics()
        
        report = []
        report.append("=" * 60)
        report.append("                    绩效分析报告")
        report.append("=" * 60)
        report.append("")
        
        report.append("【收益指标】")
        report.append(f"  总收益率:        {metrics['total_return']:.2%}")
        report.append(f"  年化收益率:      {metrics['annual_return']:.2%}")
        report.append(f"  年化波动率:      {metrics['volatility']:.2%}")
        report.append("")
        
        report.append("【风险调整收益】")
        report.append(f"  夏普比率:        {metrics['sharpe_ratio']:.2f}")
        report.append(f"  索提诺比率:      {metrics['sortino_ratio']:.2f}")
        report.append(f"  卡玛比率:        {metrics['calmar_ratio']:.2f}")
        report.append("")
        
        report.append("【风险指标】")
        report.append(f"  最大回撤:        {metrics['max_drawdown']:.2%}")
        report.append(f"  最大回撤持续:    {metrics['max_drawdown_duration']} 天")
        report.append(f"  VaR (95%):       {metrics['var_95']:.2%}")
        report.append(f"  CVaR (95%):      {metrics['cvar_95']:.2%}")
        report.append("")
        
        report.append("【交易统计】")
        report.append(f"  总交易次数:      {metrics['total_trades']}")
        report.append(f"  胜率:            {metrics['win_rate']:.2%}")
        report.append(f"  盈亏比:          {metrics['profit_factor']:.2f}")
        report.append(f"  平均盈利:        {metrics['avg_win']:.2f}")
        report.append(f"  平均亏损:        {metrics['avg_loss']:.2f}")
        report.append(f"  期望值:          {metrics['expectancy']:.2f}")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.calculate_all_metrics()
