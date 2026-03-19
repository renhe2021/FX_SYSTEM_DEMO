"""
Plotly 可视化模块 - 交互式图表

提供基于 Plotly 的交互式可视化功能：
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

# 尝试导入 Plotly
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    logger.warning("Plotly未安装，请运行: pip install plotly")


class PlotlyPlotter:
    """Plotly 交互式绘图器
    
    提供统一的交互式绘图接口，支持多种图表类型。
    
    Example:
        >>> plotter = PlotlyPlotter()
        >>> fig = plotter.plot_equity(equity_curve)
        >>> fig.show()
    """
    
    # 默认颜色方案
    COLORS = {
        'primary': '#1f77b4',      # 蓝色
        'secondary': '#ff7f0e',    # 橙色
        'positive': '#00d4aa',     # 绿色
        'negative': '#ff6b6b',     # 红色
        'neutral': '#7f7f7f',      # 灰色
        'up': '#ff4757',           # 上涨红色
        'down': '#2ed573',         # 下跌绿色
        'background': '#ffffff',
        'grid': '#e6e6e6',
    }
    
    # 默认布局模板
    DEFAULT_LAYOUT = {
        'template': 'plotly_white',
        'hovermode': 'x unified',
        'legend': dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        'margin': dict(l=60, r=40, t=60, b=40),
    }
    
    def __init__(self, 
                 width: int = 1000,
                 height: int = 600,
                 theme: str = 'plotly_white'):
        """初始化绘图器
        
        Args:
            width: 默认图表宽度
            height: 默认图表高度
            theme: Plotly主题
        """
        self.width = width
        self.height = height
        self.theme = theme
        self._figures: List[go.Figure] = []
    
    def _check_plotly(self) -> bool:
        """检查Plotly是否可用"""
        if not HAS_PLOTLY:
            logger.error("Plotly未安装，请运行: pip install plotly")
            return False
        return True
    
    def _apply_layout(self, fig: go.Figure, title: str = '', 
                      height: int = None, width: int = None) -> go.Figure:
        """应用默认布局"""
        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            template=self.theme,
            hovermode='x unified',
            legend=self.DEFAULT_LAYOUT['legend'],
            margin=self.DEFAULT_LAYOUT['margin'],
            height=height or self.height,
            width=width or self.width,
        )
        return fig
    
    # ==================== 权益与回撤 ====================
    
    def plot_equity(self,
                    equity: Union[pd.Series, pd.DataFrame],
                    benchmark: Optional[pd.Series] = None,
                    title: str = '权益曲线',
                    show_drawdown: bool = True) -> Optional[go.Figure]:
        """绘制权益曲线
        
        Args:
            equity: 权益序列或DataFrame
            benchmark: 基准曲线
            title: 标题
            show_drawdown: 是否显示回撤
            
        Returns:
            Plotly Figure对象
        """
        if not self._check_plotly():
            return None
        
        # 处理输入
        if isinstance(equity, pd.DataFrame):
            equity_series = equity['equity'] if 'equity' in equity.columns else equity.iloc[:, 0]
        else:
            equity_series = equity
        
        if equity_series.empty:
            logger.warning("权益数据为空")
            return None
        
        # 创建子图
        if show_drawdown:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                row_heights=[0.7, 0.3],
                subplot_titles=('权益曲线', '回撤')
            )
        else:
            fig = go.Figure()
        
        # 权益曲线
        row = 1 if show_drawdown else None
        fig.add_trace(
            go.Scatter(
                x=equity_series.index,
                y=equity_series.values,
                mode='lines',
                name='策略权益',
                line=dict(color=self.COLORS['primary'], width=2),
                fill='tozeroy',
                fillcolor=f"rgba(31, 119, 180, 0.1)",
                hovertemplate='%{x}<br>权益: %{y:,.0f}<extra></extra>'
            ),
            row=row, col=1 if show_drawdown else None
        )
        
        # 基准曲线
        if benchmark is not None and not benchmark.empty:
            normalized_benchmark = benchmark / benchmark.iloc[0] * equity_series.iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=normalized_benchmark.index,
                    y=normalized_benchmark.values,
                    mode='lines',
                    name='基准',
                    line=dict(color=self.COLORS['secondary'], width=1.5, dash='dash'),
                    hovertemplate='%{x}<br>基准: %{y:,.0f}<extra></extra>'
                ),
                row=row, col=1 if show_drawdown else None
            )
        
        # 回撤曲线
        if show_drawdown:
            cummax = equity_series.cummax()
            drawdown = (equity_series - cummax) / cummax * 100
            
            fig.add_trace(
                go.Scatter(
                    x=drawdown.index,
                    y=drawdown.values,
                    mode='lines',
                    name='回撤',
                    line=dict(color=self.COLORS['negative'], width=1),
                    fill='tozeroy',
                    fillcolor=f"rgba(255, 107, 107, 0.3)",
                    hovertemplate='%{x}<br>回撤: %{y:.2f}%<extra></extra>'
                ),
                row=2, col=1
            )
            
            # 标注最大回撤
            max_dd_idx = drawdown.idxmin()
            max_dd = drawdown.min()
            fig.add_annotation(
                x=max_dd_idx, y=max_dd,
                text=f"最大回撤: {max_dd:.2f}%",
                showarrow=True,
                arrowhead=2,
                row=2, col=1
            )
            
            fig.update_yaxes(title_text="权益", row=1, col=1)
            fig.update_yaxes(title_text="回撤 (%)", row=2, col=1)
        
        self._apply_layout(fig, title, height=700 if show_drawdown else self.height)
        self._figures.append(fig)
        return fig
    
    def plot_drawdown(self,
                      equity: Union[pd.Series, pd.DataFrame],
                      title: str = '回撤分析') -> Optional[go.Figure]:
        """绘制详细回撤分析"""
        if not self._check_plotly():
            return None
        
        if isinstance(equity, pd.DataFrame):
            equity = equity['equity'] if 'equity' in equity.columns else equity.iloc[:, 0]
        
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax * 100
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('权益与峰值', '回撤曲线', '回撤分布', '回撤统计'),
            specs=[[{}, {}], [{}, {"type": "table"}]]
        )
        
        # 1. 权益与峰值
        fig.add_trace(
            go.Scatter(x=equity.index, y=equity.values, name='权益',
                       line=dict(color=self.COLORS['primary'])),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=cummax.index, y=cummax.values, name='历史峰值',
                       line=dict(color=self.COLORS['secondary'], dash='dash')),
            row=1, col=1
        )
        
        # 2. 回撤曲线
        fig.add_trace(
            go.Scatter(x=drawdown.index, y=drawdown.values, name='回撤',
                       fill='tozeroy', line=dict(color=self.COLORS['negative'])),
            row=1, col=2
        )
        
        # 3. 回撤分布
        fig.add_trace(
            go.Histogram(x=drawdown.dropna(), name='分布',
                         marker_color=self.COLORS['negative'], opacity=0.7),
            row=2, col=1
        )
        
        # 4. 统计表格
        stats = {
            '指标': ['最大回撤', '平均回撤', '当前回撤', '回撤天数'],
            '值': [
                f"{drawdown.min():.2f}%",
                f"{drawdown.mean():.2f}%",
                f"{drawdown.iloc[-1]:.2f}%",
                f"{(drawdown < 0).sum()} 天"
            ]
        }
        fig.add_trace(
            go.Table(
                header=dict(values=list(stats.keys()), fill_color='paleturquoise'),
                cells=dict(values=list(stats.values()), fill_color='lavender')
            ),
            row=2, col=2
        )
        
        self._apply_layout(fig, title, height=700)
        self._figures.append(fig)
        return fig
    
    # ==================== 收益率分析 ====================
    
    def plot_returns(self,
                     returns: pd.Series,
                     title: str = '收益率分析') -> Optional[go.Figure]:
        """绘制收益率分析图"""
        if not self._check_plotly():
            return None
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('日收益率', '收益率分布', '累计收益', '滚动波动率'),
            vertical_spacing=0.12,
            horizontal_spacing=0.08
        )
        
        # 1. 日收益率
        colors = [self.COLORS['positive'] if r >= 0 else self.COLORS['negative'] 
                  for r in returns.values]
        fig.add_trace(
            go.Bar(x=returns.index, y=returns.values * 100, name='日收益率',
                   marker_color=colors, opacity=0.7),
            row=1, col=1
        )
        
        # 2. 收益率分布
        fig.add_trace(
            go.Histogram(x=returns.dropna() * 100, name='分布',
                         marker_color=self.COLORS['primary'], opacity=0.7,
                         nbinsx=50),
            row=1, col=2
        )
        fig.add_vline(x=returns.mean() * 100, line_dash="dash", 
                      line_color="red", row=1, col=2)
        
        # 3. 累计收益
        cum_returns = (1 + returns).cumprod()
        fig.add_trace(
            go.Scatter(x=cum_returns.index, y=cum_returns.values, name='累计收益',
                       fill='tozeroy', line=dict(color=self.COLORS['primary'])),
            row=2, col=1
        )
        
        # 4. 滚动波动率
        rolling_vol = returns.rolling(20).std() * np.sqrt(252) * 100
        fig.add_trace(
            go.Scatter(x=rolling_vol.index, y=rolling_vol.values, name='20日波动率',
                       line=dict(color=self.COLORS['secondary'])),
            row=2, col=2
        )
        
        fig.update_yaxes(title_text="收益率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="累计收益", row=2, col=1)
        fig.update_yaxes(title_text="年化波动率 (%)", row=2, col=2)
        
        self._apply_layout(fig, title, height=700)
        self._figures.append(fig)
        return fig
    
    def plot_monthly_heatmap(self,
                             returns: pd.Series,
                             title: str = '月度收益热力图') -> Optional[go.Figure]:
        """绘制月度收益热力图"""
        if not self._check_plotly():
            return None
        
        # 计算月度收益
        monthly_returns = (1 + returns).resample('ME').prod() - 1
        
        # 创建年-月矩阵
        years = sorted(monthly_returns.index.year.unique())
        months = list(range(1, 13))
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月',
                       '7月', '8月', '9月', '10月', '11月', '12月']
        
        z_data = []
        text_data = []
        for year in years:
            row = []
            text_row = []
            for month in months:
                mask = (monthly_returns.index.year == year) & (monthly_returns.index.month == month)
                if mask.any():
                    val = monthly_returns[mask].iloc[0] * 100
                    row.append(val)
                    text_row.append(f"{val:.1f}%")
                else:
                    row.append(None)
                    text_row.append("")
            z_data.append(row)
            text_data.append(text_row)
        
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=month_names,
            y=[str(y) for y in years],
            text=text_data,
            texttemplate="%{text}",
            textfont={"size": 10},
            colorscale='RdYlGn',
            zmid=0,
            colorbar=dict(title="收益率 (%)")
        ))
        
        self._apply_layout(fig, title, height=max(400, len(years) * 50 + 150))
        self._figures.append(fig)
        return fig
    
    # ==================== K线图 ====================
    
    def plot_candlestick(self,
                         data: pd.DataFrame,
                         title: str = 'K线图',
                         volume: bool = True,
                         ma_periods: List[int] = None) -> Optional[go.Figure]:
        """绘制K线图"""
        if not self._check_plotly():
            return None
        
        df = data.copy()
        df.columns = df.columns.str.lower()
        
        required = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required):
            logger.error(f"数据缺少必要列: {required}")
            return None
        
        # 创建子图
        if volume and 'volume' in df.columns:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.75, 0.25]
            )
        else:
            fig = go.Figure()
        
        # K线
        row = 1 if volume and 'volume' in df.columns else None
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='K线',
                increasing_line_color=self.COLORS['up'],
                decreasing_line_color=self.COLORS['down']
            ),
            row=row, col=1 if row else None
        )
        
        # 均线
        if ma_periods:
            colors = ['#1f77b4', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2']
            for i, period in enumerate(ma_periods):
                ma = df['close'].rolling(period).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index, y=ma,
                        mode='lines',
                        name=f'MA{period}',
                        line=dict(color=colors[i % len(colors)], width=1)
                    ),
                    row=row, col=1 if row else None
                )
        
        # 成交量
        if volume and 'volume' in df.columns:
            colors = [self.COLORS['up'] if c >= o else self.COLORS['down']
                      for c, o in zip(df['close'], df['open'])]
            fig.add_trace(
                go.Bar(x=df.index, y=df['volume'], name='成交量',
                       marker_color=colors, opacity=0.5),
                row=2, col=1
            )
            fig.update_yaxes(title_text="成交量", row=2, col=1)
        
        fig.update_xaxes(rangeslider_visible=False)
        fig.update_yaxes(title_text="价格", row=1 if volume else None, col=1 if volume else None)
        
        self._apply_layout(fig, title, height=700 if volume else self.height)
        self._figures.append(fig)
        return fig
    
    # ==================== 交易分析 ====================
    
    def plot_trades(self,
                    price_data: pd.DataFrame,
                    trades: pd.DataFrame,
                    title: str = '交易信号') -> Optional[go.Figure]:
        """绘制价格和交易信号"""
        if not self._check_plotly():
            return None
        
        fig = go.Figure()
        
        # 价格曲线
        close_col = 'close' if 'close' in price_data.columns else price_data.columns[0]
        fig.add_trace(
            go.Scatter(
                x=price_data.index,
                y=price_data[close_col],
                mode='lines',
                name='价格',
                line=dict(color=self.COLORS['primary'], width=1.5)
            )
        )
        
        # 交易标记
        if not trades.empty:
            buy_trades = trades[trades['direction'].str.upper() == 'BUY']
            sell_trades = trades[trades['direction'].str.upper() == 'SELL']
            
            if not buy_trades.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_trades['timestamp'],
                        y=buy_trades['price'],
                        mode='markers',
                        name='买入',
                        marker=dict(
                            symbol='triangle-up',
                            size=12,
                            color=self.COLORS['positive'],
                            line=dict(width=1, color='black')
                        ),
                        hovertemplate='买入<br>时间: %{x}<br>价格: %{y:.4f}<extra></extra>'
                    )
                )
            
            if not sell_trades.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_trades['timestamp'],
                        y=sell_trades['price'],
                        mode='markers',
                        name='卖出',
                        marker=dict(
                            symbol='triangle-down',
                            size=12,
                            color=self.COLORS['negative'],
                            line=dict(width=1, color='black')
                        ),
                        hovertemplate='卖出<br>时间: %{x}<br>价格: %{y:.4f}<extra></extra>'
                    )
                )
        
        fig.update_yaxes(title_text="价格")
        fig.update_xaxes(title_text="日期")
        
        self._apply_layout(fig, title)
        self._figures.append(fig)
        return fig
    
    def plot_trade_pnl(self,
                       trades: pd.DataFrame,
                       title: str = '交易盈亏分析') -> Optional[go.Figure]:
        """绘制交易盈亏分析"""
        if not self._check_plotly():
            return None
        
        if 'pnl' not in trades.columns:
            logger.error("交易数据缺少pnl列")
            return None
        
        pnl = trades['pnl']
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('单笔盈亏', '累计盈亏', '盈亏分布', '统计摘要'),
            specs=[[{}, {}], [{}, {"type": "table"}]]
        )
        
        # 1. 单笔盈亏
        colors = [self.COLORS['positive'] if x > 0 else self.COLORS['negative'] for x in pnl]
        fig.add_trace(
            go.Bar(x=list(range(len(pnl))), y=pnl, name='单笔盈亏',
                   marker_color=colors, opacity=0.7),
            row=1, col=1
        )
        
        # 2. 累计盈亏
        cum_pnl = pnl.cumsum()
        fig.add_trace(
            go.Scatter(x=list(range(len(cum_pnl))), y=cum_pnl, name='累计盈亏',
                       fill='tozeroy', line=dict(color=self.COLORS['primary'])),
            row=1, col=2
        )
        
        # 3. 盈亏分布
        fig.add_trace(
            go.Histogram(x=pnl, name='分布',
                         marker_color=self.COLORS['primary'], opacity=0.7),
            row=2, col=1
        )
        
        # 4. 统计表格
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        
        avg_win = f"{wins.mean():.2f}" if len(wins) > 0 else "0"
        avg_loss = f"{losses.mean():.2f}" if len(losses) > 0 else "0"
        profit_ratio = f"{abs(wins.mean()/losses.mean()):.2f}" if len(losses) > 0 and losses.mean() != 0 else "N/A"
        
        stats = {
            '指标': ['总交易数', '盈利次数', '亏损次数', '胜率', '总盈亏', 
                    '平均盈利', '平均亏损', '盈亏比'],
            '值': [
                str(len(pnl)),
                str(len(wins)),
                str(len(losses)),
                f"{len(wins)/len(pnl)*100:.1f}%",
                f"{pnl.sum():.2f}",
                avg_win,
                avg_loss,
                profit_ratio
            ]
        }
        fig.add_trace(
            go.Table(
                header=dict(values=list(stats.keys()), fill_color='paleturquoise', align='left'),
                cells=dict(values=list(stats.values()), fill_color='lavender', align='left')
            ),
            row=2, col=2
        )
        
        self._apply_layout(fig, title, height=700)
        self._figures.append(fig)
        return fig
    
    # ==================== 滚动指标 ====================
    
    def plot_rolling_metrics(self,
                             returns: pd.Series,
                             window: int = 20,
                             title: str = '滚动指标') -> Optional[go.Figure]:
        """绘制滚动指标"""
        if not self._check_plotly():
            return None
        
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(f'{window}日滚动年化收益率', 
                           f'{window}日滚动年化波动率',
                           f'{window}日滚动夏普比率')
        )
        
        # 1. 滚动收益率
        rolling_return = returns.rolling(window).mean() * 252 * 100
        fig.add_trace(
            go.Scatter(x=rolling_return.index, y=rolling_return, name='年化收益率',
                       line=dict(color=self.COLORS['primary'])),
            row=1, col=1
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
        
        # 2. 滚动波动率
        rolling_vol = returns.rolling(window).std() * np.sqrt(252) * 100
        fig.add_trace(
            go.Scatter(x=rolling_vol.index, y=rolling_vol, name='年化波动率',
                       fill='tozeroy', line=dict(color=self.COLORS['secondary'])),
            row=2, col=1
        )
        
        # 3. 滚动夏普
        rolling_sharpe = (returns.rolling(window).mean() / returns.rolling(window).std()) * np.sqrt(252)
        fig.add_trace(
            go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe, name='夏普比率',
                       line=dict(color=self.COLORS['positive'])),
            row=3, col=1
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)
        fig.add_hline(y=1, line_dash="dot", line_color="green", opacity=0.5, row=3, col=1)
        
        fig.update_yaxes(title_text="收益率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="波动率 (%)", row=2, col=1)
        fig.update_yaxes(title_text="夏普比率", row=3, col=1)
        
        self._apply_layout(fig, title, height=800)
        self._figures.append(fig)
        return fig
    
    # ==================== 相关性分析 ====================
    
    def plot_correlation(self,
                         data: pd.DataFrame,
                         title: str = '相关性矩阵') -> Optional[go.Figure]:
        """绘制相关性矩阵"""
        if not self._check_plotly():
            return None
        
        corr = data.corr()
        
        # 创建文本标注
        text = [[f"{corr.iloc[i, j]:.2f}" for j in range(len(corr.columns))]
                for i in range(len(corr.index))]
        
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            text=text,
            texttemplate="%{text}",
            textfont={"size": 10},
            colorscale='RdYlGn',
            zmid=0,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="相关系数")
        ))
        
        self._apply_layout(fig, title, height=500, width=600)
        self._figures.append(fig)
        return fig
    
    # ==================== 综合仪表板 ====================
    
    def plot_dashboard(self,
                       equity_curve: pd.DataFrame,
                       trades: pd.DataFrame = None,
                       price_data: pd.DataFrame = None,
                       summary: Dict[str, Any] = None,
                       title: str = '量化回测报告') -> Optional[go.Figure]:
        """创建综合仪表板"""
        if not self._check_plotly():
            return None
        
        # 获取权益序列
        equity = equity_curve['equity'] if 'equity' in equity_curve.columns else equity_curve.iloc[:, 0]
        returns = equity.pct_change().dropna()
        
        # 创建子图布局
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=('权益曲线', '绩效摘要', '回撤曲线', '收益率分布', '交易信号', '交易盈亏'),
            specs=[
                [{}, {"type": "table"}],
                [{}, {}],
                [{}, {}]
            ],
            vertical_spacing=0.1,
            horizontal_spacing=0.08
        )
        
        # 1. 权益曲线
        fig.add_trace(
            go.Scatter(x=equity.index, y=equity.values, name='权益',
                       fill='tozeroy', line=dict(color=self.COLORS['primary'])),
            row=1, col=1
        )
        
        # 2. 绩效摘要表格
        if summary:
            stats = {
                '指标': ['初始资金', '最终权益', '总收益率', '年化收益', 
                        '夏普比率', '最大回撤', '总交易数', '胜率'],
                '值': [
                    f"{summary.get('initial_capital', 0):,.0f}",
                    f"{summary.get('final_equity', 0):,.0f}",
                    str(summary.get('total_return', 'N/A')),
                    str(summary.get('annual_return', 'N/A')),
                    str(summary.get('sharpe_ratio', 'N/A')),
                    str(summary.get('max_drawdown', 'N/A')),
                    str(summary.get('total_trades', 0)),
                    str(summary.get('win_rate', 'N/A'))
                ]
            }
            fig.add_trace(
                go.Table(
                    header=dict(values=list(stats.keys()), fill_color='paleturquoise', align='left'),
                    cells=dict(values=list(stats.values()), fill_color='lavender', align='left')
                ),
                row=1, col=2
            )
        
        # 3. 回撤曲线
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax * 100
        fig.add_trace(
            go.Scatter(x=drawdown.index, y=drawdown.values, name='回撤',
                       fill='tozeroy', line=dict(color=self.COLORS['negative'])),
            row=2, col=1
        )
        
        # 4. 收益率分布
        fig.add_trace(
            go.Histogram(x=returns * 100, name='收益率分布',
                         marker_color=self.COLORS['primary'], opacity=0.7),
            row=2, col=2
        )
        
        # 5. 价格和交易信号
        if price_data is not None and not price_data.empty:
            close_col = 'close' if 'close' in price_data.columns else price_data.columns[0]
            fig.add_trace(
                go.Scatter(x=price_data.index, y=price_data[close_col], name='价格',
                           line=dict(color=self.COLORS['primary'], width=1)),
                row=3, col=1
            )
            
            if trades is not None and not trades.empty:
                buy_trades = trades[trades['direction'].str.upper() == 'BUY']
                sell_trades = trades[trades['direction'].str.upper() == 'SELL']
                
                if not buy_trades.empty:
                    fig.add_trace(
                        go.Scatter(x=buy_trades['timestamp'], y=buy_trades['price'],
                                   mode='markers', name='买入',
                                   marker=dict(symbol='triangle-up', size=10, 
                                              color=self.COLORS['positive'])),
                        row=3, col=1
                    )
                if not sell_trades.empty:
                    fig.add_trace(
                        go.Scatter(x=sell_trades['timestamp'], y=sell_trades['price'],
                                   mode='markers', name='卖出',
                                   marker=dict(symbol='triangle-down', size=10,
                                              color=self.COLORS['negative'])),
                        row=3, col=1
                    )
        
        # 6. 交易盈亏
        if trades is not None and not trades.empty and 'pnl' in trades.columns:
            colors = [self.COLORS['positive'] if x > 0 else self.COLORS['negative'] 
                      for x in trades['pnl']]
            fig.add_trace(
                go.Bar(x=list(range(len(trades))), y=trades['pnl'], name='交易盈亏',
                       marker_color=colors, opacity=0.7),
                row=3, col=2
            )
        
        self._apply_layout(fig, title, height=1000, width=1200)
        self._figures.append(fig)
        return fig
    
    # ==================== 工具方法 ====================
    
    def show_all(self):
        """显示所有图表"""
        for fig in self._figures:
            fig.show()
    
    def clear(self):
        """清空图表列表"""
        self._figures.clear()
    
    def save_html(self, fig: go.Figure, path: str):
        """保存为HTML文件"""
        fig.write_html(path)
        logger.info(f"图表已保存: {path}")
    
    def save_image(self, fig: go.Figure, path: str, format: str = 'png'):
        """保存为图片（需要kaleido）"""
        try:
            fig.write_image(path, format=format)
            logger.info(f"图表已保存: {path}")
        except Exception as e:
            logger.error(f"保存图片失败: {e}. 请安装 kaleido: pip install kaleido")


# ==================== 便捷函数 ====================

def quick_equity(equity: pd.Series, title: str = '权益曲线') -> Optional[go.Figure]:
    """快速绘制权益曲线"""
    plotter = PlotlyPlotter()
    return plotter.plot_equity(equity, title=title)


def quick_returns(returns: pd.Series, title: str = '收益率分析') -> Optional[go.Figure]:
    """快速绘制收益率分析"""
    plotter = PlotlyPlotter()
    return plotter.plot_returns(returns, title=title)


def quick_kline(data: pd.DataFrame, title: str = 'K线图', 
                ma_periods: List[int] = None) -> Optional[go.Figure]:
    """快速绘制K线图"""
    plotter = PlotlyPlotter()
    return plotter.plot_candlestick(data, title=title, ma_periods=ma_periods or [5, 20])


def quick_heatmap(returns: pd.Series, title: str = '月度收益') -> Optional[go.Figure]:
    """快速绘制月度热力图"""
    plotter = PlotlyPlotter()
    return plotter.plot_monthly_heatmap(returns, title=title)
