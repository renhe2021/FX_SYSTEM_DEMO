# -*- coding: utf-8 -*-
import pandas as pd
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx', parse_dates=['timestamp'])

print('Data time range:')
print(f'  Start: {df.timestamp.min()}')
print(f'  End: {df.timestamp.max()}')
print()

df['weekday'] = df['timestamp'].dt.day_name()
df['hour'] = df['timestamp'].dt.hour

print('Data distribution by weekday and hour:')
for day in ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday']:
    day_data = df[df['weekday']==day]
    if not day_data.empty:
        print(f'{day}: hours {day_data.hour.min()}-{day_data.hour.max()}, count={len(day_data):,}')

print()
print('Sample Saturday data (first 10 rows):')
sat_data = df[df['weekday']=='Saturday'].head(10)
print(sat_data[['timestamp', 'bid', 'ask']].to_string())

print()
print('Sample Saturday data (last 10 rows):')
sat_data = df[df['weekday']=='Saturday'].tail(10)
print(sat_data[['timestamp', 'bid', 'ask']].to_string())
