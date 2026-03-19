"""
Download JPYCNH data using same method as USDCNH
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
from quant_system.tools.data_explorer import DataExplorer

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def main():
    print("=" * 60)
    print("Download JPYCNH using DataExplorer")
    print("=" * 60)
    
    explorer = DataExplorer()
    
    # Use same parameters as the USDCNH file (about 6 months)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=200)
    
    print(f"\nParameters:")
    print(f"  Symbol: JPYCNH Curncy")
    print(f"  Start: {start_time.strftime('%Y-%m-%dT%H:%M')}")
    print(f"  End: {end_time.strftime('%Y-%m-%dT%H:%M')}")
    print(f"  Resample: 1s")
    
    result = explorer.download_bid_ask(
        symbol="JPYCNH Curncy",
        resample="1s",
        start_time=start_time.strftime("%Y-%m-%dT%H:%M"),
        end_time=end_time.strftime("%Y-%m-%dT%H:%M"),
        timezone="Asia/Shanghai"
    )
    
    print(f"\nResult: {result.get('success')}")
    print(f"Message: {result.get('message')}")
    
    if result.get('success'):
        data_info = result.get('data', {})
        print(f"Rows: {data_info.get('rows')}")
        print(f"Time range: {data_info.get('start')} ~ {data_info.get('end')}")
        
        # Get the dataframe from cache
        cache_key = result.get('cache_key')
        if cache_key and cache_key in explorer._cache:
            df = explorer._cache[cache_key]
            
            # Check Saturday data
            df['weekday'] = df.index.dayofweek
            df['hour'] = df.index.hour
            sat_data = df[(df['weekday'] == 5) & (df['hour'] < 6)]
            
            print(f"\nSaturday 00-06 data: {len(sat_data)} rows")
            
            if not sat_data.empty:
                sat_data = sat_data.copy()
                sat_data['date'] = sat_data.index.date
                unique_sats = sat_data['date'].unique()
                print(f"Saturday dates: {len(unique_sats)}")
                
                for d in sorted(unique_sats)[:5]:
                    day_df = sat_data[sat_data['date'] == d]
                    print(f"  {d}: {len(day_df)} rows, ask range: {day_df['ask'].min():.4f} ~ {day_df['ask'].max():.4f}")
            
            # Save to file
            output_file = OUTPUT_DIR / f"JPYCNH_Curncy_bidask_1s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df_save = df.reset_index()
            df_save = df_save.drop(columns=['weekday', 'hour'], errors='ignore')
            
            # Check file size
            if len(df_save) > 1000000:
                print(f"\n[WARN] Data too large ({len(df_save)} rows), saving Saturday data only")
                sat_only = df[(df['weekday'] == 5) & (df['hour'] < 6)].reset_index()
                sat_only = sat_only.drop(columns=['weekday', 'hour'], errors='ignore')
                output_file = OUTPUT_DIR / f"JPYCNH_Curncy_bidask_1s_saturday_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                sat_only.to_excel(output_file, index=False)
                print(f"[SAVED] {output_file.name}")
            else:
                df_save.to_excel(output_file, index=False)
                print(f"\n[SAVED] {output_file.name}")
    
    print("\n[DONE]")


if __name__ == "__main__":
    main()
