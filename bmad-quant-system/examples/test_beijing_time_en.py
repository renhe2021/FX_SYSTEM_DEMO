"""
Test Beijing Time Default Handling
==================================

Verify bbg_wrapper now uses Beijing time by default:
- Input time is Beijing time
- Automatically converted to UTC for Bloomberg API
- Returned data timestamps are UTC (data_explorer converts to Beijing for display)
"""

import sys
sys.path.insert(0, r"c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system")

from datetime import datetime, timedelta
from quant_system.tools.bbg_wrapper import (
    BloombergWrapper, 
    beijing_now, 
    beijing_to_utc, 
    utc_to_beijing,
    BEIJING_UTC_OFFSET
)

def test_time_functions():
    """Test time conversion functions"""
    print("=" * 60)
    print("Test Time Conversion Functions")
    print("=" * 60)
    
    # Current time
    now_beijing = beijing_now()
    now_utc = datetime.utcnow()
    
    print(f"\nCurrent Beijing time: {now_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Offset: {BEIJING_UTC_OFFSET} hours")
    
    # Test conversion
    test_beijing = datetime(2026, 1, 25, 9, 0, 0)  # Beijing 09:00
    test_utc = beijing_to_utc(test_beijing)
    test_back = utc_to_beijing(test_utc)
    
    print(f"\nConversion test:")
    print(f"  Beijing time: {test_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  -> UTC: {test_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  -> Back to Beijing: {test_back.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Saturday early morning test
    saturday_beijing = datetime(2026, 1, 25, 0, 0, 0)  # Saturday Beijing 00:00
    saturday_utc = beijing_to_utc(saturday_beijing)
    
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    print(f"\nSaturday early morning conversion:")
    print(f"  Beijing Saturday 00:00: {saturday_beijing.strftime('%Y-%m-%d %H:%M:%S')} ({weekday_names[saturday_beijing.weekday()]})")
    print(f"  -> UTC: {saturday_utc.strftime('%Y-%m-%d %H:%M:%S')} ({weekday_names[saturday_utc.weekday()]})")
    print(f"  (Beijing Saturday 00:00 = UTC Friday 16:00)")
    
    return True


def test_bbg_wrapper():
    """Test BloombergWrapper Beijing time handling"""
    print("\n" + "=" * 60)
    print("Test BloombergWrapper Beijing Time Handling")
    print("=" * 60)
    
    bbg = BloombergWrapper()
    
    if not bbg.connect():
        print("[Warning] Bloomberg not connected, skip actual data test")
        return False
    
    try:
        # Test 1: Default time (current Beijing time)
        print("\nTest 1: Default time (current Beijing time)")
        print("-" * 40)
        
        # Get last 1 hour of data
        df = bbg.get_bid_ask(
            symbol="USDCNH Curncy",
            hours_back=1
        )
        
        if df is not None and not df.empty:
            print(f"[OK] Got {len(df)} ticks")
            print(f"  Data range (UTC): {df.index[0]} ~ {df.index[-1]}")
            # Convert to Beijing time for display
            beijing_start = utc_to_beijing(df.index[0].to_pydatetime())
            beijing_end = utc_to_beijing(df.index[-1].to_pydatetime())
            print(f"  Data range (Beijing): {beijing_start} ~ {beijing_end}")
        else:
            print("[FAIL] No data returned")
        
        # Test 2: Specify Beijing time range
        print("\nTest 2: Specify Beijing time range")
        print("-" * 40)
        
        # Beijing time 09:00 ~ 10:00
        start_beijing = datetime(2026, 1, 29, 9, 0, 0)
        end_beijing = datetime(2026, 1, 29, 10, 0, 0)
        
        print(f"  Request time (Beijing): {start_beijing} ~ {end_beijing}")
        
        df2 = bbg.get_bid_ask(
            symbol="USDCNH Curncy",
            start_date=start_beijing,
            end_date=end_beijing,
            is_beijing_time=True  # Explicitly specify input is Beijing time
        )
        
        if df2 is not None and not df2.empty:
            print(f"[OK] Got {len(df2)} ticks")
            print(f"  Data range (UTC): {df2.index[0]} ~ {df2.index[-1]}")
            beijing_start = utc_to_beijing(df2.index[0].to_pydatetime())
            beijing_end = utc_to_beijing(df2.index[-1].to_pydatetime())
            print(f"  Data range (Beijing): {beijing_start} ~ {beijing_end}")
        else:
            print("[FAIL] No data returned")
        
        return True
        
    finally:
        bbg.disconnect()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Bloomberg Beijing Time Handling Test")
    print("=" * 60)
    
    # Test time conversion functions
    test_time_functions()
    
    # Test actual data retrieval
    test_bbg_wrapper()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    print("\nSummary:")
    print("- All time inputs now default to Beijing time")
    print("- bbg_wrapper internally converts Beijing time to UTC")
    print("- Returned data timestamps are in UTC")
    print("- data_explorer converts UTC to Beijing time for display")
