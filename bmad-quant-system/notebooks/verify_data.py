import pandas as pd
import numpy as np
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

# Load data
all_files = os.listdir(OUTPUT_DIR)
usdcnh_files = [f for f in all_files if 'USDCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]
jpycnh_files = [f for f in all_files if 'JPYCNH' in f and '1year' in f and f.endswith('.xlsx') and not f.startswith('~$')]

print(f'Loading USDCNH: {usdcnh_files[0]}')
df_usdcnh = pd.read_excel(os.path.join(OUTPUT_DIR, usdcnh_files[0]))
df_usdcnh['timestamp'] = pd.to_datetime(df_usdcnh['timestamp'])
df_usdcnh.set_index('timestamp', inplace=True)

print(f'Loading JPYCNH: {jpycnh_files[0]}')
df_jpycnh = pd.read_excel(os.path.join(OUTPUT_DIR, jpycnh_files[0]))
df_jpycnh['timestamp'] = pd.to_datetime(df_jpycnh['timestamp'])
df_jpycnh.set_index('timestamp', inplace=True)
df_jpycnh['mid_per_jpy'] = df_jpycnh['mid'] / 100

for df in [df_usdcnh, df_jpycnh]:
    df['date'] = df.index.date
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['weekday'] = df.index.dayofweek

sat_usdcnh = df_usdcnh[df_usdcnh['weekday'] == 5].copy()
sat_jpycnh = df_jpycnh[df_jpycnh['weekday'] == 5].copy()

sat_dates = sat_usdcnh['date'].unique()
print(f'Total {len(sat_dates)} Saturdays')

# Validate first week
sat_date = sat_dates[0]
print(f'\n{"="*60}')
print(f'Validating Week 1: {sat_date}')
print(f'{"="*60}')

sat_usd = sat_usdcnh[sat_usdcnh['date'] == sat_date]
sat_jpy = sat_jpycnh[sat_jpycnh['date'] == sat_date]

# Get key time points
usd_h0 = sat_usd[(sat_usd['hour'] == 0) & (sat_usd['minute'] == 0)]['mid'].values[0]
usd_h2 = sat_usd[(sat_usd['hour'] == 2) & (sat_usd['minute'] == 0)]['mid'].values[0]
usd_h6 = sat_usd[(sat_usd['hour'] == 6) & (sat_usd['minute'] == 0)]['mid'].values[0]

jpy_h0 = sat_jpy[(sat_jpy['hour'] == 0) & (sat_jpy['minute'] == 0)]['mid_per_jpy'].values[0]
jpy_h2 = sat_jpy[(sat_jpy['hour'] == 2) & (sat_jpy['minute'] == 0)]['mid_per_jpy'].values[0]
jpy_h6 = sat_jpy[(sat_jpy['hour'] == 6) & (sat_jpy['minute'] == 0)]['mid_per_jpy'].values[0]

print(f'\nUSD Key Time Points:')
print(f'  00:00 = {usd_h0:.6f}')
print(f'  02:00 = {usd_h2:.6f}')
print(f'  06:00 = {usd_h6:.6f}')
print(f'  max(2,6) = {max(usd_h2, usd_h6):.6f}  <-- BASELINE')

print(f'\nJPY Key Time Points (per 1 JPY):')
print(f'  00:00 = {jpy_h0:.8f}')
print(f'  02:00 = {jpy_h2:.8f}')
print(f'  06:00 = {jpy_h6:.8f}')
print(f'  max(2,6) = {max(jpy_h2, jpy_h6):.8f}  <-- BASELINE')

# Get 00:00~06:00 every 15min (25 time points)
print(f'\n{"="*60}')
print(f'00:00~06:00 Every 15min (25 Time Points)')
print(f'{"="*60}')
usd_sat_15min = []
jpy_sat_15min = []
print(f'\nTime        USD Price     JPY Price(per 1 JPY)')
print('-' * 55)
for h in range(7):
    for m in [0, 15, 30, 45]:
        if h == 6 and m > 0:
            continue
        usd_data = sat_usd[(sat_usd['hour'] == h) & (sat_usd['minute'] == m)]
        jpy_data = sat_jpy[(sat_jpy['hour'] == h) & (sat_jpy['minute'] == m)]
        if len(usd_data) > 0 and len(jpy_data) > 0:
            usd_p = usd_data['mid'].values[0]
            jpy_p = jpy_data['mid_per_jpy'].values[0]
            usd_sat_15min.append(usd_p)
            jpy_sat_15min.append(jpy_p)
            print(f'{h:02d}:{m:02d}       {usd_p:.6f}     {jpy_p:.8f}')

print(f'\nTotal {len(usd_sat_15min)} time points')

# Calculate Percentile
print(f'\n{"="*60}')
print(f'Percentile Calculation (based on {len(usd_sat_15min)} time points above)')
print(f'{"="*60}')
print(f'\nUSD Percentile:')
print(f'  max (P100) = {max(usd_sat_15min):.6f}')
print(f'  P90 = {np.percentile(usd_sat_15min, 90):.6f}')
print(f'  P80 = {np.percentile(usd_sat_15min, 80):.6f}')
print(f'  P70 = {np.percentile(usd_sat_15min, 70):.6f}')
print(f'  P60 = {np.percentile(usd_sat_15min, 60):.6f}')
print(f'  P50 = {np.percentile(usd_sat_15min, 50):.6f}')

print(f'\nJPY Percentile:')
print(f'  max (P100) = {max(jpy_sat_15min):.8f}')
print(f'  P90 = {np.percentile(jpy_sat_15min, 90):.8f}')
print(f'  P80 = {np.percentile(jpy_sat_15min, 80):.8f}')
print(f'  P70 = {np.percentile(jpy_sat_15min, 70):.8f}')
print(f'  P60 = {np.percentile(jpy_sat_15min, 60):.8f}')
print(f'  P50 = {np.percentile(jpy_sat_15min, 50):.8f}')

# Calculate BPS
usd_baseline = max(usd_h2, usd_h6)
jpy_baseline = max(jpy_h2, jpy_h6)

print(f'\n{"="*60}')
print(f'BPS Calculation (vs max(2,6) baseline)')
print(f'{"="*60}')
print(f'USD baseline max(2,6) = {usd_baseline:.6f}')
print(f'JPY baseline max(2,6) = {jpy_baseline:.8f}')

print(f'\nUSD BPS = (strategy_price - baseline) / baseline * 10000:')
strategies_usd = [
    ('max(0,2,6)', max(usd_h0, usd_h2, usd_h6)),
    ('max(00~06) 15min', max(usd_sat_15min)),
    ('P90', np.percentile(usd_sat_15min, 90)),
    ('P80', np.percentile(usd_sat_15min, 80)),
    ('P70', np.percentile(usd_sat_15min, 70)),
    ('P60', np.percentile(usd_sat_15min, 60)),
    ('P50', np.percentile(usd_sat_15min, 50)),
]
for name, price in strategies_usd:
    bps = (price - usd_baseline) / usd_baseline * 10000
    print(f'  {name:<18}: {price:.6f} -> {bps:+.2f} bps')

print(f'\nJPY BPS = (strategy_price - baseline) / baseline * 10000:')
strategies_jpy = [
    ('max(0,2,6)', max(jpy_h0, jpy_h2, jpy_h6)),
    ('max(00~06) 15min', max(jpy_sat_15min)),
    ('P90', np.percentile(jpy_sat_15min, 90)),
    ('P80', np.percentile(jpy_sat_15min, 80)),
    ('P70', np.percentile(jpy_sat_15min, 70)),
    ('P60', np.percentile(jpy_sat_15min, 60)),
    ('P50', np.percentile(jpy_sat_15min, 50)),
]
for name, price in strategies_jpy:
    bps = (price - jpy_baseline) / jpy_baseline * 10000
    print(f'  {name:<18}: {price:.8f} -> {bps:+.2f} bps')

print(f'\n{"="*60}')
print(f'Validation Complete!')
print(f'{"="*60}')
