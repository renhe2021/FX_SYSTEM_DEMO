"""
专业回测报告生成器
生成JSON格式的专业报告，适合前端展示
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime


class ProfessionalReportGenerator:
    """专业回测报告生成器"""
    
    def __init__(self, backtest_result: Dict[str, Any]):
        self.result = backtest_result
        self.equity_curve = pd.DataFrame(backtest_result.get('equity_curve', []))
        self.trades = pd.DataFrame(backtest_result.get('trades', []))
        
        if not self.equity_curve.empty and 'timestamp' in self.equity_curve.columns:
            self.equity_curve['timestamp'] = pd.to_datetime(self.equity_curve['timestamp'])
            self.equity_curve.set_index('timestamp', inplace=True)
    
    def generate_full_report(self) -> Dict[str, Any]:
        """生成完整报告"""
        return {
            'meta': self._generate_meta(),
            'summary': self._generate_summary(),
            'performance': self._generate_performance_metrics(),
            'risk': self._generate_risk_metrics(),
            'trades': self._generate_trade_analysis(),
            'charts': self._generate_chart_data(),
            'monthly': self._generate_monthly_returns(),
            'drawdown': self._generate_drawdown_analysis()
        }
    
    def _generate_meta(self) -> Dict[str, Any]:
        """元信息"""
        return {
            'id': self.result.get('id', ''),
            'strategy_name': self.result.get('strategy_name', ''),
            'symbol': self.result.get('symbol', ''),
            'start_date': self.result.get('start_date', ''),
            'end_date': self.result.get('end_date', ''),
            'created_at': self.result.get('created_at', ''),
            'parameters': self.result.get('parameters', {})
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """摘要信息"""
        return {
            'initial_capital': self.result.get('initial_capital', 0),
            'final_equity': self.result.get('final_equity', 0),
            'total_pnl': self.result.get('total_pnl', 0),
            'total_return': round(self.result.get('total_return', 0) * 100, 2),
            'total_return_display': f"{self.result.get('total_return', 0) * 100:.2f}%",
            'total_trades': self.result.get('total_trades', 0),
            'total_commission': self.result.get('total_commission', 0)
        }
    
    def _generate_performance_metrics(self) -> Dict[str, Any]:
        """绩效指标"""
        total_return = self.result.get('total_return', 0)
        annual_return = self.result.get('annual_return', 0)
        sharpe = self.result.get('sharpe_ratio', 0)
        
        # 计算额外指标
        if not self.equity_curve.empty and 'equity' in self.equity_curve.columns:
            returns = self.equity_curve['equity'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
            
            # 索提诺比率
            downside_returns = returns[returns < 0]
            sortino = (returns.mean() * 252) / (downside_returns.std() * np.sqrt(252)) if len(downside_returns) > 0 and downside_returns.std() > 0 else 0
        else:
            volatility = 0
            sortino = 0
        
        return {
            'total_return': round(total_return * 100, 2),
            'annual_return': round(annual_return * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'sortino_ratio': round(sortino, 2),
            'volatility': round(volatility * 100, 2),
            'profit_factor': round(self.result.get('profit_factor', 0), 2),
            'calmar_ratio': round(annual_return / abs(self.result.get('max_drawdown', 1)) if self.result.get('max_drawdown', 0) != 0 else 0, 2)
        }
    
    def _generate_risk_metrics(self) -> Dict[str, Any]:
        """风险指标"""
        max_dd = self.result.get('max_drawdown', 0)
        
        # 计算VaR和CVaR
        if not self.equity_curve.empty and 'equity' in self.equity_curve.columns:
            returns = self.equity_curve['equity'].pct_change().dropna()
            var_95 = returns.quantile(0.05) if len(returns) > 0 else 0
            cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else 0
        else:
            var_95 = 0
            cvar_95 = 0
        
        return {
            'max_drawdown': round(max_dd * 100, 2),
            'max_drawdown_display': f"{max_dd * 100:.2f}%",
            'var_95': round(var_95 * 100, 2),
            'cvar_95': round(cvar_95 * 100, 2),
            'risk_level': self._calculate_risk_level(max_dd, var_95)
        }
    
    def _calculate_risk_level(self, max_dd: float, var: float) -> str:
        """计算风险等级"""
        score = abs(max_dd) * 0.6 + abs(var) * 0.4
        if score < 0.05:
            return 'low'
        elif score < 0.15:
            return 'medium'
        elif score < 0.25:
            return 'high'
        else:
            return 'very_high'
    
    def _generate_trade_analysis(self) -> Dict[str, Any]:
        """交易分析"""
        if self.trades.empty:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'avg_holding_period': 0,
                'trades_per_month': 0
            }
        
        pnl_col = 'pnl' if 'pnl' in self.trades.columns else None
        
        if pnl_col:
            winning = self.trades[self.trades[pnl_col] > 0]
            losing = self.trades[self.trades[pnl_col] <= 0]
            
            return {
                'total_trades': len(self.trades),
                'winning_trades': len(winning),
                'losing_trades': len(losing),
                'win_rate': round(len(winning) / len(self.trades) * 100, 1) if len(self.trades) > 0 else 0,
                'avg_win': round(winning[pnl_col].mean(), 2) if len(winning) > 0 else 0,
                'avg_loss': round(losing[pnl_col].mean(), 2) if len(losing) > 0 else 0,
                'largest_win': round(winning[pnl_col].max(), 2) if len(winning) > 0 else 0,
                'largest_loss': round(losing[pnl_col].min(), 2) if len(losing) > 0 else 0,
                'total_pnl': round(self.trades[pnl_col].sum(), 2),
                'avg_pnl': round(self.trades[pnl_col].mean(), 2)
            }
        
        return {'total_trades': len(self.trades)}
    
    def _generate_chart_data(self) -> Dict[str, Any]:
        """图表数据"""
        charts = {}
        
        # 权益曲线
        if not self.equity_curve.empty and 'equity' in self.equity_curve.columns:
            charts['equity_curve'] = {
                'labels': [str(d.date()) for d in self.equity_curve.index],
                'data': self.equity_curve['equity'].round(2).tolist()
            }
            
            # 回撤曲线
            cummax = self.equity_curve['equity'].cummax()
            drawdown = ((self.equity_curve['equity'] - cummax) / cummax * 100).round(2)
            charts['drawdown_curve'] = {
                'labels': [str(d.date()) for d in self.equity_curve.index],
                'data': drawdown.tolist()
            }
            
            # 日收益率
            returns = (self.equity_curve['equity'].pct_change() * 100).round(2).dropna()
            charts['daily_returns'] = {
                'labels': [str(d.date()) for d in returns.index],
                'data': returns.tolist()
            }
        
        # 交易盈亏分布
        if not self.trades.empty and 'pnl' in self.trades.columns:
            charts['trade_pnl'] = {
                'data': self.trades['pnl'].round(2).tolist(),
                'colors': ['#10b981' if x > 0 else '#ef4444' for x in self.trades['pnl']]
            }
        
        return charts
    
    def _generate_monthly_returns(self) -> Dict[str, Any]:
        """月度收益"""
        if self.equity_curve.empty or 'equity' not in self.equity_curve.columns:
            return {'data': [], 'years': [], 'months': list(range(1, 13))}
        
        # 计算月度收益
        monthly = self.equity_curve['equity'].resample('M').last()
        monthly_returns = monthly.pct_change().dropna()
        
        # 构建年-月矩阵
        data = []
        years = sorted(monthly_returns.index.year.unique())
        
        for year in years:
            year_data = {'year': year, 'months': {}}
            for month in range(1, 13):
                try:
                    val = monthly_returns[(monthly_returns.index.year == year) & 
                                         (monthly_returns.index.month == month)]
                    if len(val) > 0:
                        year_data['months'][month] = round(val.iloc[0] * 100, 2)
                    else:
                        year_data['months'][month] = None
                except:
                    year_data['months'][month] = None
            
            # 年度总收益
            year_returns = monthly_returns[monthly_returns.index.year == year]
            year_data['annual'] = round((1 + year_returns).prod() - 1, 4) * 100 if len(year_returns) > 0 else 0
            data.append(year_data)
        
        return {
            'data': data,
            'years': years,
            'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        }
    
    def _generate_drawdown_analysis(self) -> Dict[str, Any]:
        """回撤分析"""
        if self.equity_curve.empty or 'equity' not in self.equity_curve.columns:
            return {'max_drawdown': 0, 'drawdown_periods': []}
        
        equity = self.equity_curve['equity']
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        
        # 找到主要回撤期
        drawdown_periods = []
        in_drawdown = False
        start_idx = None
        
        for i, (idx, dd) in enumerate(drawdown.items()):
            if dd < 0 and not in_drawdown:
                in_drawdown = True
                start_idx = idx
            elif dd >= 0 and in_drawdown:
                in_drawdown = False
                if start_idx:
                    period_dd = drawdown[start_idx:idx]
                    drawdown_periods.append({
                        'start': str(start_idx.date()),
                        'end': str(idx.date()),
                        'max_drawdown': round(period_dd.min() * 100, 2),
                        'duration_days': (idx - start_idx).days
                    })
        
        # 按回撤幅度排序，取前5个
        drawdown_periods.sort(key=lambda x: x['max_drawdown'])
        top_drawdowns = drawdown_periods[:5]
        
        return {
            'max_drawdown': round(drawdown.min() * 100, 2),
            'current_drawdown': round(drawdown.iloc[-1] * 100, 2) if len(drawdown) > 0 else 0,
            'drawdown_periods': top_drawdowns
        }


def generate_report_for_miniprogram(backtest_result: Dict[str, Any]) -> Dict[str, Any]:
    """为小程序生成优化的报告格式"""
    generator = ProfessionalReportGenerator(backtest_result)
    full_report = generator.generate_full_report()
    
    # 为小程序优化的格式
    return {
        'id': full_report['meta']['id'],
        'title': full_report['meta']['strategy_name'],
        'symbol': full_report['meta']['symbol'],
        'period': f"{full_report['meta']['start_date']} ~ {full_report['meta']['end_date']}",
        
        # 核心指标卡片
        'cards': [
            {
                'label': '总收益率',
                'value': f"{full_report['summary']['total_return']}%",
                'color': '#10b981' if full_report['summary']['total_return'] > 0 else '#ef4444'
            },
            {
                'label': '夏普比率',
                'value': str(full_report['performance']['sharpe_ratio']),
                'color': '#3b82f6'
            },
            {
                'label': '最大回撤',
                'value': f"{full_report['risk']['max_drawdown']}%",
                'color': '#ef4444'
            },
            {
                'label': '胜率',
                'value': f"{full_report['trades']['win_rate']}%",
                'color': '#8b5cf6'
            }
        ],
        
        # 详细指标
        'metrics': {
            'performance': full_report['performance'],
            'risk': full_report['risk'],
            'trades': full_report['trades']
        },
        
        # 图表数据
        'charts': full_report['charts'],
        
        # 月度收益
        'monthly': full_report['monthly'],
        
        # 回撤分析
        'drawdown': full_report['drawdown']
    }
