"""
Direct test: JPYCNH BID/ASK Bar Request
Test different configurations to find working Saturday data
"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
import blpapi

def test_bar_request(symbol, event_type, interval, start_date, end_date):
    """Test IntradayBarRequest with different configurations"""
    
    # Connect
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
    
    print(f"\n{'='*60}")
    print(f"Testing: {symbol} - {event_type}")
    print(f"Interval: {interval}")
    print(f"Period: {start_date} ~ {end_date}")
    print('='*60)
    
    try:
        request = service.createRequest("IntradayBarRequest")
        request.set("security", symbol)
        request.set("eventType", event_type)
        request.set("interval", interval)
        request.set("startDateTime", start_date)
        request.set("endDateTime", end_date)
        
        session.sendRequest(request)
        
        data = []
        while True:
            event = session.nextEvent(5000)
            
            for msg in event:
                if msg.hasElement("responseError"):
                    error = msg.getElement("responseError")
                    print(f"Error: {error}")
                
                if msg.hasElement("barData"):
                    bar_data = msg.getElement("barData")
                    if bar_data.hasElement("barTickData"):
                        tick_data = bar_data.getElement("barTickData")
                        for i in range(tick_data.numValues()):
                            bar = tick_data.getValueAsElement(i)
                            ts = bar.getElementAsDatetime("time")
                            close = bar.getElementAsFloat("close")
                            data.append({
                                'timestamp': ts,
                                'close': close,
                                'weekday': ts.weekday() if hasattr(ts, 'weekday') else None
                            })
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        print(f"Total bars: {len(data)}")
        
        # Check Saturday data
        if data:
            from datetime import datetime as dt
            sat_data = [d for d in data if hasattr(d['timestamp'], 'weekday') and d['timestamp'].weekday() == 5]
            sun_data = [d for d in data if hasattr(d['timestamp'], 'weekday') and d['timestamp'].weekday() == 6]
            print(f"Saturday bars: {len(sat_data)}")
            print(f"Sunday bars: {len(sun_data)}")
            
            if sat_data:
                print(f"Saturday sample: {sat_data[:3]}")
        
        session.stop()
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        session.stop()
        return None


def main():
    # Test period: last few weeks to cover weekends
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    # Different symbol variations to try
    symbols = [
        "JPYCNH Curncy",
        "JPYCNH BGN Curncy",
        "JPYCNH CMPT Curncy", 
        "JPYCNH BFIX Curncy",
        "CNHJPY Curncy",  # Try reverse
    ]
    
    # Test configurations
    for symbol in symbols:
        for event_type in ["BID", "ASK", "TRADE"]:
            for interval in [1, 60]:  # 1 min, 1 hour
                try:
                    result = test_bar_request(symbol, event_type, interval, start_date, end_date)
                    if result and len(result) > 0:
                        print(f"SUCCESS: {symbol} / {event_type} / {interval}min -> {len(result)} bars")
                except Exception as e:
                    print(f"FAILED: {symbol} / {event_type} / {interval}min -> {e}")
    
    # Also try USDCNH for comparison
    print("\n" + "="*80)
    print("COMPARISON: USDCNH")
    print("="*80)
    test_bar_request("USDCNH Curncy", "BID", 1, start_date, end_date)
    test_bar_request("USDCNH Curncy", "ASK", 1, start_date, end_date)


if __name__ == "__main__":
    main()
