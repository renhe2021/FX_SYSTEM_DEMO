"""
Revenue Peak Analyzer
=====================

分析加价率 (Markup%) 与营业收入 (Revenue) 的倒U型关系曲线，
并找到收入峰值点（最优定价策略）。

核心概念:
- 加价率 (Markup%): (售价 - 成本) / 成本 × 100%
- 营业收入 (Revenue): 售价 × 销量
- 需求函数: Q = a - b×P (线性需求)

经济学原理:
- 价格太低: 销量高但单价低，总收入受限
- 价格太高: 单价高但销量锐减，总收入下降
- 最优点: 在两者之间，收入达到峰值
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from scipy.optimize import minimize_scalar
from typing import Dict, Tuple, Optional, List
import warnings

warnings.filterwarnings('ignore')


class RevenuePeakAnalyzer:
    """
    加价率-收入峰值分析器
    
    分析在线性需求函数下，不同加价率对应的销量、收入和利润，
    找到使收入最大化的最优加价率。
    
    Usage:
    ------
    analyzer = RevenuePeakAnalyzer(cost=50, demand_intercept=200, demand_slope=1.0)
    df = analyzer.generate_revenue_matrix(markup_start=0, markup_end=150, step=5)
    peak = analyzer.find_revenue_peak(df)
    analyzer.plot_revenue_curve(df, peak_info=peak, show_quantity=True)
    plt.show()
    """
    
    def __init__(self, cost: float, demand_intercept: float, demand_slope: float):
        """
        初始化分析器
        
        Args:
            cost: 单位产品成本
            demand_intercept: 需求函数 Q = a - b*P 中的 a (P=0时的最大需求量)
            demand_slope: 需求函数 Q = a - b*P 中的 b (价格敏感度, >0)
        
        需求函数: Q = a - b*P
        - a: 截距，代表价格为0时的理论最大需求量
        - b: 斜率（绝对值），代表价格每上涨1单位，需求减少b单位
        """
        if cost <= 0:
            raise ValueError("Cost must be positive")
        if demand_intercept <= 0:
            raise ValueError("Demand intercept (a) must be positive")
        if demand_slope <= 0:
            raise ValueError("Demand slope (b) must be positive")
        
        self.cost = cost
        self.a = demand_intercept
        self.b = demand_slope
        
        # 计算理论最高价格（需求降为0的价格）
        self.max_price = self.a / self.b
        self.max_markup = (self.max_price / self.cost - 1) * 100
        
        print(f"[RevenuePeakAnalyzer] Initialized:")
        print(f"  - Unit Cost: {self.cost}")
        print(f"  - Demand Function: Q = {self.a} - {self.b}*P")
        print(f"  - Max Price (Q=0): {self.max_price:.2f}")
        print(f"  - Max Markup (Q=0): {self.max_markup:.1f}%")
    
    def _calc_quantity(self, price: float) -> float:
        """计算给定价格下的需求量"""
        return max(0, self.a - self.b * price)
    
    def _calc_revenue(self, price: float) -> float:
        """计算给定价格下的收入"""
        q = self._calc_quantity(price)
        return price * q
    
    def _calc_profit(self, price: float) -> float:
        """计算给定价格下的利润"""
        q = self._calc_quantity(price)
        return (price - self.cost) * q
    
    def generate_revenue_matrix(
        self, 
        markup_start: float = 0, 
        markup_end: float = 200, 
        step: float = 1
    ) -> pd.DataFrame:
        """
        生成不同加价率下的价格、销量、收入矩阵
        
        Args:
            markup_start: 起始加价率 (%)
            markup_end: 结束加价率 (%)
            step: 步长 (%)
        
        Returns:
            DataFrame with columns: [markup_pct, price, quantity, revenue, profit, profit_margin]
        """
        markups = np.arange(markup_start, markup_end + step, step)
        
        data = []
        for m in markups:
            price = self.cost * (1 + m / 100)
            quantity = self._calc_quantity(price)
            revenue = price * quantity
            profit = (price - self.cost) * quantity
            profit_margin = (profit / revenue * 100) if revenue > 0 else 0
            
            data.append({
                'markup_pct': m,
                'price': price,
                'quantity': quantity,
                'revenue': revenue,
                'profit': profit,
                'profit_margin': profit_margin
            })
        
        df = pd.DataFrame(data)
        
        print(f"[RevenuePeakAnalyzer] Generated matrix: {len(df)} rows")
        print(f"  - Markup range: {markup_start}% ~ {markup_end}%")
        print(f"  - Price range: {df['price'].min():.2f} ~ {df['price'].max():.2f}")
        print(f"  - Revenue range: {df['revenue'].min():.2f} ~ {df['revenue'].max():.2f}")
        
        return df
    
    def find_revenue_peak(self, df: pd.DataFrame = None) -> Dict:
        """
        找到收入峰值点
        
        Args:
            df: 预计算的数据矩阵（可选，如果不提供则使用解析解）
        
        Returns:
            dict: {markup_pct, price, quantity, revenue, profit, profit_margin}
        """
        # 解析解: 对于 Q = a - b*P, R = P*Q = P*(a-bP) = aP - bP^2
        # dR/dP = a - 2bP = 0  =>  P* = a / (2b)
        optimal_price = self.a / (2 * self.b)
        optimal_markup = (optimal_price / self.cost - 1) * 100
        optimal_quantity = self._calc_quantity(optimal_price)
        optimal_revenue = self._calc_revenue(optimal_price)
        optimal_profit = self._calc_profit(optimal_price)
        optimal_profit_margin = (optimal_profit / optimal_revenue * 100) if optimal_revenue > 0 else 0
        
        # 如果提供了 df，也返回数值解（验证）
        peak_info = {
            'markup_pct': optimal_markup,
            'price': optimal_price,
            'quantity': optimal_quantity,
            'revenue': optimal_revenue,
            'profit': optimal_profit,
            'profit_margin': optimal_profit_margin,
            'method': 'analytical'
        }
        
        if df is not None and not df.empty:
            # 数值解
            idx_max = df['revenue'].idxmax()
            numerical_peak = df.loc[idx_max].to_dict()
            numerical_peak['method'] = 'numerical'
            
            # 验证两者是否接近
            diff = abs(peak_info['revenue'] - numerical_peak['revenue'])
            if diff > 0.01 * peak_info['revenue']:
                print(f"[Warning] Analytical and numerical solutions differ by {diff:.2f}")
        
        print(f"\n[RevenuePeakAnalyzer] Revenue Peak Found:")
        print(f"  - Optimal Markup: {peak_info['markup_pct']:.2f}%")
        print(f"  - Optimal Price: {peak_info['price']:.2f}")
        print(f"  - Quantity at Peak: {peak_info['quantity']:.2f}")
        print(f"  - Peak Revenue: {peak_info['revenue']:.2f}")
        print(f"  - Profit at Peak: {peak_info['profit']:.2f}")
        print(f"  - Profit Margin: {peak_info['profit_margin']:.2f}%")
        
        return peak_info
    
    def find_profit_peak(self) -> Dict:
        """
        找到利润峰值点（与收入峰值点不同）
        
        利润 = (P - C) * Q = (P - C) * (a - bP)
        dProfit/dP = a - 2bP + bC = 0
        P* = (a + bC) / (2b)
        """
        optimal_price = (self.a + self.b * self.cost) / (2 * self.b)
        optimal_markup = (optimal_price / self.cost - 1) * 100
        optimal_quantity = self._calc_quantity(optimal_price)
        optimal_revenue = self._calc_revenue(optimal_price)
        optimal_profit = self._calc_profit(optimal_price)
        optimal_profit_margin = (optimal_profit / optimal_revenue * 100) if optimal_revenue > 0 else 0
        
        peak_info = {
            'markup_pct': optimal_markup,
            'price': optimal_price,
            'quantity': optimal_quantity,
            'revenue': optimal_revenue,
            'profit': optimal_profit,
            'profit_margin': optimal_profit_margin
        }
        
        print(f"\n[RevenuePeakAnalyzer] Profit Peak Found:")
        print(f"  - Optimal Markup: {peak_info['markup_pct']:.2f}%")
        print(f"  - Optimal Price: {peak_info['price']:.2f}")
        print(f"  - Max Profit: {peak_info['profit']:.2f}")
        
        return peak_info
    
    def plot_revenue_curve(
        self, 
        df: pd.DataFrame, 
        peak_info: Dict = None,
        profit_peak_info: Dict = None,
        show_quantity: bool = False,
        show_profit: bool = False,
        smooth: bool = True,
        figsize: Tuple[int, int] = (12, 7),
        title: str = None
    ):
        """
        绘制收入曲线并标记峰值点
        
        Args:
            df: 数据矩阵
            peak_info: 收入峰值信息
            profit_peak_info: 利润峰值信息
            show_quantity: 是否显示销量曲线（次Y轴）
            show_profit: 是否显示利润曲线
            smooth: 是否平滑曲线
            figsize: 图表大小
            title: 标题
        """
        fig, ax1 = plt.subplots(figsize=figsize)
        
        x = df['markup_pct'].values
        y_revenue = df['revenue'].values
        y_quantity = df['quantity'].values
        y_profit = df['profit'].values
        
        # 平滑处理
        if smooth and len(x) > 10:
            x_smooth = np.linspace(x.min(), x.max(), 300)
            
            # Revenue
            spl_rev = make_interp_spline(x, y_revenue, k=3)
            y_revenue_smooth = spl_rev(x_smooth)
            
            # Quantity
            spl_qty = make_interp_spline(x, y_quantity, k=3)
            y_quantity_smooth = spl_qty(x_smooth)
            
            # Profit
            spl_profit = make_interp_spline(x, y_profit, k=3)
            y_profit_smooth = spl_profit(x_smooth)
        else:
            x_smooth = x
            y_revenue_smooth = y_revenue
            y_quantity_smooth = y_quantity
            y_profit_smooth = y_profit
        
        # 绘制收入曲线
        color_revenue = '#2196F3'
        ax1.plot(x_smooth, y_revenue_smooth, color=color_revenue, linewidth=2.5, label='Revenue')
        ax1.fill_between(x_smooth, 0, y_revenue_smooth, alpha=0.1, color=color_revenue)
        ax1.set_xlabel('Markup Rate (%)', fontsize=12)
        ax1.set_ylabel('Revenue', color=color_revenue, fontsize=12)
        ax1.tick_params(axis='y', labelcolor=color_revenue)
        
        # 标记收入峰值点
        if peak_info:
            ax1.scatter([peak_info['markup_pct']], [peak_info['revenue']], 
                       color='red', s=150, zorder=5, marker='o', edgecolors='white', linewidths=2)
            ax1.axvline(x=peak_info['markup_pct'], color='red', linestyle='--', alpha=0.7, linewidth=1.5)
            ax1.axhline(y=peak_info['revenue'], color='red', linestyle=':', alpha=0.5, linewidth=1)
            
            # 标注文字
            ax1.annotate(
                f"Revenue Peak\nMarkup: {peak_info['markup_pct']:.1f}%\nPrice: {peak_info['price']:.2f}\nRevenue: {peak_info['revenue']:.0f}",
                xy=(peak_info['markup_pct'], peak_info['revenue']),
                xytext=(peak_info['markup_pct'] + 15, peak_info['revenue'] * 0.85),
                fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', color='red')
            )
        
        # 绘制利润曲线
        if show_profit:
            ax1.plot(x_smooth, y_profit_smooth, color='#4CAF50', linewidth=2, 
                    linestyle='--', label='Profit', alpha=0.8)
            
            if profit_peak_info:
                ax1.scatter([profit_peak_info['markup_pct']], [profit_peak_info['profit']], 
                           color='#4CAF50', s=100, zorder=5, marker='s', edgecolors='white', linewidths=2)
                ax1.annotate(
                    f"Profit Peak\nMarkup: {profit_peak_info['markup_pct']:.1f}%",
                    xy=(profit_peak_info['markup_pct'], profit_peak_info['profit']),
                    xytext=(profit_peak_info['markup_pct'] + 15, profit_peak_info['profit'] * 1.1),
                    fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=-0.3', color='green')
                )
        
        # 绘制销量曲线（次Y轴）
        if show_quantity:
            ax2 = ax1.twinx()
            color_quantity = '#FF9800'
            ax2.plot(x_smooth, y_quantity_smooth, color=color_quantity, linewidth=2, 
                    linestyle='-.', label='Quantity', alpha=0.8)
            ax2.set_ylabel('Quantity', color=color_quantity, fontsize=12)
            ax2.tick_params(axis='y', labelcolor=color_quantity)
            
            # 合并图例
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        else:
            ax1.legend(loc='upper right')
        
        # 标题
        if title is None:
            title = f'Markup Rate vs Revenue (Inverted U-Curve)\nCost={self.cost}, Demand: Q={self.a}-{self.b}P'
        ax1.set_title(title, fontsize=14, fontweight='bold')
        
        # 网格
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(df['markup_pct'].min(), df['markup_pct'].max())
        ax1.set_ylim(0, None)
        
        plt.tight_layout()
        
        return fig, ax1
    
    def sensitivity_analysis(
        self, 
        cost_range: List[float] = None,
        slope_range: List[float] = None,
        figsize: Tuple[int, int] = (14, 5)
    ):
        """
        敏感性分析：不同成本或需求参数下，最优加价率如何变化
        
        Args:
            cost_range: 成本范围 [min, max, step]
            slope_range: 需求斜率范围 [min, max, step]
        
        Returns:
            fig, axes
        """
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        # 1. 成本敏感性
        ax1 = axes[0]
        if cost_range is None:
            cost_range = [self.cost * 0.5, self.cost * 1.5, self.cost * 0.1]
        
        costs = np.arange(cost_range[0], cost_range[1] + cost_range[2], cost_range[2])
        optimal_markups_cost = []
        optimal_revenues_cost = []
        
        for c in costs:
            temp_analyzer = RevenuePeakAnalyzer.__new__(RevenuePeakAnalyzer)
            temp_analyzer.cost = c
            temp_analyzer.a = self.a
            temp_analyzer.b = self.b
            
            optimal_price = self.a / (2 * self.b)
            optimal_markup = (optimal_price / c - 1) * 100
            optimal_revenue = optimal_price * (self.a - self.b * optimal_price)
            
            optimal_markups_cost.append(optimal_markup)
            optimal_revenues_cost.append(optimal_revenue)
        
        ax1.plot(costs, optimal_markups_cost, 'b-o', linewidth=2, markersize=6)
        ax1.axvline(x=self.cost, color='red', linestyle='--', alpha=0.7, label=f'Current Cost={self.cost}')
        ax1.set_xlabel('Unit Cost', fontsize=11)
        ax1.set_ylabel('Optimal Markup (%)', fontsize=11)
        ax1.set_title('Sensitivity: Cost vs Optimal Markup', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 需求斜率敏感性
        ax2 = axes[1]
        if slope_range is None:
            slope_range = [self.b * 0.5, self.b * 2, self.b * 0.1]
        
        slopes = np.arange(slope_range[0], slope_range[1] + slope_range[2], slope_range[2])
        optimal_markups_slope = []
        optimal_revenues_slope = []
        
        for b in slopes:
            optimal_price = self.a / (2 * b)
            optimal_markup = (optimal_price / self.cost - 1) * 100
            optimal_revenue = optimal_price * (self.a - b * optimal_price)
            
            optimal_markups_slope.append(optimal_markup)
            optimal_revenues_slope.append(optimal_revenue)
        
        ax2.plot(slopes, optimal_markups_slope, 'g-s', linewidth=2, markersize=6)
        ax2.axvline(x=self.b, color='red', linestyle='--', alpha=0.7, label=f'Current b={self.b}')
        ax2.set_xlabel('Demand Slope (b)', fontsize=11)
        ax2.set_ylabel('Optimal Markup (%)', fontsize=11)
        ax2.set_title('Sensitivity: Price Sensitivity vs Optimal Markup', fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        return fig, axes
    
    def compare_revenue_vs_profit_optimization(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        比较收入最大化和利润最大化两种策略
        
        Returns:
            DataFrame comparing the two strategies
        """
        revenue_peak = self.find_revenue_peak(df)
        profit_peak = self.find_profit_peak()
        
        comparison = pd.DataFrame({
            'Metric': ['Markup (%)', 'Price', 'Quantity', 'Revenue', 'Profit', 'Profit Margin (%)'],
            'Revenue Maximization': [
                f"{revenue_peak['markup_pct']:.2f}",
                f"{revenue_peak['price']:.2f}",
                f"{revenue_peak['quantity']:.2f}",
                f"{revenue_peak['revenue']:.2f}",
                f"{revenue_peak['profit']:.2f}",
                f"{revenue_peak['profit_margin']:.2f}"
            ],
            'Profit Maximization': [
                f"{profit_peak['markup_pct']:.2f}",
                f"{profit_peak['price']:.2f}",
                f"{profit_peak['quantity']:.2f}",
                f"{profit_peak['revenue']:.2f}",
                f"{profit_peak['profit']:.2f}",
                f"{profit_peak['profit_margin']:.2f}"
            ]
        })
        
        print("\n[RevenuePeakAnalyzer] Strategy Comparison:")
        print(comparison.to_string(index=False))
        
        return comparison


def demo_multiple_scenarios():
    """演示多种场景下的分析"""
    
    scenarios = [
        {'name': 'Low Cost, High Demand', 'cost': 30, 'a': 300, 'b': 1.5},
        {'name': 'Medium Cost, Medium Demand', 'cost': 50, 'a': 200, 'b': 1.0},
        {'name': 'High Cost, Low Demand', 'cost': 80, 'a': 150, 'b': 0.8},
    ]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    for i, scenario in enumerate(scenarios):
        ax = axes[i]
        
        analyzer = RevenuePeakAnalyzer(
            cost=scenario['cost'],
            demand_intercept=scenario['a'],
            demand_slope=scenario['b']
        )
        
        df = analyzer.generate_revenue_matrix(markup_start=0, markup_end=200, step=2)
        peak = analyzer.find_revenue_peak(df)
        
        # 绘制
        x = df['markup_pct'].values
        y = df['revenue'].values
        
        ax.plot(x, y, 'b-', linewidth=2)
        ax.fill_between(x, 0, y, alpha=0.1, color='blue')
        ax.scatter([peak['markup_pct']], [peak['revenue']], color='red', s=100, zorder=5)
        ax.axvline(x=peak['markup_pct'], color='red', linestyle='--', alpha=0.5)
        
        ax.set_xlabel('Markup (%)')
        ax.set_ylabel('Revenue')
        ax.set_title(f"{scenario['name']}\nOptimal Markup: {peak['markup_pct']:.1f}%")
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('Revenue Peak Analysis - Multiple Scenarios', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    return fig


def plot_simple(save_path: str = 'revenue_peak_simple.png'):
    """简洁的倒U型曲线示意图"""
    
    # 数据
    analyzer = RevenuePeakAnalyzer(cost=50, demand_intercept=200, demand_slope=1.0)
    df = analyzer.generate_revenue_matrix(markup_start=0, markup_end=250, step=1)
    peak = analyzer.find_revenue_peak(df)
    
    # 画图
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = df['markup_pct'].values
    y = df['revenue'].values
    
    # 曲线
    ax.plot(x, y, color='#2196F3', linewidth=3)
    ax.fill_between(x, 0, y, alpha=0.2, color='#2196F3')
    
    # 峰值点
    ax.scatter([peak['markup_pct']], [peak['revenue']], color='red', s=150, zorder=5)
    ax.axvline(x=peak['markup_pct'], color='red', linestyle='--', alpha=0.5)
    
    # 标注
    ax.annotate(f"Peak: {peak['markup_pct']:.0f}%",
                xy=(peak['markup_pct'], peak['revenue']),
                xytext=(peak['markup_pct'] + 30, peak['revenue'] * 0.9),
                fontsize=12, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='red'))
    
    ax.set_xlabel('Markup Rate (%)', fontsize=12)
    ax.set_ylabel('Revenue', fontsize=12)
    ax.set_title('Markup vs Revenue (Inverted U-Curve)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 250)
    ax.set_ylim(0, None)
    
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {save_path}")
    
    return fig


if __name__ == '__main__':
    fig = plot_simple('revenue_peak_simple.png')
    plt.show()
