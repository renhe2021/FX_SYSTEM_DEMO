"""分析模块"""
from .performance import PerformanceAnalyzer
from .metrics import (
    calculate_sharpe,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor
)
# Matplotlib 可视化（保留兼容）
from .visualization import (
    QuantPlotter,
    quick_equity_plot,
    quick_returns_plot,
    quick_candlestick,
    quick_dashboard
)
# Plotly 交互式可视化（推荐）
from .plotly_viz import (
    PlotlyPlotter,
    quick_equity,
    quick_returns,
    quick_kline,
    quick_heatmap
)

__all__ = [
    'PerformanceAnalyzer',
    'calculate_sharpe', 'calculate_max_drawdown',
    'calculate_win_rate', 'calculate_profit_factor',
    # Matplotlib 可视化
    'QuantPlotter',
    'quick_equity_plot', 'quick_returns_plot',
    'quick_candlestick', 'quick_dashboard',
    # Plotly 可视化
    'PlotlyPlotter',
    'quick_equity', 'quick_returns',
    'quick_kline', 'quick_heatmap'
]
