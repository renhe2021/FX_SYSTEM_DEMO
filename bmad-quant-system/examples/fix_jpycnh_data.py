"""
Fix JPYCNH data: Only keep Saturday 00:00-06:00 Beijing time (active trading hours)
"""
import pandas as pd
from datetime import datetime

# Read the downloaded file
df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\JPYCNH_Curncy_bidask_1min_20260130_115338.xlsx')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['weekday'] = df['timestamp'].dt.dayofweek
df['hour'] = df['timestamp'].dt.hour

print("Original data:")
print(f"  Total rows: {len(df)}")
print(f"  Saturday rows: {len(df[df['weekday'] == 5])}")
print(f"  Sunday rows: {len(df[df['weekday'] == 6])}")

# Filter logic:
# - Keep Mon-Fri all day (weekday 0-4)
# - Keep Saturday 00:00-05:59 only (weekday 5, hour 0-5)
# - Remove Sunday completely (weekday 6)

# Create mask
is_weekday = df['weekday'] <= 4  # Mon-Fri
is_sat_active = (df['weekday'] == 5) & (df['hour'] <= 5)  # Sat 00:00-05:59

mask = is_weekday | is_sat_active

df_filtered = df[mask].copy()

print("\nFiltered data:")
print(f"  Total rows: {len(df_filtered)}")
print(f"  Saturday rows: {len(df_filtered[df_filtered['weekday'] == 5])}")
print(f"  Sunday rows: {len(df_filtered[df_filtered['weekday'] == 6])}")

# Verify Saturday data quality
sat_df = df_filtered[df_filtered['weekday'] == 5]
print(f"\nSaturday data verification:")
for hour in range(6):
    hour_df = sat_df[sat_df['hour'] == hour]
    if len(hour_df) > 0:
        unique = hour_df['bid'].nunique()
        bid_range = hour_df['bid'].max() - hour_df['bid'].min()
        print(f"  Hour {hour:02d}: {len(hour_df)} rows, unique={unique}, range={bid_range:.6f}")

# Save corrected file
output_df = df_filtered[['timestamp', 'bid', 'ask', 'spread', 'mid']].copy()
output_file = f"c:/Users/tencentren/CodeBuddy/FX_SYSTEM/bmad-quant-system/output/JPYCNH_Curncy_bidask_1min_corrected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
output_df.to_excel(output_file, index=False)
print(f"\nSaved corrected file to: {output_file}")

# Final comparison
print("\n" + "="*60)
print("Final Data Summary")
print("="*60)

usd_df = pd.read_excel(r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system\output\USDCNH_Curncy_bidask_1s_20260116_144224.xlsx')
usd_df['timestamp'] = pd.to_datetime(usd_df['timestamp'])
usd_df['weekday'] = usd_df['timestamp'].dt.dayofweek

print(f"\nUSDCNH:")
print(f"  Total: {len(usd_df)} rows")
print(f"  Saturday: {len(usd_df[usd_df['weekday']==5])} rows")

print(f"\nJPYCNH (corrected):")
print(f"  Total: {len(df_filtered)} rows")
print(f"  Saturday: {len(sat_df)} rows")
