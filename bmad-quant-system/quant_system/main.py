"""
BMAD量化系统 - 主程序
运行USDCNH周五夜盘策略回测
"""
import logging
from datetime import datetime, timedelta
import pandas as pd
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_bloomberg_backtest():
    """使用Bloomberg数据运行回测"""
    from quant_system import (
        BloombergDataSource, BacktestEngine, 
        FridayNightStrategy, PerformanceAnalyzer, QuantVisualizer
    )
    
    print("=" * 60)
    print("BMAD量化系统 - USDCNH周五夜盘策略回测")
    print("=" * 60)
    
    # ========== 1. 连接Bloomberg数据源 ==========
    print("\n[1] 连接Bloomberg API...")
    bbg = BloombergDataSource(host="localhost", port=8194)
    
    if not bbg.connect():
        print("错误: Bloomberg连接失败!")
        print("请确保:")
        print("  1. Bloomberg Terminal已启动")
        print("  2. API已启用 (SAPI <GO>)")
        print("  3. blpapi已安装 (pip install blpapi)")
        return None
    
    print("Bloomberg连接成功!")
    
    # ========== 2. 获取历史数据 ==========
    print("\n[2] 获取USDCNH历史数据...")
    
    # 设置回测区间 (最近2年)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2年
    
    symbol = "USDCNH Curncy"
    
    try:
        data = bbg.get_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            frequency="1D"
        )
        
        if data.empty:
            print(f"错误: 未获取到{symbol}数据")
            bbg.disconnect()
            return None
        
        print(f"获取数据成功: {len(data)}条")
        print(f"数据区间: {data.index[0]} ~ {data.index[-1]}")
        print(f"\n数据预览:")
        print(data.head())
        
    except Exception as e:
        print(f"获取数据失败: {e}")
        bbg.disconnect()
        return None
    
    # ========== 3. 创建回测引擎 ==========
    print("\n[3] 初始化回测引擎...")
    
    engine = BacktestEngine(
        initial_capital=1000000,  # 100万初始资金
        commission_rate=0.00005,  # 万分之0.5手续费
        slippage=0.0001           # 万分之1滑点
    )
    
    # 添加数据
    engine.add_data("USDCNH", data)
    
    # ========== 4. 创建策略 ==========
    print("\n[4] 配置周五夜盘策略...")
    
    strategy = FridayNightStrategy(
        entry_day=4,        # 周五
        entry_hour=21,      # 21:00
        exit_hour=2,        # 02:00 (周六凌晨)
        position_size=100000  # 每次交易10万美元
    )
    
    engine.add_strategy(strategy)
    
    print("策略配置:")
    print(f"  入场: 每周五 21:00")
    print(f"  出场: 周六凌晨 02:00 (日线数据用周一开盘代替)")
    print(f"  仓位: {strategy.position_size:,} USD")
    
    # ========== 5. 运行回测 ==========
    print("\n[5] 运行回测...")
    
    results = engine.run()
    
    # ========== 6. 绩效分析 ==========
    print("\n[6] 绩效分析...")
    
    equity_curve = results['equity_curve']
    trades = results['trades']
    
    analyzer = PerformanceAnalyzer(
        equity_curve=equity_curve,
        trades=trades,
        initial_capital=1000000
    )
    
    # 打印绩效报告
    print(analyzer.generate_report())
    
    # ========== 7. 可视化 ==========
    print("\n[7] 生成可视化图表...")
    
    visualizer = QuantVisualizer()
    
    # 创建综合仪表板
    fig = visualizer.create_dashboard(
        results=results,
        price_data=data,
        symbol="USDCNH",
        save_path="backtest_dashboard.png"
    )
    
    # 显示图表
    if fig:
        visualizer.show()
    
    # ========== 8. 断开连接 ==========
    bbg.disconnect()
    print("\n回测完成!")
    
    return results


def run_excel_backtest(excel_path: str):
    """使用Excel数据运行回测"""
    from quant_system import (
        ExcelDataSource, BacktestEngine,
        FridayNightStrategy, PerformanceAnalyzer, QuantVisualizer
    )
    
    print("=" * 60)
    print("BMAD量化系统 - Excel数据回测")
    print("=" * 60)
    
    # 连接Excel数据源
    print(f"\n[1] 读取Excel文件: {excel_path}")
    excel = ExcelDataSource(excel_path)
    
    if not excel.connect():
        print("错误: Excel文件读取失败!")
        return None
    
    # 列出可用的sheet
    symbols = excel.list_symbols()
    print(f"可用数据: {symbols}")
    
    if not symbols:
        print("错误: Excel文件中没有数据sheet")
        return None
    
    symbol = symbols[0]  # 使用第一个sheet
    
    # 获取数据
    print(f"\n[2] 获取{symbol}数据...")
    data = excel.get_historical_data(
        symbol=symbol,
        start_date=datetime(2020, 1, 1),
        end_date=datetime.now()
    )
    
    if data.empty:
        print("错误: 未获取到数据")
        return None
    
    print(f"获取数据成功: {len(data)}条")
    
    # 创建回测引擎
    print("\n[3] 初始化回测引擎...")
    engine = BacktestEngine(initial_capital=1000000)
    engine.add_data(symbol, data)
    
    # 添加策略
    strategy = FridayNightStrategy()
    engine.add_strategy(strategy)
    
    # 运行回测
    print("\n[4] 运行回测...")
    results = engine.run()
    
    # 绩效分析
    print("\n[5] 绩效分析...")
    analyzer = PerformanceAnalyzer(
        equity_curve=results['equity_curve'],
        trades=results['trades'],
        initial_capital=1000000
    )
    print(analyzer.generate_report())
    
    # 可视化
    visualizer = QuantVisualizer()
    visualizer.create_dashboard(
        results=results,
        price_data=data,
        symbol=symbol,
        save_path="backtest_dashboard.png"
    )
    visualizer.show()
    
    excel.disconnect()
    return results


def run_demo_backtest():
    """使用模拟数据运行演示回测"""
    from quant_system import (
        BacktestEngine, FridayNightStrategy, 
        PerformanceAnalyzer, QuantVisualizer
    )
    import numpy as np
    
    print("=" * 60)
    print("BMAD量化系统 - 演示回测 (模拟数据)")
    print("=" * 60)
    
    # 生成模拟USDCNH数据
    print("\n[1] 生成模拟数据...")
    
    np.random.seed(42)
    
    # 生成2年的日线数据
    dates = pd.date_range(start='2024-01-01', end='2025-12-31', freq='B')  # 工作日
    n = len(dates)
    
    # 模拟USDCNH价格 (起始价7.2，有趋势和波动)
    base_price = 7.2
    trend = np.linspace(0, 0.3, n)  # 缓慢上涨趋势
    noise = np.cumsum(np.random.randn(n) * 0.01)  # 随机游走
    
    close_prices = base_price + trend + noise
    
    # 生成OHLC
    data = pd.DataFrame({
        'open': close_prices + np.random.randn(n) * 0.005,
        'high': close_prices + np.abs(np.random.randn(n) * 0.01),
        'low': close_prices - np.abs(np.random.randn(n) * 0.01),
        'close': close_prices,
        'volume': np.random.randint(1000000, 5000000, n)
    }, index=dates)
    
    print(f"生成数据: {len(data)}条")
    print(f"数据区间: {data.index[0].date()} ~ {data.index[-1].date()}")
    print(f"\n数据预览:")
    print(data.head())
    
    # 创建回测引擎
    print("\n[2] 初始化回测引擎...")
    engine = BacktestEngine(
        initial_capital=1000000,
        commission_rate=0.00005,
        slippage=0.0001
    )
    engine.add_data("USDCNH", data)
    
    # 添加策略
    print("\n[3] 配置周五夜盘策略...")
    strategy = FridayNightStrategy(
        entry_day=4,
        entry_hour=21,
        exit_hour=2,
        position_size=100000
    )
    engine.add_strategy(strategy)
    
    # 运行回测
    print("\n[4] 运行回测...")
    results = engine.run()
    
    # 绩效分析
    print("\n[5] 绩效分析...")
    analyzer = PerformanceAnalyzer(
        equity_curve=results['equity_curve'],
        trades=results['trades'],
        initial_capital=1000000
    )
    print(analyzer.generate_report())
    
    # 可视化
    print("\n[6] 生成可视化...")
    visualizer = QuantVisualizer()
    visualizer.create_dashboard(
        results=results,
        price_data=data,
        symbol="USDCNH (模拟)",
        save_path="demo_backtest_dashboard.png"
    )
    visualizer.show()
    
    return results


if __name__ == "__main__":
    print("\nBMAD量化交易系统")
    print("-" * 40)
    print("请选择运行模式:")
    print("  1. Bloomberg数据回测 (需要Bloomberg Terminal)")
    print("  2. Excel数据回测")
    print("  3. 演示回测 (模拟数据)")
    print("-" * 40)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = input("请输入选项 (1/2/3): ").strip()
    
    if mode == "1":
        run_bloomberg_backtest()
    elif mode == "2":
        excel_path = input("请输入Excel文件路径: ").strip()
        if excel_path:
            run_excel_backtest(excel_path)
        else:
            print("未输入文件路径")
    elif mode == "3":
        run_demo_backtest()
    else:
        print("无效选项，运行演示模式...")
        run_demo_backtest()
