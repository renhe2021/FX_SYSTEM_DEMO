import pandas as pd

# The original file with real Saturday data
df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['weekday'] = df['timestamp'].dt.dayofweek
df['date'] = df['timestamp'].dt.date
df['hour'] = df['timestamp'].dt.hour

sat_df = df[df['weekday']==5]

print('Original USDCNH file - Saturday analysis:')
print(f'Total Saturday rows: {len(sat_df)}')
print()

# Check different hour ranges
print('Saturday data by hour:')
for hour in range(8):
    hour_df = sat_df[sat_df['hour'] == hour]
    if len(hour_df) > 0:
        unique = hour_df['bid'].nunique()
        bid_range = hour_df['bid'].max() - hour_df['bid'].min()
        print(f'  Hour {hour:02d}: {len(hour_df)} rows, unique_prices={unique}, bid_range={bid_range:.4f}')

print()
print('Sample Saturday data (first few):')
for d in sorted(sat_df['date'].unique())[:3]:
    day_df = sat_df[sat_df['date']==d]
    first_time = day_df['timestamp'].min().strftime('%H:%M')
    last_time = day_df['timestamp'].max().strftime('%H:%M')
    unique = day_df['bid'].nunique()
    bid_range = day_df['bid'].max() - day_df['bid'].min()
    print(f'  {d}: {first_time}~{last_time}, unique_prices={unique}, bid_range={bid_range:.4f}')
