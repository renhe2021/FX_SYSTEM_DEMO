"""
波动率加权 Markup 引擎 V3 — Bloomberg API (10min, 4-month lookback)
- 通过 Bloomberg Desktop API 拉取各币种兑CNY 过去4个月的 10 分钟级 MID 价
- 每次计算都实时拉取，不缓存
- 用 MID = (High + Low) / 2 的 log return 计算已实现波动率
- 按波动率加权分配 markup，使得交易量加权平均 = 目标 BPS
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import json, os, time

# ─── Bloomberg 币种 Ticker 映射 ───
# BBG FX ticker 格式: XXXCNY Curncy
BBG_CCY_TICKERS = {
    'USD': 'USDCNY Curncy',
    'HKD': 'HKDCNY Curncy',
    'EUR': 'EURCNY Curncy',
    'GBP': 'GBPCNY Curncy',
    'MOP': None,           # MOP 挂钩 HKD，BBG 无直接 MOPCNY
    'SGD': 'SGDCNY Curncy',
    'JPY': 'JPYCNY Curncy',
    'CAD': 'CADCNY Curncy',
    'THB': 'THBCNY Curncy',
    'AUD': 'AUDCNY Curncy',
    'SEK': 'SEKCNY Curncy',
    'NZD': 'NZDCNY Curncy',
    'CHF': 'CHFCNY Curncy',
}

# 挂钩币种：直接复用被挂钩币种的波动率
CCY_PEGGED = {
    'MOP': 'HKD',
}

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'vol_cache')


# ═══════════════════════════════════════════════
#  Bloomberg Data Fetch
# ═══════════════════════════════════════════════

def _create_bbg_session():
    """创建并启动 BBG Session"""
    import blpapi
    opts = blpapi.SessionOptions()
    opts.setServerHost('localhost')
    opts.setServerPort(8194)
    session = blpapi.Session(opts)
    if not session.start():
        raise ConnectionError("Failed to start Bloomberg session. Is BBG Terminal running?")
    return session


def fetch_bbg_intraday_bars(ticker: str, interval: int = 10, days_back: int = 120) -> pd.DataFrame:
    """
    通过 BBG IntradayBarRequest 拉取 intraday bar 数据
    
    BBG IntradayBarRequest 对于 FX 最多支持 140 天回溯。
    我们用 10 分钟 interval、4 个月(~120天)。
    
    因为 BBG 单次请求可能有行数限制，我们按月分段拉取后合并。
    
    Returns: DataFrame with columns: [open, high, low, close, volume, numEvents, mid]
    """
    import blpapi

    all_rows = []
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days_back)

    # 按 ~30 天分段拉取，避免单次请求数据量过大
    chunk_days = 30
    seg_end = end_dt
    seg_start = max(start_dt, seg_end - timedelta(days=chunk_days))

    while seg_start < seg_end:
        print(f"    [{ticker}] pulling {seg_start.strftime('%Y-%m-%d')} ~ {seg_end.strftime('%Y-%m-%d')} ...", end=' ')
        session = _create_bbg_session()
        try:
            if not session.openService("//blp/refdata"):
                raise ConnectionError("Failed to open //blp/refdata service")

            refdata = session.getService("//blp/refdata")
            request = refdata.createRequest("IntradayBarRequest")
            request.set("security", ticker)
            request.set("eventType", "TRADE")
            request.set("interval", interval)

            request.set("startDateTime", seg_start)
            request.set("endDateTime", seg_end)

            session.sendRequest(request)

            rows = []
            while True:
                event = session.nextEvent(10000)
                for msg in event:
                    if msg.hasElement("barData"):
                        bar_data = msg.getElement("barData")
                        if bar_data.hasElement("barTickData"):
                            tick_data = bar_data.getElement("barTickData")
                            for i in range(tick_data.numValues()):
                                bar = tick_data.getValueAsElement(i)
                                rows.append({
                                    'time': bar.getElementAsDatetime("time"),
                                    'open': bar.getElementAsFloat("open"),
                                    'high': bar.getElementAsFloat("high"),
                                    'low': bar.getElementAsFloat("low"),
                                    'close': bar.getElementAsFloat("close"),
                                    'volume': bar.getElementAsInteger("volume") if bar.hasElement("volume") else 0,
                                    'numEvents': bar.getElementAsInteger("numEvents") if bar.hasElement("numEvents") else 0,
                                })
                if event.eventType() == blpapi.Event.RESPONSE:
                    break

            print(f"{len(rows)} bars")
            all_rows.extend(rows)
        finally:
            session.stop()

        # 下一个分段
        seg_end = seg_start
        seg_start = max(start_dt, seg_end - timedelta(days=chunk_days))
        if seg_start >= seg_end:
            break

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df['time'] = pd.to_datetime(df['time'])
    df = df.drop_duplicates(subset='time').set_index('time').sort_index()
    # MID = (high + low) / 2 作为每根 bar 的 mid price
    df['mid'] = (df['high'] + df['low']) / 2.0
    print(f"    [{ticker}] Total: {len(df)} bars over {days_back} days, "
          f"range: {df.index[0]} ~ {df.index[-1]}")
    return df


def fetch_bbg_reference_mid(ticker: str) -> float:
    """获取当前 MID 价 (PX_MID)"""
    import blpapi

    session = _create_bbg_session()
    try:
        if not session.openService("//blp/refdata"):
            return None

        refdata = session.getService("//blp/refdata")
        request = refdata.createRequest("ReferenceDataRequest")
        request.append("securities", ticker)
        request.append("fields", "PX_MID")
        session.sendRequest(request)

        while True:
            event = session.nextEvent(5000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    for i in range(sec_data.numValues()):
                        sec = sec_data.getValueAsElement(i)
                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            if fd.hasElement("PX_MID"):
                                return fd.getElementAsFloat("PX_MID")
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        return None
    finally:
        session.stop()


def fetch_bbg_historical_mid(ticker: str, days_back: int = 30) -> pd.DataFrame:
    """
    通过 BBG HistoricalDataRequest 拉取日级 MID 数据作为备用
    """
    import blpapi

    session = _create_bbg_session()
    try:
        if not session.openService("//blp/refdata"):
            return pd.DataFrame()

        refdata = session.getService("//blp/refdata")
        request = refdata.createRequest("HistoricalDataRequest")
        request.append("securities", ticker)
        request.append("fields", "PX_MID")
        request.append("fields", "PX_HIGH")
        request.append("fields", "PX_LOW")

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days_back)
        request.set("startDate", start_dt.strftime("%Y%m%d"))
        request.set("endDate", end_dt.strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")

        session.sendRequest(request)

        rows = []
        while True:
            event = session.nextEvent(5000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    if sec_data.hasElement("fieldData"):
                        fd_array = sec_data.getElement("fieldData")
                        for i in range(fd_array.numValues()):
                            fd = fd_array.getValueAsElement(i)
                            row = {'date': fd.getElementAsDatetime("date")}
                            if fd.hasElement("PX_MID"):
                                row['mid'] = fd.getElementAsFloat("PX_MID")
                            if fd.hasElement("PX_HIGH"):
                                row['high'] = fd.getElementAsFloat("PX_HIGH")
                            if fd.hasElement("PX_LOW"):
                                row['low'] = fd.getElementAsFloat("PX_LOW")
                            rows.append(row)
            if event.eventType() == blpapi.Event.RESPONSE:
                break

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        return df

    finally:
        session.stop()


# ═══════════════════════════════════════════════
#  Volatility Computation
# ═══════════════════════════════════════════════

def compute_volatility(prices: pd.Series, interval_minutes: int = 1) -> dict:
    """
    计算多维度波动率指标，基于 MID 价的 log return
    
    Args:
        prices: MID price series
        interval_minutes: bar 间隔（分钟），用于年化因子
    """
    if len(prices) < 30:
        return {'realized_vol_annual': 0, 'realized_vol_pct': 0, 'data_points': 0}

    # 过滤掉 0 和 NaN
    prices = prices[prices > 0].dropna()
    if len(prices) < 30:
        return {'realized_vol_annual': 0, 'realized_vol_pct': 0, 'data_points': 0}

    log_returns = np.log(prices / prices.shift(1)).dropna()

    # 年化因子
    # FX 市场约 252 交易日, 每天约 22 小时活跃 (亚洲+欧洲+美洲)
    # bars_per_day = 22h * 60min / interval_minutes
    bars_per_day = 22 * 60 / interval_minutes
    bars_per_year = 252 * bars_per_day

    annualize = np.sqrt(bars_per_year)
    realized_vol = float(log_returns.std() * annualize)

    # 每分钟平均绝对变动 (BPS)
    avg_abs_return_bps = float(log_returns.abs().mean() * 10000)

    return {
        'realized_vol_annual': round(realized_vol, 6),
        'realized_vol_pct': round(realized_vol * 100, 4),
        'avg_move_bps': round(avg_abs_return_bps, 2),
        'std_move_bps': round(float(log_returns.std() * 10000), 2),
        'max_move_bps': round(float(log_returns.abs().max() * 10000), 2),
        'data_points': len(log_returns),
    }


# ═══════════════════════════════════════════════
#  Main: Fetch All Volatilities
# ═══════════════════════════════════════════════

def fetch_all_volatilities(ccys: list = None, use_cache: bool = False, max_age_hours: int = 0,
                           interval: int = 10, days_back: int = 120) -> dict:
    """
    获取所有币种的波动率 — 每次实时从 BBG 拉取
    
    Args:
        interval: bar 间隔（分钟），默认 10 分钟
        days_back: 回溯天数，默认 120 天（~4个月）
    """
    if ccys is None:
        ccys = list(BBG_CCY_TICKERS.keys())

    print(f"[VOL] Fetching {days_back}-day, {interval}-min bar data for {len(ccys)} currencies via Bloomberg API...")
    print(f"[VOL] Each fetch is LIVE (no cache)")
    result = {}
    bbg_available = _check_bbg_available()

    for ccy in ccys:
        if ccy in CCY_PEGGED:
            continue

        ticker = BBG_CCY_TICKERS.get(ccy)
        print(f"\n  === {ccy} ({ticker}) ===")

        if bbg_available and ticker:
            # ─── BBG: 10 分钟级 IntradayBar, 4 个月 ───
            try:
                df = fetch_bbg_intraday_bars(ticker, interval=interval, days_back=days_back)
                if len(df) > 30:
                    vol = compute_volatility(df['mid'], interval_minutes=interval)
                    vol['data_source'] = f'BBG-{interval}min-MID'
                    vol['data_period'] = f'{days_back}d'
                    vol['ticker'] = ticker
                    vol['last_price'] = round(float(df['mid'].iloc[-1]), 6)
                    result[ccy] = vol
                    print(f"  -> OK: {vol['data_points']} return pts, vol={vol['realized_vol_pct']:.2f}%")
                    continue
            except Exception as e:
                print(f"  -> BBG intraday failed: {e}")

            # ─── BBG: 日级 Historical MID (fallback) ───
            try:
                df_d = fetch_bbg_historical_mid(ticker, days_back=days_back)
                if len(df_d) > 10 and 'mid' in df_d.columns:
                    vol = compute_volatility(df_d['mid'], interval_minutes=1440)
                    vol['data_source'] = 'BBG-daily-MID'
                    vol['data_period'] = f'{days_back}d'
                    vol['ticker'] = ticker
                    vol['last_price'] = round(float(df_d['mid'].iloc[-1]), 6)
                    result[ccy] = vol
                    print(f"  -> BBG-daily OK: {vol['data_points']} pts, vol={vol['realized_vol_pct']:.2f}%")
                    continue
            except Exception as e:
                print(f"  -> BBG daily failed: {e}")

        # ─── Fallback: yfinance ───
        try:
            vol_yf = _fetch_yfinance_vol(ccy)
            if vol_yf:
                result[ccy] = vol_yf
                print(f"  -> yfinance OK: {vol_yf['data_points']} pts, vol={vol_yf['realized_vol_pct']:.2f}%")
                continue
        except Exception as e:
            print(f"  -> yfinance failed: {e}")

        # ─── 最终 fallback ───
        print("  -> FAILED - using fallback estimate")
        result[ccy] = {
            'realized_vol_annual': 0.05, 'realized_vol_pct': 5.0,
            'avg_move_bps': 3.0, 'std_move_bps': 3.0, 'max_move_bps': 15.0,
            'data_points': 0, 'data_source': 'fallback', 'data_period': 'N/A',
        }

    # 处理挂钩币种
    for pegged_ccy, ref_ccy in CCY_PEGGED.items():
        if ref_ccy in result:
            result[pegged_ccy] = dict(result[ref_ccy])
            result[pegged_ccy]['data_source'] = f'pegged->{ref_ccy}'
            print(f"\n  {pegged_ccy}: using {ref_ccy} vol (pegged)")
        else:
            result[pegged_ccy] = {
                'realized_vol_annual': 0.03, 'realized_vol_pct': 3.0,
                'avg_move_bps': 2.0, 'std_move_bps': 2.0, 'max_move_bps': 10.0,
                'data_points': 0, 'data_source': 'fallback', 'data_period': 'N/A',
            }

    print(f"\n[VOL] Done. {len(result)} currencies processed.")
    return result


def _check_bbg_available() -> bool:
    """检查 BBG Desktop API 是否可用"""
    try:
        import blpapi
        opts = blpapi.SessionOptions()
        opts.setServerHost('localhost')
        opts.setServerPort(8194)
        s = blpapi.Session(opts)
        ok = s.start()
        s.stop()
        if ok:
            print("[VOL] Bloomberg Desktop API: CONNECTED")
        return ok
    except:
        print("[VOL] Bloomberg Desktop API: NOT AVAILABLE, will use yfinance fallback")
        return False


def _fetch_yfinance_vol(ccy: str) -> dict:
    """yfinance fallback"""
    import yfinance as yf

    YF_TICKERS = {
        'USD': 'USDCNY=X', 'HKD': 'HKDCNY=X', 'EUR': 'EURCNY=X',
        'GBP': 'GBPCNY=X', 'SGD': 'SGDCNY=X', 'JPY': 'JPYCNY=X',
        'CAD': 'CADCNY=X', 'THB': 'THBCNY=X', 'AUD': 'AUDCNY=X',
        'SEK': 'SEKCNY=X', 'NZD': 'NZDCNY=X', 'CHF': 'CHFCNY=X',
    }
    ticker = YF_TICKERS.get(ccy)
    if not ticker:
        return None

    df = yf.download(ticker, period='5d', interval='1m', progress=False)
    if df is None or len(df) < 30:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    vol = compute_volatility(df['Close'], interval_minutes=1)
    vol['data_source'] = 'yfinance-1min'
    vol['data_period'] = '5d'
    return vol


# ═══════════════════════════════════════════════
#  Markup Allocation
# ═══════════════════════════════════════════════

def compute_vol_weighted_markups(volumes: dict, vol_data: dict, target_avg_bps: float = 0.5) -> dict:
    """
    基于波动率加权计算每个币种的 markup，使得交易量加权平均 = target_avg_bps

    markup_i = target_avg_bps * (vol_i / vol_weighted_avg)
    vol_weighted_avg = sum(volume_i * vol_i) / sum(volume_i)
    """
    active_ccys = {ccy: vol for ccy, vol in volumes.items() if vol > 0}
    total_volume = sum(active_ccys.values())

    if total_volume == 0:
        return {}

    ccy_vols = {}
    for ccy in active_ccys:
        if ccy in vol_data and vol_data[ccy].get('realized_vol_annual', 0) > 0:
            ccy_vols[ccy] = vol_data[ccy]['realized_vol_annual']
        else:
            known_vols = [v['realized_vol_annual'] for v in vol_data.values() if v.get('realized_vol_annual', 0) > 0]
            ccy_vols[ccy] = np.median(known_vols) if known_vols else 0.05

    vol_weighted_avg = sum(active_ccys[ccy] * ccy_vols[ccy] for ccy in active_ccys) / total_volume
    if vol_weighted_avg == 0:
        vol_weighted_avg = 0.05

    result = {}
    for ccy in active_ccys:
        raw_markup = target_avg_bps * (ccy_vols[ccy] / vol_weighted_avg)
        markup = max(0.1, min(raw_markup, target_avg_bps * 5))
        result[ccy] = {
            'ccy': ccy,
            'volume': active_ccys[ccy],
            'volume_pct': round(active_ccys[ccy] / total_volume * 100, 2),
            'realized_vol_pct': round(ccy_vols[ccy] * 100, 4),
            'realized_vol_annual': round(ccy_vols[ccy], 6),
            'avg_move_bps': vol_data.get(ccy, {}).get('avg_move_bps', 0),
            'raw_markup_bps': round(raw_markup, 4),
            'suggested_markup_bps': round(markup, 2),
            'monthly_revenue': round(active_ccys[ccy] * markup * 1e-4, 2),
            'data_source': vol_data.get(ccy, {}).get('data_source', 'N/A'),
        }

    actual_avg = sum(result[c]['volume'] * result[c]['suggested_markup_bps'] for c in result) / total_volume

    if abs(actual_avg - target_avg_bps) > 0.001:
        correction = target_avg_bps / actual_avg if actual_avg > 0 else 1
        for ccy in result:
            result[ccy]['suggested_markup_bps'] = round(result[ccy]['suggested_markup_bps'] * correction, 2)
            result[ccy]['monthly_revenue'] = round(result[ccy]['volume'] * result[ccy]['suggested_markup_bps'] * 1e-4, 2)
        actual_avg = sum(result[c]['volume'] * result[c]['suggested_markup_bps'] for c in result) / total_volume

    total_monthly_rev = sum(r['monthly_revenue'] for r in result.values())

    return {
        'ccys': result,
        'summary': {
            'target_avg_bps': target_avg_bps,
            'actual_weighted_avg_bps': round(actual_avg, 4),
            'total_volume': total_volume,
            'total_monthly_revenue': round(total_monthly_rev, 2),
            'total_annual_revenue': round(total_monthly_rev * 12, 2),
            'vol_weighted_avg': round(vol_weighted_avg, 6),
            'vol_weighted_avg_pct': round(vol_weighted_avg * 100, 4),
        }
    }


# ═══════════════════════════════════════════════
#  Main test
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 70)
    print("  Volatility Engine V3 — Bloomberg 10min MID, 4-month lookback")
    print("=" * 70)

    vol_data = fetch_all_volatilities(use_cache=False, interval=10, days_back=120)

    print("\n" + "=" * 70)
    print("  Volatility Results (sorted by vol desc):")
    print("=" * 70)
    print(f"  {'CCY':5s} {'Vol%':>7s} {'AvgMove':>8s} {'MaxMove':>8s} {'Source':>18s} {'Pts':>6s}")
    print("  " + "-" * 58)
    for ccy, v in sorted(vol_data.items(), key=lambda x: -x[1].get('realized_vol_annual', 0)):
        print(f"  {ccy:5s} {v['realized_vol_pct']:6.2f}% {v.get('avg_move_bps',0):6.1f}BPS "
              f"{v.get('max_move_bps',0):6.1f}BPS {v.get('data_source','?'):>18s} {v['data_points']:>5d}")

    test_volumes = {
        'USD': 5_560_841_299, 'HKD': 1_907_671_150, 'EUR': 938_652_894,
        'GBP': 504_303_471, 'MOP': 428_067_462, 'SGD': 276_464_884,
        'JPY': 119_552_928, 'CAD': 70_903_354, 'THB': 58_258_904,
        'AUD': 34_022_102, 'SEK': 20_102_004, 'NZD': 2_546_272, 'CHF': 189_641,
    }

    print("\n" + "=" * 70)
    print("  Vol-Weighted Markup Suggestion (target = 0.5 BPS):")
    print("=" * 70)
    result = compute_vol_weighted_markups(test_volumes, vol_data, target_avg_bps=0.5)

    print(f"  {'CCY':5s} {'Vol%':>7s} {'Markup':>8s} {'Volume':>12s} {'Pct':>6s} {'MonthlyRev':>12s} {'Source':>18s}")
    print("  " + "-" * 74)
    for ccy, r in sorted(result['ccys'].items(), key=lambda x: -x[1]['volume']):
        print(f"  {ccy:5s} {r['realized_vol_pct']:6.2f}% {r['suggested_markup_bps']:6.2f}BPS "
              f"{r['volume']/1e8:10.1f}yi {r['volume_pct']:5.1f}% "
              f"Y{r['monthly_revenue']:>10,.0f} {r.get('data_source',''):>18s}")

    s = result['summary']
    print(f"\n  Weighted Avg Markup: {s['actual_weighted_avg_bps']:.4f} BPS (target: {s['target_avg_bps']})")
    print(f"  Total Monthly Rev:  Y{s['total_monthly_revenue']:,.0f}")
    print(f"  Total Annual Rev:   Y{s['total_annual_revenue']:,.0f}")
