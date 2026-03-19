"""
Download JPYCNH Raw Tick Data - Check if Saturday has real ticks
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import blpapi

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def download_jpycnh_ticks():
    """
    Download raw tick data for JPYCNH to check Saturday activity
    """
    print("=" * 60)
    print("Download JPYCNH Raw Tick Data")
    print("=" * 60)
    
    # Connect to Bloomberg
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost("localhost")
    sessionOptions.setServerPort(8194)
    
    session = blpapi.Session(sessionOptions)
    
    if not session.start():
        print("[ERROR] Cannot start session")
        return None
    
    if not session.openService("//blp/refdata"):
        print("[ERROR] Cannot open refdata service")
        return None
    
    refDataService = session.getService("//blp/refdata")
    
    # Find last Saturday
    today = datetime.now()
    days_since_saturday = (today.weekday() - 5) % 7
    if days_since_saturday == 0 and today.weekday() != 5:
        days_since_saturday = 7
    last_saturday = today - timedelta(days=days_since_saturday)
    last_saturday = last_saturday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    print(f"\nLast Saturday: {last_saturday.strftime('%Y-%m-%d')}")
    
    # Download ticks for Saturday 00:00-06:00
    start_time = last_saturday
    end_time = last_saturday.replace(hour=6)
    
    print(f"Request: {start_time} ~ {end_time}")
    
    request = refDataService.createRequest("IntradayTickRequest")
    request.set("security", "JPYCNH Curncy")
    request.append("eventTypes", "BID")
    request.append("eventTypes", "ASK")
    request.set("startDateTime", start_time)
    request.set("endDateTime", end_time)
    request.set("includeConditionCodes", True)
    
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
    
    print(f"\nTotal ticks received: {len(ticks)}")
    
    if ticks:
        df = pd.DataFrame(ticks)
        df['time'] = pd.to_datetime(df['time'])
        
        print(f"\nTime range: {df['time'].min()} ~ {df['time'].max()}")
        print(f"Tick types: {df['type'].value_counts().to_dict()}")
        
        # Show sample
        print(f"\nFirst 20 ticks:")
        print(df.head(20))
        
        # Check value variation
        bid_ticks = df[df['type'] == 'BID']
        ask_ticks = df[df['type'] == 'ASK']
        
        if not bid_ticks.empty:
            print(f"\nBID: {bid_ticks['value'].min():.4f} ~ {bid_ticks['value'].max():.4f}, unique: {bid_ticks['value'].nunique()}")
        if not ask_ticks.empty:
            print(f"ASK: {ask_ticks['value'].min():.4f} ~ {ask_ticks['value'].max():.4f}, unique: {ask_ticks['value'].nunique()}")
    else:
        print("\n*** NO TICKS RECEIVED FOR SATURDAY ***")
        
        # Try Friday evening to Saturday morning
        print("\n\nTrying Friday evening ~ Saturday morning...")
        friday_evening = last_saturday - timedelta(days=1)
        friday_evening = friday_evening.replace(hour=20)
        
        request = refDataService.createRequest("IntradayTickRequest")
        request.set("security", "JPYCNH Curncy")
        request.append("eventTypes", "BID")
        request.append("eventTypes", "ASK")
        request.set("startDateTime", friday_evening)
        request.set("endDateTime", end_time)
        
        session.sendRequest(request)
        
        ticks2 = []
        while True:
            event = session.nextEvent(5000)
            for msg in event:
                if msg.hasElement("tickData"):
                    tickData = msg.getElement("tickData")
                    if tickData.hasElement("tickData"):
                        tickArray = tickData.getElement("tickData")
                        for i in range(tickArray.numValues()):
                            tick = tickArray.getValueAsElement(i)
                            ticks2.append({
                                'time': tick.getElementAsDatetime("time"),
                                'type': tick.getElementAsString("type"),
                                'value': tick.getElementAsFloat("value"),
                            })
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        print(f"Ticks from Friday 20:00 to Saturday 06:00: {len(ticks2)}")
        
        if ticks2:
            df2 = pd.DataFrame(ticks2)
            df2['time'] = pd.to_datetime(df2['time'])
            df2['hour'] = df2['time'].dt.hour
            df2['weekday'] = df2['time'].dt.dayofweek
            
            print(f"Time range: {df2['time'].min()} ~ {df2['time'].max()}")
            
            # Saturday ticks
            sat_ticks = df2[df2['weekday'] == 5]
            print(f"Saturday ticks: {len(sat_ticks)}")
            
            if not sat_ticks.empty:
                print(f"Saturday time range: {sat_ticks['time'].min()} ~ {sat_ticks['time'].max()}")
    
    session.stop()
    print("\n[DONE]")


if __name__ == "__main__":
    download_jpycnh_ticks()
