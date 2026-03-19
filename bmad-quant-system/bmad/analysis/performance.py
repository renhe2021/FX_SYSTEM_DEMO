"""绩效分析器"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from .metrics import (
    calculate_sharpe,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_sortino,
    calculate_calmar
)


class PerformanceAnalyzer:
    """绩效分析器
    
    分析回测结果，生成绩效报告
    """
    
    def __init__(self, 
                 equity_curve: pd.DataFrame = None,
                 trades: pd.DataFrame = None,
                 initial_capital: float = 1000000):
        self.equity_curve = equity_curve
        self.trades = trades
        self.initial_capital = initial_capital
        self._metrics: Dict[str, Any] = {}
    
    def analyze(self) -> Dict[str, Any]:
        """执行完整分析"""
        self._metrics = {}
        
        if self.equity_curve is not None and not self.equity_curve.empty:
            self._analyze_returns()
            self._analyze_drawdown()
        
        if self.trades is not None and not self.trades.empty:
            self._analyze_trades()
        
        return self._metrics
    
    def _analyze_returns(self):
        """分析收益"""
        equity = self.equity_curve['equity']
        returns = equity.pct_change().dropna()
        
        # 总收益
        total_return = (equity.iloc[-1] - self.initial_capital) / self.initial_capital
        
        # 年化收益
        days = (equity.index[-1] - equity.index[0]).days
        annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
        
        # 波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 风险调整收益
        sharpe = calculate_sharpe(returns)
        sortino = calculate_sortino(returns)
        
        self._metrics.update({
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino
        })
    
    def _analyze_drawdown(self):
        """分析回撤"""
        equity = self.equity_curve['equity']
        
        max_dd = calculate_max_drawdown(equity)
        
        # 计算回撤持续时间
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        
        # 找最大回撤区间
        max_dd_end = drawdown.idxmin()
        max_dd_start = equity[:max_dd_end].idxmax()
        
        # 恢复时间
        recovery_data = equity[max_dd_end:]
        recovery_idx = recovery_data[recovery_data >= cummax[max_dd_end]].index
        recovery_date = recovery_idx[0] if len(recovery_idx) > 0 else None
        
        self._metrics.update({
            'max_drawdown': max_dd,
            'max_dd_start': max_dd_start,
            'max_dd_end': max_dd_end,
            'recovery_date': recovery_date,
            'calmar_ratio': calculate_calmar(
                self._metrics.get('annual_return', 0), max_dd
            )
        })
    
    def _analyze_trades(self):
        """分析交易"""
        trades = self.trades
        
        total_trades = len(trades)
        
        if 'pnl' in trades.columns:
            win_rate = calculate_win_rate(trades)
            profit_factor = calculate_profit_factor(trades)
            
            winning_trades = trades[trades['pnl'] > 0]
            losing_trades = trades[trades['pnl'] < 0]
            
            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
            
            self._metrics.update({
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'total_pnl': trades['pnl'].sum(),
                'avg_pnl': trades['pnl'].mean()
            })
        else:
            self._metrics['total_trades'] = total_trades
    
    def get_summary(self) -> Dict[str, str]:
        """获取格式化的摘要"""
        if not self._metrics:
            self.analyze()
        
        summary = {}
        
        # 收益指标
        if 'total_return' in self._metrics:
            summary['总收益'] = f"{self._metrics['total_return']:.2%}"
            summary['年化收益'] = f"{self._metrics['annual_return']:.2%}"
            summary['波动率'] = f"{self._metrics['volatility']:.2%}"
        
        # 风险指标
        if 'sharpe_ratio' in self._metrics:
            summary['夏普比率'] = f"{self._metrics['sharpe_ratio']:.2f}"
            summary['索提诺比率'] = f"{self._metrics['sortino_ratio']:.2f}"
        
        if 'max_drawdown' in self._metrics:
            summary['最大回撤'] = f"{self._metrics['max_drawdown']:.2%}"
            summary['卡玛比率'] = f"{self._metrics['calmar_ratio']:.2f}"
        
        # 交易指标
        if 'total_trades' in self._metrics:
            summary['交易次数'] = str(self._metrics['total_trades'])
        
        if 'win_rate' in self._metrics:
            summary['胜率'] = f"{self._metrics['win_rate']:.2%}"
            summary['盈亏比'] = f"{self._metrics['profit_factor']:.2f}"
        
        return summary
    
    def generate_report(self) -> str:
        """生成文本报告"""
        summary = self.get_summary()
        
        lines = ["=" * 40, "绩效分析报告", "=" * 40, ""]
        
        for key, value in summary.items():
            lines.append(f"{key}: {value}")
        
        lines.append("")
        lines.append("=" * 40)
        
        return "\n".join(lines)
