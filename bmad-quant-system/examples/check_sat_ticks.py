"""Check Saturday tick activity"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from quant_system.tools.bbg_wrapper import BloombergWrapper
from datetime import datetime, timedelta

bbg = BloombergWrapper()
end = datetime.now()
start = end - timedelta(days=7)

print('Getting USDCNH raw ticks...')
df = bbg.get_bid_ask('USDCNH Curncy', start_date=start, end_date=end)
print(f'USDCNH ticks: {len(df)}')

df['weekday'] = df.index.dayofweek
sat = df[df['weekday'] == 5]
print(f'Saturday ticks: {len(sat)}')

if len(sat) > 0:
    print(f'Saturday range: {sat.index.min()} ~ {sat.index.max()}')
    sat['hour'] = sat.index.hour
    for h in range(6):
        h_data = sat[sat['hour'] == h]
        if not h_data.empty:
            print(f'  {h:02d}:00: {len(h_data)} ticks, ask: {h_data["ask"].min():.4f} ~ {h_data["ask"].max():.4f}')

print('\nGetting JPYCNH raw ticks...')
df2 = bbg.get_bid_ask('JPYCNH Curncy', start_date=start, end_date=end)
print(f'JPYCNH ticks: {len(df2)}')

df2['weekday'] = df2.index.dayofweek
sat2 = df2[df2['weekday'] == 5]
print(f'Saturday ticks: {len(sat2)}')

if len(sat2) > 0:
    print(f'Saturday range: {sat2.index.min()} ~ {sat2.index.max()}')
