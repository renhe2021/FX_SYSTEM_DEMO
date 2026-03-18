"""
Test: Use UTC time directly to get Saturday data
Saturday 00:00-06:00 Beijing = Friday 16:00-22:00 UTC
"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
import blpapi

def test_utc_saturday():
    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)
    
    session = blpapi.Session(session_options)
    session.start()
    session.openService("//blp/refdata")
    service = session.getService("//blp/refdata")
    
    # Try different time ranges in UTC
    # Beijing Saturday 00:00-06:00 = UTC Friday 16:00-22:00
    
    # Test 1: UTC Friday 16:00 to UTC Saturday 00:00
    print("="*60)
    print("Test: UTC Friday 16:00 ~ UTC Saturday 00:00")
    print("(This is Beijing Saturday 00:00 ~ 08:00)")
    print("="*60)
    
    # Find last Friday
    today = datetime.now()
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0:
        days_since_friday = 7
    last_friday = today - timedelta(days=days_since_friday)
    
    # UTC Friday 16:00 to Saturday 00:00
    start_utc = datetime(last_friday.year, last_friday.month, last_friday.day, 16, 0)
    end_utc = start_utc + timedelta(hours=8)
    
    print(f"UTC range: {start_utc} ~ {end_utc}")
    print(f"Last Friday was: {last_friday.date()}")
    
    for symbol in ["USDCNH Curncy", "JPYCNH Curncy"]:
        print(f"\n{symbol}:")
        
        request = service.createRequest("IntradayTickRequest")
        request.set("security", symbol)
        request.getElement("eventTypes").appendValue("BID")
        request.getElement("eventTypes").appendValue("ASK")
        request.set("startDateTime", start_utc)
        request.set("endDateTime", end_utc)
        
        session.sendRequest(request)
        
        ticks = []
        while True:
            event = session.nextEvent(5000)
            for msg in event:
                if msg.hasElement("tickData"):
                    tick_data = msg.getElement("tickData")
                    if tick_data.hasElement("tickData"):
                        tick_array = tick_data.getElement("tickData")
                        for i in range(tick_array.numValues()):
                            tick = tick_array.getValueAsElement(i)
                            ts = tick.getElementAsDatetime("time")
                            ticks.append(ts)
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        print(f"  Total ticks: {len(ticks)}")
        if ticks:
            # Group by UTC day
            from collections import Counter
            days = Counter()
            for ts in ticks:
                if hasattr(ts, 'weekday'):
                    days[ts.weekday()] += 1
            
            weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            for wd in sorted(days.keys()):
                print(f"    {weekday_names[wd]}: {days[wd]} ticks")
    
    session.stop()

if __name__ == "__main__":
    test_utc_saturday()
