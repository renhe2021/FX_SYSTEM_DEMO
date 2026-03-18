"""
可视化模块测试

测试 bmad/analysis/visualization.py 的各种绘图功能
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os


class TestQuantPlotter:
    """QuantPlotter 测试类"""
    
    @pytest.fixture
    def plotter(self):
        """创建绘图器实例"""
        from bmad.analysis.visualization import QuantPlotter
        return QuantPlotter(figsize=(10, 6))
    
    @pytest.fixture
    def sample_equity(self):
        """生成示例权益曲线"""
        dates = pd.date_range('2024-01-01', periods=252, freq='D')
        # 模拟带波动的上涨曲线
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
        assert plotter.figsize == (10, 6)
    
    def test_plotter_colors(self, plotter):
        """测试颜色方案"""
        assert 'primary' in plotter.COLORS
        assert 'positive' in plotter.COLORS
        assert 'negative' in plotter.COLORS
    
    # ==================== 权益曲线测试 ====================
    
    def test_plot_equity_series(self, plotter, sample_equity):
        """测试绘制权益曲线（Series输入）"""
        import matplotlib
        matplotlib.use('Agg')  # 非交互式后端
        
        fig = plotter.plot_equity(sample_equity, show_drawdown=False)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_equity_dataframe(self, plotter, sample_equity_df):
        """测试绘制权益曲线（DataFrame输入）"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_equity(sample_equity_df, show_drawdown=True)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_equity_with_benchmark(self, plotter, sample_equity):
        """测试绘制权益曲线（含基准）"""
        import matplotlib
        matplotlib.use('Agg')
        
        # 创建基准
        benchmark = sample_equity * 0.95  # 略低于策略
        
        fig = plotter.plot_equity(sample_equity, benchmark=benchmark)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_equity_save(self, plotter, sample_equity):
        """测试保存权益曲线图"""
        import matplotlib
        matplotlib.use('Agg')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, 'equity.png')
            fig = plotter.plot_equity(sample_equity, save_path=save_path)
            
            assert fig is not None
            assert os.path.exists(save_path)
        
        plotter.close_all()
    
    def test_plot_equity_empty(self, plotter):
        """测试空数据处理"""
        import matplotlib
        matplotlib.use('Agg')
        
        empty_equity = pd.Series(dtype=float)
        fig = plotter.plot_equity(empty_equity)
        
        assert fig is None
    
    # ==================== 回撤分析测试 ====================
    
    def test_plot_drawdown(self, plotter, sample_equity):
        """测试绘制回撤分析"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_drawdown(sample_equity)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_drawdown_dataframe(self, plotter, sample_equity_df):
        """测试回撤分析（DataFrame输入）"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_drawdown(sample_equity_df)
        
        assert fig is not None
        plotter.close_all()
    
    # ==================== 收益率分析测试 ====================
    
    def test_plot_returns(self, plotter, sample_returns):
        """测试绘制收益率分析"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_returns(sample_returns)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_monthly_heatmap(self, plotter, sample_returns):
        """测试绘制月度热力图"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_monthly_heatmap(sample_returns)
        
        assert fig is not None
        plotter.close_all()
    
    # ==================== K线图测试 ====================
    
    def test_plot_candlestick(self, plotter, sample_ohlcv):
        """测试绘制K线图"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_candlestick(sample_ohlcv)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_candlestick_with_ma(self, plotter, sample_ohlcv):
        """测试绘制K线图（含均线）"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_candlestick(sample_ohlcv, ma_periods=[5, 20])
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_candlestick_no_volume(self, plotter, sample_ohlcv):
        """测试绘制K线图（无成交量）"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_candlestick(sample_ohlcv, volume=False)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_candlestick_missing_columns(self, plotter):
        """测试K线图缺少必要列"""
        import matplotlib
        matplotlib.use('Agg')
        
        incomplete_data = pd.DataFrame({'close': [1, 2, 3]})
        fig = plotter.plot_candlestick(incomplete_data)
        
        assert fig is None
    
    # ==================== 交易分析测试 ====================
    
    def test_plot_trades(self, plotter, sample_ohlcv, sample_trades):
        """测试绘制交易信号"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_trades(sample_ohlcv, sample_trades)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_trades_empty(self, plotter, sample_ohlcv):
        """测试空交易记录"""
        import matplotlib
        matplotlib.use('Agg')
        
        empty_trades = pd.DataFrame()
        fig = plotter.plot_trades(sample_ohlcv, empty_trades)
        
        assert fig is not None  # 应该只显示价格
        plotter.close_all()
    
    def test_plot_trade_pnl(self, plotter, sample_trades):
        """测试绘制交易盈亏分析"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_trade_pnl(sample_trades)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_trade_pnl_no_pnl_column(self, plotter):
        """测试缺少pnl列"""
        import matplotlib
        matplotlib.use('Agg')
        
        trades_no_pnl = pd.DataFrame({'direction': ['BUY', 'SELL']})
        fig = plotter.plot_trade_pnl(trades_no_pnl)
        
        assert fig is None
    
    # ==================== 滚动指标测试 ====================
    
    def test_plot_rolling_metrics(self, plotter, sample_returns):
        """测试绘制滚动指标"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_rolling_metrics(sample_returns, window=20)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_rolling_metrics_different_window(self, plotter, sample_returns):
        """测试不同窗口的滚动指标"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_rolling_metrics(sample_returns, window=60)
        
        assert fig is not None
        plotter.close_all()
    
    # ==================== 相关性分析测试 ====================
    
    def test_plot_correlation(self, plotter):
        """测试绘制相关性矩阵"""
        import matplotlib
        matplotlib.use('Agg')
        
        # 创建多资产数据
        np.random.seed(42)
        data = pd.DataFrame({
            'USDCNH': np.random.normal(0, 0.01, 100),
            'EURUSD': np.random.normal(0, 0.01, 100),
            'GBPUSD': np.random.normal(0, 0.01, 100),
            'USDJPY': np.random.normal(0, 0.01, 100)
        })
        
        fig = plotter.plot_correlation(data)
        
        assert fig is not None
        plotter.close_all()
    
    # ==================== 仪表板测试 ====================
    
    def test_plot_dashboard(self, plotter, sample_equity_df, sample_trades, sample_ohlcv):
        """测试绘制综合仪表板"""
        import matplotlib
        matplotlib.use('Agg')
        
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
        plotter.close_all()
    
    def test_plot_dashboard_minimal(self, plotter, sample_equity_df):
        """测试最小化仪表板（仅权益曲线）"""
        import matplotlib
        matplotlib.use('Agg')
        
        fig = plotter.plot_dashboard(equity_curve=sample_equity_df)
        
        assert fig is not None
        plotter.close_all()
    
    def test_plot_dashboard_save(self, plotter, sample_equity_df):
        """测试保存仪表板"""
        import matplotlib
        matplotlib.use('Agg')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, 'dashboard.png')
            fig = plotter.plot_dashboard(
                equity_curve=sample_equity_df,
                save_path=save_path
            )
            
            assert fig is not None
            assert os.path.exists(save_path)
        
        plotter.close_all()
    
    # ==================== 工具方法测试 ====================
    
    def test_close_all(self, plotter, sample_equity):
        """测试关闭所有图表"""
        import matplotlib
        matplotlib.use('Agg')
        
        plotter.plot_equity(sample_equity)
        plotter.plot_drawdown(sample_equity)
        
        assert len(plotter._figures) == 2
        
        plotter.close_all()
        
        assert len(plotter._figures) == 0
    
    def test_save_all(self, plotter, sample_equity):
        """测试保存所有图表"""
        import matplotlib
        matplotlib.use('Agg')
        
        plotter.plot_equity(sample_equity)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            plotter.save_all(tmpdir, prefix='test')
            
            files = os.listdir(tmpdir)
            assert len(files) == 1
            assert files[0].startswith('test_')
        
        plotter.close_all()


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
    
    def test_quick_equity_plot_import(self):
        """测试导入便捷函数"""
        from bmad.analysis.visualization import quick_equity_plot
        assert callable(quick_equity_plot)
    
    def test_quick_returns_plot_import(self):
        """测试导入便捷函数"""
        from bmad.analysis.visualization import quick_returns_plot
        assert callable(quick_returns_plot)
    
    def test_quick_candlestick_import(self):
        """测试导入便捷函数"""
        from bmad.analysis.visualization import quick_candlestick
        assert callable(quick_candlestick)
    
    def test_quick_dashboard_import(self):
        """测试导入便捷函数"""
        from bmad.analysis.visualization import quick_dashboard
        assert callable(quick_dashboard)


class TestVisualizationEdgeCases:
    """边缘情况测试"""
    
    @pytest.fixture
    def plotter(self):
        from bmad.analysis.visualization import QuantPlotter
        return QuantPlotter()
    
    def test_single_data_point(self, plotter):
        """测试单个数据点"""
        import matplotlib
        matplotlib.use('Agg')
        
        single_point = pd.Series([100000], index=[datetime(2024, 1, 1)])
        fig = plotter.plot_equity(single_point, show_drawdown=False)
        
        # 单个数据点应该能绘制
        assert fig is not None
        plotter.close_all()
    
    def test_nan_values(self, plotter):
        """测试包含NaN值的数据"""
        import matplotlib
        matplotlib.use('Agg')
        
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        equity = pd.Series(np.random.random(100) * 100000, index=dates)
        equity.iloc[10:15] = np.nan  # 添加一些NaN
        
        fig = plotter.plot_equity(equity, show_drawdown=False)
        
        assert fig is not None
        plotter.close_all()
    
    def test_negative_equity(self, plotter):
        """测试负权益值"""
        import matplotlib
        matplotlib.use('Agg')
        
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        equity = pd.Series(100000 - np.cumsum(np.random.random(100) * 2000), index=dates)
        
        fig = plotter.plot_equity(equity)
        
        assert fig is not None
        plotter.close_all()
    
    def test_all_positive_returns(self, plotter):
        """测试全部正收益"""
        import matplotlib
        matplotlib.use('Agg')
        
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        returns = pd.Series(np.abs(np.random.normal(0.001, 0.005, 100)), index=dates)
        
        fig = plotter.plot_returns(returns)
        
        assert fig is not None
        plotter.close_all()
    
    def test_all_negative_returns(self, plotter):
        """测试全部负收益"""
        import matplotlib
        matplotlib.use('Agg')
        
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        returns = pd.Series(-np.abs(np.random.normal(0.001, 0.005, 100)), index=dates)
        
        fig = plotter.plot_returns(returns)
        
        assert fig is not None
        plotter.close_all()
    
    def test_zero_returns(self, plotter):
        """测试零收益"""
        import matplotlib
        matplotlib.use('Agg')
        
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        returns = pd.Series(np.zeros(100), index=dates)
        
        fig = plotter.plot_returns(returns)
        
        assert fig is not None
        plotter.close_all()
    
    def test_large_dataset(self, plotter):
        """测试大数据集"""
        import matplotlib
        matplotlib.use('Agg')
        
        dates = pd.date_range('2020-01-01', periods=2000, freq='D')
        np.random.seed(42)
        equity = pd.Series(100000 * np.cumprod(1 + np.random.normal(0.0002, 0.01, 2000)), index=dates)
        
        fig = plotter.plot_equity(equity)
        
        assert fig is not None
        plotter.close_all()
    
    def test_uppercase_columns(self, plotter):
        """测试大写列名"""
        import matplotlib
        matplotlib.use('Agg')
        
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
        plotter.close_all()
