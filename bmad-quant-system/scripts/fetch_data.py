#!/usr/bin/env python
"""数据获取脚本

从Bloomberg获取数据并保存
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def fetch_from_bloomberg(symbol: str, days_back: int = 365):
    """从Bloomberg获取数据"""
    from bmad.data import BloombergDataSource
    
    print(f"连接Bloomberg...")
    bbg = BloombergDataSource()
    
    if not bbg.connect():
        print("Bloomberg连接失败")
        print("请确保:")
        print("  1. Bloomberg Terminal已启动")
        print("  2. 在Terminal中输入 SAPI <GO> 启用API")
        return None
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        print(f"获取 {symbol} 数据...")
        print(f"时间范围: {start_date.date()} ~ {end_date.date()}")
        
        data = bbg.get_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            frequency="1D"
        )
        
        if not data.empty:
            # 保存数据
            output_dir = ROOT / 'data' / 'raw'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{symbol.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
            output_path = output_dir / filename
            
            data.to_csv(output_path)
            print(f"✓ 数据已保存: {output_path}")
            print(f"  共 {len(data)} 条记录")
            
            return data
        else:
            print("未获取到数据")
            return None
            
    finally:
        bbg.disconnect()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='获取市场数据')
    parser.add_argument('--symbol', default='USDCNH Curncy', help='品种代码')
    parser.add_argument('--days', type=int, default=365, help='获取天数')
    parser.add_argument('--source', default='bloomberg', 
                        choices=['bloomberg'], help='数据源')
    args = parser.parse_args()
    
    print("=" * 60)
    print("数据获取工具")
    print("=" * 60)
    
    if args.source == 'bloomberg':
        fetch_from_bloomberg(args.symbol, args.days)


if __name__ == '__main__':
    main()
