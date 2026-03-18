"""
Plotly 可视化模块测试

测试 bmad/analysis/plotly_viz.py 的各种绘图功能
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
import os

# 检查 plotly 是否安装
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

pytestmark = pytest.mark.skipif(not HAS_PLOTLY, reason="Plotly未安装")


class TestPlotlyPlotter:
    """PlotlyPlotter 测试类"""
    
    @pytest.fixture
    def plotter(self):
        """创建绘图器实例"""
        from bmad.analysis.plotly_viz import PlotlyPlotter
        return PlotlyPlotter(width=800, height=500)
    
    @pytest.fixture
    def sample_equity(self):
        """生成示例权益曲线"""
        dates = pd.date_range('2024-01-01', periods=252, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 252)
        equity = 100000 * np.cumprod(1 + returns)
        return pd.Series(equity, index=dates, name='equity')
    
    @pytest.fixture
    def sample_equity_df(self, sample_equity):
        """生成示例权益曲线DataFrame"""
        return pd.DataFrame({'equity': sample_equity})
    
    @pytest.fixture
    def sample_returns(self):
        """生成示例收益率序列"""
        dates = pd.date_range('2024-01-01', periods=252, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 252)
        return pd.Series(returns, index=dates)
    
    @pytest.fixture
    def sample_ohlcv(self):
        """生成示例OHLCV数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        close = 7.25 + np.cumsum(np.random.normal(0, 0.01, 100))
        high = close + np.abs(np.random.normal(0, 0.005, 100))
        low = close - np.abs(np.random.normal(0, 0.005, 100))
        open_price = low + np.random.random(100) * (high - low)
        volume = np.random.randint(1000, 10000, 100)
        
        return pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
    
    @pytest.fixture
    def sample_trades(self):
        """生成示例交易记录"""
        return pd.DataFrame({
            'timestamp': pd.date_range('2024-01-15', periods=10, freq='15D'),
            'direction': ['BUY', 'SELL'] * 5,
            'price': [7.25, 7.28, 7.22, 7.30, 7.26, 7.32, 7.28, 7.35, 7.30, 7.38],
            'quantity': [10000] * 10,
            'pnl': [300, -200, 400, -100, 500, -150, 350, -50, 450, 200]
        })
    
    # ==================== 初始化测试 ====================
    
    def test_plotter_init(self, plotter):
        """测试绘图器初始化"""
        assert plotter is not None
        assert plotter.width == 800
        assert plotter.height == 500
    
    def test_plotter_colors(self, plotter):
        """测试颜色方案"""
        assert 'primary' in plotter.COLORS
        assert 'positive' in plotter.COLORS
        assert 'negative' in plotter.COLORS
    
    # ==================== 权益曲线测试 ====================
    
    def test_plot_equity_series(self, plotter, sample_equity):
        """测试绘制权益曲线（Series输入）"""
        fig = plotter.plot_equity(sample_equity, show_drawdown=False)
        
        assert fig is not None
        assert isinstance(fig, go.Figure)
    
    def test_plot_equity_dataframe(self, plotter, sample_equity_df):
        """测试绘制权益曲线（DataFrame输入）"""
        fig = plotter.plot_equity(sample_equity_df, show_drawdown=True)
        
        assert fig is not None
        assert isinstance(fig, go.Figure)
    
    def test_plot_equity_with_benchmark(self, plotter, sample_equity):
        """测试绘制权益曲线（含基准）"""
        benchmark = sample_equity * 0.95
        fig = plotter.plot_equity(sample_equity, benchmark=benchmark)
        
        assert fig is not None
        # 应该有2条线（策略+基准）+ 回撤
        assert len(fig.data) >= 2
    
    def test_plot_equity_empty(self, plotter):
        """测试空数据处理"""
        empty_equity = pd.Series(dtype=float)
        fig = plotter.plot_equity(empty_equity)
        
        assert fig is None
    
    # ==================== 回撤分析测试 ====================
    
    def test_plot_drawdown(self, plotter, sample_equity):
        """测试绘制回撤分析"""
        fig = plotter.plot_drawdown(sample_equity)
        
        assert fig is not None
        assert isinstance(fig, go.Figure)
    
    # ==================== 收益率分析测试 ====================
    
    def test_plot_returns(self, plotter, sample_returns):
        """测试绘制收益率分析"""
        fig = plotter.plot_returns(sample_returns)
        
        assert fig is not None
        assert isinstance(fig, go.Figure)
    
    def test_plot_monthly_heatmap(self, plotter, sample_returns):
        """测试绘制月度热力图"""
        fig = plotter.plot_monthly_heatmap(sample_returns)
        
        assert fig is not None
        assert isinstance(fig, go.Figure)
    
    # ==================== K线图测试 ====================
    
    def test_plot_candlestick(self, plotter, sample_ohlcv):
        """测试绘制K线图"""
        fig = plotter.plot_candlestick(sample_ohlcv)
        
        assert fig is not None
        assert isinstance(fig, go.Figure)
    
    def test_plot_candlestick_with_ma(self, plotter, sample_ohlcv):
        """测试绘制K线图（含均线）"""
        fig = plotter.plot_candlestick(sample_ohlcv, ma_periods=[5, 20])
        
        assert fig is not None
        # 应该有K线 + 2条均线 + 成交量
        assert len(fig.data) >= 3
    
    def test_plot_candlestick_no_volume(self, plotter, sample_ohlcv):
        """测试绘制K线图（无成交量）"""
        fig = plotter.plot_candlestick(sample_ohlcv, volume=False)
        
        assert fig is not None
    
    def test_plot_candlestick_missing_columns(self, plotter):
        """测试K线图缺少必要列"""
        incomplete_data = pd.DataFrame({'close': [1, 2, 3]})
        fig = plotter.plot_candlestick(incomplete_data)
        
        assert fig is None
    
    # ==================== 交易分析测试 ====================
    
    def test_plot_trades(self, plotter, sample_ohlcv, sample_trades):
        """测试绘制交易信号"""
        fig = plotter.plot_trades(sample_ohlcv, sample_trades)
        
        assert fig is not None
        # 应该有价格线 + 买入点 + 卖出点
        assert len(fig.data) >= 1
    
    def test_plot_trades_empty(self, plotter, sample_ohlcv):
        """测试空交易记录"""
        empty_trades = pd.DataFrame()
        fig = plotter.plot_trades(sample_ohlcv, empty_trades)
        
        assert fig is not None
    
    def test_plot_trade_pnl(self, plotter, sample_trades):
        """测试绘制交易盈亏分析"""
        fig = plotter.plot_trade_pnl(sample_trades)
        
        assert fig is not None
    
    def test_plot_trade_pnl_no_pnl_column(self, plotter):
        """测试缺少pnl列"""
        trades_no_pnl = pd.DataFrame({'direction': ['BUY', 'SELL']})
        fig = plotter.plot_trade_pnl(trades_no_pnl)
        
        assert fig is None
    
    # ==================== 滚动指标测试 ====================
    
    def test_plot_rolling_metrics(self, plotter, sample_returns):
        """测试绘制滚动指标"""
        fig = plotter.plot_rolling_metrics(sample_returns, window=20)
        
        assert fig is not None
    
    # ==================== 相关性分析测试 ====================
    
    def test_plot_correlation(self, plotter):
        """测试绘制相关性矩阵"""
        np.random.seed(42)
        data = pd.DataFrame({
            'USDCNH': np.random.normal(0, 0.01, 100),
            'EURUSD': np.random.normal(0, 0.01, 100),
            'GBPUSD': np.random.normal(0, 0.01, 100)
        })
        
        fig = plotter.plot_correlation(data)
        
        assert fig is not None
    
    # ==================== 仪表板测试 ====================
    
    def test_plot_dashboard(self, plotter, sample_equity_df, sample_trades, sample_ohlcv):
        """测试绘制综合仪表板"""
        summary = {
            'initial_capital': 100000,
            'final_equity': 112500,
            'total_return': '12.5%',
            'annual_return': '15.2%',
            'sharpe_ratio': 1.5,
            'max_drawdown': '-5.2%',
            'total_trades': 10,
            'win_rate': '60%'
        }
        
        fig = plotter.plot_dashboard(
            equity_curve=sample_equity_df,
            trades=sample_trades,
            price_data=sample_ohlcv,
            summary=summary
        )
        
        assert fig is not None
    
    def test_plot_dashboard_minimal(self, plotter, sample_equity_df):
        """测试最小化仪表板"""
        fig = plotter.plot_dashboard(equity_curve=sample_equity_df)
        
        assert fig is not None
    
    # ==================== 工具方法测试 ====================
    
    def test_clear(self, plotter, sample_equity):
        """测试清空图表列表"""
        plotter.plot_equity(sample_equity)
        plotter.plot_drawdown(sample_equity)
        
        assert len(plotter._figures) == 2
        
        plotter.clear()
        
        assert len(plotter._figures) == 0
    
    def test_save_html(self, plotter, sample_equity):
        """测试保存HTML"""
        fig = plotter.plot_equity(sample_equity)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, 'test.html')
            plotter.save_html(fig, save_path)
            
            assert os.path.exists(save_path)
            # 检查文件大小
            assert os.path.getsize(save_path) > 0


class TestQuickFunctions:
    """便捷函数测试"""
    
    @pytest.fixture
    def sample_equity(self):
        """生成示例权益曲线"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 100)
        equity = 100000 * np.cumprod(1 + returns)
        return pd.Series(equity, index=dates)
    
    @pytest.fixture
    def sample_returns(self):
        """生成示例收益率"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        return pd.Series(np.random.normal(0.0005, 0.01, 100), index=dates)
    
    @pytest.fixture
    def sample_ohlcv(self):
        """生成示例OHLCV"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        close = 7.25 + np.cumsum(np.random.normal(0, 0.01, 50))
        return pd.DataFrame({
            'open': close - 0.01,
            'high': close + 0.02,
            'low': close - 0.02,
            'close': close,
            'volume': np.random.randint(1000, 10000, 50)
        }, index=dates)
    
    def test_quick_equity(self, sample_equity):
        """测试快速权益曲线"""
        from bmad.analysis.plotly_viz import quick_equity
        
        fig = quick_equity(sample_equity)
        assert fig is not None
    
    def test_quick_returns(self, sample_returns):
        """测试快速收益率分析"""
        from bmad.analysis.plotly_viz import quick_returns
        
        fig = quick_returns(sample_returns)
        assert fig is not None
    
    def test_quick_kline(self, sample_ohlcv):
        """测试快速K线图"""
        from bmad.analysis.plotly_viz import quick_kline
        
        fig = quick_kline(sample_ohlcv, ma_periods=[5, 10])
        assert fig is not None
    
    def test_quick_heatmap(self, sample_returns):
        """测试快速热力图"""
        from bmad.analysis.plotly_viz import quick_heatmap
        
        fig = quick_heatmap(sample_returns)
        assert fig is not None


class TestDraftsModule:
    """草稿管理模块测试"""
    
    def test_import_drafts(self):
        """测试导入草稿模块"""
        from notebooks.drafts import create_draft, list_drafts, show_drafts
        
        assert callable(create_draft)
        assert callable(list_drafts)
        assert callable(show_drafts)
    
    def test_create_and_delete_draft(self):
        """测试创建和删除草稿"""
        from notebooks.drafts import create_draft, delete_draft, get_draft
        import os
        
        # 创建草稿
        path = create_draft("测试草稿", "这是一个测试")
        assert os.path.exists(path)
        
        # 获取草稿ID
        import re
        match = re.search(r'draft_(\d+)_', path)
        assert match
        draft_id = int(match.group(1))
        
        # 验证可以获取
        draft_path = get_draft(draft_id)
        assert draft_path is not None
        
        # 删除草稿（跳过确认）
        result = delete_draft(draft_id, confirm=False)
        assert result is True
        assert not os.path.exists(path)
    
    def test_list_drafts(self):
        """测试列出草稿"""
        from notebooks.drafts import list_drafts
        
        drafts = list_drafts()
        assert isinstance(drafts, list)


class TestEdgeCases:
    """边缘情况测试"""
    
    @pytest.fixture
    def plotter(self):
        from bmad.analysis.plotly_viz import PlotlyPlotter
        return PlotlyPlotter()
    
    def test_single_data_point(self, plotter):
        """测试单个数据点"""
        single_point = pd.Series([100000], index=[datetime(2024, 1, 1)])
        fig = plotter.plot_equity(single_point, show_drawdown=False)
        
        assert fig is not None
    
    def test_nan_values(self, plotter):
        """测试包含NaN值的数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        equity = pd.Series(np.random.random(100) * 100000, index=dates)
        equity.iloc[10:15] = np.nan
        
        fig = plotter.plot_equity(equity, show_drawdown=False)
        assert fig is not None
    
    def test_large_dataset(self, plotter):
        """测试大数据集"""
        dates = pd.date_range('2020-01-01', periods=2000, freq='D')
        np.random.seed(42)
        equity = pd.Series(
            100000 * np.cumprod(1 + np.random.normal(0.0002, 0.01, 2000)),
            index=dates
        )
        
        fig = plotter.plot_equity(equity)
        assert fig is not None
    
    def test_uppercase_columns(self, plotter):
        """测试大写列名"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        data = pd.DataFrame({
            'OPEN': np.random.random(50) * 10,
            'HIGH': np.random.random(50) * 10 + 0.5,
            'LOW': np.random.random(50) * 10 - 0.5,
            'CLOSE': np.random.random(50) * 10,
            'VOLUME': np.random.randint(1000, 10000, 50)
        }, index=dates)
        
        fig = plotter.plot_candlestick(data)
        assert fig is not None
