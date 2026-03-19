"""
Calculate bps difference between 3 strategies
"""
import pandas as pd
import os

OUTPUT_DIR = r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output'

df = pd.read_excel(os.path.join(OUTPUT_DIR, 'strategy_comparison_3way_detail.xlsx'))

print('='*70)
print('Strategy Reference Price Difference Analysis (bps)')
print('='*70)

# 1 bp = 0.0001
df['bps_06_vs_26'] = (df['ref_max_0_6'] - df['ref_max_2_6']) / df['ref_max_2_6'] * 10000
df['bps_026_vs_06'] = (df['ref_max_0_2_6'] - df['ref_max_0_6']) / df['ref_max_0_6'] * 10000
df['bps_026_vs_26'] = (df['ref_max_0_2_6'] - df['ref_max_2_6']) / df['ref_max_2_6'] * 10000

print(f'\nPeriod: {df["date"].iloc[0]} ~ {df["date"].iloc[-1]}')
print(f'Total weeks: {len(df)}')

print(f'\n' + '='*70)
print('Reference Price Difference Stats (bps)')
print('='*70)

print(f'\n1. max(0,6) vs max(2,6):')
print(f'   Mean:   {df["bps_06_vs_26"].mean():>8.2f} bps')
print(f'   Median: {df["bps_06_vs_26"].median():>8.2f} bps')
print(f'   Max:    {df["bps_06_vs_26"].max():>8.2f} bps')
print(f'   Min:    {df["bps_06_vs_26"].min():>8.2f} bps')
print(f'   Std:    {df["bps_06_vs_26"].std():>8.2f} bps')

print(f'\n2. max(0,2,6) vs max(0,6):')
print(f'   Mean:   {df["bps_026_vs_06"].mean():>8.2f} bps')
print(f'   Median: {df["bps_026_vs_06"].median():>8.2f} bps')
print(f'   Max:    {df["bps_026_vs_06"].max():>8.2f} bps')
print(f'   Min:    {df["bps_026_vs_06"].min():>8.2f} bps')
print(f'   Std:    {df["bps_026_vs_06"].std():>8.2f} bps')

print(f'\n3. max(0,2,6) vs max(2,6):')
print(f'   Mean:   {df["bps_026_vs_26"].mean():>8.2f} bps')
print(f'   Median: {df["bps_026_vs_26"].median():>8.2f} bps')
print(f'   Max:    {df["bps_026_vs_26"].max():>8.2f} bps')
print(f'   Min:    {df["bps_026_vs_26"].min():>8.2f} bps')
print(f'   Std:    {df["bps_026_vs_26"].std():>8.2f} bps')

print(f'\n' + '='*70)
print('Value per bp')
print('='*70)
USD_WEEKLY = 60_000_000
JPY_WEEKLY = 4_000_000_000

usd_per_bp = 0.0001 * USD_WEEKLY
print(f'\nUSD: 1 bp x 60M USD = {usd_per_bp:,.0f} CNH/bp/week')

total_pnl_026_vs_26 = df['total_diff_026_vs_26'].sum()
total_bps_026_vs_26 = df['bps_026_vs_26'].sum()
if total_bps_026_vs_26 > 0:
    cnh_per_bp_actual = total_pnl_026_vs_26 / total_bps_026_vs_26
    print(f'Actual (USD+JPY): 1 bp = {cnh_per_bp_actual:,.0f} CNH/bp/week')

print(f'\n' + '='*70)
print('SUMMARY')
print('='*70)
print(f'\nUsing max(0,2,6) strategy:')
print(f'  vs max(0,6): avg +{df["bps_026_vs_06"].mean():.2f} bps/week')
print(f'  vs max(2,6): avg +{df["bps_026_vs_26"].mean():.2f} bps/week')

nonzero_026_vs_06 = df[df['bps_026_vs_06'] > 0]
nonzero_026_vs_26 = df[df['bps_026_vs_26'] > 0]
print(f'\n  max(0,2,6) > max(0,6): {len(nonzero_026_vs_06)}/{len(df)} weeks ({len(nonzero_026_vs_06)/len(df)*100:.1f}%)')
print(f'  max(0,2,6) > max(2,6): {len(nonzero_026_vs_26)}/{len(df)} weeks ({len(nonzero_026_vs_26)/len(df)*100:.1f}%)')

avg_bps_per_week_026_vs_26 = df['bps_026_vs_26'].mean()
avg_bps_per_week_026_vs_06 = df['bps_026_vs_06'].mean()
print(f'\nAnnualized (52 weeks):')
print(f'  max(0,2,6) vs max(0,6): {avg_bps_per_week_026_vs_06:.2f} bps/wk x 52 = {avg_bps_per_week_026_vs_06 * 52:.1f} bps/year')
print(f'  max(0,2,6) vs max(2,6): {avg_bps_per_week_026_vs_26:.2f} bps/wk x 52 = {avg_bps_per_week_026_vs_26 * 52:.1f} bps/year')
print(f'  => ~{df["total_diff_026_vs_26"].mean() * 52 / 1e6:.2f}M CNH/year extra')

print('\n' + '='*70)
