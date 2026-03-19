"""
Analyze USDCNH Excel file to understand data source
"""
import pandas as pd
import os
from datetime import datetime

# Read the Excel file
file_path = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx'

df = pd.read_excel(file_path)
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("=" * 60)
print("USDCNH Excel File Analysis")
print("=" * 60)

# File info
stat = os.stat(file_path)
print(f"\nFile created: {datetime.fromtimestamp(stat.st_ctime)}")
print(f"File modified: {datetime.fromtimestamp(stat.st_mtime)}")
print(f"File size: {stat.st_size / 1024 / 1024:.2f} MB")

# Data info
print(f"\nShape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"\nTime range: {df['timestamp'].min()} ~ {df['timestamp'].max()}")

# Check interval
df_sorted = df.sort_values('timestamp')
intervals = df_sorted['timestamp'].diff().dt.total_seconds().dropna()
print(f"\nInterval analysis:")
print(f"  Most common: {intervals.mode().values[0]}s")
print(f"  Min: {intervals.min()}s")
print(f"  Max: {intervals.max()}s")

# Check if data has high/low columns (indicates Bar data)
if 'bid_high' in df.columns:
    print(f"\nData type: BAR DATA (has bid_high, bid_low, ask_high, ask_low)")
else:
    print(f"\nData type: TICK DATA (no high/low columns)")

# Weekday distribution
df['weekday'] = df['timestamp'].dt.dayofweek
print(f"\nWeekday distribution:")
weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
for wd in range(7):
    cnt = len(df[df['weekday'] == wd])
    if cnt > 0:
        print(f"  {weekday_names[wd]}: {cnt} rows")

# Saturday details
sat_df = df[df['weekday'] == 5].copy()
if len(sat_df) > 0:
    print(f"\nSaturday data analysis:")
    sat_df['date'] = sat_df['timestamp'].dt.date
    sat_df['hour'] = sat_df['timestamp'].dt.hour
    
    print(f"  Total Saturday rows: {len(sat_df)}")
    print(f"  Saturday dates: {sorted(sat_df['date'].unique())[:5]}... (showing first 5)")
    
    # Check price variation on Saturday
    print(f"\n  Price variation on Saturday:")
    for d in sorted(sat_df['date'].unique())[:3]:
        day_df = sat_df[sat_df['date'] == d]
        bid_range = day_df['bid'].max() - day_df['bid'].min()
        ask_range = day_df['ask'].max() - day_df['ask'].min()
        unique_bids = day_df['bid'].nunique()
        unique_asks = day_df['ask'].nunique()
        print(f"    {d}: bid_range={bid_range:.4f}, ask_range={ask_range:.4f}, unique_bids={unique_bids}, unique_asks={unique_asks}")

print("\n" + "=" * 60)
