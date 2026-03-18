"""
Test direct tick request for JPYCNH on Saturday
Using different approaches
"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
import blpapi

def test_tick_request(symbol, start_date, end_date, event_types):
    """Test IntradayTickRequest"""
    
    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)
    
    session = blpapi.Session(session_options)
    if not session.start():
        print("Failed to start session")
        return None
    
    if not session.openService("//blp/refdata"):
        print("Failed to open refdata service")
        return None
    
    service = session.getService("//blp/refdata")
    
    print(f"\nTesting: {symbol}")
    print(f"Period: {start_date} ~ {end_date}")
    print(f"Events: {event_types}")
    print("-" * 50)
    
    try:
        request = service.createRequest("IntradayTickRequest")
        request.set("security", symbol)
        
        for event_type in event_types:
            request.append("eventTypes", event_type)
        
        request.set("startDateTime", start_date)
        request.set("endDateTime", end_date)
        request.set("includeConditionCodes", True)
        
        session.sendRequest(request)
        
        ticks = []
        while True:
            event = session.nextEvent(5000)
            
            for msg in event:
                if msg.hasElement("responseError"):
                    error = msg.getElement("responseError")
                    print(f"Error: {error}")
                
                if msg.hasElement("tickData"):
                    tick_data = msg.getElement("tickData")
                    if tick_data.hasElement("tickData"):
                        tick_array = tick_data.getElement("tickData")
                        for i in range(tick_array.numValues()):
                            tick = tick_array.getValueAsElement(i)
                            ts = tick.getElementAsDatetime("time")
                            val = tick.getElementAsFloat("value") if tick.hasElement("value") else None
                            etype = tick.getElementAsString("type") if tick.hasElement("type") else None
                            ticks.append({
                                'timestamp': ts,
                                'value': val,
                                'type': etype
                            })
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        print(f"Total ticks: {len(ticks)}")
        if ticks:
            # Show by weekday
            from datetime import datetime as dt
            weekday_counts = {}
            for t in ticks:
                ts = t['timestamp']
                if hasattr(ts, 'weekday'):
                    wd = ts.weekday()
                    weekday_counts[wd] = weekday_counts.get(wd, 0) + 1
            
            weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            for wd in sorted(weekday_counts.keys()):
                print(f"  {weekday_names[wd]}: {weekday_counts[wd]} ticks")
            
            # Show Saturday sample
            sat_ticks = [t for t in ticks if hasattr(t['timestamp'], 'weekday') and t['timestamp'].weekday() == 5]
            if sat_ticks:
                print(f"\nSaturday sample (first 5):")
                for t in sat_ticks[:5]:
                    print(f"  {t}")
        
        session.stop()
        return ticks
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        session.stop()
        return None


def main():
    # Test on a Saturday - Jan 25, 2025 was a Saturday
    # Let's try from Friday evening to Saturday morning
    sat_date = datetime(2026, 1, 25)  # This is a Saturday
    start_date = sat_date - timedelta(days=1, hours=12)  # Friday noon
    end_date = sat_date + timedelta(hours=8)  # Saturday 8am
    
    print("=" * 60)
    print("Testing JPYCNH tick data on Saturday")
    print("=" * 60)
    
    # Test JPYCNH with different event types
    test_tick_request("JPYCNH Curncy", start_date, end_date, ["BID", "ASK"])
    test_tick_request("JPYCNH Curncy", start_date, end_date, ["TRADE"])
    
    # Compare with USDCNH
    print("\n" + "=" * 60)
    print("Comparison: USDCNH")
    print("=" * 60)
    test_tick_request("USDCNH Curncy", start_date, end_date, ["BID", "ASK"])
    

if __name__ == "__main__":
    main()
