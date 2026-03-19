"""
Download JPYCNH weekend data (Friday 16:00 ~ Saturday 00:00 UTC)
This is Beijing Saturday 00:00 ~ 08:00
"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
from quant_system.tools.bbg_wrapper import BloombergWrapper
import pandas as pd

def main():
    print("="*60)
    print("Downloading JPYCNH weekend data")
    print("="*60)
    
    bbg = BloombergWrapper()
    if not bbg.connect():
        print("Failed to connect to Bloomberg")
        return
    
    # Download 6 months of data - using UTC time
    # Beijing Saturday 00:00 = UTC Friday 16:00
    # Beijing Saturday 06:00 = UTC Friday 22:00
    
    # We want data from July 2025 to now
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
        bbg.disconnect()
        return
    
    print(f"\nTotal rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Reset index to get timestamp as column
    df = df.reset_index()
    
    # Convert UTC to Beijing time (+8 hours)
    df['timestamp_beijing'] = df['timestamp'] + pd.Timedelta(hours=8)
    df['weekday_beijing'] = df['timestamp_beijing'].dt.dayofweek
    df['date_beijing'] = df['timestamp_beijing'].dt.date
    df['hour_beijing'] = df['timestamp_beijing'].dt.hour
    
    # Filter for Saturday Beijing time (which is Friday-Saturday UTC)
    sat_df = df[df['weekday_beijing'] == 5]
    print(f"\nSaturday (Beijing time) rows: {len(sat_df)}")
    
    if len(sat_df) > 0:
        print("\nSaturday data by hour (Beijing time):")
        for hour in range(8):
            hour_df = sat_df[sat_df['hour_beijing'] == hour]
            if len(hour_df) > 0:
                unique = hour_df['bid'].nunique()
                bid_range = hour_df['bid'].max() - hour_df['bid'].min()
                print(f"  Hour {hour:02d}: {len(hour_df)} rows, unique_prices={unique}, bid_range={bid_range:.6f}")
        
        print("\nSample Saturday data (first 5 Saturdays):")
        for d in sorted(sat_df['date_beijing'].unique())[:5]:
            day_df = sat_df[sat_df['date_beijing'] == d]
            first_time = day_df['timestamp_beijing'].min().strftime('%H:%M')
            last_time = day_df['timestamp_beijing'].max().strftime('%H:%M')
            unique = day_df['bid'].nunique()
            bid_range = day_df['bid'].max() - day_df['bid'].min()
            print(f"  {d}: {first_time}~{last_time}, unique_prices={unique}, bid_range={bid_range:.6f}")
    
    # Save to Excel with Beijing timestamps
    output_df = df[['timestamp_beijing', 'bid', 'ask', 'spread', 'mid']].copy()
    output_df.columns = ['timestamp', 'bid', 'ask', 'spread', 'mid']
    
    output_file = f"c:/Users/tencentren/CodeBuddy/FX_SYSTEM/bmad-quant-system/output/JPYCNH_Curncy_bidask_1min_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_df.to_excel(output_file, index=False)
    print(f"\nSaved to: {output_file}")
    
    bbg.disconnect()

if __name__ == "__main__":
    main()
