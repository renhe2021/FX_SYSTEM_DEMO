"""
Download JPYCNH Bid/Ask Bar Data (10s interval)
For weekend pricing analysis
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
    Download JPYCNH Bid/Ask Bar Data
    """
    print("=" * 60)
    print("Download JPYCNH Bid/Ask Bar Data")
    print("=" * 60)
    
    # Initialize Bloomberg
    bbg = BloombergWrapper()
    
    # Set time range - download as much historical data as possible
    end_date = datetime.now()
    start_date = end_date - timedelta(days=140)  # Bloomberg Bar data usually supports 140 days history
    
    print(f"\nTime range: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"Currency pair: JPYCNH Curncy")
    print(f"Bar interval: 10 seconds")
    
    # Download data
    print("\nDownloading...")
    
    try:
        df = bbg.get_bid_ask_bars(
            symbol="JPYCNH Curncy",  # 正确的参数名是 symbol
            start_date=start_date,
            end_date=end_date,
            resample="10s"  # 10秒 bar，用 resample 参数
        )
        
        if df is not None and not df.empty:
            print(f"\n[OK] Download successful! Total {len(df)} records")
            print(f"     Time range: {df.index.min()} ~ {df.index.max()}")
            
            # Check Saturday data
            df['weekday'] = df.index.dayofweek
            sat_data = df[df['weekday'] == 5]  # 5 = Saturday
            
            print(f"\n[STATS] Saturday data:")
            print(f"   Saturday records: {len(sat_data)}")
            
            if not sat_data.empty:
                # Analyze Saturday hour distribution
                sat_data_copy = sat_data.copy()
                sat_data_copy['hour'] = sat_data_copy.index.hour
                hour_counts = sat_data_copy.groupby('hour').size()
                print(f"   Saturday hour distribution:")
                for hour, count in hour_counts.items():
                    print(f"      {hour:02d}:00 ~ {hour:02d}:59: {count} records")
                
                # Count unique Saturdays
                sat_dates = sat_data.index.date
                unique_sat_dates = pd.unique(sat_dates)
                print(f"   Number of Saturdays: {len(unique_sat_dates)}")
                print(f"   Saturday dates: {[str(d) for d in unique_sat_dates]}")
            
            # Save to file
            output_file = OUTPUT_DIR / f"JPYCNH_Curncy_bidask_10s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Reset index for saving
            df_save = df.reset_index()
            df_save = df_save.drop(columns=['weekday'], errors='ignore')
            df_save.to_excel(output_file, index=False)
            
            print(f"\n[SAVED] Data saved: {output_file.name}")
            
            return df
        else:
            print("\n[FAIL] No data received")
            return None
            
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_with_weekly_chunks():
    """
    Download data week by week to get more Saturday data
    """
    print("\n" + "=" * 60)
    print("Download JPYCNH data week by week")
    print("=" * 60)
    
    bbg = BloombergWrapper()
    
    all_data = []
    end_date = datetime.now()
    
    # Download past 20 weeks
    for week in range(20):
        week_end = end_date - timedelta(weeks=week)
        week_start = week_end - timedelta(days=7)
        
        print(f"\nDownloading week {week+1}: {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}...", end=" ")
        
        try:
            df = bbg.get_bid_ask_bars(
                symbol="JPYCNH Curncy",
                start_date=week_start,
                end_date=week_end,
                resample="10s"
            )
            
            if df is not None and not df.empty:
                # Filter Saturday 00:00-06:00 data
                sat_data = df[(df.index.dayofweek == 5) & (df.index.hour < 6)]
                if not sat_data.empty:
                    print(f"[OK] {len(sat_data)} Saturday records")
                    all_data.append(sat_data)
                else:
                    # Also keep all data for reference
                    print(f"[OK] {len(df)} records (no Saturday 00-06 data)")
                    all_data.append(df)
            else:
                print("[EMPTY]")
        except Exception as e:
            print(f"[ERROR] {e}")
    
    if all_data:
        combined = pd.concat(all_data)
        combined = combined.sort_index()
        combined = combined[~combined.index.duplicated(keep='first')]
        
        # Show Saturday stats
        sat_only = combined[(combined.index.dayofweek == 5) & (combined.index.hour < 6)]
        print(f"\n[SUMMARY]")
        print(f"   Total records: {len(combined)}")
        print(f"   Saturday 00-06 records: {len(sat_only)}")
        
        if not sat_only.empty:
            unique_sats = pd.unique(sat_only.index.date)
            print(f"   Number of Saturdays with data: {len(unique_sats)}")
        
        # Save
        output_file = OUTPUT_DIR / f"JPYCNH_Curncy_bidask_10s_weekly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        combined.reset_index().to_excel(output_file, index=False)
        print(f"[SAVED] {output_file.name}")
        
        return combined
    
    return None


if __name__ == "__main__":
    # Method 1: Download all at once
    df = download_jpycnh_bars()
    
    # Check if we got enough Saturday data
    if df is not None:
        sat_data = df[(df.index.dayofweek == 5) & (df.index.hour < 6)]
        if len(sat_data) < 1000:
            print("\n\nNot enough Saturday 00-06 data, trying weekly download...")
            download_with_weekly_chunks()
    else:
        print("\n\nTrying weekly download...")
        download_with_weekly_chunks()
