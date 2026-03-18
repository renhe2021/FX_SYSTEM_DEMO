"""
Bloomberg 数据工具箱 Web App 测试用例
测试所有UI功能和交互逻辑
"""

import unittest
import json
from unittest.mock import MagicMock, patch
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from quant_system.tools.web_app import create_app


class TestWebAppBasic(unittest.TestCase):
    """基础功能测试"""
    
    @classmethod
    def setUpClass(cls):
        """创建测试客户端"""
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_01_homepage_loads(self):
        """测试1: 主页能正常加载"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Bloomberg', response.data)
        print("✓ 测试1通过: 主页正常加载")
    
    def test_02_version_displayed(self):
        """测试2: 版本号正确显示"""
        response = self.client.get('/')
        self.assertIn(b'v1.6.0', response.data)
        print("✓ 测试2通过: 版本号正确显示")
    
    def test_03_chart_section_exists(self):
        """测试3: 图表区域存在"""
        response = self.client.get('/')
        self.assertIn(b'chart-section', response.data)
        self.assertIn(b'chart-container', response.data)
        print("✓ 测试3通过: 图表区域存在")
    
    def test_04_table_section_exists(self):
        """测试4: 表格区域存在"""
        response = self.client.get('/')
        self.assertIn(b'table-section', response.data)
        self.assertIn(b'data-table', response.data)
        print("✓ 测试4通过: 表格区域存在")
    
    def test_05_modal_exists(self):
        """测试5: 自定义画图模态框存在"""
        response = self.client.get('/')
        self.assertIn(b'chartModal', response.data)
        self.assertIn(b'modalChartContainer', response.data)
        print("✓ 测试5通过: 自定义画图模态框存在")


class TestLayoutRatio(unittest.TestCase):
    """布局比例测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_06_chart_flex_ratio(self):
        """测试6: 图表区域flex比例为45"""
        response = self.client.get('/')
        # 检查CSS中chart-section的flex值
        self.assertIn(b'.chart-section', response.data)
        self.assertIn(b'flex: 45', response.data)
        print("✓ 测试6通过: 图表区域flex比例正确(45)")
    
    def test_07_table_flex_ratio(self):
        """测试7: 表格区域flex比例为55"""
        response = self.client.get('/')
        self.assertIn(b'.table-section', response.data)
        self.assertIn(b'flex: 55', response.data)
        print("✓ 测试7通过: 表格区域flex比例正确(55)")
    
    def test_08_chart_min_height(self):
        """测试8: 图表区域最小高度"""
        response = self.client.get('/')
        self.assertIn(b'min-height: 350px', response.data)
        print("✓ 测试8通过: 图表区域最小高度正确")


class TestModalFunctionality(unittest.TestCase):
    """模态框功能测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_09_column_checkboxes_exist(self):
        """测试9: 列选择复选框存在"""
        response = self.client.get('/')
        self.assertIn(b'columnCheckboxes', response.data)
        self.assertIn(b'rightAxisCheckboxes', response.data)
        print("✓ 测试9通过: 列选择复选框存在")
    
    def test_10_dual_yaxis_config(self):
        """测试10: 双Y轴配置存在"""
        response = self.client.get('/')
        self.assertIn(b'leftCols', response.data)
        self.assertIn(b'rightCols', response.data)
        print("✓ 测试10通过: 双Y轴配置存在")
    
    def test_11_modal_chart_functions(self):
        """测试11: 模态框图表函数存在"""
        response = self.client.get('/')
        self.assertIn(b'buildModalBarChartOption', response.data)
        self.assertIn(b'buildModalTickChartOption', response.data)
        self.assertIn(b'buildModalBidAskChartOption', response.data)
        print("✓ 测试11通过: 模态框图表函数存在")
    
    def test_12_apply_to_main_chart(self):
        """测试12: 应用到主图功能存在"""
        response = self.client.get('/')
        self.assertIn(b'applyToMainChart', response.data)
        self.assertIn(b'应用到主图', response.data)
        print("✓ 测试12通过: 应用到主图功能存在")


class TestSmartTimeFormat(unittest.TestCase):
    """智能时间格式测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_13_smart_time_format_function(self):
        """测试13: 智能时间格式函数存在"""
        response = self.client.get('/')
        self.assertIn(b'getSmartTimeFormat', response.data)
        print("✓ 测试13通过: 智能时间格式函数存在")
    
    def test_14_format_timestamp_function(self):
        """测试14: 时间戳格式化函数存在"""
        response = self.client.get('/')
        self.assertIn(b'formatTimestamp', response.data)
        print("✓ 测试14通过: 时间戳格式化函数存在")
    
    def test_15_xaxis_rotate(self):
        """测试15: X轴标签旋转配置"""
        response = self.client.get('/')
        self.assertIn(b'rotate: 45', response.data)
        print("✓ 测试15通过: X轴标签旋转配置正确")


class TestAPIEndpoints(unittest.TestCase):
    """API端点测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_16_status_api(self):
        """测试16: 状态API"""
        self.mock_explorer.get_status.return_value = {'connected': False}
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        print("✓ 测试16通过: 状态API正常")
    
    def test_17_fulldata_api_exists(self):
        """测试17: 完整数据API存在"""
        response = self.client.get('/')
        self.assertIn(b'/api/fulldata', response.data)
        print("✓ 测试17通过: 完整数据API存在")
    
    def test_18_fulldata_api_post(self):
        """测试18: 完整数据API POST请求"""
        self.mock_explorer._cache = {}
        response = self.client.post('/api/fulldata', 
                                    data=json.dumps({'cache_key': 'test'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])  # 缓存不存在
        print("✓ 测试18通过: 完整数据API POST正常")


class TestChartOptions(unittest.TestCase):
    """图表配置测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_19_datazoom_config(self):
        """测试19: DataZoom配置正确"""
        response = self.client.get('/')
        self.assertIn(b'dataZoom', response.data)
        self.assertIn(b"type: 'slider'", response.data)
        self.assertIn(b"type: 'inside'", response.data)
        print("✓ 测试19通过: DataZoom配置正确")
    
    def test_20_grid_bottom_spacing(self):
        """测试20: Grid底部间距"""
        response = self.client.get('/')
        self.assertIn(b'bottom: 80', response.data)
        print("✓ 测试20通过: Grid底部间距正确")
    
    def test_21_legend_config(self):
        """测试21: 图例配置"""
        response = self.client.get('/')
        self.assertIn(b'legend:', response.data)
        print("✓ 测试21通过: 图例配置存在")


class TestDataTypeSupport(unittest.TestCase):
    """数据类型支持测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_22_bar_data_support(self):
        """测试22: Bar数据类型支持"""
        response = self.client.get('/')
        self.assertIn(b"currentDataType === 'bar'", response.data)
        print("✓ 测试22通过: Bar数据类型支持")
    
    def test_23_tick_data_support(self):
        """测试23: Tick数据类型支持"""
        response = self.client.get('/')
        self.assertIn(b"currentDataType === 'tick'", response.data)
        print("✓ 测试23通过: Tick数据类型支持")
    
    def test_24_bidask_data_support(self):
        """测试24: BidAsk数据类型支持"""
        response = self.client.get('/')
        self.assertIn(b"currentDataType === 'bidask'", response.data)
        print("✓ 测试24通过: BidAsk数据类型支持")


class TestUIComponents(unittest.TestCase):
    """UI组件测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.mock_explorer = MagicMock()
        cls.app = create_app(cls.mock_explorer)
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_25_color_pickers(self):
        """测试25: 颜色选择器"""
        response = self.client.get('/')
        self.assertIn(b'colorUp', response.data)
        self.assertIn(b'colorDown', response.data)
        print("✓ 测试25通过: 颜色选择器存在")
    
    def test_26_line_width_selector(self):
        """测试26: 线宽选择器"""
        response = self.client.get('/')
        self.assertIn(b'lineWidth', response.data)
        print("✓ 测试26通过: 线宽选择器存在")
    
    def test_27_time_range_inputs(self):
        """测试27: 时间范围输入"""
        response = self.client.get('/')
        self.assertIn(b'chartStartTime', response.data)
        self.assertIn(b'chartEndTime', response.data)
        print("✓ 测试27通过: 时间范围输入存在")
    
    def test_28_ma_checkbox(self):
        """测试28: 均线复选框"""
        response = self.client.get('/')
        self.assertIn(b'showMA', response.data)
        print("✓ 测试28通过: 均线复选框存在")
    
    def test_29_chart_type_selector(self):
        """测试29: 图表类型选择器"""
        response = self.client.get('/')
        self.assertIn(b'modalChartType', response.data)
        print("✓ 测试29通过: 图表类型选择器存在")
    
    def test_30_log_panel(self):
        """测试30: 日志面板"""
        response = self.client.get('/')
        self.assertIn(b'logPanel', response.data)
        self.assertIn(b'addLog', response.data)
        print("✓ 测试30通过: 日志面板存在")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Bloomberg 数据工具箱 Web App 测试")
    print("="*60 + "\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestWebAppBasic,
        TestLayoutRatio,
        TestModalFunctionality,
        TestSmartTimeFormat,
        TestAPIEndpoints,
        TestChartOptions,
        TestDataTypeSupport,
        TestUIComponents
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "="*60)
    print(f"测试总结:")
    print(f"  运行: {result.testsRun}")
    print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    print("="*60)
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n出错的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
