"""
Try to download JPYCNH Saturday data using various Bloomberg methods
"""
import blpapi
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def get_historical_data(session, security, start_date, end_date):
    """Get historical daily data"""
    refDataService = session.getService("//blp/refdata")
    
    request = refDataService.createRequest("HistoricalDataRequest")
    request.append("securities", security)
    request.append("fields", "PX_BID")
    request.append("fields", "PX_ASK")
    request.append("fields", "PX_LAST")
    request.set("startDate", start_date.strftime("%Y%m%d"))
    request.set("endDate", end_date.strftime("%Y%m%d"))
    request.set("periodicitySelection", "DAILY")
    
    session.sendRequest(request)
    
    data = []
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("securityData"):
                secData = msg.getElement("securityData")
                if secData.hasElement("fieldData"):
                    fieldDataArray = secData.getElement("fieldData")
                    for i in range(fieldDataArray.numValues()):
                        fieldData = fieldDataArray.getValueAsElement(i)
                        row = {'date': fieldData.getElementAsDatetime("date")}
                        for field in ["PX_BID", "PX_ASK", "PX_LAST"]:
                            if fieldData.hasElement(field):
                                row[field] = fieldData.getElementAsFloat(field)
                        data.append(row)
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    
    return pd.DataFrame(data)


def try_intraday_tick_extended(session, security, start_time, end_time):
    """Try extended tick request"""
    refDataService = session.getService("//blp/refdata")
    
    request = refDataService.createRequest("IntradayTickRequest")
    request.set("security", security)
    request.append("eventTypes", "BID")
    request.append("eventTypes", "ASK")
    request.set("startDateTime", start_time)
    request.set("endDateTime", end_time)
    request.set("includeConditionCodes", True)
    request.set("includeNonPlottableEvents", True)  # Include all events
    request.set("includeExchangeCodes", True)
    
    session.sendRequest(request)
    
    ticks = []
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("tickData"):
                tickData = msg.getElement("tickData")
                if tickData.hasElement("tickData"):
                    tickArray = tickData.getElement("tickData")
                    for i in range(tickArray.numValues()):
                        tick = tickArray.getValueAsElement(i)
                        ticks.append({
                            'time': tick.getElementAsDatetime("time"),
                            'type': tick.getElementAsString("type"),
                            'value': tick.getElementAsFloat("value"),
                        })
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    
    return ticks


def main():
    print("=" * 60)
    print("Try Various Methods for JPYCNH Saturday Data")
    print("=" * 60)
    
    # Connect
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost("localhost")
    sessionOptions.setServerPort(8194)
    
    session = blpapi.Session(sessionOptions)
    session.start()
    session.openService("//blp/refdata")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Test 1: Historical daily data (check if Saturday included)
    print("\n[TEST 1] Historical Daily Data - Check if Saturday included")
    df = get_historical_data(session, "JPYCNH Curncy", start_date, end_date)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['weekday'] = df['date'].dt.dayofweek
        print(f"  Total days: {len(df)}")
        print(f"  Saturday count: {len(df[df['weekday']==5])}")
        print(f"  Sunday count: {len(df[df['weekday']==6])}")
        print(f"\n  Sample data:")
        print(df.tail(10))
    
    # Test 2: Try tick with extended options for recent Saturday
    print("\n[TEST 2] Extended Tick Request for Last Saturday")
    today = datetime.now()
    days_since_saturday = (today.weekday() - 5) % 7
    if days_since_saturday == 0 and today.weekday() != 5:
        days_since_saturday = 7
    last_saturday = today - timedelta(days=days_since_saturday)
    
    # Friday 22:00 to Saturday 06:00
    start_time = (last_saturday - timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
    end_time = last_saturday.replace(hour=6, minute=0, second=0, microsecond=0)
    
    print(f"  Time range: {start_time} ~ {end_time}")
    
    ticks = try_intraday_tick_extended(session, "JPYCNH Curncy", start_time, end_time)
    print(f"  Ticks received: {len(ticks)}")
    
    if ticks:
        df = pd.DataFrame(ticks)
        df['time'] = pd.to_datetime(df['time'])
        df['weekday'] = df['time'].dt.dayofweek
        sat_ticks = df[df['weekday'] == 5]
        print(f"  Saturday ticks: {len(sat_ticks)}")
        if not sat_ticks.empty:
            print(f"  Saturday time range: {sat_ticks['time'].min()} ~ {sat_ticks['time'].max()}")
    
    # Test 3: Try USDCNH to compare
    print("\n[TEST 3] Compare with USDCNH (same method)")
    ticks_usd = try_intraday_tick_extended(session, "USDCNH Curncy", start_time, end_time)
    print(f"  USDCNH Ticks received: {len(ticks_usd)}")
    
    if ticks_usd:
        df_usd = pd.DataFrame(ticks_usd)
        df_usd['time'] = pd.to_datetime(df_usd['time'])
        df_usd['weekday'] = df_usd['time'].dt.dayofweek
        sat_ticks_usd = df_usd[df_usd['weekday'] == 5]
        print(f"  USDCNH Saturday ticks: {len(sat_ticks_usd)}")
        if not sat_ticks_usd.empty:
            print(f"  Saturday time range: {sat_ticks_usd['time'].min()} ~ {sat_ticks_usd['time'].max()}")
    
    session.stop()
    print("\n[DONE]")
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    print("""
If both JPYCNH and USDCNH have no Saturday ticks via Bloomberg API,
but your USDCNH Excel file has Saturday data, then:

1. Your USDCNH data was obtained through a DIFFERENT source
   (possibly Excel BDH function with special parameters,
   or a third-party data provider)

2. To get JPYCNH Saturday data, you need to use the SAME method
   that was used to get USDCNH data

QUESTION: How was the USDCNH_Curncy_bidask_1s_20260116_144224.xlsx
file created? This will help us get JPYCNH data the same way.
""")


if __name__ == "__main__":
    main()
