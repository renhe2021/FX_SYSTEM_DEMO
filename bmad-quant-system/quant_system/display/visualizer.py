"""
可视化模块 - BMAD Display Layer
"""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# 尝试导入绘图库
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib未安装，可视化功能将受限")


class QuantVisualizer:
    """量化可视化工具"""
    
    def __init__(self, figsize: tuple = (14, 8), style: str = 'seaborn-v0_8-whitegrid'):
        self.figsize = figsize
        self.style = style
        
        if HAS_MATPLOTLIB:
            try:
                plt.style.use(style)
            except:
                plt.style.use('seaborn-whitegrid' if 'seaborn-whitegrid' in plt.style.available else 'default')
    
    def plot_equity_curve(self, equity_curve: pd.DataFrame, 
                          title: str = "权益曲线",
                          save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制权益曲线"""
        if not HAS_MATPLOTLIB:
            logger.error("matplotlib未安装")
            return None
        
        if equity_curve.empty:
            logger.warning("权益曲线为空")
            return None
        
        fig, axes = plt.subplots(2, 1, figsize=self.figsize, height_ratios=[3, 1])
        
        # 权益曲线
        ax1 = axes[0]
        ax1.plot(equity_curve.index, equity_curve['equity'], 
                 label='权益', color='blue', linewidth=1.5)
        ax1.fill_between(equity_curve.index, equity_curve['equity'], 
                         alpha=0.3, color='blue')
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.set_ylabel('权益', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 回撤曲线
        ax2 = axes[1]
        cummax = equity_curve['equity'].cummax()
        drawdown = (equity_curve['equity'] - cummax) / cummax * 100
        ax2.fill_between(equity_curve.index, drawdown, 0, 
                         color='red', alpha=0.5, label='回撤')
        ax2.set_ylabel('回撤 (%)', fontsize=12)
        ax2.set_xlabel('日期', fontsize=12)
        ax2.legend(loc='lower left')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"图表已保存: {save_path}")
        
        return fig
    
    def plot_returns_distribution(self, returns: pd.Series,
                                   title: str = "收益率分布",
                                   save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制收益率分布"""
        if not HAS_MATPLOTLIB:
            return None
        
        if returns.empty:
            return None
        
        fig, axes = plt.subplots(1, 2, figsize=self.figsize)
        
        # 直方图
        ax1 = axes[0]
        ax1.hist(returns * 100, bins=50, color='blue', alpha=0.7, edgecolor='black')
        ax1.axvline(returns.mean() * 100, color='red', linestyle='--', 
                    label=f'均值: {returns.mean()*100:.2f}%')
        ax1.axvline(0, color='black', linestyle='-', linewidth=0.5)
        ax1.set_xlabel('收益率 (%)', fontsize=12)
        ax1.set_ylabel('频数', fontsize=12)
        ax1.set_title('收益率分布', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # QQ图
        ax2 = axes[1]
        from scipy import stats
        stats.probplot(returns, dist="norm", plot=ax2)
        ax2.set_title('Q-Q 图', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_trades(self, price_data: pd.DataFrame, 
                    trades: pd.DataFrame,
                    symbol: str = "",
                    title: str = "交易信号",
                    save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制价格和交易信号"""
        if not HAS_MATPLOTLIB:
            return None
        
        if price_data.empty:
            return None
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 价格曲线
        ax.plot(price_data.index, price_data['close'], 
                label='收盘价', color='blue', linewidth=1)
        
        # 标记交易
        if not trades.empty:
            buy_trades = trades[trades['direction'] == 'BUY']
            sell_trades = trades[trades['direction'] == 'SELL']
            
            if not buy_trades.empty:
                ax.scatter(buy_trades['timestamp'], buy_trades['price'],
                          marker='^', color='green', s=100, label='买入', zorder=5)
            
            if not sell_trades.empty:
                ax.scatter(sell_trades['timestamp'], sell_trades['price'],
                          marker='v', color='red', s=100, label='卖出', zorder=5)
        
        ax.set_title(f"{title} - {symbol}", fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格', fontsize=12)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_monthly_returns(self, equity_curve: pd.DataFrame,
                              title: str = "月度收益热力图",
                              save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制月度收益热力图"""
        if not HAS_MATPLOTLIB:
            return None
        
        if equity_curve.empty:
            return None
        
        # 计算月度收益
        monthly_equity = equity_curve['equity'].resample('M').last()
        monthly_returns = monthly_equity.pct_change().dropna()
        
        if monthly_returns.empty:
            return None
        
        # 创建年-月矩阵
        years = monthly_returns.index.year.unique()
        months = range(1, 13)
        
        returns_matrix = pd.DataFrame(index=years, columns=months)
        for date, ret in monthly_returns.items():
            returns_matrix.loc[date.year, date.month] = ret * 100
        
        returns_matrix = returns_matrix.astype(float)
        
        fig, ax = plt.subplots(figsize=(12, len(years) * 0.8 + 2))
        
        # 热力图
        import seaborn as sns
        sns.heatmap(returns_matrix, annot=True, fmt='.1f', center=0,
                    cmap='RdYlGn', ax=ax, cbar_kws={'label': '收益率 (%)'})
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('年份', fontsize=12)
        ax.set_xticklabels(['1月', '2月', '3月', '4月', '5月', '6月',
                           '7月', '8月', '9月', '10月', '11月', '12月'])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_rolling_metrics(self, equity_curve: pd.DataFrame,
                              window: int = 20,
                              title: str = "滚动指标",
                              save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制滚动指标"""
        if not HAS_MATPLOTLIB:
            return None
        
        if equity_curve.empty:
            return None
        
        returns = equity_curve['equity'].pct_change().dropna()
        
        fig, axes = plt.subplots(3, 1, figsize=self.figsize, sharex=True)
        
        # 滚动收益率
        ax1 = axes[0]
        rolling_return = returns.rolling(window).mean() * 252 * 100
        ax1.plot(rolling_return.index, rolling_return, color='blue')
        ax1.axhline(0, color='black', linestyle='--', linewidth=0.5)
        ax1.set_ylabel('年化收益率 (%)', fontsize=10)
        ax1.set_title(f'{window}日滚动年化收益率', fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # 滚动波动率
        ax2 = axes[1]
        rolling_vol = returns.rolling(window).std() * np.sqrt(252) * 100
        ax2.plot(rolling_vol.index, rolling_vol, color='orange')
        ax2.set_ylabel('年化波动率 (%)', fontsize=10)
        ax2.set_title(f'{window}日滚动年化波动率', fontsize=11)
        ax2.grid(True, alpha=0.3)
        
        # 滚动夏普
        ax3 = axes[2]
        rolling_sharpe = (returns.rolling(window).mean() / returns.rolling(window).std()) * np.sqrt(252)
        ax3.plot(rolling_sharpe.index, rolling_sharpe, color='green')
        ax3.axhline(0, color='black', linestyle='--', linewidth=0.5)
        ax3.set_ylabel('夏普比率', fontsize=10)
        ax3.set_xlabel('日期', fontsize=10)
        ax3.set_title(f'{window}日滚动夏普比率', fontsize=11)
        ax3.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def create_dashboard(self, results: Dict[str, Any],
                          price_data: pd.DataFrame = None,
                          symbol: str = "",
                          save_path: Optional[str] = None) -> Optional[Figure]:
        """创建综合仪表板"""
        if not HAS_MATPLOTLIB:
            return None
        
        equity_curve = results.get('equity_curve', pd.DataFrame())
        trades = results.get('trades', pd.DataFrame())
        summary = results.get('summary', {})
        
        if equity_curve.empty:
            return None
        
        fig = plt.figure(figsize=(16, 12))
        
        # 布局
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. 权益曲线 (大图)
        ax1 = fig.add_subplot(gs[0, :2])
        ax1.plot(equity_curve.index, equity_curve['equity'], 
                 color='blue', linewidth=1.5)
        ax1.fill_between(equity_curve.index, equity_curve['equity'], 
                         alpha=0.3, color='blue')
        ax1.set_title('权益曲线', fontsize=12, fontweight='bold')
        ax1.set_ylabel('权益')
        ax1.grid(True, alpha=0.3)
        
        # 2. 绩效摘要 (文本)
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.axis('off')
        summary_text = f"""
绩效摘要
────────────────
初始资金: {summary.get('initial_capital', 0):,.0f}
最终权益: {summary.get('final_equity', 0):,.0f}
总收益率: {summary.get('total_return', '0%')}
年化收益: {summary.get('annual_return', '0%')}
夏普比率: {summary.get('sharpe_ratio', 0)}
最大回撤: {summary.get('max_drawdown', '0%')}
总交易数: {summary.get('total_trades', 0)}
胜率: {summary.get('win_rate', '0%')}
总盈亏: {summary.get('total_pnl', 0):,.2f}
"""
        ax2.text(0.1, 0.9, summary_text, transform=ax2.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 3. 回撤曲线
        ax3 = fig.add_subplot(gs[1, :2])
        cummax = equity_curve['equity'].cummax()
        drawdown = (equity_curve['equity'] - cummax) / cummax * 100
        ax3.fill_between(equity_curve.index, drawdown, 0, 
                         color='red', alpha=0.5)
        ax3.set_title('回撤曲线', fontsize=12, fontweight='bold')
        ax3.set_ylabel('回撤 (%)')
        ax3.grid(True, alpha=0.3)
        
        # 4. 收益率分布
        ax4 = fig.add_subplot(gs[1, 2])
        returns = equity_curve['equity'].pct_change().dropna() * 100
        ax4.hist(returns, bins=30, color='blue', alpha=0.7, edgecolor='black')
        ax4.axvline(returns.mean(), color='red', linestyle='--')
        ax4.set_title('收益率分布', fontsize=12, fontweight='bold')
        ax4.set_xlabel('收益率 (%)')
        ax4.grid(True, alpha=0.3)
        
        # 5. 价格和交易信号
        if price_data is not None and not price_data.empty:
            ax5 = fig.add_subplot(gs[2, :2])
            ax5.plot(price_data.index, price_data['close'], 
                     color='blue', linewidth=1, label='价格')
            
            if not trades.empty:
                buy_trades = trades[trades['direction'] == 'BUY']
                sell_trades = trades[trades['direction'] == 'SELL']
                
                if not buy_trades.empty:
                    ax5.scatter(buy_trades['timestamp'], buy_trades['price'],
                               marker='^', color='green', s=80, label='买入', zorder=5)
                if not sell_trades.empty:
                    ax5.scatter(sell_trades['timestamp'], sell_trades['price'],
                               marker='v', color='red', s=80, label='卖出', zorder=5)
            
            ax5.set_title(f'交易信号 - {symbol}', fontsize=12, fontweight='bold')
            ax5.set_ylabel('价格')
            ax5.legend(loc='upper left')
            ax5.grid(True, alpha=0.3)
        
        # 6. 交易盈亏分布
        ax6 = fig.add_subplot(gs[2, 2])
        if not trades.empty and 'pnl' in trades.columns:
            colors = ['green' if x > 0 else 'red' for x in trades['pnl']]
            ax6.bar(range(len(trades)), trades['pnl'], color=colors, alpha=0.7)
            ax6.axhline(0, color='black', linewidth=0.5)
            ax6.set_title('交易盈亏', fontsize=12, fontweight='bold')
            ax6.set_xlabel('交易序号')
            ax6.set_ylabel('盈亏')
            ax6.grid(True, alpha=0.3)
        
        plt.suptitle(f'量化回测报告 - {symbol}', fontsize=16, fontweight='bold', y=1.02)
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"仪表板已保存: {save_path}")
        
        return fig
    
    def show(self):
        """显示所有图表"""
        if HAS_MATPLOTLIB:
            plt.show()
