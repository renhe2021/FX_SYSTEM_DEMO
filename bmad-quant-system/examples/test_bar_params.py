"""
Test: IntradayBarRequest with different parameters
Try to find what makes Saturday data available
"""
import sys
sys.path.insert(0, r'c:\Users\tencentren\CodeBuddy\FX_SYSTEM\bmad-quant-system')

from datetime import datetime, timedelta
import blpapi

def test_with_params():
    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)
    
    session = blpapi.Session(session_options)
    session.start()
    session.openService("//blp/refdata")
    service = session.getService("//blp/refdata")
    
    # Test range: include a weekend
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    print("Testing different IntradayBarRequest parameters...")
    print(f"Date range: {start_date} ~ {end_date}")
    print()
    
    # Test 1: Standard request
    print("Test 1: Standard request")
    request = service.createRequest("IntradayBarRequest")
    request.set("security", "USDCNH Curncy")
    request.set("eventType", "BID")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    count1, sat1 = count_bars(session)
    print(f"  Total: {count1}, Saturday: {sat1}")
    
    # Test 2: With gapFillInitialBar
    print("\nTest 2: With gapFillInitialBar=True")
    request = service.createRequest("IntradayBarRequest")
    request.set("security", "USDCNH Curncy")
    request.set("eventType", "BID")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    try:
        request.set("gapFillInitialBar", True)
    except:
        print("  gapFillInitialBar not supported")
    
    session.sendRequest(request)
    count2, sat2 = count_bars(session)
    print(f"  Total: {count2}, Saturday: {sat2}")
    
    # Test 3: With adjustmentNormal
    print("\nTest 3: With adjustmentNormal=True")
    request = service.createRequest("IntradayBarRequest")
    request.set("security", "USDCNH Curncy")
    request.set("eventType", "BID")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    try:
        request.set("adjustmentNormal", True)
    except:
        print("  adjustmentNormal not supported")
    
    session.sendRequest(request)
    count3, sat3 = count_bars(session)
    print(f"  Total: {count3}, Saturday: {sat3}")
    
    # Test 4: eventType = TRADE
    print("\nTest 4: eventType=TRADE")
    request = service.createRequest("IntradayBarRequest")
    request.set("security", "USDCNH Curncy")
    request.set("eventType", "TRADE")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    count4, sat4 = count_bars(session)
    print(f"  Total: {count4}, Saturday: {sat4}")
    
    # Test 5: Try BGN (Bloomberg Generic) price source
    print("\nTest 5: USDCNH BGN Curncy")
    request = service.createRequest("IntradayBarRequest")
    request.set("security", "USDCNH BGN Curncy")
    request.set("eventType", "TRADE")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    count5, sat5 = count_bars(session)
    print(f"  Total: {count5}, Saturday: {sat5}")
    
    # Test 6: Try CMPT (Composite)
    print("\nTest 6: USDCNH CMPT Curncy")
    request = service.createRequest("IntradayBarRequest")
    request.set("security", "USDCNH CMPT Curncy")
    request.set("eventType", "TRADE")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    count6, sat6 = count_bars(session)
    print(f"  Total: {count6}, Saturday: {sat6}")
    
    session.stop()


def count_bars(session):
    total = 0
    sat = 0
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("responseError"):
                print(f"  Error: {msg.getElement('responseError')}")
            if msg.hasElement("barData"):
                bar_data = msg.getElement("barData")
                if bar_data.hasElement("barTickData"):
                    tick_data = bar_data.getElement("barTickData")
                    for i in range(tick_data.numValues()):
                        bar = tick_data.getValueAsElement(i)
                        ts = bar.getElementAsDatetime("time")
                        total += 1
                        if hasattr(ts, 'weekday') and ts.weekday() == 5:
                            sat += 1
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    return total, sat


if __name__ == "__main__":
    test_with_params()
