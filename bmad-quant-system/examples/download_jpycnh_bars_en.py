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
            security="JPYCNH Curncy",
            start_date=start_date,
            end_date=end_date,
            interval=10  # 10s bar
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


def download_with_daily_chunks():
    """
    Download data day by day to get more complete data
    """
    print("\n" + "=" * 60)
    print("Try downloading JPYCNH data day by day")
    print("=" * 60)
    
    bbg = BloombergWrapper()
    
    all_data = []
    end_date = datetime.now()
    
    # Collect all Saturday dates
    saturdays = []
    current = end_date
    for _ in range(52):  # Search up to 52 weeks
        # Find Saturday of this week
        days_since_saturday = (current.weekday() - 5) % 7
        saturday = current - timedelta(days=days_since_saturday)
        saturday = saturday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if saturday not in saturdays and saturday < end_date:
            saturdays.append(saturday)
        
        current -= timedelta(days=7)
    
    saturdays = sorted(saturdays, reverse=True)[:20]  # Only take recent 20 weeks
    
    print(f"\nWill download data for the following Saturdays (00:00-06:00 Beijing time):")
    for sat in saturdays[:5]:
        print(f"   {sat.strftime('%Y-%m-%d')}")
    print(f"   ... Total {len(saturdays)} Saturdays")
    
    success_count = 0
    
    for sat in saturdays:
        start_time = sat.replace(hour=0, minute=0, second=0)
        end_time = sat.replace(hour=6, minute=0, second=0)
        
        print(f"\nDownloading {sat.strftime('%Y-%m-%d')} 00:00-06:00...", end=" ")
        
        try:
            df = bbg.get_bid_ask_bars(
                security="JPYCNH Curncy",
                start_date=start_time,
                end_date=end_time,
                interval=10
            )
            
            if df is not None and not df.empty:
                print(f"[OK] {len(df)} records")
                all_data.append(df)
                success_count += 1
            else:
                print("[EMPTY]")
        except Exception as e:
            print(f"[ERROR] {e}")
    
    if all_data:
        combined = pd.concat(all_data)
        combined = combined.sort_index()
        combined = combined[~combined.index.duplicated(keep='first')]
        
        print(f"\n[OK] Total {len(combined)} records from {success_count} Saturdays")
        
        # Save
        output_file = OUTPUT_DIR / f"JPYCNH_Curncy_bidask_10s_saturdays_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        combined.reset_index().to_excel(output_file, index=False)
        print(f"[SAVED] {output_file.name}")
        
        return combined
    
    return None


if __name__ == "__main__":
    # Method 1: Download all at once
    df = download_jpycnh_bars()
    
    # Method 2: If bulk download doesn't work well, try downloading Saturday data day by day
    if df is None or len(df) < 1000:
        print("\n\nTrying to download Saturday data day by day...")
        download_with_daily_chunks()
