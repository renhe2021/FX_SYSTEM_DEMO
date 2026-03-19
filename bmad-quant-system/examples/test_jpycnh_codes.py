"""
Test different JPYCNH Bloomberg codes to find one with Saturday data
"""
import blpapi
from datetime import datetime, timedelta
import pandas as pd

def test_security(session, refDataService, security, event_type="BID"):
    """Test if a security has Saturday data"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    request = refDataService.createRequest("IntradayBarRequest")
    request.set("security", security)
    request.set("eventType", event_type)
    request.set("interval", 60)  # 60 min bars
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    
    data = []
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("barData"):
                barData = msg.getElement("barData")
                if barData.hasElement("barTickData"):
                    tickData = barData.getElement("barTickData")
                    for i in range(tickData.numValues()):
                        bar = tickData.getValueAsElement(i)
                        data.append({
                            'timestamp': bar.getElementAsDatetime("time"),
                            'close': bar.getElementAsFloat("close"),
                        })
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    
    if data:
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['weekday'] = df['timestamp'].dt.dayofweek
        sat_count = len(df[df['weekday'] == 5])
        return len(data), sat_count
    return 0, 0


def main():
    print("=" * 60)
    print("Test Different JPYCNH Bloomberg Codes")
    print("=" * 60)
    
    # Connect
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost("localhost")
    sessionOptions.setServerPort(8194)
    
    session = blpapi.Session(sessionOptions)
    session.start()
    session.openService("//blp/refdata")
    refDataService = session.getService("//blp/refdata")
    
    # Test different securities
    securities = [
        "JPYCNH Curncy",
        "CNHJPY Curncy",
        "JPY Curncy",
        "JPYCNY Curncy",
        "CNYJPY Curncy",
        "JPYCNH BGN Curncy",
        "JPYCNH CMPL Curncy", 
        "JPYCNH CMPT Curncy",
        "JPYCNH NDF Curncy",
    ]
    
    print("\nTesting securities for Saturday data (14 days, 60min bars):\n")
    print(f"{'Security':<25} {'Total Bars':<15} {'Saturday Bars':<15}")
    print("-" * 55)
    
    for sec in securities:
        try:
            total, sat = test_security(session, refDataService, sec)
            status = "HAS SAT DATA" if sat > 0 else ""
            print(f"{sec:<25} {total:<15} {sat:<15} {status}")
        except Exception as e:
            print(f"{sec:<25} ERROR: {str(e)[:30]}")
    
    # Also test USDCNH for comparison
    print("\n--- Comparison with USDCNH ---")
    for sec in ["USDCNH Curncy", "USDCNH BGN Curncy", "USDCNH CMPL Curncy"]:
        try:
            total, sat = test_security(session, refDataService, sec)
            status = "HAS SAT DATA" if sat > 0 else ""
            print(f"{sec:<25} {total:<15} {sat:<15} {status}")
        except Exception as e:
            print(f"{sec:<25} ERROR: {str(e)[:30]}")
    
    session.stop()
    print("\n[DONE]")


if __name__ == "__main__":
    main()
