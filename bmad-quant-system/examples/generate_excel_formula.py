"""
Generate Excel BDH formula for downloading JPYCNH Saturday data
===============================================================

Since Bloomberg API doesn't return Saturday tick data,
but Excel BDH function might have access to more data,
this script generates the Excel formula to use.

Instructions:
1. Open Excel with Bloomberg Terminal connected
2. Copy and paste the BDH formula into a cell
3. The data will populate automatically
4. Export to CSV/XLSX for analysis
"""

from datetime import datetime, timedelta

def generate_bdh_formula():
    """Generate Excel BDH formula for JPYCNH bid/ask data"""
    
    print("=" * 70)
    print("Excel BDH Formula Generator for JPYCNH Weekend Data")
    print("=" * 70)
    
    # Calculate date range (last 6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # BDH formula for intraday data
    # Note: This requires Bloomberg Terminal Excel Add-in
    
    print("\n" + "=" * 70)
    print("METHOD 1: Excel BDH Formula (for Intraday Bars)")
    print("=" * 70)
    
    formula_bid = f'''=BDH("JPYCNH Curncy", "PX_BID", "{start_date.strftime('%Y/%m/%d')}", "{end_date.strftime('%Y/%m/%d')}", "BarTp=B", "BarSz=1", "Dir=V", "Dts=H", "Fill=P", "cols=1;rows=500000")'''
    
    formula_ask = f'''=BDH("JPYCNH Curncy", "PX_ASK", "{start_date.strftime('%Y/%m/%d')}", "{end_date.strftime('%Y/%m/%d')}", "BarTp=B", "BarSz=1", "Dir=V", "Dts=H", "Fill=P", "cols=1;rows=500000")'''
    
    print("\nBID Price Formula (paste in cell A1):")
    print(formula_bid)
    
    print("\nASK Price Formula (paste in cell C1):")
    print(formula_ask)
    
    print("\n" + "=" * 70)
    print("METHOD 2: Excel BSRCH/BEQS for Historical Tick Data")
    print("=" * 70)
    
    # Alternative: Use BDH with specific event types
    formula_tick = f'''=BDH("JPYCNH Curncy", "PX_BID, PX_ASK", "{start_date.strftime('%Y/%m/%d')}", "{end_date.strftime('%Y/%m/%d')}", "BarTp=B", "BarSz=1", "Dir=V", "Dts=H", "UseDPDF=Y")'''
    
    print("\nCombined BID/ASK Formula:")
    print(formula_tick)
    
    print("\n" + "=" * 70)
    print("METHOD 3: Excel BDH with Bar Size in Seconds")  
    print("=" * 70)
    
    # Try different bar sizes
    for bar_size in [1, 10, 60]:
        formula = f'''=BDH("JPYCNH Curncy", "OPEN, HIGH, LOW, CLOSE, VOLUME", "{start_date.strftime('%Y/%m/%d')}", "{end_date.strftime('%Y/%m/%d')}", "BarTp=B", "BarSz={bar_size}", "Dir=V")'''
        print(f"\nBar Size = {bar_size} seconds:")
        print(formula)
    
    print("\n" + "=" * 70)
    print("IMPORTANT NOTES")
    print("=" * 70)
    print("""
1. Make sure Bloomberg Terminal is running and you're logged in
2. The Excel Add-in must be enabled (check Bloomberg menu in Excel)
3. If formula returns #N/A, try:
   - Reducing the date range
   - Changing BarTp to "T" (trade) or "A" (ask)
   - Using different BarSz values
   
4. For Saturday specific data, you may need to use:
   - Bloomberg Terminal: ALLQ (All Quotes) function
   - Or filter the downloaded data for Saturday only

5. Save the data as .xlsx after download for our analysis script
""")
    
    print("\n" + "=" * 70)
    print("ALTERNATIVE: Check Your USDCNH Data Source")
    print("=" * 70)
    print("""
Your USDCNH file 'USDCNH_Curncy_bidask_1s_20260116_144224.xlsx' contains
Saturday data. Please check how this file was created:

1. If from Excel BDH: Use the same formula for JPYCNH
2. If from internal system: Request JPYCNH data the same way
3. If manually exported: Export JPYCNH from Bloomberg Terminal

Once you have JPYCNH data with Saturday quotes, save it to:
  output/JPYCNH_Curncy_bidask_1s_YYYYMMDD_HHMMSS.xlsx

Then run the analysis script again.
""")


if __name__ == "__main__":
    generate_bdh_formula()
