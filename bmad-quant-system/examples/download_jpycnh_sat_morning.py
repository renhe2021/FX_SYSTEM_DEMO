"""
Download JPYCNH Saturday early morning data (00:00 ~ 06:00)
Using the same approach as USDCNH
"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
from quant_system.tools.bbg_wrapper import BloombergWrapper
import pandas as pd

def main():
    print("="*60)
    print("Downloading JPYCNH Saturday data (00:00~06:00)")
    print("="*60)
    
    bbg = BloombergWrapper()
    if not bbg.connect():
        print("Failed to connect to Bloomberg")
        return
    
    # Download 6 months of data
    end_date = datetime.now()
    start_date = datetime(2025, 7, 1)
    
    print(f"\nDate range: {start_date} ~ {end_date}")
    print("Downloading bid/ask bars with 1min resample...")
    
    # Use get_bid_ask_bars with 1min resample
    df = bbg.get_bid_ask_bars(
        symbol="JPYCNH Curncy",
        start_date=start_date,
        end_date=end_date,
        resample="1min"
    )
    
    if df is None or df.empty:
        print("No data returned!")
        return
    
    print(f"\nTotal rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Add time info
    df = df.reset_index()
    df['weekday'] = df['timestamp'].dt.dayofweek
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    
    # Check Saturday data
    sat_df = df[df['weekday'] == 5]
    print(f"\nSaturday rows: {len(sat_df)}")
    
    if len(sat_df) > 0:
        print("\nSaturday data by hour:")
        for hour in range(8):
            hour_df = sat_df[sat_df['hour'] == hour]
            if len(hour_df) > 0:
                unique = hour_df['bid'].nunique()
                bid_range = hour_df['bid'].max() - hour_df['bid'].min()
                print(f"  Hour {hour:02d}: {len(hour_df)} rows, unique_prices={unique}, bid_range={bid_range:.6f}")
        
        # Save to Excel
        output_file = f"c:/Users/tencentren/CodeBuddy/FX_SYSTEM/bmad-quant-system/output/JPYCNH_Curncy_bidask_1min_saturday_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\nSaved to: {output_file}")
    else:
        # Maybe need to filter to only Saturday 00:00-06:00
        print("\nNo Saturday data found. Checking raw tick data...")
        
        # Try raw tick data
        tick_df = bbg.get_bid_ask(
            symbol="JPYCNH Curncy",
            start_date=start_date,
            end_date=end_date
        )
        
        if tick_df is not None and not tick_df.empty:
            tick_df = tick_df.reset_index()
            tick_df['weekday'] = tick_df['timestamp'].dt.dayofweek
            sat_ticks = tick_df[tick_df['weekday'] == 5]
            print(f"Saturday ticks: {len(sat_ticks)}")
    
    bbg.disconnect()

if __name__ == "__main__":
    main()
