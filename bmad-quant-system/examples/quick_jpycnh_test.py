"""Quick test: JPYCNH tick data on Saturday morning"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
from quant_system.tools.bbg_wrapper import BloombergWrapper

bbg = BloombergWrapper()
bbg.connect()

# Test recent 2 weeks
end_date = datetime.now()
start_date = end_date - timedelta(days=14)

print(f"Testing JPYCNH tick data: {start_date} ~ {end_date}")

# Get raw bid/ask ticks
df = bbg.get_bid_ask("JPYCNH Curncy", start_date, end_date)

if df is not None and not df.empty:
    df = df.reset_index()
    df['weekday'] = df['timestamp'].dt.dayofweek
    df['hour'] = df['timestamp'].dt.hour
    
    sat_df = df[df['weekday'] == 5]
    print(f"Total ticks: {len(df)}")
    print(f"Saturday ticks: {len(sat_df)}")
    
    if len(sat_df) > 0:
        print("\nSaturday ticks by hour:")
        for hour in range(8):
            hour_df = sat_df[sat_df['hour'] == hour]
            if len(hour_df) > 0:
                print(f"  Hour {hour:02d}: {len(hour_df)} ticks")
else:
    print("No data!")

bbg.disconnect()
