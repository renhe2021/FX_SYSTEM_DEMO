"""
Check JPYCNH weekend data - verify timestamps
"""
import pandas as pd

# Read the newly downloaded file
df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\JPYCNH_Curncy_bidask_1min_20260130_115338.xlsx')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['weekday'] = df['timestamp'].dt.dayofweek
df['date'] = df['timestamp'].dt.date
df['hour'] = df['timestamp'].dt.hour

print("="*60)
print("JPYCNH Data Check (Beijing Time)")
print("="*60)

print(f"\nTotal rows: {len(df)}")
print(f"Time range: {df['timestamp'].min()} ~ {df['timestamp'].max()}")

# Check weekday distribution
print("\nWeekday distribution:")
weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
for wd in range(7):
    cnt = len(df[df['weekday'] == wd])
    if cnt > 0:
        print(f"  {weekday_names[wd]}: {cnt} rows")

# Saturday analysis
sat_df = df[df['weekday'] == 5]
print(f"\nSaturday analysis:")
print(f"  Total Saturday rows: {len(sat_df)}")

if len(sat_df) > 0:
    # By hour
    print(f"\n  Saturday data by hour:")
    for hour in range(24):
        hour_df = sat_df[sat_df['hour'] == hour]
        if len(hour_df) > 0:
            unique_bids = hour_df['bid'].nunique()
            bid_range = hour_df['bid'].max() - hour_df['bid'].min()
            # Check if data is static (all same price)
            is_static = "STATIC" if unique_bids <= 2 else "ACTIVE"
            print(f"    Hour {hour:02d}: {len(hour_df):5} rows, unique={unique_bids:3}, range={bid_range:.6f} [{is_static}]")
    
    # Sample of actual Saturday dates
    print(f"\n  Sample Saturday dates with price variation:")
    for d in sorted(sat_df['date'].unique())[:5]:
        day_df = sat_df[sat_df['date'] == d]
        # Only count active hours (00-05)
        active_df = day_df[day_df['hour'] <= 5]
        unique_bids = active_df['bid'].nunique()
        bid_range = active_df['bid'].max() - active_df['bid'].min()
        first_time = day_df['timestamp'].min().strftime('%H:%M')
        last_time = day_df['timestamp'].max().strftime('%H:%M')
        print(f"    {d}: {first_time}~{last_time}, active_hours unique={unique_bids}, range={bid_range:.6f}")

# Compare with USDCNH
print("\n" + "="*60)
print("Comparison with USDCNH (Beijing Time)")
print("="*60)

usd_df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx')
usd_df['timestamp'] = pd.to_datetime(usd_df['timestamp'])
usd_df['weekday'] = usd_df['timestamp'].dt.dayofweek
usd_df['date'] = usd_df['timestamp'].dt.date
usd_df['hour'] = usd_df['timestamp'].dt.hour

usd_sat = usd_df[usd_df['weekday'] == 5]

print(f"\nUSDCNH Saturday rows: {len(usd_sat)}")
print(f"JPYCNH Saturday rows: {len(sat_df)}")

print(f"\nUSDCNH Saturday hours with data:")
for hour in range(8):
    hour_df = usd_sat[usd_sat['hour'] == hour]
    if len(hour_df) > 0:
        unique = hour_df['bid'].nunique()
        print(f"  Hour {hour:02d}: {len(hour_df)} rows, unique={unique}")

print(f"\nJPYCNH Saturday hours with ACTIVE data (00-05):")
for hour in range(6):
    hour_df = sat_df[sat_df['hour'] == hour]
    if len(hour_df) > 0:
        unique = hour_df['bid'].nunique()
        print(f"  Hour {hour:02d}: {len(hour_df)} rows, unique={unique}")
