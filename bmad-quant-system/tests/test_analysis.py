"""分析模块测试

测试 metrics, performance 模块
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


class TestMetrics:
    """绩效指标测试"""
    
    def test_sharpe_ratio(self):
        """测试夏普比率计算"""
        from bmad.analysis.metrics import calculate_sharpe
        
        # 正收益序列
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005] * 50)
        sharpe = calculate_sharpe(returns)
        
        assert sharpe > 0  # 正收益应该有正夏普
    
    def test_sharpe_ratio_zero_std(self):
        """测试零波动率情况"""
        from bmad.analysis.metrics import calculate_sharpe
        
        # 零收益（零波动）
        returns = pd.Series([0.0] * 100)
        sharpe = calculate_sharpe(returns)
        
        assert sharpe == 0  # 零波动率返回0
    
    def test_sharpe_ratio_negative(self):
        """测试负收益夏普"""
        from bmad.analysis.metrics import calculate_sharpe
        
        returns = pd.Series([-0.01, -0.02, -0.015, -0.01, -0.005] * 50)
        sharpe = calculate_sharpe(returns)
        
        assert sharpe < 0  # 负收益应该有负夏普
    
    def test_max_drawdown(self):
        """测试最大回撤计算"""
        from bmad.analysis.metrics import calculate_max_drawdown
        
        # 先涨后跌的权益曲线
        equity = pd.Series([100, 110, 120, 100, 90, 95])
        mdd = calculate_max_drawdown(equity)
        
        # 从120跌到90，回撤 = (90-120)/120 = -0.25
        assert mdd == pytest.approx(-0.25, rel=0.01)
    
    def test_max_drawdown_no_drawdown(self):
        """测试无回撤情况"""
        from bmad.analysis.metrics import calculate_max_drawdown
        
        # 持续上涨
        equity = pd.Series([100, 110, 120, 130, 140])
        mdd = calculate_max_drawdown(equity)
        
        assert mdd == 0
    
    def test_win_rate(self):
        """测试胜率计算"""
        from bmad.analysis.metrics import calculate_win_rate
        
        trades = pd.DataFrame({
            'pnl': [100, -50, 200, -30, 150, -20, 80, -10]
        })
        
        win_rate = calculate_win_rate(trades)
        
        # 4胜4负 = 4/8 = 0.5 (100, 200, 150, 80 > 0)
        assert win_rate == pytest.approx(0.5, rel=0.01)
    
    def test_win_rate_empty(self):
        """测试空交易胜率"""
        from bmad.analysis.metrics import calculate_win_rate
        
        trades = pd.DataFrame()
        win_rate = calculate_win_rate(trades)
        
        assert win_rate == 0
    
    def test_profit_factor(self):
        """测试盈亏比计算"""
        from bmad.analysis.metrics import calculate_profit_factor
        
        trades = pd.DataFrame({
            'pnl': [100, -50, 200, -50]
        })
        
        pf = calculate_profit_factor(trades)
        
        # 总盈利300，总亏损100，盈亏比=3
        assert pf == pytest.approx(3.0, rel=0.01)
    
    def test_profit_factor_no_loss(self):
        """测试无亏损盈亏比"""
        from bmad.analysis.metrics import calculate_profit_factor
        
        trades = pd.DataFrame({'pnl': [100, 200, 300]})
        pf = calculate_profit_factor(trades)
        
        assert pf == float('inf')
    
    def test_sortino_ratio(self):
        """测试索提诺比率"""
        from bmad.analysis.metrics import calculate_sortino
        
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005] * 50)
        sortino = calculate_sortino(returns)
        
        assert sortino > 0
    
    def test_calmar_ratio(self):
        """测试卡玛比率"""
        from bmad.analysis.metrics import calculate_calmar
        
        annual_return = 0.20  # 20%年化
        max_drawdown = -0.10  # 10%最大回撤
        
        calmar = calculate_calmar(annual_return, max_drawdown)
        
        # 0.20 / 0.10 = 2.0
        assert calmar == pytest.approx(2.0, rel=0.01)


class TestPerformanceAnalyzer:
    """绩效分析器测试"""
    
    @pytest.fixture
    def sample_results(self):
        """创建测试回测结果"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        equity_curve = pd.DataFrame({
            'equity': 1000000 * (1 + np.random.randn(100).cumsum() * 0.001)
        }, index=dates)
        
        trades = pd.DataFrame({
            'entry_time': dates[:10],
            'exit_time': dates[1:11],
            'symbol': ['USDCNH'] * 10,
            'direction': ['BUY'] * 5 + ['SELL'] * 5,
            'quantity': [100000] * 10,
            'entry_price': [7.25] * 10,
            'exit_price': [7.26, 7.24, 7.27, 7.23, 7.28, 7.24, 7.26, 7.23, 7.27, 7.25],
            'pnl': [1000, -1000, 2000, -2000, 3000, 1000, -1000, 2000, -2000, 0],
            'commission': [10] * 10
        })
        
        return {
            'equity_curve': equity_curve,
            'trades': trades,
            'summary': {
                'initial_capital': 1000000,
                'final_equity': equity_curve['equity'].iloc[-1]
            }
        }
    
    def test_analyzer_init(self, sample_results):
        """测试分析器初始化"""
        from bmad.analysis.performance import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer(
            equity_curve=sample_results['equity_curve'],
            trades=sample_results['trades'],
            initial_capital=sample_results['summary']['initial_capital']
        )
        
        assert analyzer is not None
    
    def test_analyzer_summary(self, sample_results):
        """测试分析摘要"""
        from bmad.analysis.performance import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer(
            equity_curve=sample_results['equity_curve'],
            trades=sample_results['trades'],
            initial_capital=sample_results['summary']['initial_capital']
        )
        summary = analyzer.get_summary()
        
        assert '总收益' in summary or '夏普比率' in summary


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
