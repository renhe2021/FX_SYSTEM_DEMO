"""数据模块测试

测试 loader, sources 模块
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
import os


class TestDataLoader:
    """数据加载器测试"""
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """创建测试CSV文件"""
        df = pd.DataFrame({
            'open': [7.25, 7.26, 7.27],
            'high': [7.26, 7.27, 7.28],
            'low': [7.24, 7.25, 7.26],
            'close': [7.255, 7.265, 7.275],
            'volume': [1000, 2000, 3000]
        }, index=pd.date_range('2024-01-01', periods=3, freq='D'))
        
        csv_path = tmp_path / 'test_data.csv'
        df.to_csv(csv_path)
        return str(csv_path)
    
    def test_load_csv(self, sample_csv):
        """测试CSV加载"""
        from bmad.data.loader import DataLoader
        
        df = DataLoader.load_csv(sample_csv)
        
        assert len(df) == 3
        assert 'close' in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)
    
    def test_load_csv_columns_lowercase(self, sample_csv):
        """测试列名小写化"""
        from bmad.data.loader import DataLoader
        
        df = DataLoader.load_csv(sample_csv)
        
        for col in df.columns:
            assert col == col.lower()
    
    def test_load_auto_detect(self, sample_csv):
        """测试自动格式检测"""
        from bmad.data.loader import DataLoader
        
        df = DataLoader.load(sample_csv)
        
        assert len(df) == 3
        assert 'close' in df.columns
    
    def test_resample(self):
        """测试数据重采样"""
        from bmad.data.loader import DataLoader
        
        # 创建小时数据
        df = pd.DataFrame({
            'open': np.random.randn(24) + 7.25,
            'high': np.random.randn(24) + 7.26,
            'low': np.random.randn(24) + 7.24,
            'close': np.random.randn(24) + 7.25,
            'volume': np.random.randint(100, 1000, 24)
        }, index=pd.date_range('2024-01-01', periods=24, freq='H'))
        
        # 重采样为日线
        daily = DataLoader.resample(df, '1D')
        
        assert len(daily) == 1
        assert daily['open'].iloc[0] == df['open'].iloc[0]  # first
        assert daily['high'].iloc[0] == df['high'].max()     # max
        assert daily['low'].iloc[0] == df['low'].min()       # min
        assert daily['close'].iloc[0] == df['close'].iloc[-1]  # last


class TestCSVDataSource:
    """CSV数据源测试"""
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """创建测试CSV"""
        df = pd.DataFrame({
            'open': [7.25, 7.26, 7.27, 7.28, 7.29],
            'high': [7.26, 7.27, 7.28, 7.29, 7.30],
            'low': [7.24, 7.25, 7.26, 7.27, 7.28],
            'close': [7.255, 7.265, 7.275, 7.285, 7.295],
            'volume': [1000, 2000, 3000, 4000, 5000]
        }, index=pd.date_range('2024-01-01', periods=5, freq='D'))
        
        csv_path = tmp_path / 'usdcnh.csv'
        df.to_csv(csv_path)
        return str(csv_path)
    
    def test_csv_source_connect(self, sample_csv):
        """测试CSV数据源连接"""
        from bmad.data.sources.csv_source import CSVDataSource
        
        source = CSVDataSource(sample_csv)
        connected = source.connect()
        
        assert connected is True
    
    def test_csv_source_get_data(self, sample_csv):
        """测试CSV数据源获取数据"""
        from bmad.data.sources.csv_source import CSVDataSource
        
        source = CSVDataSource(sample_csv)
        source.connect()
        df = source.get_historical_data('USDCNH')
        
        assert len(df) == 5
        assert 'close' in df.columns
    
    def test_csv_source_date_range(self, sample_csv):
        """测试日期范围筛选"""
        from bmad.data.sources.csv_source import CSVDataSource
        from datetime import datetime
        
        source = CSVDataSource(sample_csv)
        source.connect()
        df = source.get_historical_data(
            'USDCNH',
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 4)
        )
        
        assert len(df) == 3


class TestBaseDataSource:
    """数据源基类测试"""
    
    def test_base_source_abstract(self):
        """测试基类是抽象类"""
        from bmad.data.sources.base import BaseDataSource
        
        # 不能直接实例化抽象类
        with pytest.raises(TypeError):
            BaseDataSource()


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
