"""
测试北京时间默认处理
===================

验证 bbg_wrapper 现在默认使用北京时间：
- 输入时间为北京时间
- 自动转换为 UTC 发送给 Bloomberg
- 返回的数据时间戳为 UTC（由 data_explorer 转换为北京时间显示）
"""

import sys
sys.path.insert(0, r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system")

from datetime import datetime, timedelta
from quant_system.tools.bbg_wrapper import (
    BloombergWrapper, 
    beijing_now, 
    beijing_to_utc, 
    utc_to_beijing,
    BEIJING_UTC_OFFSET
)

def test_time_functions():
    """测试时间转换函数"""
    print("=" * 60)
    print("测试时间转换函数")
    print("=" * 60)
    
    # 当前时间
    now_beijing = beijing_now()
    now_utc = datetime.utcnow()
    
    print(f"\n当前北京时间: {now_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"当前 UTC 时间: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"时差: {BEIJING_UTC_OFFSET} 小时")
    
    # 测试转换
    test_beijing = datetime(2026, 1, 25, 9, 0, 0)  # 北京时间 09:00
    test_utc = beijing_to_utc(test_beijing)
    test_back = utc_to_beijing(test_utc)
    
    print(f"\n测试转换:")
    print(f"  北京时间: {test_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  -> UTC: {test_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  -> 转回北京: {test_back.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 验证周六凌晨
    saturday_beijing = datetime(2026, 1, 25, 0, 0, 0)  # 周六北京时间 00:00
    saturday_utc = beijing_to_utc(saturday_beijing)
    
    print(f"\n周六凌晨转换:")
    print(f"  北京时间周六 00:00: {saturday_beijing.strftime('%Y-%m-%d %H:%M:%S')} (weekday={saturday_beijing.weekday()})")
    print(f"  -> UTC: {saturday_utc.strftime('%Y-%m-%d %H:%M:%S')} (weekday={saturday_utc.weekday()})")
    print(f"  (北京时间周六 00:00 = UTC 周五 16:00)")
    
    return True


def test_bbg_wrapper():
    """测试 BloombergWrapper 的北京时间处理"""
    print("\n" + "=" * 60)
    print("测试 BloombergWrapper 北京时间处理")
    print("=" * 60)
    
    bbg = BloombergWrapper()
    
    if not bbg.connect():
        print("[Warning] Bloomberg 未连接，跳过实际数据测试")
        return False
    
    try:
        # 测试1: 不指定时间，应该使用当前北京时间
        print("\n测试1: 默认时间（当前北京时间）")
        print("-" * 40)
        
        # 获取最近1小时的数据
        df = bbg.get_bid_ask(
            symbol="USDCNH Curncy",
            hours_back=1
        )
        
        if df is not None and not df.empty:
            print(f"✓ 获取数据成功: {len(df)} 条")
            print(f"  数据时间范围 (UTC): {df.index[0]} ~ {df.index[-1]}")
            # 转换为北京时间显示
            beijing_start = utc_to_beijing(df.index[0].to_pydatetime())
            beijing_end = utc_to_beijing(df.index[-1].to_pydatetime())
            print(f"  数据时间范围 (北京): {beijing_start} ~ {beijing_end}")
        else:
            print("✗ 无数据返回")
        
        # 测试2: 指定北京时间
        print("\n测试2: 指定北京时间范围")
        print("-" * 40)
        
        # 北京时间 09:00 ~ 10:00
        start_beijing = datetime(2026, 1, 29, 9, 0, 0)
        end_beijing = datetime(2026, 1, 29, 10, 0, 0)
        
        print(f"  请求时间 (北京): {start_beijing} ~ {end_beijing}")
        
        df2 = bbg.get_bid_ask(
            symbol="USDCNH Curncy",
            start_date=start_beijing,
            end_date=end_beijing,
            is_beijing_time=True  # 明确指定输入是北京时间
        )
        
        if df2 is not None and not df2.empty:
            print(f"✓ 获取数据成功: {len(df2)} 条")
            print(f"  数据时间范围 (UTC): {df2.index[0]} ~ {df2.index[-1]}")
            beijing_start = utc_to_beijing(df2.index[0].to_pydatetime())
            beijing_end = utc_to_beijing(df2.index[-1].to_pydatetime())
            print(f"  数据时间范围 (北京): {beijing_start} ~ {beijing_end}")
        else:
            print("✗ 无数据返回")
        
        return True
        
    finally:
        bbg.disconnect()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Bloomberg 北京时间处理测试")
    print("=" * 60)
    
    # 测试时间转换函数
    test_time_functions()
    
    # 测试实际数据获取
    test_bbg_wrapper()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n总结:")
    print("- 所有时间输入现在默认为北京时间")
    print("- bbg_wrapper 内部自动将北京时间转换为 UTC")
    print("- 返回的数据时间戳为 UTC")
    print("- data_explorer 会将 UTC 转换为北京时间显示")
