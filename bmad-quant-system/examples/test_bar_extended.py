"""
Test: Download USDCNH Bar data with EXACT same parameters as the working file
The working file has data from 2025-07-04 05:00 to 2026-01-15 23:59
Let's test if we can get Saturday data with this range
"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
import blpapi

def test_bar_request_extended():
    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)
    
    session = blpapi.Session(session_options)
    session.start()
    session.openService("//blp/refdata")
    service = session.getService("//blp/refdata")
    
    # Try different date ranges
    test_cases = [
        # Short range (recent week)
        ("Recent 7 days", datetime.now() - timedelta(days=7), datetime.now()),
        # Longer range
        ("Recent 30 days", datetime.now() - timedelta(days=30), datetime.now()),
        # Very long range (like the working file)
        ("6 months", datetime(2025, 7, 4, 5, 0), datetime(2026, 1, 15, 23, 59)),
        # Just Saturday
        ("Specific Saturday", datetime(2026, 1, 25, 0, 0), datetime(2026, 1, 25, 8, 0)),
    ]
    
    for name, start_date, end_date in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {name}")
        print(f"Range: {start_date} ~ {end_date}")
        print('='*60)
        
        request = service.createRequest("IntradayBarRequest")
        request.set("security", "USDCNH Curncy")
        request.set("eventType", "BID")
        request.set("interval", 1)  # 1 minute
        request.set("startDateTime", start_date)
        request.set("endDateTime", end_date)
        
        session.sendRequest(request)
        
        total_bars = 0
        sat_bars = 0
        
        while True:
            event = session.nextEvent(5000)
            for msg in event:
                if msg.hasElement("barData"):
                    bar_data = msg.getElement("barData")
                    if bar_data.hasElement("barTickData"):
                        tick_data = bar_data.getElement("barTickData")
                        for i in range(tick_data.numValues()):
                            bar = tick_data.getValueAsElement(i)
                            ts = bar.getElementAsDatetime("time")
                            total_bars += 1
                            if hasattr(ts, 'weekday') and ts.weekday() == 5:
                                sat_bars += 1
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        print(f"Total bars: {total_bars}")
        print(f"Saturday bars: {sat_bars}")
    
    session.stop()

if __name__ == "__main__":
    test_bar_request_extended()
