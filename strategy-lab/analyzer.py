"""策略分析器 - 生成可视化图表"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json


class StrategyAnalyzer:
    """策略分析器"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
        self._prepare_data()
    
    def _prepare_data(self):
        """准备数据"""
        if not isinstance(self.data.index, pd.DatetimeIndex):
            if 'timestamp' in self.data.columns:
                self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
                self.data.set_index('timestamp', inplace=True)
    
    def price_chart_data(self) -> Dict:
        """价格走势图数据"""
        df = self.data
        return {
            'dates': df.index.strftime('%Y-%m-%d %H:%M').tolist(),
            'open': df['open'].tolist() if 'open' in df.columns else [],
            'high': df['high'].tolist() if 'high' in df.columns else [],
            'low': df['low'].tolist() if 'low' in df.columns else [],
            'close': df['close'].tolist(),
            'volume': df['volume'].tolist() if 'volume' in df.columns else []
        }
    
    def returns_distribution(self, returns: List[float]) -> Dict:
        """收益分布图数据"""
        returns = np.array(returns)
        
        # 直方图数据
        hist, bin_edges = np.histogram(returns, bins=20)
        
        return {
            'histogram': {
                'counts': hist.tolist(),
                'bins': bin_edges.tolist()
            },
            'stats': {
                'mean': float(np.mean(returns)),
                'std': float(np.std(returns)),
                'skew': float(pd.Series(returns).skew()),
                'kurtosis': float(pd.Series(returns).kurtosis()),
                'min': float(np.min(returns)),
                'max': float(np.max(returns)),
                'median': float(np.median(returns))
            }
        }
    
    def drawdown_analysis(self, equity_curve: List[float]) -> Dict:
        """回撤分析"""
        equity = np.array(equity_curve)
        
        # 计算回撤
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100
        
        # 最大回撤
        max_dd = np.max(drawdown)
        max_dd_idx = np.argmax(drawdown)
        
        # 找到最大回撤的起始点
        peak_idx = np.argmax(equity[:max_dd_idx + 1])
        
        return {
            'drawdown_curve': drawdown.tolist(),
            'max_drawdown': float(max_dd),
            'max_dd_start_idx': int(peak_idx),
            'max_dd_end_idx': int(max_dd_idx),
            'current_drawdown': float(drawdown[-1]) if len(drawdown) > 0 else 0
        }
    
    def monthly_returns(self, trades: List[Dict]) -> Dict:
        """月度收益分析"""
        if not trades:
            return {'months': [], 'returns': []}
        
        # 按月汇总
        monthly = {}
        for t in trades:
            month = t['entry_time'][:7]  # YYYY-MM
            if month not in monthly:
                monthly[month] = []
            monthly[month].append(t['return_pct'])
        
        months = sorted(monthly.keys())
        returns = [sum(monthly[m]) for m in months]
        
        return {
            'months': months,
            'returns': returns,
            'avg_monthly': float(np.mean(returns)) if returns else 0
        }
    
    def weekday_analysis(self) -> Dict:
        """星期分析"""
        df = self.data.copy()
        df['weekday'] = df.index.dayofweek
        df['return'] = df['close'].pct_change() * 100
        
        weekday_stats = df.groupby('weekday')['return'].agg(['mean', 'std', 'count'])
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        
        return {
            'weekdays': [weekday_names[i] for i in weekday_stats.index],
            'avg_returns': weekday_stats['mean'].tolist(),
            'volatility': weekday_stats['std'].tolist(),
            'counts': weekday_stats['count'].tolist()
        }
    
    def hourly_analysis(self) -> Dict:
        """小时分析"""
        df = self.data.copy()
        df['hour'] = df.index.hour
        df['return'] = df['close'].pct_change() * 100
        
        hourly_stats = df.groupby('hour')['return'].agg(['mean', 'std', 'count'])
        
        return {
            'hours': hourly_stats.index.tolist(),
            'avg_returns': hourly_stats['mean'].tolist(),
            'volatility': hourly_stats['std'].tolist(),
            'counts': hourly_stats['count'].tolist()
        }
    
    def correlation_matrix(self, other_data: Dict[str, pd.DataFrame] = None) -> Dict:
        """相关性矩阵"""
        df = self.data[['close']].copy()
        df.columns = ['main']
        
        if other_data:
            for name, data in other_data.items():
                if 'close' in data.columns:
                    df[name] = data['close']
        
        # 计算收益率相关性
        returns = df.pct_change().dropna()
        corr = returns.corr()
        
        return {
            'labels': corr.columns.tolist(),
            'matrix': corr.values.tolist()
        }
    
    def generate_full_report(self, strategy_result: Dict) -> Dict:
        """生成完整分析报告"""
        trades = strategy_result.get('trades', [])
        returns = strategy_result.get('returns', [])
        
        # 计算权益曲线
        if returns:
            initial = 100
            equity = [initial]
            for r in returns:
                equity.append(equity[-1] * (1 + r / 100))
        else:
            equity = [100]
        
        report = {
            'summary': {
                'total_trades': strategy_result.get('total_trades', 0),
                'win_rate': strategy_result.get('win_rate', 0),
                'total_return': strategy_result.get('total_return', 0),
                'sharpe_ratio': strategy_result.get('sharpe_ratio', 0),
                'avg_return': strategy_result.get('avg_return', 0)
            },
            'charts': {
                'price': self.price_chart_data(),
                'equity_curve': equity,
                'drawdown': self.drawdown_analysis(equity),
                'returns_distribution': self.returns_distribution(returns) if returns else None,
                'monthly_returns': self.monthly_returns(trades),
                'weekday_analysis': self.weekday_analysis(),
                'hourly_analysis': self.hourly_analysis()
            },
            'trades': trades
        }
        
        return report
