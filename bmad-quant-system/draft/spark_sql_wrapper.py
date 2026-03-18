# -*- coding: utf-8 -*-
"""
Spark SQL Wrapper for FX Data Analysis
======================================

使用方法（在已有 spark session 的环境中）:
-----------------------------------------
from spark_sql_wrapper import FX

fx = FX(spark)

# 获取信号
df = fx.get_signals(model_version='v3', limit=2000)

# 获取汇率数据
data = fx.fetch_daily_data(date='20240905', currency_pairs=['USDCNY', 'USDCNH'])

# 计算价差
spreads = fx.calculate_spreads(data, cny_pair='USDCNY', cnh_pair='USDCNH')

# 绘图
fx.plot_spread(spreads)
"""

from pyspark.sql import functions as F


class FX:
    """
    FX 数据分析工具类
    
    Tables:
    -------
    - SIGNALS: dal_wisefx.daa_mr_weekend_pre_lock_price_model_predict_all
    - RATES: dal_wisefx.dm_daily_fx_rates_sec_continuous_spot_forward
    - ORDERS: dal_wisefx.dal_kjzf_fx_orders_wide_dd
    """
    
    # 表名常量
    SIGNALS = "dal_wisefx.daa_mr_weekend_pre_lock_price_model_predict_all"
    RATES = "dal_wisefx.dm_daily_fx_rates_sec_continuous_spot_forward"
    ORDERS = "dal_wisefx.dal_kjzf_fx_orders_wide_dd"
    
    def __init__(self, spark):
        """初始化，需要传入 spark session"""
        self.spark = spark
    
    # ==================== 基础查询 ====================
    
    def signals(self):
        """获取信号表"""
        return self.spark.table(self.SIGNALS)
    
    def rates(self):
        """获取汇率表"""
        return self.spark.table(self.RATES)
    
    def orders(self):
        """获取订单表"""
        return self.spark.table(self.ORDERS)
    
    def sql(self, query):
        """执行原生 SQL"""
        return self.spark.sql(query)
    
    def schema(self, table_name):
        """打印表结构"""
        self.spark.table(table_name).printSchema()
    
    # ==================== 信号查询 ====================
    
    def get_signals(self, model_version='v3', ccy_pair=None, fdate=None, 
                    start_date=None, end_date=None, is_positive=None, limit=2000):
        """
        获取模型预测信号
        
        Parameters:
        -----------
        model_version : str, 模型版本，默认 'v3'
        ccy_pair : str, 货币对，如 'USDCNH'
        fdate : int/str, 特定日期
        start_date : int/str, 起始日期
        end_date : int/str, 结束日期
        is_positive : int, 0 或 1
        limit : int, 最大记录数
        
        Example:
        --------
        df = fx.get_signals(model_version='v3', limit=2000)
        df = fx.get_signals(ccy_pair='USDCNH', fdate=20250610)
        """
        df = self.signals().filter(F.col("model_version") == model_version)
        
        if ccy_pair:
            df = df.filter(F.col("target_current_pair") == ccy_pair)
        if fdate:
            df = df.filter(F.col("fdate") == int(fdate))
        if start_date:
            df = df.filter(F.col("fdate") >= int(start_date))
        if end_date:
            df = df.filter(F.col("fdate") < int(end_date))
        if is_positive is not None:
            df = df.filter(F.col("is_positive") == is_positive)
        
        return df.orderBy("fdate", "predict_time").limit(limit)
    
    # ==================== 汇率数据查询 ====================
    
    def fetch_daily_data(
        self,
        date,
        currency_pairs=None,
        time_range=None,
        liquidity_provider="scb-svf",
        tenor_filter="SPOT",
        return_pandas=True,
        verbose=True
    ):
        """
        获取特定日期的外汇数据
        
        Parameters:
        -----------
        date : str/int, 日期 YYYYMMDD
        currency_pairs : list, 货币对列表，默认 ["USDCNY", "USDCNH", "HKDCNY", "HKDCNH"]
        time_range : tuple, 时间范围 (start_time, end_time)，格式 HHMM
        liquidity_provider : str, 流动性提供者
        tenor_filter : str, 期限筛选
        return_pandas : bool, 是否返回 pandas DataFrame
        verbose : bool, 是否打印详细信息
        
        Example:
        --------
        # 全天数据
        data = fx.fetch_daily_data(date='20240905', currency_pairs=['USDCNY', 'USDCNH'])
        
        # 指定时间范围
        data = fx.fetch_daily_data(date='20240905', time_range=('0945', '1200'))
        """
        date_int = int(date) if isinstance(date, str) else date
        
        if currency_pairs is None:
            currency_pairs = ["USDCNY", "USDCNH", "HKDCNY", "HKDCNH"]
        
        if verbose:
            print(f"获取日期 {date_int} 的外汇数据")
            print(f"货币对: {currency_pairs}")
            print(f"流动性提供者: {liquidity_provider}")
            if tenor_filter:
                print(f"期限筛选: {tenor_filter}")
            if time_range:
                print(f"时间范围: {time_range[0]} 到 {time_range[1]}")
        
        try:
            df = self.rates()
            
            query = (
                (F.col("fdate") == date_int) & 
                (F.col("liquidity_provider") == liquidity_provider) & 
                (F.col("ccy_pair").isin(currency_pairs))
            )
            
            if tenor_filter:
                query = query & (F.col("tenor") == tenor_filter)
            
            df_filtered = df.filter(query).orderBy("fdate", "transact_time")
            
            if time_range:
                start_time, end_time = time_range
                transaction_time_start = int(f"{date_int}{start_time}00")
                transaction_time_end = int(f"{date_int}{end_time}00")
                
                df_filtered = df_filtered.filter(
                    (F.col("transact_time") >= transaction_time_start) &
                    (F.col("transact_time") <= transaction_time_end)
                )
            
            record_count = df_filtered.count()
            
            if verbose:
                print(f"找到 {record_count} 条记录")
            
            if record_count == 0:
                print("警告: 未找到符合指定条件的数据!")
                return None
            
            if return_pandas:
                result = df_filtered.toPandas()
                if verbose and not result.empty:
                    print("\n数据示例 (第一行):")
                    print(result.iloc[0])
                return result
            else:
                return df_filtered
                
        except Exception as e:
            print(f"获取数据时出错: {str(e)}")
            return None
    
    # ==================== 价差计算 ====================
    
    def calculate_spreads(
        self,
        data,
        cny_pair,
        cnh_pair,
        transaction_cost_bps=0.0,
        clean_data=True,
        verbose=True
    ):
        """
        计算 CNY 和 CNH 货币对之间的价差
        
        Parameters:
        -----------
        data : pandas.DataFrame, FX 数据
        cny_pair : str, CNY 货币对 (如 "USDCNY")
        cnh_pair : str, CNH 货币对 (如 "USDCNH")
        transaction_cost_bps : float, 交易成本（基点）
        clean_data : bool, 是否清理 NaN 值
        verbose : bool, 是否打印详细信息
        
        Example:
        --------
        data = fx.fetch_daily_data(date='20240905')
        spreads = fx.calculate_spreads(data, cny_pair='USDCNY', cnh_pair='USDCNH')
        """
        import pandas as pd
        import numpy as np
        
        if verbose:
            print(f"\n计算 {cny_pair} 和 {cnh_pair} 之间的价差")
            print(f"交易成本: {transaction_cost_bps} bps")
        
        try:
            df_cny = data[data['ccy_pair'] == cny_pair]
            df_cnh = data[data['ccy_pair'] == cnh_pair]
            
            if verbose:
                print(f"筛选后的记录数:")
                print(f"  - {cny_pair}: {len(df_cny)} 行")
                print(f"  - {cnh_pair}: {len(df_cnh)} 行")
            
            if len(df_cny) == 0:
                print(f"警告: 没有 {cny_pair} 的数据。")
                return None
                
            if len(df_cnh) == 0:
                print(f"警告: 没有 {cnh_pair} 的数据。")
                return None
            
            price_columns = ['bid', 'ask', 'bid2', 'ask2', 'bid_mket_pts', 'ask_mket_pts']
            
            ask_col_cny = None
            for col in price_columns:
                if col.startswith('ask') and col in df_cny.columns and df_cny[col].notna().sum() > 0:
                    ask_col_cny = col
                    break
                    
            if ask_col_cny is None:
                print(f"错误: 找不到 {cny_pair} 的有效ask价格列")
                return None
                
            bid_col_cnh = None
            for col in price_columns:
                if col.startswith('bid') and col in df_cnh.columns and df_cnh[col].notna().sum() > 0:
                    bid_col_cnh = col
                    break
                    
            if bid_col_cnh is None:
                print(f"错误: 找不到 {cnh_pair} 的有效bid价格列")
                return None
                
            if verbose:
                print(f"选定的价格列:")
                print(f"  - {cny_pair} ask列: {ask_col_cny}")
                print(f"  - {cnh_pair} bid列: {bid_col_cnh}")
            
            df_cny_filtered = df_cny[['transact_time', ask_col_cny]].rename(
                columns={ask_col_cny: f'ask_{cny_pair.lower()}'}
            )
            df_cnh_filtered = df_cnh[['transact_time', bid_col_cnh]].rename(
                columns={bid_col_cnh: f'bid_{cnh_pair.lower()}'}
            )
            
            df_cny_filtered[f'ask_{cny_pair.lower()}'] = pd.to_numeric(
                df_cny_filtered[f'ask_{cny_pair.lower()}'], errors='coerce'
            )
            df_cnh_filtered[f'bid_{cnh_pair.lower()}'] = pd.to_numeric(
                df_cnh_filtered[f'bid_{cnh_pair.lower()}'], errors='coerce'
            )
            
            if clean_data:
                df_cny_filtered = df_cny_filtered.dropna()
                df_cnh_filtered = df_cnh_filtered.dropna()
            
            df_merged = pd.merge(df_cny_filtered, df_cnh_filtered, on='transact_time', how='inner')
            
            if verbose:
                print(f"时间窗口内有效价格数据点: {len(df_merged)}")
            
            if len(df_merged) == 0:
                print(f"警告: {cny_pair} 和 {cnh_pair} 之间没有匹配的交易时间")
                return None
            
            ask_col = f'ask_{cny_pair.lower()}'
            bid_col = f'bid_{cnh_pair.lower()}'
            
            df_merged['spread'] = df_merged[bid_col] - df_merged[ask_col]
            df_merged['spread_bps'] = (df_merged['spread'] / df_merged[ask_col]) * 10000
            df_merged['return_bps'] = df_merged['spread_bps']
            df_merged['net_return_bps'] = df_merged['return_bps'] - transaction_cost_bps
            
            df_merged['transact_time_str'] = df_merged['transact_time'].astype(str)
            df_merged['datetime'] = pd.to_datetime(df_merged['transact_time_str'], format='%Y%m%d%H%M%S')
            df_merged.sort_values('datetime', inplace=True)
            
            if verbose:
                print(f"\n价差统计:")
                print(f"  - 最小价差: {df_merged['spread'].min():.6f}")
                print(f"  - 最大价差: {df_merged['spread'].max():.6f}")
                print(f"  - 平均价差: {df_merged['spread'].mean():.6f}")
                
                print(f"\n收益统计 (bps):")
                print(f"  - 最小净收益: {df_merged['net_return_bps'].min():.2f} bps")
                print(f"  - 最大净收益: {df_merged['net_return_bps'].max():.2f} bps")
                print(f"  - 平均净收益: {df_merged['net_return_bps'].mean():.2f} bps")
                
                executable = (df_merged['net_return_bps'] > 0).mean() * 100
                print(f"  - 可执行交易 (净收益 > 0): {executable:.2f}%")
            
            return df_merged
            
        except Exception as e:
            print(f"计算价差时出错: {str(e)}")
            return None
    
    # ==================== 绘图 ====================
    
    def plot_spread(self, spreads_df, threshold=None, title=None, save_path=None):
        """
        绘制日内价差图表
        
        Parameters:
        -----------
        spreads_df : pandas.DataFrame, 价差数据
        threshold : float, 阈值线
        title : str, 图表标题
        save_path : str, 保存路径 (如 'spread.html')
        
        Example:
        --------
        fx.plot_spread(spreads, threshold=5.0, save_path='spread.html')
        """
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(
                x=spreads_df['datetime'],
                y=spreads_df['net_return_bps'],
                mode='lines',
                name='净收益 (bps)'
            )
        )
        
        if threshold is not None:
            fig.add_hline(
                y=threshold,
                line_dash="dash",
                line_color="red",
                annotation_text=f"阈值: {threshold} bps",
                annotation_position="bottom right"
            )
        
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="black",
            annotation_text="零收益线",
            annotation_position="bottom left"
        )
        
        if title is None:
            cny_col = [col for col in spreads_df.columns if col.startswith('ask_')][0]
            cnh_col = [col for col in spreads_df.columns if col.startswith('bid_')][0]
            cny_pair = cny_col.replace('ask_', '').upper()
            cnh_pair = cnh_col.replace('bid_', '').upper()
            date_str = spreads_df['datetime'].min().strftime('%Y-%m-%d')
            title = f"{cny_pair} - {cnh_pair} 日内价差 ({date_str})"
        
        fig.update_layout(
            title=title,
            xaxis_title="时间",
            yaxis_title="价差 (bps)",
            template="plotly_white",
            height=600,
            width=1000
        )
        
        if save_path:
            fig.write_html(save_path)
            print(f"图表已保存到: {save_path}")
        
        fig.show()
        return fig


# ==================== 快速参考 ====================
QUICK_REF = """
================================================================================
                           FX WRAPPER 快速参考
================================================================================

1. 初始化:
   from spark_sql_wrapper import FX
   fx = FX(spark)

2. 获取信号:
   df = fx.get_signals(model_version='v3', limit=2000)
   df = fx.get_signals(ccy_pair='USDCNH', fdate=20250610)

3. 获取汇率数据:
   data = fx.fetch_daily_data(date='20240905', currency_pairs=['USDCNY', 'USDCNH'])
   data = fx.fetch_daily_data(date='20240905', time_range=('0945', '1200'))

4. 计算价差:
   spreads = fx.calculate_spreads(data, cny_pair='USDCNY', cnh_pair='USDCNH')

5. 绘图:
   fx.plot_spread(spreads, threshold=5.0, save_path='spread.html')

6. 原生 SQL:
   df = fx.sql("SELECT * FROM dal_wisefx.xxx WHERE ...")

7. 查看表结构:
   fx.schema('dal_wisefx.daa_mr_weekend_pre_lock_price_model_predict_all')

================================================================================
"""

if __name__ == "__main__":
    print(QUICK_REF)
