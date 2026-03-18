import pandas as pd

df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['weekday'] = df['timestamp'].dt.dayofweek
df['date'] = df['timestamp'].dt.date

print('Time range:', df['timestamp'].min(), '~', df['timestamp'].max())
print()

sat_df = df[df['weekday']==5]
print('Saturday dates with data:')
for d in sorted(sat_df['date'].unique()):
    day_df = sat_df[sat_df['date']==d]
    cnt = len(day_df)
    first = day_df['timestamp'].min().strftime('%H:%M')
    last = day_df['timestamp'].max().strftime('%H:%M')
    print(f'  {d}: {cnt} rows, {first} ~ {last}')
    
print()
print('Data interval analysis:')
# Check interval
df_sorted = df.sort_values('timestamp')
intervals = df_sorted['timestamp'].diff().dt.total_seconds().dropna()
print(f'  Most common interval: {intervals.mode().values[0]}s')
print(f'  Interval range: {intervals.min()}s ~ {intervals.max()}s')
