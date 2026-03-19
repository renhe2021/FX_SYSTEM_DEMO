"""Compare USDCNH vs JPYCNH tick data"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
from quant_system.tools.bbg_wrapper import BloombergWrapper

bbg = BloombergWrapper()
bbg.connect()

# Test recent 2 weeks
end_date = datetime.now()
start_date = end_date - timedelta(days=14)

print(f"Testing tick data: {start_date} ~ {end_date}")
print()

for symbol in ["USDCNH Curncy", "JPYCNH Curncy"]:
    print(f"\n{symbol}:")
    df = bbg.get_bid_ask(symbol, start_date, end_date)
    
    if df is not None and not df.empty:
        df = df.reset_index()
        df['weekday'] = df['timestamp'].dt.dayofweek
        df['hour'] = df['timestamp'].dt.hour
        
        sat_df = df[df['weekday'] == 5]
        print(f"  Total ticks: {len(df)}")
        print(f"  Saturday ticks: {len(sat_df)}")
        
        if len(sat_df) > 0:
            print(f"  Saturday hours: {sorted(sat_df['hour'].unique())}")
    else:
        print("  No data!")

bbg.disconnect()
