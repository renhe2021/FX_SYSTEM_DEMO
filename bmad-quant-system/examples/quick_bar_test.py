"""Quick test: JPYCNH Bar data"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
import blpapi

def quick_test():
    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)
    
    session = blpapi.Session(session_options)
    session.start()
    session.openService("//blp/refdata")
    service = session.getService("//blp/refdata")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Key tests
    tests = [
        ("JPYCNH Curncy", "BID", 1),
        ("CNHJPY Curncy", "BID", 1),
        ("JPYCNH BGN Curncy", "BID", 1),
        ("USDCNH Curncy", "BID", 1),  # Comparison
    ]
    
    for symbol, event_type, interval in tests:
        request = service.createRequest("IntradayBarRequest")
        request.set("security", symbol)
        request.set("eventType", event_type)
        request.set("interval", interval)
        request.set("startDateTime", start_date)
        request.set("endDateTime", end_date)
        
        session.sendRequest(request)
        
        count = 0
        sat_count = 0
        while True:
            event = session.nextEvent(3000)
            for msg in event:
                if msg.hasElement("barData"):
                    bar_data = msg.getElement("barData")
                    if bar_data.hasElement("barTickData"):
                        tick_data = bar_data.getElement("barTickData")
                        for i in range(tick_data.numValues()):
                            bar = tick_data.getValueAsElement(i)
                            ts = bar.getElementAsDatetime("time")
                            count += 1
                            if hasattr(ts, 'weekday') and ts.weekday() == 5:
                                sat_count += 1
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        print(f"{symbol:25} {event_type:5} int={interval}: {count:6} bars, Saturday: {sat_count}")
    
    session.stop()

if __name__ == "__main__":
    quick_test()
