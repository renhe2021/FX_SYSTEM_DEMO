"""工具箱测试

测试 fx_calculator, data_explorer, spread_analyzer 模块
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import tempfile


class TestFXCalculator:
    """外汇计算器测试"""
    
    def test_pip_value_usdcnh(self):
        """测试USDCNH点值计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        pip_value = calc.pip_value('USDCNH', 100000)
        
        # 100000 * 0.0001 = 10
        assert pip_value == pytest.approx(10, rel=0.01)
    
    def test_pip_value_usdjpy(self):
        """测试USDJPY点值计算（日元特殊）"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        pip_value = calc.pip_value('USDJPY', 100000)
        
        # 100000 * 0.01 = 1000
        assert pip_value == pytest.approx(1000, rel=0.01)
    
    def test_margin_required(self):
        """测试保证金计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        margin = calc.margin_required('USDCNH', 100000, 7.25, leverage=100)
        
        # 100000 * 7.25 / 100 = 7250
        assert margin == pytest.approx(7250, rel=0.01)
    
    def test_position_size(self):
        """测试仓位计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        size = calc.position_size(
            account=100000,
            risk_pct=0.02,
            stop_pips=50,
            pair='USDCNH'
        )
        
        # 风险金额 = 100000 * 0.02 = 2000
        # 仓位 = 2000 / (50 * 10) * 100000 = 400000
        assert size > 0
    
    def test_pips_to_price(self):
        """测试点数转价格"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        price_change = calc.pips_to_price(100, 'USDCNH')
        
        # 100 * 0.0001 = 0.01
        assert price_change == pytest.approx(0.01, rel=0.01)
    
    def test_price_to_pips(self):
        """测试价格转点数"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        pips = calc.price_to_pips(0.01, 'USDCNH')
        
        # 0.01 / 0.0001 = 100
        assert pips == pytest.approx(100, rel=0.01)
    
    def test_calculate_pnl_long(self):
        """测试多头盈亏计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        result = calc.calculate_pnl(
            entry_price=7.25,
            exit_price=7.26,
            size=100000,
            direction='long',
            pair='USDCNH'
        )
        
        assert result['pips'] == pytest.approx(100, rel=0.1)
        assert result['amount'] > 0  # 盈利
    
    def test_calculate_pnl_short(self):
        """测试空头盈亏计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        result = calc.calculate_pnl(
            entry_price=7.26,
            exit_price=7.25,
            size=100000,
            direction='short',
            pair='USDCNH'
        )
        
        assert result['pips'] == pytest.approx(100, rel=0.1)
        assert result['amount'] > 0  # 盈利
    
    def test_spread_cost(self):
        """测试点差成本计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        cost = calc.spread_cost(spread_pips=2, size=100000, pair='USDCNH')
        
        # 2 * 10 = 20
        assert cost == pytest.approx(20, rel=0.1)
    
    def test_breakeven_pips(self):
        """测试盈亏平衡点计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        be_pips = calc.breakeven_pips(spread_pips=2, commission_per_lot=5, size=100000)
        
        assert be_pips >= 2  # 至少要覆盖点差
    
    def test_swap_cost(self):
        """测试隔夜利息计算"""
        from tools.fx_calculator import FXCalculator
        
        calc = FXCalculator()
        swap = calc.swap_cost(
            size=100000,
            days=7,
            long_swap=-0.5,
            short_swap=0.3,
            direction='long'
        )
        
        assert swap != 0


class TestDataExplorer:
    """数据探索器测试"""
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """创建测试CSV"""
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        df = pd.DataFrame({
            'open': 7.25 + np.random.randn(100) * 0.01,
            'high': 7.26 + np.random.randn(100) * 0.01,
            'low': 7.24 + np.random.randn(100) * 0.01,
            'close': 7.25 + np.random.randn(100) * 0.01,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        csv_path = tmp_path / 'test_data.csv'
        df.to_csv(csv_path)
        return str(csv_path)
    
    def test_load(self, sample_csv):
        """测试数据加载"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer()
        explorer.load(sample_csv)
        
        assert explorer.data is not None
        assert len(explorer.data) == 100
    
    def test_load_chain(self, sample_csv):
        """测试链式调用"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        
        assert explorer.data is not None
    
    def test_summary(self, sample_csv):
        """测试数据摘要"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        summary = explorer.summary()
        
        assert '行数' in summary
        assert summary['行数'] == 100
    
    def test_describe(self, sample_csv):
        """测试统计描述"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        desc = explorer.describe()
        
        assert 'close' in desc.columns
        assert 'mean' in desc.index
    
    def test_head_tail(self, sample_csv):
        """测试头尾查看"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        
        head = explorer.head(5)
        tail = explorer.tail(5)
        
        assert len(head) == 5
        assert len(tail) == 5
    
    def test_filter_date(self, sample_csv):
        """测试日期筛选"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        filtered = explorer.filter_date(start='2024-01-02', end='2024-01-03')
        
        assert len(filtered) < 100
    
    def test_filter_time(self, sample_csv):
        """测试时间筛选"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        filtered = explorer.filter_time(start_hour=9, end_hour=17)
        
        assert len(filtered) < 100
    
    def test_resample(self, sample_csv):
        """测试重采样"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        daily = explorer.resample('1D')
        
        assert len(daily) < 100
    
    def test_returns(self, sample_csv):
        """测试收益率计算"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        returns = explorer.returns('close')
        
        assert len(returns) == 100
        assert pd.isna(returns.iloc[0])  # 第一个是NaN
    
    def test_rolling_stats(self, sample_csv):
        """测试滚动统计"""
        from tools.data_explorer import DataExplorer
        
        explorer = DataExplorer().load(sample_csv)
        stats = explorer.rolling_stats('close', window=10)
        
        assert 'mean' in stats.columns
        assert 'std' in stats.columns


class TestSpreadAnalyzer:
    """价差分析器测试"""
    
    def test_spread_analyzer_init(self):
        """测试初始化"""
        from tools.spread_analyzer import SpreadAnalyzer
        
        analyzer = SpreadAnalyzer()
        assert analyzer is not None
    
    def test_from_dataframe(self):
        """测试从DataFrame加载"""
        from tools.spread_analyzer import SpreadAnalyzer
        
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        df = pd.DataFrame({
            'bid': 7.25 + np.random.randn(100) * 0.001,
            'ask': 7.2502 + np.random.randn(100) * 0.001
        }, index=dates)
        
        analyzer = SpreadAnalyzer()
        analyzer.from_dataframe(df)
        
        assert 'spread' in analyzer.data.columns
        assert 'spread_pips' in analyzer.data.columns
    
    def test_analyze(self):
        """测试价差分析"""
        from tools.spread_analyzer import SpreadAnalyzer
        
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        df = pd.DataFrame({
            'bid': 7.25,
            'ask': 7.2502
        }, index=dates)
        
        analyzer = SpreadAnalyzer().from_dataframe(df)
        stats = analyzer.analyze()
        
        assert 'mean' in stats
        assert 'median' in stats
    
    def test_by_hour(self):
        """测试按小时统计"""
        from tools.spread_analyzer import SpreadAnalyzer
        
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        df = pd.DataFrame({
            'bid': 7.25,
            'ask': 7.2502
        }, index=dates)
        
        analyzer = SpreadAnalyzer().from_dataframe(df)
        hourly = analyzer.by_hour()
        
        assert len(hourly) > 0


class TestFXPosition:
    """外汇持仓测试"""
    
    def test_position_pnl_long(self):
        """测试多头持仓盈亏"""
        from tools.fx_calculator import FXPosition
        
        position = FXPosition(
            pair='USDCNH',
            direction='long',
            size=100000,
            entry_price=7.25,
            current_price=7.26
        )
        
        assert position.pnl_pips == pytest.approx(100, rel=0.1)
        assert position.pnl_amount > 0
    
    def test_position_pnl_short(self):
        """测试空头持仓盈亏"""
        from tools.fx_calculator import FXPosition
        
        position = FXPosition(
            pair='USDCNH',
            direction='short',
            size=100000,
            entry_price=7.26,
            current_price=7.25
        )
        
        assert position.pnl_pips == pytest.approx(100, rel=0.1)
        assert position.pnl_amount > 0


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
