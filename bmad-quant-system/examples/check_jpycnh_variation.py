"""Check JPYCNH data variation"""
import pandas as pd

df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\JPYCNH_Curncy_bidask_10s_weekly_20260130_100245.xlsx', 
                   parse_dates=['timestamp'], index_col=0)

df['date'] = df.index.date

print("JPYCNH Saturday Data Variation:")
print("-" * 70)

for d in sorted(df['date'].unique()):
    day_df = df[df['date']==d]
    ask_min = day_df['ask'].min()
    ask_max = day_df['ask'].max()
    ask_range = ask_max - ask_min
    unique_asks = day_df['ask'].nunique()
    print(f"{d}: range={ask_range:.4f}, min={ask_min:.4f}, max={ask_max:.4f}, unique_values={unique_asks}")
