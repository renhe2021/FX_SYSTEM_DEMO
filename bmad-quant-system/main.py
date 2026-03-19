#!/usr/bin/env python
"""BMAD 量化交易系统 - 主入口

快速开始:
    # 运行回测
    python main.py backtest --data usdcnh_intraday.csv
    
    # 数据探索
    python main.py explore usdcnh_intraday.csv
    
    # 启动Web界面
    python main.py web
"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def cmd_backtest(args):
    """运行回测"""
    from bmad import BacktestEngine, FridayNightStrategy, DataLoader
    
    print("=" * 60)
    print("BMAD 回测系统")
    print("=" * 60)
    
    # 加载数据
    data_path = ROOT / args.data
    if not data_path.exists():
        print(f"文件不存在: {data_path}")
        return
    
    print(f"\n加载数据: {data_path}")
    data = DataLoader.load_csv(str(data_path))
    print(f"数据量: {len(data)} 行")
    
    # 创建引擎
    engine = BacktestEngine(
        initial_capital=args.capital,
        commission_rate=0.00005,
        slippage=0.0001
    )
    
    engine.add_data('USDCNH', data)
    engine.add_strategy(FridayNightStrategy(
        entry_day=4, entry_hour=21,
        exit_day=5, exit_hour=2,
        position_size=100000
    ))
    
    # 运行
    results = engine.run()
    
    print("\n回测结果:")
    for k, v in results['summary'].items():
        print(f"  {k}: {v}")


def cmd_explore(args):
    """数据探索"""
    from tools import DataExplorer
    
    explorer = DataExplorer()
    explorer.load(args.file)
    explorer.summary()
    
    if args.plot:
        explorer.plot()


def cmd_web(args):
    """启动Web界面"""
    print("启动Web界面...")
    print("功能开发中...")


def main():
    parser = argparse.ArgumentParser(
        description='BMAD 量化交易系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py backtest --data usdcnh_intraday.csv
  python main.py explore usdcnh_intraday.csv --plot
  python main.py web
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # backtest 命令
    p_backtest = subparsers.add_parser('backtest', help='运行回测')
    p_backtest.add_argument('--data', required=True, help='数据文件')
    p_backtest.add_argument('--capital', type=float, default=1000000, help='初始资金')
    p_backtest.set_defaults(func=cmd_backtest)
    
    # explore 命令
    p_explore = subparsers.add_parser('explore', help='数据探索')
    p_explore.add_argument('file', help='数据文件')
    p_explore.add_argument('--plot', action='store_true', help='绘图')
    p_explore.set_defaults(func=cmd_explore)
    
    # web 命令
    p_web = subparsers.add_parser('web', help='启动Web界面')
    p_web.add_argument('--port', type=int, default=8080, help='端口')
    p_web.set_defaults(func=cmd_web)
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
