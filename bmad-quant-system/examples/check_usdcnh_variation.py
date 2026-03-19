"""Check USDCNH data variation"""
import pandas as pd

df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx', 
                   parse_dates=['timestamp'], index_col=0)

# Filter Saturday 00:00-06:00
df['weekday'] = df.index.dayofweek
df['hour'] = df.index.hour
sat_df = df[(df['weekday'] == 5) & (df['hour'] < 6)]
sat_df = sat_df.copy()
sat_df['date'] = sat_df.index.date

print("USDCNH Saturday 00:00-06:00 Data Variation:")
print("-" * 70)

for d in sorted(sat_df['date'].unique()):
    day_df = sat_df[sat_df['date']==d]
    ask_min = day_df['ask'].min()
    ask_max = day_df['ask'].max()
    ask_range = ask_max - ask_min
    unique_asks = day_df['ask'].nunique()
    print(f"{d}: range={ask_range:.4f}, min={ask_min:.4f}, max={ask_max:.4f}, unique_values={unique_asks}")
