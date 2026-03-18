# -*- coding: utf-8 -*-
"""
Weekend Price Data Fetcher (Bloomberg Only)
=============================================

从 Bloomberg 获取周末回测所需的价格数据，不使用任何 mock 数据。

数据获取逻辑:
1. Entry Price: 信号时刻 (周五晚 ~ 周六凌晨) 的 mid price (bid+ask)/2
2. Exit Price: 周六 02:00 的 ASK price (参考价)

使用方法:
    python weekend_price_fetcher.py

Author: FX Strategy Team
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from quant_system.tools.bbg_wrapper import BloombergWrapper, beijing_to_utc, utc_to_beijing, beijing_now
    HAS_BBG = True
except ImportError:
    HAS_BBG = False


class WeekendPriceDataFetcher:
    """
    周末策略价格数据获取器 (Bloomberg Only)
    
    强制从 Bloomberg 获取真实数据，不使用 mock 数据。
    如果 Bloomberg 不可用则直接报错退出。
    
    获取数据:
    1. Entry Price: 信号时刻的 mid price = (bid + ask) / 2
    2. Exit Price: 周六 02:00 北京时间的 ASK Price
    
    Usage:
    ------
    fetcher = WeekendPriceDataFetcher()
    fetcher.connect()  # 必须成功连接
    prices = fetcher.fetch_all_weekend_prices(
        symbol="USDCNH Curncy",
        signal_df=signal_df,  # 信号数据
    )
    fetcher.save_prices(prices, "weekend_prices_bbg.csv")
    fetcher.disconnect()
    """
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        if not HAS_BBG:
            raise RuntimeError(
                "Bloomberg wrapper (blpapi) 未安装或不可导入。\n"
                "请确保: 1) 安装了 blpapi  2) Bloomberg Terminal 正在运行\n"
                "本脚本不支持 mock 数据，必须连接 Bloomberg。"
            )
        
        self.host = host
        self.port = port
        self.bbg = BloombergWrapper(host, port)
        self._connected = False
    
    def connect(self) -> bool:
        """连接 Bloomberg（失败则抛出异常）"""
        if self.bbg.connect():
            self._connected = True
            print("[WeekendPrice] OK - 已连接 Bloomberg")
            return True
        else:
            raise ConnectionError(
                "无法连接 Bloomberg Terminal。\n"
                "请确保 Bloomberg Terminal 已启动并运行。"
            )
    
    def disconnect(self):
        """断开连接"""
        if self.bbg:
            self.bbg.disconnect()
            self._connected = False
            print("[WeekendPrice] OK - 已断开 Bloomberg 连接")
    
    def _ensure_connected(self):
        """确保已连接"""
        if not self._connected:
            raise ConnectionError("未连接 Bloomberg，请先调用 connect()")
    
    # =========================================================================
    # 核心价格获取方法
    # =========================================================================
    
    def get_exit_price(
        self, 
        symbol: str, 
        saturday_date: datetime,
        window_minutes: int = 30
    ) -> Tuple[Optional[float], Optional[datetime]]:
        """
        获取周六 02:00 北京时间附近的 ASK 价格（Exit Price）
        
        先尝试 get_bid_ask (tick级别)，如果失败则尝试 get_bid_ask_bars。
        
        Args:
            symbol: Bloomberg 代码，如 "USDCNH Curncy"
            saturday_date: 周六日期
            window_minutes: 在 02:00 前后搜索窗口（分钟）
        
        Returns:
            (ask_price, actual_time) 或 (None, None)
        """
        self._ensure_connected()
        
        # 目标: 周六 02:00 北京时间
        target_time = saturday_date.replace(hour=2, minute=0, second=0, microsecond=0)
        start_time = target_time - timedelta(minutes=window_minutes)
        end_time = target_time + timedelta(minutes=window_minutes)
        
        # --- 方法1: 使用 get_bid_ask (tick) ---
        try:
            df = self.bbg.get_bid_ask(
                symbol=symbol,
                start_date=start_time,
                end_date=end_time,
                is_beijing_time=True
            )
            
            if df is not None and not df.empty:
                ask_df = df[df['type'] == 'ASK'].copy()
                
                if not ask_df.empty:
                    # 转换 UTC -> 北京时间
                    ask_df.index = ask_df.index + timedelta(hours=8)
                    
                    # 找最接近 02:00 的
                    time_diff = abs(ask_df.index - target_time)
                    closest_idx = time_diff.argmin()
                    
                    ask_price = ask_df.iloc[closest_idx]['price']
                    actual_time = ask_df.index[closest_idx]
                    
                    print(f"  [Exit] {saturday_date.strftime('%Y-%m-%d')} ASK={ask_price:.4f} "
                          f"at {actual_time.strftime('%H:%M:%S')} (tick)")
                    return ask_price, actual_time
        except Exception as e:
            print(f"  [Exit] tick 方式失败: {e}")
        
        # --- 方法2: 使用 get_bid_ask_bars ---
        try:
            df = self.bbg.get_bid_ask_bars(
                symbol=symbol,
                start_date=start_time,
                end_date=end_time,
                resample="1min",
                is_beijing_time=True
            )
            
            if df is not None and not df.empty:
                # 转换 UTC -> 北京时间
                df.index = df.index + timedelta(hours=8)
                
                # 找最接近 02:00 的
                time_diff = abs(df.index - target_time)
                closest_idx = time_diff.argmin()
                
                ask_price = df.iloc[closest_idx]['ask']
                actual_time = df.index[closest_idx]
                
                print(f"  [Exit] {saturday_date.strftime('%Y-%m-%d')} ASK={ask_price:.4f} "
                      f"at {actual_time.strftime('%H:%M:%S')} (bar)")
                return ask_price, actual_time
        except Exception as e:
            print(f"  [Exit] bar 方式也失败: {e}")
        
        # --- 方法3: 回退到日线 PX_ASK (周五收盘) ---
        try:
            friday_date = saturday_date - timedelta(days=1)
            df = self.bbg.get_historical(
                symbol,
                start_date=friday_date,
                end_date=friday_date,
                fields=['PX_ASK']
            )
            
            if df is not None and not df.empty and 'PX_ASK' in df.columns:
                ask_price = df['PX_ASK'].iloc[0]
                if pd.notna(ask_price):
                    print(f"  [Exit] {saturday_date.strftime('%Y-%m-%d')} ASK={ask_price:.4f} "
                          f"(daily fallback - Friday close)")
                    return ask_price, friday_date
        except Exception as e:
            print(f"  [Exit] daily fallback 也失败: {e}")
        
        print(f"  [Exit] {saturday_date.strftime('%Y-%m-%d')} *** 无法获取 ASK 价格 ***")
        return None, None
    
    def get_entry_price(
        self, 
        symbol: str, 
        signal_time: datetime,
        window_minutes: int = 30
    ) -> Tuple[Optional[float], Optional[datetime]]:
        """
        获取信号时刻的 Entry Price = mid price = (bid + ask) / 2
        
        Args:
            symbol: Bloomberg 代码
            signal_time: 信号时间（北京时间）
            window_minutes: 搜索窗口（分钟）
        
        Returns:
            (mid_price, actual_time) 或 (None, None)
        """
        self._ensure_connected()
        
        target_time = signal_time
        start_time = target_time - timedelta(minutes=window_minutes)
        end_time = target_time + timedelta(minutes=window_minutes)
        
        # --- 方法1: 使用 get_bid_ask (tick) ---
        try:
            df = self.bbg.get_bid_ask(
                symbol=symbol,
                start_date=start_time,
                end_date=end_time,
                is_beijing_time=True
            )
            
            if df is not None and not df.empty:
                df_bj = df.copy()
                df_bj.index = df_bj.index + timedelta(hours=8)
                
                bid_df = df_bj[df_bj['type'] == 'BID']
                ask_df = df_bj[df_bj['type'] == 'ASK']
                
                if not bid_df.empty and not ask_df.empty:
                    bid_idx = abs(bid_df.index - target_time).argmin()
                    ask_idx = abs(ask_df.index - target_time).argmin()
                    
                    bid_price = bid_df.iloc[bid_idx]['price']
                    ask_price = ask_df.iloc[ask_idx]['price']
                    mid_price = (bid_price + ask_price) / 2
                    
                    actual_time = bid_df.index[bid_idx]
                    
                    print(f"  [Entry] {signal_time.strftime('%Y-%m-%d %H:%M')} "
                          f"BID={bid_price:.4f} ASK={ask_price:.4f} MID={mid_price:.5f} (tick)")
                    return mid_price, actual_time
        except Exception as e:
            print(f"  [Entry] tick 方式失败: {e}")
        
        # --- 方法2: 使用 get_bid_ask_bars ---
        try:
            df = self.bbg.get_bid_ask_bars(
                symbol=symbol,
                start_date=start_time,
                end_date=end_time,
                resample="1min",
                is_beijing_time=True
            )
            
            if df is not None and not df.empty:
                df.index = df.index + timedelta(hours=8)
                
                time_diff = abs(df.index - target_time)
                closest_idx = time_diff.argmin()
                
                mid_price = df.iloc[closest_idx]['mid']
                actual_time = df.index[closest_idx]
                
                print(f"  [Entry] {signal_time.strftime('%Y-%m-%d %H:%M')} "
                      f"MID={mid_price:.5f} (bar)")
                return mid_price, actual_time
        except Exception as e:
            print(f"  [Entry] bar 方式也失败: {e}")
        
        # --- 方法3: 回退到日线 mid = (PX_BID + PX_ASK) / 2 (周五收盘) ---
        try:
            # signal_time 可能是周五或周六，取周五
            if signal_time.weekday() == 5:  # Saturday
                friday_date = signal_time - timedelta(days=1)
            else:
                friday_date = signal_time
            friday_date = friday_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            df = self.bbg.get_historical(
                symbol,
                start_date=friday_date,
                end_date=friday_date,
                fields=['PX_BID', 'PX_ASK']
            )
            
            if df is not None and not df.empty:
                bid = df['PX_BID'].iloc[0] if 'PX_BID' in df.columns else None
                ask = df['PX_ASK'].iloc[0] if 'PX_ASK' in df.columns else None
                
                if pd.notna(bid) and pd.notna(ask):
                    mid_price = (bid + ask) / 2
                    print(f"  [Entry] {signal_time.strftime('%Y-%m-%d %H:%M')} "
                          f"BID={bid:.4f} ASK={ask:.4f} MID={mid_price:.5f} (daily fallback)")
                    return mid_price, friday_date
        except Exception as e:
            print(f"  [Entry] daily fallback 也失败: {e}")
        
        print(f"  [Entry] {signal_time.strftime('%Y-%m-%d %H:%M')} *** 无法获取价格 ***")
        return None, None
    
    # =========================================================================
    # 信号数据处理
    # =========================================================================
    
    @staticmethod
    def _get_last_signal_per_week(signal_df: pd.DataFrame) -> pd.DataFrame:
        """
        从信号数据中，按周提取交易窗口内的最后一个信号
        
        交易窗口: 周五 22:30 ~ 周六 01:30 (北京时间)
        每半小时一次: 22:30, 23:00, 23:30, 00:00, 00:30, 01:00, 01:30
        Reference/Exit: 周六 02:00
        """
        df = signal_df.copy()
        df['predict_time'] = pd.to_datetime(df['predict_time'])
        df['hour'] = df['predict_time'].dt.hour
        df['minute'] = df['predict_time'].dt.minute
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        df['weekday'] = df['predict_time'].dt.weekday  # Monday=0, Friday=4, Saturday=5
        
        # 交易窗口: 周五 22:30+ 或 周六 00:00-01:30
        friday_mask = (df['weekday'] == 4) & (df['time_decimal'] >= 22.5)
        saturday_mask = (df['weekday'] == 5) & (df['time_decimal'] <= 1.5)
        
        window_df = df[friday_mask | saturday_mask].copy()
        
        if 'year_week' not in window_df.columns:
            window_df['year_week'] = window_df['predict_time'].dt.strftime('%Y_%W')
        
        # 每周取最后一个信号
        last_signals = (
            window_df.sort_values('predict_time')
            .groupby('year_week')
            .last()
            .reset_index()
        )
        
        return last_signals
    
    @staticmethod
    def _get_weekend_dates_from_signals(signal_df: pd.DataFrame) -> List[dict]:
        """
        从信号数据解析出每周的关键日期和信号时间
        """
        last_signals = WeekendPriceDataFetcher._get_last_signal_per_week(signal_df)
        
        weekends = []
        for _, row in last_signals.iterrows():
            predict_time = pd.to_datetime(row['predict_time'])
            
            # 推算周五和周六的日期
            if predict_time.weekday() == 5:  # Saturday
                friday_date = predict_time - timedelta(days=1)
                saturday_date = predict_time
            elif predict_time.weekday() == 4:  # Friday
                friday_date = predict_time
                saturday_date = predict_time + timedelta(days=1)
            else:
                # 异常情况，跳过
                continue
            
            weekends.append({
                'year_week': row['year_week'],
                'friday_date': friday_date.strftime('%Y-%m-%d'),
                'saturday_date': saturday_date.strftime('%Y-%m-%d'),
                'signal_time': predict_time,
                'prediction': row.get('prediction'),
                'confidence': row.get('confidence'),
                'direction': row.get('direction'),
            })
        
        return weekends
    
    # =========================================================================
    # 主要批量获取方法
    # =========================================================================
    
    def fetch_all_weekend_prices(
        self,
        symbol: str = "USDCNH Curncy",
        signal_df: Optional[pd.DataFrame] = None,
        signal_file: Optional[str] = None,
        existing_prices_file: Optional[str] = None,
        force_refetch: bool = False
    ) -> pd.DataFrame:
        """
        批量获取所有周末的 entry/exit 价格
        
        Args:
            symbol: Bloomberg 代码
            signal_df: 信号 DataFrame（与 signal_file 二选一）
            signal_file: 信号 CSV 文件路径（与 signal_df 二选一）
            existing_prices_file: 已有的价格文件路径（增量更新用）
            force_refetch: 是否强制重新获取所有数据
        
        Returns:
            DataFrame: year_week, friday_date, saturday_date, signal_time, 
                       entry_price, exit_price
        """
        self._ensure_connected()
        
        # 1. 加载信号数据
        if signal_df is None and signal_file is not None:
            signal_df = pd.read_csv(signal_file)
            print(f"[WeekendPrice] 加载信号数据: {len(signal_df)} 条")
        elif signal_df is None:
            raise ValueError("必须提供 signal_df 或 signal_file")
        
        # 2. 解析每周的信号时间
        weekends = self._get_weekend_dates_from_signals(signal_df)
        print(f"[WeekendPrice] 共 {len(weekends)} 个交易周需要获取价格")
        
        # 3. 加载已有价格数据（增量更新）
        existing_prices = {}
        if existing_prices_file and not force_refetch:
            if os.path.exists(existing_prices_file):
                existing_df = pd.read_csv(existing_prices_file)
                for _, row in existing_df.iterrows():
                    if pd.notna(row.get('entry_price')) and pd.notna(row.get('exit_price')):
                        existing_prices[row['year_week']] = {
                            'entry_price': row['entry_price'],
                            'exit_price': row['exit_price'],
                        }
                print(f"[WeekendPrice] 已有 {len(existing_prices)} 周的完整价格数据（将跳过）")
        
        # 4. 逐周获取价格
        results = []
        fetched_count = 0
        skipped_count = 0
        failed_count = 0
        
        for i, weekend in enumerate(weekends):
            year_week = weekend['year_week']
            signal_time = weekend['signal_time']
            saturday_date = pd.to_datetime(weekend['saturday_date'])
            
            print(f"\n--- [{i+1}/{len(weekends)}] {year_week} "
                  f"(信号: {signal_time.strftime('%Y-%m-%d %H:%M')}) ---")
            
            # 检查是否已有数据
            if year_week in existing_prices and not force_refetch:
                entry_price = existing_prices[year_week]['entry_price']
                exit_price = existing_prices[year_week]['exit_price']
                print(f"  [Skip] 已有数据 Entry={entry_price:.5f} Exit={exit_price:.4f}")
                skipped_count += 1
            else:
                # 从 Bloomberg 获取
                entry_price, _ = self.get_entry_price(symbol, signal_time)
                exit_price, _ = self.get_exit_price(symbol, saturday_date)
                
                if entry_price is not None and exit_price is not None:
                    fetched_count += 1
                else:
                    failed_count += 1
            
            results.append({
                'year_week': year_week,
                'friday_date': weekend['friday_date'],
                'saturday_date': weekend['saturday_date'],
                'signal_time': signal_time.strftime('%Y-%m-%d %H:%M:%S'),
                'entry_price': entry_price,
                'exit_price': exit_price,
            })
        
        df = pd.DataFrame(results)
        
        # 5. 汇总
        total = len(df)
        valid = df['entry_price'].notna().sum()
        missing = df['entry_price'].isna().sum()
        
        print(f"\n{'='*60}")
        print(f"[WeekendPrice] 数据获取完成")
        print(f"{'='*60}")
        print(f"  总周数:     {total}")
        print(f"  有效数据:   {valid} ({valid/total*100:.1f}%)")
        print(f"  缺失数据:   {missing}")
        print(f"  新获取:     {fetched_count}")
        print(f"  已有跳过:   {skipped_count}")
        print(f"  获取失败:   {failed_count}")
        
        if missing > 0:
            print(f"\n  [!] 以下周次缺失价格数据:")
            for _, row in df[df['entry_price'].isna()].iterrows():
                print(f"      {row['year_week']} ({row['friday_date']})")
        
        return df
    
    # =========================================================================
    # 文件 I/O
    # =========================================================================
    
    def save_prices(self, df: pd.DataFrame, filename: str = "weekend_prices_bbg.csv") -> str:
        """保存价格数据到 CSV"""
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"[WeekendPrice] OK - 已保存到: {filepath}")
        return filepath
    
    @staticmethod
    def load_prices(filename: str = "weekend_prices_bbg.csv") -> pd.DataFrame:
        """从 CSV 加载价格数据"""
        filepath = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'raw', filename
        )
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"价格文件不存在: {filepath}")
        
        df = pd.read_csv(filepath)
        valid = df['entry_price'].notna().sum()
        print(f"[WeekendPrice] 加载 {len(df)} 条记录 (有效: {valid})")
        return df


# =============================================================================
# 命令行入口
# =============================================================================

def main():
    """
    主函数: 从 Bloomberg 获取所有周末价格数据
    """
    # 路径
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    signal_file = os.path.join(project_dir, 'data', 'raw', 'USD_SIGNAL_V3_processed.csv')
    prices_file = os.path.join(project_dir, 'data', 'raw', 'weekend_prices_bbg.csv')
    
    print("=" * 60)
    print("Weekend Price Data Fetcher (Bloomberg Only)")
    print("=" * 60)
    print(f"信号文件: {signal_file}")
    print(f"价格文件: {prices_file}")
    print()
    
    # 检查信号文件
    if not os.path.exists(signal_file):
        print(f"[ERROR] 信号文件不存在: {signal_file}")
        sys.exit(1)
    
    # 初始化 & 连接
    fetcher = WeekendPriceDataFetcher()
    fetcher.connect()
    
    try:
        # 获取价格（增量更新：已有的不重复获取）
        prices = fetcher.fetch_all_weekend_prices(
            symbol="USDCNH Curncy",
            signal_file=signal_file,
            existing_prices_file=prices_file,
            force_refetch=False  # 改为 True 可强制重新获取全部
        )
        
        # 保存
        fetcher.save_prices(prices, "weekend_prices_bbg.csv")
        
        # 显示结果
        print(f"\n{'='*60}")
        print("价格数据预览:")
        print("=" * 60)
        print(prices.to_string(index=False))
        
    finally:
        fetcher.disconnect()
    
    return prices


if __name__ == "__main__":
    prices = main()
