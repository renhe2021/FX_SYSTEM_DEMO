"""价差分析工具

分析买卖价差、时间序列价差等
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


class SpreadAnalyzer:
    """价差分析器
    
    分析买卖价差的统计特性
    
    示例:
    ------
    analyzer = SpreadAnalyzer()
    analyzer.load_bidask('bidask_data.csv')
    stats = analyzer.analyze()
    analyzer.plot_spread()
    """
    
    def __init__(self, data: pd.DataFrame = None):
        self.data = data
        self._stats = {}
    
    def load_bidask(self, file_path: str, 
                    bid_col: str = 'bid',
                    ask_col: str = 'ask') -> 'SpreadAnalyzer':
        """加载买卖价数据"""
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        df.columns = df.columns.str.lower()
        
        if bid_col not in df.columns or ask_col not in df.columns:
            raise ValueError(f"找不到 {bid_col} 或 {ask_col} 列")
        
        self.data = df
        self.data['spread'] = df[ask_col] - df[bid_col]
        self.data['spread_pips'] = self.data['spread'] * 10000
        self.data['mid'] = (df[bid_col] + df[ask_col]) / 2
        
        print(f"✓ 加载成功: {len(self.data)} 条记录")
        return self
    
    def from_dataframe(self, df: pd.DataFrame,
                       bid_col: str = 'bid',
                       ask_col: str = 'ask') -> 'SpreadAnalyzer':
        """从DataFrame加载"""
        self.data = df.copy()
        self.data['spread'] = df[ask_col] - df[bid_col]
        self.data['spread_pips'] = self.data['spread'] * 10000
        self.data['mid'] = (df[bid_col] + df[ask_col]) / 2
        return self
    
    def analyze(self) -> Dict:
        """分析价差统计"""
        if self.data is None:
            return {}
        
        spread_pips = self.data['spread_pips']
        
        self._stats = {
            'count': len(spread_pips),
            'mean': spread_pips.mean(),
            'median': spread_pips.median(),
            'std': spread_pips.std(),
            'min': spread_pips.min(),
            'max': spread_pips.max(),
            'percentile_25': spread_pips.quantile(0.25),
            'percentile_75': spread_pips.quantile(0.75),
            'percentile_95': spread_pips.quantile(0.95),
            'percentile_99': spread_pips.quantile(0.99),
        }
        
        # 按小时分析
        if hasattr(self.data.index, 'hour'):
            hourly = self.data.groupby(self.data.index.hour)['spread_pips'].mean()
            self._stats['hourly_mean'] = hourly.to_dict()
            self._stats['best_hour'] = hourly.idxmin()
            self._stats['worst_hour'] = hourly.idxmax()
        
        return self._stats
    
    def print_stats(self):
        """打印统计信息"""
        if not self._stats:
            self.analyze()
        
        print("\n" + "=" * 50)
        print("价差统计分析 (单位: pips)")
        print("=" * 50)
        print(f"数据量: {self._stats['count']:,}")
        print(f"平均价差: {self._stats['mean']:.2f}")
        print(f"中位数: {self._stats['median']:.2f}")
        print(f"标准差: {self._stats['std']:.2f}")
        print(f"最小值: {self._stats['min']:.2f}")
        print(f"最大值: {self._stats['max']:.2f}")
        print(f"25%分位: {self._stats['percentile_25']:.2f}")
        print(f"75%分位: {self._stats['percentile_75']:.2f}")
        print(f"95%分位: {self._stats['percentile_95']:.2f}")
        print(f"99%分位: {self._stats['percentile_99']:.2f}")
        
        if 'best_hour' in self._stats:
            print(f"\n最佳交易时段: {self._stats['best_hour']}:00")
            print(f"最差交易时段: {self._stats['worst_hour']}:00")
    
    def by_hour(self) -> pd.DataFrame:
        """按小时统计"""
        if self.data is None:
            return pd.DataFrame()
        
        return self.data.groupby(self.data.index.hour)['spread_pips'].agg([
            'mean', 'median', 'std', 'min', 'max', 'count'
        ])
    
    def by_weekday(self) -> pd.DataFrame:
        """按星期统计"""
        if self.data is None:
            return pd.DataFrame()
        
        result = self.data.groupby(self.data.index.dayofweek)['spread_pips'].agg([
            'mean', 'median', 'std', 'min', 'max', 'count'
        ])
        result.index = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][:len(result)]
        return result
    
    def find_wide_spreads(self, threshold_pips: float = None) -> pd.DataFrame:
        """找出异常宽的价差
        
        Args:
            threshold_pips: 阈值（默认使用95%分位数）
        """
        if self.data is None:
            return pd.DataFrame()
        
        if threshold_pips is None:
            threshold_pips = self.data['spread_pips'].quantile(0.95)
        
        wide = self.data[self.data['spread_pips'] > threshold_pips]
        print(f"发现 {len(wide)} 条价差 > {threshold_pips:.2f} pips 的记录")
        return wide
    
    def plot_spread(self, **kwargs):
        """绘制价差图"""
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # 价差时间序列
            axes[0, 0].plot(self.data.index, self.data['spread_pips'], alpha=0.7)
            axes[0, 0].set_title('价差时间序列')
            axes[0, 0].set_ylabel('Spread (pips)')
            
            # 价差分布
            axes[0, 1].hist(self.data['spread_pips'], bins=50, edgecolor='black')
            axes[0, 1].set_title('价差分布')
            axes[0, 1].set_xlabel('Spread (pips)')
            
            # 按小时
            hourly = self.by_hour()
            axes[1, 0].bar(hourly.index, hourly['mean'])
            axes[1, 0].set_title('按小时平均价差')
            axes[1, 0].set_xlabel('Hour')
            axes[1, 0].set_ylabel('Avg Spread (pips)')
            
            # 按星期
            weekly = self.by_weekday()
            axes[1, 1].bar(range(len(weekly)), weekly['mean'])
            axes[1, 1].set_xticks(range(len(weekly)))
            axes[1, 1].set_xticklabels(weekly.index)
            axes[1, 1].set_title('按星期平均价差')
            axes[1, 1].set_ylabel('Avg Spread (pips)')
            
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            print("请安装 matplotlib: pip install matplotlib")
    
    def cost_analysis(self, trade_size: float = 100000,
                      trades_per_day: int = 1) -> Dict:
        """交易成本分析
        
        Args:
            trade_size: 每笔交易规模
            trades_per_day: 每天交易次数
        """
        if not self._stats:
            self.analyze()
        
        avg_spread = self._stats['mean']
        
        # 每点价值 (假设USDCNH)
        pip_value = trade_size * 0.0001
        
        # 单笔成本
        cost_per_trade = avg_spread * pip_value
        
        # 日/月/年成本
        daily_cost = cost_per_trade * trades_per_day
        monthly_cost = daily_cost * 22  # 约22个交易日
        yearly_cost = daily_cost * 252
        
        result = {
            'avg_spread_pips': avg_spread,
            'pip_value': pip_value,
            'cost_per_trade': cost_per_trade,
            'daily_cost': daily_cost,
            'monthly_cost': monthly_cost,
            'yearly_cost': yearly_cost
        }
        
        print("\n" + "=" * 50)
        print("交易成本分析")
        print("=" * 50)
        print(f"交易规模: {trade_size:,.0f}")
        print(f"平均价差: {avg_spread:.2f} pips")
        print(f"每点价值: {pip_value:.2f}")
        print(f"单笔成本: {cost_per_trade:.2f}")
        print(f"日成本 ({trades_per_day}笔): {daily_cost:.2f}")
        print(f"月成本: {monthly_cost:.2f}")
        print(f"年成本: {yearly_cost:.2f}")
        
        return result
