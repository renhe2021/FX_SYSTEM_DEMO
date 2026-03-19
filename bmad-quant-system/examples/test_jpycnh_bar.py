"""
Download JPYCNH Bid/Ask Bar Data - Direct Bar Request
Try different event types and intervals
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import blpapi

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def download_jpycnh_direct_bar():
    """
    Direct Bloomberg IntradayBarRequest for JPYCNH
    """
    print("=" * 60)
    print("Download JPYCNH - Direct IntradayBarRequest")
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
    
    # Test different configurations
    end_date = datetime.now()
    
    # Test 1: Recent week with BID event type
    print("\n[TEST 1] JPYCNH with BID event type, 1 week")
    start_date = end_date - timedelta(days=7)
    
    request = refDataService.createRequest("IntradayBarRequest")
    request.set("security", "JPYCNH Curncy")
    request.set("eventType", "BID")  # BID event type
    request.set("interval", 1)  # 1 minute
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    print(f"  Request: {start_date} ~ {end_date}")
    session.sendRequest(request)
    
    bid_data = []
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("barData"):
                barData = msg.getElement("barData")
                if barData.hasElement("barTickData"):
                    tickData = barData.getElement("barTickData")
                    for i in range(tickData.numValues()):
                        bar = tickData.getValueAsElement(i)
                        bid_data.append({
                            'timestamp': bar.getElementAsDatetime("time"),
                            'open': bar.getElementAsFloat("open"),
                            'high': bar.getElementAsFloat("high"),
                            'low': bar.getElementAsFloat("low"),
                            'close': bar.getElementAsFloat("close"),
                        })
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    
    print(f"  BID bars received: {len(bid_data)}")
    
    if bid_data:
        df = pd.DataFrame(bid_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['weekday'] = df['timestamp'].dt.dayofweek
        df['hour'] = df['timestamp'].dt.hour
        
        # Check Saturday data
        sat_data = df[(df['weekday'] == 5)]
        print(f"  Saturday data rows: {len(sat_data)}")
        
        if not sat_data.empty:
            print(f"  Saturday time range: {sat_data['timestamp'].min()} ~ {sat_data['timestamp'].max()}")
            print(f"  Saturday high range: {sat_data['high'].min():.4f} ~ {sat_data['high'].max():.4f}")
            print(f"  Unique high values: {sat_data['high'].nunique()}")
    
    # Test 2: ASK event type
    print("\n[TEST 2] JPYCNH with ASK event type, 1 week")
    
    request = refDataService.createRequest("IntradayBarRequest")
    request.set("security", "JPYCNH Curncy")
    request.set("eventType", "ASK")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    
    ask_data = []
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("barData"):
                barData = msg.getElement("barData")
                if barData.hasElement("barTickData"):
                    tickData = barData.getElement("barTickData")
                    for i in range(tickData.numValues()):
                        bar = tickData.getValueAsElement(i)
                        ask_data.append({
                            'timestamp': bar.getElementAsDatetime("time"),
                            'open': bar.getElementAsFloat("open"),
                            'high': bar.getElementAsFloat("high"),
                            'low': bar.getElementAsFloat("low"),
                            'close': bar.getElementAsFloat("close"),
                        })
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    
    print(f"  ASK bars received: {len(ask_data)}")
    
    if ask_data:
        df = pd.DataFrame(ask_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['weekday'] = df['timestamp'].dt.dayofweek
        
        sat_data = df[(df['weekday'] == 5)]
        print(f"  Saturday data rows: {len(sat_data)}")
        
        if not sat_data.empty:
            print(f"  Saturday time range: {sat_data['timestamp'].min()} ~ {sat_data['timestamp'].max()}")
            print(f"  Saturday high range: {sat_data['high'].min():.4f} ~ {sat_data['high'].max():.4f}")
    
    # Test 3: Try TRADE event type (might have data)
    print("\n[TEST 3] JPYCNH with TRADE event type")
    
    request = refDataService.createRequest("IntradayBarRequest")
    request.set("security", "JPYCNH Curncy")
    request.set("eventType", "TRADE")
    request.set("interval", 1)
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    
    trade_data = []
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("barData"):
                barData = msg.getElement("barData")
                if barData.hasElement("barTickData"):
                    tickData = barData.getElement("barTickData")
                    for i in range(tickData.numValues()):
                        bar = tickData.getValueAsElement(i)
                        trade_data.append({
                            'timestamp': bar.getElementAsDatetime("time"),
                            'close': bar.getElementAsFloat("close"),
                        })
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    
    print(f"  TRADE bars received: {len(trade_data)}")
    
    # Test 4: Try longer history (140 days) with BID
    print("\n[TEST 4] JPYCNH BID bars - 140 days history")
    start_date = end_date - timedelta(days=140)
    
    request = refDataService.createRequest("IntradayBarRequest")
    request.set("security", "JPYCNH Curncy")
    request.set("eventType", "BID")
    request.set("interval", 10)  # 10 minute bars
    request.set("startDateTime", start_date)
    request.set("endDateTime", end_date)
    
    session.sendRequest(request)
    
    long_data = []
    while True:
        event = session.nextEvent(5000)
        for msg in event:
            if msg.hasElement("barData"):
                barData = msg.getElement("barData")
                if barData.hasElement("barTickData"):
                    tickData = barData.getElement("barTickData")
                    for i in range(tickData.numValues()):
                        bar = tickData.getValueAsElement(i)
                        long_data.append({
                            'timestamp': bar.getElementAsDatetime("time"),
                            'high': bar.getElementAsFloat("high"),
                            'low': bar.getElementAsFloat("low"),
                            'close': bar.getElementAsFloat("close"),
                        })
        if event.eventType() == blpapi.Event.RESPONSE:
            break
    
    print(f"  Total bars received: {len(long_data)}")
    
    if long_data:
        df = pd.DataFrame(long_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['weekday'] = df['timestamp'].dt.dayofweek
        df['hour'] = df['timestamp'].dt.hour
        
        # Saturday 00:00-06:00
        sat_data = df[(df['weekday'] == 5) & (df['hour'] < 6)]
        print(f"  Saturday 00-06 rows: {len(sat_data)}")
        
        if not sat_data.empty:
            sat_data = sat_data.copy()
            sat_data['date'] = sat_data['timestamp'].dt.date
            
            print(f"\n  Saturday dates with data:")
            for d in sorted(sat_data['date'].unique()):
                day_df = sat_data[sat_data['date'] == d]
                print(f"    {d}: {len(day_df)} bars, high range: {day_df['high'].min():.4f} ~ {day_df['high'].max():.4f}, unique: {day_df['high'].nunique()}")
    
    session.stop()
    print("\n[DONE]")


if __name__ == "__main__":
    download_jpycnh_direct_bar()
