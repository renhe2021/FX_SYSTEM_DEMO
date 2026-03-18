"""
下载 JPYCNH 的 Bid/Ask Bar 数据（10秒间隔）
用于周末定价分析
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
from quant_system.tools.bbg_wrapper import BloombergWrapper

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def download_jpycnh_bars():
    """
    下载 JPYCNH Bid/Ask Bar 数据
    """
    print("=" * 60)
    print("下载 JPYCNH Bid/Ask Bar 数据")
    print("=" * 60)
    
    # 初始化 Bloomberg
    bbg = BloombergWrapper()
    
    # 设置时间范围 - 下载尽可能多的历史数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=140)  # Bloomberg Bar 数据通常支持 140 天历史
    
    print(f"\n时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"货币对: JPYCNH Curncy")
    print(f"Bar 间隔: 10 秒")
    
    # 下载数据
    print("\n正在下载...")
    
    try:
        df = bbg.get_bid_ask_bars(
            security="JPYCNH Curncy",
            start_date=start_date,
            end_date=end_date,
            interval=10  # 10秒 bar
        )
        
        if df is not None and not df.empty:
            print(f"\n✅ 下载成功！共 {len(df)} 条数据")
            print(f"   时间范围: {df.index.min()} ~ {df.index.max()}")
            
            # 检查周六数据
            df['weekday'] = df.index.dayofweek
            sat_data = df[df['weekday'] == 5]  # 5 = Saturday
            
            print(f"\n📊 周六数据统计:")
            print(f"   周六数据条数: {len(sat_data)}")
            
            if not sat_data.empty:
                # 分析周六的小时分布
                sat_data_copy = sat_data.copy()
                sat_data_copy['hour'] = sat_data_copy.index.hour
                hour_counts = sat_data_copy.groupby('hour').size()
                print(f"   周六小时分布:")
                for hour, count in hour_counts.items():
                    print(f"      {hour:02d}:00 ~ {hour:02d}:59: {count} 条")
                
                # 计算有多少个完整的周六
                sat_dates = sat_data.index.date
                unique_sat_dates = pd.unique(sat_dates)
                print(f"   周六天数: {len(unique_sat_dates)}")
            
            # 保存到文件
            output_file = OUTPUT_DIR / f"JPYCNH_Curncy_bidask_10s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # 重置索引以便保存
            df_save = df.reset_index()
            df_save = df_save.drop(columns=['weekday'], errors='ignore')
            df_save.to_excel(output_file, index=False)
            
            print(f"\n💾 数据已保存: {output_file.name}")
            
            return df
        else:
            print("\n❌ 未获取到数据")
            return None
            
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_with_daily_chunks():
    """
    分天下载以获取更完整的数据
    """
    print("\n" + "=" * 60)
    print("尝试分天下载 JPYCNH 数据")
    print("=" * 60)
    
    bbg = BloombergWrapper()
    
    all_data = []
    end_date = datetime.now()
    
    # 收集所有周六日期
    saturdays = []
    current = end_date
    for _ in range(52):  # 最多查找52周
        # 找到这周的周六
        days_until_saturday = (5 - current.weekday()) % 7
        if days_until_saturday == 0 and current.weekday() != 5:
            days_until_saturday = 7
        saturday = current - timedelta(days=current.weekday() - 5 if current.weekday() >= 5 else current.weekday() + 2)
        
        if saturday not in saturdays:
            saturdays.append(saturday.replace(hour=0, minute=0, second=0, microsecond=0))
        
        current -= timedelta(days=7)
    
    saturdays = sorted(saturdays, reverse=True)[:20]  # 只取最近20周
    
    print(f"\n将下载以下周六的数据 (00:00-06:00 北京时间):")
    for sat in saturdays[:5]:
        print(f"   {sat.strftime('%Y-%m-%d')}")
    print(f"   ... 共 {len(saturdays)} 个周六")
    
    success_count = 0
    
    for sat in saturdays:
        start_time = sat.replace(hour=0, minute=0, second=0)
        end_time = sat.replace(hour=6, minute=0, second=0)
        
        print(f"\n下载 {sat.strftime('%Y-%m-%d')} 00:00-06:00...", end=" ")
        
        try:
            df = bbg.get_bid_ask_bars(
                security="JPYCNH Curncy",
                start_date=start_time,
                end_date=end_time,
                interval=10
            )
            
            if df is not None and not df.empty:
                print(f"✅ {len(df)} 条")
                all_data.append(df)
                success_count += 1
            else:
                print("❌ 无数据")
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    if all_data:
        combined = pd.concat(all_data)
        combined = combined.sort_index()
        combined = combined[~combined.index.duplicated(keep='first')]
        
        print(f"\n✅ 共获取 {len(combined)} 条数据, 来自 {success_count} 个周六")
        
        # 保存
        output_file = OUTPUT_DIR / f"JPYCNH_Curncy_bidask_10s_saturdays_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        combined.reset_index().to_excel(output_file, index=False)
        print(f"💾 已保存: {output_file.name}")
        
        return combined
    
    return None


if __name__ == "__main__":
    # 方法1: 整体下载
    df = download_jpycnh_bars()
    
    # 方法2: 如果整体下载效果不好，尝试分天下载周六数据
    if df is None or len(df) < 1000:
        print("\n\n尝试分天下载周六数据...")
        download_with_daily_chunks()
