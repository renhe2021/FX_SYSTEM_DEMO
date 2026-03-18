import pandas as pd

df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_10s_0900_1000_20260130_083820.xlsx')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['weekday'] = df['timestamp'].dt.dayofweek
df['date'] = df['timestamp'].dt.date

sat_df = df[df['weekday']==5]

print('Saturday analysis:')
for d in sorted(sat_df['date'].unique())[:5]:
    day_df = sat_df[sat_df['date']==d]
    bid_range = day_df['bid'].max() - day_df['bid'].min()
    unique = day_df['bid'].nunique()
    first_time = day_df['timestamp'].min().strftime('%H:%M')
    last_time = day_df['timestamp'].max().strftime('%H:%M')
    print(f'  {d}: {first_time}~{last_time}, bid_range={bid_range:.4f}, unique_prices={unique}')
