"""
可视化模块 - BMAD Visualization

提供量化交易系统的各种可视化功能：
- 权益曲线
- 回撤分析
- 收益率分布
- K线图
- 交易信号
- 月度热力图
- 滚动指标
- 相关性矩阵
- 综合仪表板
"""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 尝试导入绘图库
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib未安装，请运行: pip install matplotlib")

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


class QuantPlotter:
    """量化可视化绘图器
    
    提供统一的绘图接口，支持多种图表类型。
    
    Example:
        >>> plotter = QuantPlotter()
        >>> plotter.plot_equity(equity_curve)
        >>> plotter.plot_drawdown(equity_curve)
        >>> plotter.show()
    """
    
    # 默认颜色方案
    COLORS = {
        'primary': '#1f77b4',      # 蓝色
        'secondary': '#ff7f0e',    # 橙色
        'positive': '#2ca02c',     # 绿色
        'negative': '#d62728',     # 红色
        'neutral': '#7f7f7f',      # 灰色
        'up': '#d62728',           # 上涨红色（中国习惯）
        'down': '#2ca02c',         # 下跌绿色
    }
    
    def __init__(self, 
                 figsize: Tuple[int, int] = (14, 8),
                 style: str = 'default',
                 dpi: int = 100,
                 chinese_font: bool = True):
        """初始化绘图器
        
        Args:
            figsize: 默认图形大小
            style: matplotlib样式
            dpi: 图像分辨率
            chinese_font: 是否启用中文字体
        """
        self.figsize = figsize
        self.style = style
        self.dpi = dpi
        self._figures: List[Figure] = []
        
        if HAS_MATPLOTLIB:
            self._setup_style(style, chinese_font)
    
    def _setup_style(self, style: str, chinese_font: bool):
        """设置绘图样式"""
        try:
            if style in plt.style.available:
                plt.style.use(style)
        except Exception:
            pass
        
        if chinese_font:
            # 尝试设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
    
    def _check_matplotlib(self) -> bool:
        """检查matplotlib是否可用"""
        if not HAS_MATPLOTLIB:
            logger.error("matplotlib未安装，请运行: pip install matplotlib")
            return False
        return True
    
    # ==================== 权益与回撤 ====================
    
    def plot_equity(self, 
                    equity: Union[pd.Series, pd.DataFrame],
                    benchmark: Optional[pd.Series] = None,
                    title: str = '权益曲线',
                    show_drawdown: bool = True,
                    save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制权益曲线
        
        Args:
            equity: 权益序列或包含'equity'列的DataFrame
            benchmark: 基准曲线（可选）
            title: 标题
            show_drawdown: 是否显示回撤子图
            save_path: 保存路径
            
        Returns:
            Figure对象
        """
        if not self._check_matplotlib():
            return None
        
        # 处理输入
        if isinstance(equity, pd.DataFrame):
            if 'equity' in equity.columns:
                equity_series = equity['equity']
            else:
                equity_series = equity.iloc[:, 0]
        else:
            equity_series = equity
        
        if equity_series.empty:
            logger.warning("权益数据为空")
            return None
        
        # 创建图形
        if show_drawdown:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, 
                                           height_ratios=[3, 1], sharex=True)
        else:
            fig, ax1 = plt.subplots(figsize=self.figsize)
            ax2 = None
        
        # 绘制权益曲线
        ax1.plot(equity_series.index, equity_series.values, 
                 color=self.COLORS['primary'], linewidth=1.5, label='策略权益')
        ax1.fill_between(equity_series.index, equity_series.values, 
                         alpha=0.2, color=self.COLORS['primary'])
        
        # 绘制基准
        if benchmark is not None and not benchmark.empty:
            # 归一化基准到相同起点
            normalized_benchmark = benchmark / benchmark.iloc[0] * equity_series.iloc[0]
            ax1.plot(normalized_benchmark.index, normalized_benchmark.values,
                     color=self.COLORS['secondary'], linewidth=1, 
                     linestyle='--', label='基准', alpha=0.8)
        
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.set_ylabel('权益', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 绘制回撤
        if ax2 is not None:
            cummax = equity_series.cummax()
            drawdown = (equity_series - cummax) / cummax * 100
            ax2.fill_between(drawdown.index, drawdown.values, 0,
                             color=self.COLORS['negative'], alpha=0.5)
            ax2.plot(drawdown.index, drawdown.values, 
                     color=self.COLORS['negative'], linewidth=0.5)
            ax2.set_ylabel('回撤 (%)', fontsize=12)
            ax2.set_xlabel('日期', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            # 标注最大回撤
            max_dd_idx = drawdown.idxmin()
            max_dd = drawdown.min()
            ax2.annotate(f'最大回撤: {max_dd:.2f}%',
                         xy=(max_dd_idx, max_dd),
                         xytext=(max_dd_idx, max_dd * 0.7),
                         fontsize=9,
                         arrowprops=dict(arrowstyle='->', color='black', lw=0.5))
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"图表已保存: {save_path}")
        
        self._figures.append(fig)
        return fig
    
    def plot_drawdown(self,
                      equity: Union[pd.Series, pd.DataFrame],
                      title: str = '回撤分析',
                      top_n: int = 5,
                      save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制详细回撤分析
        
        Args:
            equity: 权益序列
            title: 标题
            top_n: 显示前N大回撤
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        if isinstance(equity, pd.DataFrame):
            equity = equity['equity'] if 'equity' in equity.columns else equity.iloc[:, 0]
        
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax * 100
        
        # 1. 权益与峰值
        ax1 = axes[0, 0]
        ax1.plot(equity.index, equity.values, label='权益', color=self.COLORS['primary'])
        ax1.plot(cummax.index, cummax.values, '--', label='历史峰值', 
                 color=self.COLORS['secondary'], alpha=0.7)
        ax1.set_title('权益曲线与历史峰值', fontsize=11)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. 回撤曲线
        ax2 = axes[0, 1]
        ax2.fill_between(drawdown.index, drawdown.values, 0,
                         color=self.COLORS['negative'], alpha=0.5)
        ax2.set_title('回撤曲线', fontsize=11)
        ax2.set_ylabel('回撤 (%)')
        ax2.grid(True, alpha=0.3)
        
        # 3. 回撤分布
        ax3 = axes[1, 0]
        ax3.hist(drawdown.dropna(), bins=50, color=self.COLORS['negative'], 
                 alpha=0.7, edgecolor='black')
        ax3.axvline(drawdown.mean(), color='blue', linestyle='--', 
                    label=f'平均: {drawdown.mean():.2f}%')
        ax3.set_title('回撤分布', fontsize=11)
        ax3.set_xlabel('回撤 (%)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 回撤持续时间（简化版）
        ax4 = axes[1, 1]
        # 找到回撤开始和结束点
        in_drawdown = drawdown < 0
        drawdown_periods = []
        start = None
        for i, (idx, is_dd) in enumerate(in_drawdown.items()):
            if is_dd and start is None:
                start = idx
            elif not is_dd and start is not None:
                drawdown_periods.append((start, idx))
                start = None
        
        if drawdown_periods:
            durations = [(end - start).days for start, end in drawdown_periods]
            ax4.hist(durations, bins=30, color=self.COLORS['secondary'], 
                     alpha=0.7, edgecolor='black')
            ax4.axvline(np.mean(durations), color='red', linestyle='--',
                        label=f'平均: {np.mean(durations):.0f}天')
        ax4.set_title('回撤持续时间分布', fontsize=11)
        ax4.set_xlabel('天数')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    # ==================== 收益率分析 ====================
    
    def plot_returns(self,
                     returns: pd.Series,
                     title: str = '收益率分析',
                     save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制收益率分析图
        
        Args:
            returns: 收益率序列
            title: 标题
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        # 1. 收益率时间序列
        ax1 = axes[0, 0]
        ax1.plot(returns.index, returns.values * 100, alpha=0.7, 
                 color=self.COLORS['primary'], linewidth=0.5)
        ax1.axhline(0, color='black', linestyle='-', linewidth=0.5)
        ax1.fill_between(returns.index, returns.values * 100, 0,
                         where=returns.values >= 0, color=self.COLORS['positive'], alpha=0.3)
        ax1.fill_between(returns.index, returns.values * 100, 0,
                         where=returns.values < 0, color=self.COLORS['negative'], alpha=0.3)
        ax1.set_title('日收益率', fontsize=11)
        ax1.set_ylabel('收益率 (%)')
        ax1.grid(True, alpha=0.3)
        
        # 2. 收益率分布
        ax2 = axes[0, 1]
        ax2.hist(returns.dropna() * 100, bins=50, color=self.COLORS['primary'],
                 alpha=0.7, edgecolor='black', density=True)
        
        # 添加正态分布拟合
        from scipy import stats
        mu, std = returns.mean() * 100, returns.std() * 100
        x = np.linspace(returns.min() * 100, returns.max() * 100, 100)
        ax2.plot(x, stats.norm.pdf(x, mu, std), 'r--', linewidth=2, label='正态分布')
        ax2.axvline(mu, color='red', linestyle='-', label=f'均值: {mu:.3f}%')
        ax2.set_title('收益率分布', fontsize=11)
        ax2.set_xlabel('收益率 (%)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 累计收益
        ax3 = axes[1, 0]
        cum_returns = (1 + returns).cumprod()
        ax3.plot(cum_returns.index, cum_returns.values, color=self.COLORS['primary'])
        ax3.fill_between(cum_returns.index, cum_returns.values, 1, alpha=0.2)
        ax3.axhline(1, color='black', linestyle='--', linewidth=0.5)
        ax3.set_title('累计收益', fontsize=11)
        ax3.set_ylabel('累计收益倍数')
        ax3.grid(True, alpha=0.3)
        
        # 4. Q-Q图
        ax4 = axes[1, 1]
        stats.probplot(returns.dropna(), dist="norm", plot=ax4)
        ax4.set_title('Q-Q 图 (正态性检验)', fontsize=11)
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    def plot_monthly_heatmap(self,
                             returns: pd.Series,
                             title: str = '月度收益热力图',
                             save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制月度收益热力图
        
        Args:
            returns: 日收益率序列
            title: 标题
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        # 计算月度收益
        monthly_returns = (1 + returns).resample('ME').prod() - 1
        
        # 创建年-月矩阵
        years = monthly_returns.index.year.unique()
        months = range(1, 13)
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月',
                       '7月', '8月', '9月', '10月', '11月', '12月']
        
        returns_matrix = pd.DataFrame(index=sorted(years), columns=months, dtype=float)
        for date, ret in monthly_returns.items():
            returns_matrix.loc[date.year, date.month] = ret * 100
        
        fig, ax = plt.subplots(figsize=(12, max(4, len(years) * 0.6 + 2)))
        
        if HAS_SEABORN:
            sns.heatmap(returns_matrix, annot=True, fmt='.1f', center=0,
                        cmap='RdYlGn', ax=ax, cbar_kws={'label': '收益率 (%)'},
                        linewidths=0.5)
        else:
            # 简化版热力图
            im = ax.imshow(returns_matrix.values.astype(float), cmap='RdYlGn',
                           aspect='auto', vmin=-10, vmax=10)
            plt.colorbar(im, ax=ax, label='收益率 (%)')
            
            # 添加数值标注
            for i in range(len(years)):
                for j in range(12):
                    val = returns_matrix.iloc[i, j]
                    if pd.notna(val):
                        ax.text(j, i, f'{val:.1f}', ha='center', va='center', fontsize=8)
        
        ax.set_xticklabels(month_names)
        ax.set_yticklabels(sorted(years))
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('年份', fontsize=12)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    # ==================== K线图 ====================
    
    def plot_candlestick(self,
                         data: pd.DataFrame,
                         title: str = 'K线图',
                         volume: bool = True,
                         ma_periods: List[int] = None,
                         save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制K线图
        
        Args:
            data: OHLCV数据
            title: 标题
            volume: 是否显示成交量
            ma_periods: 均线周期列表，如 [5, 20, 60]
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        df = data.copy()
        df.columns = df.columns.str.lower()
        
        # 确保有必要的列
        required = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required):
            logger.error(f"数据缺少必要列: {required}")
            return None
        
        # 创建图形
        if volume and 'volume' in df.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize,
                                           gridspec_kw={'height_ratios': [3, 1]},
                                           sharex=True)
        else:
            fig, ax1 = plt.subplots(figsize=self.figsize)
            ax2 = None
        
        # 绘制K线
        width = 0.6
        up = df[df['close'] >= df['open']]
        down = df[df['close'] < df['open']]
        
        # 上涨K线（红色）
        ax1.bar(range(len(up)), up['close'] - up['open'], width,
                bottom=up['open'], color=self.COLORS['up'], alpha=0.8)
        ax1.vlines(range(len(up)), up['low'], up['high'], 
                   color=self.COLORS['up'], linewidth=0.5)
        
        # 下跌K线（绿色）
        ax1.bar([df.index.get_loc(i) for i in down.index], 
                down['close'] - down['open'], width,
                bottom=down['open'], color=self.COLORS['down'], alpha=0.8)
        ax1.vlines([df.index.get_loc(i) for i in down.index],
                   down['low'], down['high'],
                   color=self.COLORS['down'], linewidth=0.5)
        
        # 绘制均线
        if ma_periods:
            colors = ['blue', 'orange', 'purple', 'brown', 'pink']
            for i, period in enumerate(ma_periods):
                ma = df['close'].rolling(period).mean()
                ax1.plot(range(len(df)), ma.values, 
                         label=f'MA{period}', color=colors[i % len(colors)],
                         linewidth=1, alpha=0.8)
            ax1.legend(loc='upper left')
        
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.set_ylabel('价格', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # 设置x轴标签
        tick_positions = np.linspace(0, len(df) - 1, min(10, len(df))).astype(int)
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels([df.index[i].strftime('%Y-%m-%d') for i in tick_positions],
                           rotation=45, ha='right')
        
        # 绘制成交量
        if ax2 is not None:
            colors = [self.COLORS['up'] if c >= o else self.COLORS['down']
                      for c, o in zip(df['close'], df['open'])]
            ax2.bar(range(len(df)), df['volume'], color=colors, alpha=0.5, width=width)
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    # ==================== 交易分析 ====================
    
    def plot_trades(self,
                    price_data: pd.DataFrame,
                    trades: pd.DataFrame,
                    title: str = '交易信号',
                    save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制价格和交易信号
        
        Args:
            price_data: 价格数据
            trades: 交易记录，需包含timestamp, direction, price列
            title: 标题
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 绘制价格
        close_col = 'close' if 'close' in price_data.columns else price_data.columns[0]
        ax.plot(price_data.index, price_data[close_col],
                color=self.COLORS['primary'], linewidth=1, label='价格')
        
        # 标记交易
        if not trades.empty:
            # 买入信号
            buy_trades = trades[trades['direction'].str.upper() == 'BUY']
            if not buy_trades.empty:
                ax.scatter(buy_trades['timestamp'], buy_trades['price'],
                          marker='^', color=self.COLORS['positive'], s=100,
                          label='买入', zorder=5, edgecolors='black', linewidths=0.5)
            
            # 卖出信号
            sell_trades = trades[trades['direction'].str.upper() == 'SELL']
            if not sell_trades.empty:
                ax.scatter(sell_trades['timestamp'], sell_trades['price'],
                          marker='v', color=self.COLORS['negative'], s=100,
                          label='卖出', zorder=5, edgecolors='black', linewidths=0.5)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格', fontsize=12)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # 格式化日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    def plot_trade_pnl(self,
                       trades: pd.DataFrame,
                       title: str = '交易盈亏分析',
                       save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制交易盈亏分析
        
        Args:
            trades: 交易记录，需包含pnl列
            title: 标题
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        if 'pnl' not in trades.columns:
            logger.error("交易数据缺少pnl列")
            return None
        
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        pnl = trades['pnl']
        
        # 1. 单笔盈亏
        ax1 = axes[0, 0]
        colors = [self.COLORS['positive'] if x > 0 else self.COLORS['negative'] for x in pnl]
        ax1.bar(range(len(pnl)), pnl, color=colors, alpha=0.7)
        ax1.axhline(0, color='black', linewidth=0.5)
        ax1.set_title('单笔交易盈亏', fontsize=11)
        ax1.set_xlabel('交易序号')
        ax1.set_ylabel('盈亏')
        ax1.grid(True, alpha=0.3)
        
        # 2. 累计盈亏
        ax2 = axes[0, 1]
        cum_pnl = pnl.cumsum()
        ax2.plot(range(len(cum_pnl)), cum_pnl, color=self.COLORS['primary'], linewidth=2)
        ax2.fill_between(range(len(cum_pnl)), cum_pnl, 0, alpha=0.2)
        ax2.axhline(0, color='black', linewidth=0.5)
        ax2.set_title('累计盈亏', fontsize=11)
        ax2.set_xlabel('交易序号')
        ax2.set_ylabel('累计盈亏')
        ax2.grid(True, alpha=0.3)
        
        # 3. 盈亏分布
        ax3 = axes[1, 0]
        ax3.hist(pnl, bins=30, color=self.COLORS['primary'], alpha=0.7, edgecolor='black')
        ax3.axvline(pnl.mean(), color='red', linestyle='--', label=f'均值: {pnl.mean():.2f}')
        ax3.axvline(0, color='black', linewidth=0.5)
        ax3.set_title('盈亏分布', fontsize=11)
        ax3.set_xlabel('盈亏')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 盈亏统计
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        
        avg_win = f"{wins.mean():.2f}" if len(wins) > 0 else "0"
        avg_loss = f"{losses.mean():.2f}" if len(losses) > 0 else "0"
        profit_ratio = f"{abs(wins.mean()/losses.mean()):.2f}" if len(losses) > 0 and losses.mean() != 0 else "N/A"
        
        stats_text = f"""
盈亏统计
────────────────
总交易数: {len(pnl)}
盈利次数: {len(wins)}
亏损次数: {len(losses)}
胜率: {len(wins)/len(pnl)*100:.1f}%
────────────────
总盈亏: {pnl.sum():.2f}
平均盈亏: {pnl.mean():.2f}
最大盈利: {pnl.max():.2f}
最大亏损: {pnl.min():.2f}
────────────────
平均盈利: {avg_win}
平均亏损: {avg_loss}
盈亏比: {profit_ratio}
"""
        ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    # ==================== 滚动指标 ====================
    
    def plot_rolling_metrics(self,
                             returns: pd.Series,
                             window: int = 20,
                             title: str = '滚动指标',
                             save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制滚动指标
        
        Args:
            returns: 收益率序列
            window: 滚动窗口
            title: 标题
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        fig, axes = plt.subplots(3, 1, figsize=self.figsize, sharex=True)
        
        # 1. 滚动收益率
        ax1 = axes[0]
        rolling_return = returns.rolling(window).mean() * 252 * 100
        ax1.plot(rolling_return.index, rolling_return, color=self.COLORS['primary'])
        ax1.axhline(0, color='black', linestyle='--', linewidth=0.5)
        ax1.fill_between(rolling_return.index, rolling_return, 0,
                         where=rolling_return >= 0, color=self.COLORS['positive'], alpha=0.3)
        ax1.fill_between(rolling_return.index, rolling_return, 0,
                         where=rolling_return < 0, color=self.COLORS['negative'], alpha=0.3)
        ax1.set_ylabel('年化收益率 (%)', fontsize=10)
        ax1.set_title(f'{window}日滚动年化收益率', fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # 2. 滚动波动率
        ax2 = axes[1]
        rolling_vol = returns.rolling(window).std() * np.sqrt(252) * 100
        ax2.plot(rolling_vol.index, rolling_vol, color=self.COLORS['secondary'])
        ax2.fill_between(rolling_vol.index, rolling_vol, alpha=0.3, color=self.COLORS['secondary'])
        ax2.set_ylabel('年化波动率 (%)', fontsize=10)
        ax2.set_title(f'{window}日滚动年化波动率', fontsize=11)
        ax2.grid(True, alpha=0.3)
        
        # 3. 滚动夏普比率
        ax3 = axes[2]
        rolling_mean = returns.rolling(window).mean()
        rolling_std = returns.rolling(window).std()
        rolling_sharpe = (rolling_mean / rolling_std) * np.sqrt(252)
        ax3.plot(rolling_sharpe.index, rolling_sharpe, color=self.COLORS['positive'])
        ax3.axhline(0, color='black', linestyle='--', linewidth=0.5)
        ax3.axhline(1, color='green', linestyle=':', linewidth=0.5, alpha=0.5)
        ax3.axhline(-1, color='red', linestyle=':', linewidth=0.5, alpha=0.5)
        ax3.set_ylabel('夏普比率', fontsize=10)
        ax3.set_xlabel('日期', fontsize=10)
        ax3.set_title(f'{window}日滚动夏普比率', fontsize=11)
        ax3.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    # ==================== 相关性分析 ====================
    
    def plot_correlation(self,
                         data: pd.DataFrame,
                         title: str = '相关性矩阵',
                         save_path: Optional[str] = None) -> Optional[Figure]:
        """绘制相关性矩阵
        
        Args:
            data: 多列数据
            title: 标题
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        corr = data.corr()
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        if HAS_SEABORN:
            sns.heatmap(corr, annot=True, fmt='.2f', center=0,
                        cmap='RdYlGn', ax=ax, vmin=-1, vmax=1,
                        square=True, linewidths=0.5)
        else:
            im = ax.imshow(corr, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)
            plt.colorbar(im, ax=ax)
            
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha='right')
            ax.set_yticklabels(corr.columns)
            
            for i in range(len(corr)):
                for j in range(len(corr)):
                    ax.text(j, i, f'{corr.iloc[i, j]:.2f}',
                            ha='center', va='center', fontsize=8)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        
        self._figures.append(fig)
        return fig
    
    # ==================== 综合仪表板 ====================
    
    def plot_dashboard(self,
                       equity_curve: pd.DataFrame,
                       trades: pd.DataFrame = None,
                       price_data: pd.DataFrame = None,
                       summary: Dict[str, Any] = None,
                       title: str = '量化回测报告',
                       save_path: Optional[str] = None) -> Optional[Figure]:
        """创建综合仪表板
        
        Args:
            equity_curve: 权益曲线
            trades: 交易记录
            price_data: 价格数据
            summary: 绩效摘要
            title: 标题
            save_path: 保存路径
        """
        if not self._check_matplotlib():
            return None
        
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 获取权益序列
        equity = equity_curve['equity'] if 'equity' in equity_curve.columns else equity_curve.iloc[:, 0]
        returns = equity.pct_change().dropna()
        
        # 1. 权益曲线（大图）
        ax1 = fig.add_subplot(gs[0, :2])
        ax1.plot(equity.index, equity.values, color=self.COLORS['primary'], linewidth=1.5)
        ax1.fill_between(equity.index, equity.values, alpha=0.2, color=self.COLORS['primary'])
        ax1.set_title('权益曲线', fontsize=12, fontweight='bold')
        ax1.set_ylabel('权益')
        ax1.grid(True, alpha=0.3)
        
        # 2. 绩效摘要
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.axis('off')
        if summary:
            summary_text = f"""
绩效摘要
────────────────
初始资金: {summary.get('initial_capital', 0):,.0f}
最终权益: {summary.get('final_equity', 0):,.0f}
总收益率: {summary.get('total_return', 'N/A')}
年化收益: {summary.get('annual_return', 'N/A')}
夏普比率: {summary.get('sharpe_ratio', 'N/A')}
最大回撤: {summary.get('max_drawdown', 'N/A')}
总交易数: {summary.get('total_trades', 0)}
胜率: {summary.get('win_rate', 'N/A')}
"""
            ax2.text(0.1, 0.9, summary_text, transform=ax2.transAxes,
                    fontsize=10, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 3. 回撤曲线
        ax3 = fig.add_subplot(gs[1, :2])
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax * 100
        ax3.fill_between(drawdown.index, drawdown.values, 0, 
                         color=self.COLORS['negative'], alpha=0.5)
        ax3.set_title('回撤曲线', fontsize=12, fontweight='bold')
        ax3.set_ylabel('回撤 (%)')
        ax3.grid(True, alpha=0.3)
        
        # 4. 收益率分布
        ax4 = fig.add_subplot(gs[1, 2])
        ax4.hist(returns * 100, bins=30, color=self.COLORS['primary'], 
                 alpha=0.7, edgecolor='black')
        ax4.axvline(returns.mean() * 100, color='red', linestyle='--')
        ax4.set_title('收益率分布', fontsize=12, fontweight='bold')
        ax4.set_xlabel('收益率 (%)')
        ax4.grid(True, alpha=0.3)
        
        # 5. 价格和交易信号
        if price_data is not None and not price_data.empty:
            ax5 = fig.add_subplot(gs[2, :2])
            close_col = 'close' if 'close' in price_data.columns else price_data.columns[0]
            ax5.plot(price_data.index, price_data[close_col],
                     color=self.COLORS['primary'], linewidth=1, label='价格')
            
            if trades is not None and not trades.empty:
                buy_trades = trades[trades['direction'].str.upper() == 'BUY']
                sell_trades = trades[trades['direction'].str.upper() == 'SELL']
                
                if not buy_trades.empty:
                    ax5.scatter(buy_trades['timestamp'], buy_trades['price'],
                               marker='^', color=self.COLORS['positive'], s=80, 
                               label='买入', zorder=5)
                if not sell_trades.empty:
                    ax5.scatter(sell_trades['timestamp'], sell_trades['price'],
                               marker='v', color=self.COLORS['negative'], s=80,
                               label='卖出', zorder=5)
            
            ax5.set_title('交易信号', fontsize=12, fontweight='bold')
            ax5.set_ylabel('价格')
            ax5.legend(loc='upper left')
            ax5.grid(True, alpha=0.3)
        
        # 6. 交易盈亏
        ax6 = fig.add_subplot(gs[2, 2])
        if trades is not None and not trades.empty and 'pnl' in trades.columns:
            colors = [self.COLORS['positive'] if x > 0 else self.COLORS['negative'] 
                      for x in trades['pnl']]
            ax6.bar(range(len(trades)), trades['pnl'], color=colors, alpha=0.7)
            ax6.axhline(0, color='black', linewidth=0.5)
            ax6.set_title('交易盈亏', fontsize=12, fontweight='bold')
            ax6.set_xlabel('交易序号')
            ax6.set_ylabel('盈亏')
            ax6.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"仪表板已保存: {save_path}")
        
        self._figures.append(fig)
        return fig
    
    # ==================== 工具方法 ====================
    
    def show(self):
        """显示所有图表"""
        if HAS_MATPLOTLIB:
            plt.show()
    
    def close_all(self):
        """关闭所有图表"""
        if HAS_MATPLOTLIB:
            plt.close('all')
        self._figures.clear()
    
    def save_all(self, directory: str, prefix: str = 'plot'):
        """保存所有图表
        
        Args:
            directory: 保存目录
            prefix: 文件名前缀
        """
        import os
        os.makedirs(directory, exist_ok=True)
        
        for i, fig in enumerate(self._figures):
            path = os.path.join(directory, f'{prefix}_{i+1}.png')
            fig.savefig(path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"图表已保存: {path}")


# ==================== 便捷函数 ====================

def quick_equity_plot(equity: pd.Series, title: str = '权益曲线'):
    """快速绘制权益曲线"""
    plotter = QuantPlotter()
    plotter.plot_equity(equity, title=title)
    plotter.show()


def quick_returns_plot(returns: pd.Series, title: str = '收益率分析'):
    """快速绘制收益率分析"""
    plotter = QuantPlotter()
    plotter.plot_returns(returns, title=title)
    plotter.show()


def quick_candlestick(data: pd.DataFrame, title: str = 'K线图', ma_periods: List[int] = None):
    """快速绘制K线图"""
    plotter = QuantPlotter()
    plotter.plot_candlestick(data, title=title, ma_periods=ma_periods or [5, 20])
    plotter.show()


def quick_dashboard(results: Dict[str, Any], price_data: pd.DataFrame = None):
    """快速创建仪表板"""
    plotter = QuantPlotter()
    plotter.plot_dashboard(
        equity_curve=results.get('equity_curve', pd.DataFrame()),
        trades=results.get('trades', pd.DataFrame()),
        price_data=price_data,
        summary=results.get('summary', {})
    )
    plotter.show()
