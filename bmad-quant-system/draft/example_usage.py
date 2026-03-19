# -*- coding: utf-8 -*-
"""
Example Usage of SparkSQLWrapper
================================

This file demonstrates how to use the SparkSQLWrapper for FX data queries.

Note: This requires an active SparkSession connected to your Hive/Spark environment.
"""

# ==================== Basic Setup ====================

# Assuming you have SparkSession already created in your environment
# from pyspark.sql import SparkSession
# spark = SparkSession.builder.appName("FX_Analysis").getOrCreate()

from spark_sql_wrapper import (
    SparkSQLWrapper, 
    FXQueryBuilder, 
    QueryParams, 
    JoinType
)


def demo_model_signals(spark):
    """
    Demonstrate model signals query usage.
    
    核心表: dal_wisefx.daa_mr_weekend_pre_lock_price_model_predict_all
    """
    wrapper = SparkSQLWrapper(spark)
    
    # ==================== 1. Basic Signal Query ====================
    print("=" * 60)
    print("1. Get model signals (basic)")
    print("=" * 60)
    
    # 获取 v3 版本的所有信号
    df = wrapper.get_model_signals(
        model_version='v3',
        limit=2000
    )
    print(f"Total signals: {df.count()}")
    df.show(5)
    
    # ==================== 2. Filter by Date Range ====================
    print("\n" + "=" * 60)
    print("2. Get signals for date range")
    print("=" * 60)
    
    df = wrapper.get_model_signals(
        model_version='v3',
        start_date='20250601',
        end_date='20250701',
        limit=1000
    )
    print(f"Signals in June 2025: {df.count()}")
    
    # ==================== 3. Filter by Currency Pair ====================
    print("\n" + "=" * 60)
    print("3. Get USDCNH signals only")
    print("=" * 60)
    
    df = wrapper.get_model_signals(
        model_version='v3',
        ccy_pair='USDCNH',
        limit=1000
    )
    print(f"USDCNH signals: {df.count()}")
    
    # ==================== 4. Filter by is_positive ====================
    print("\n" + "=" * 60)
    print("4. Get positive signals only")
    print("=" * 60)
    
    df = wrapper.get_model_signals(
        model_version='v3',
        is_positive=1,
        limit=1000
    )
    print(f"Positive signals: {df.count()}")
    
    # ==================== 5. Get Signals Summary ====================
    print("\n" + "=" * 60)
    print("5. Get signals summary by currency pair")
    print("=" * 60)
    
    df_summary = wrapper.get_model_signals_summary(
        model_version='v3',
        start_date='20250101',
        end_date='20260101'
    )
    df_summary.show()
    
    # ==================== 6. Get Signals for Specific Date ====================
    print("\n" + "=" * 60)
    print("6. Get all signals for a specific date")
    print("=" * 60)
    
    df = wrapper.get_model_signals_by_date(
        fdate='20250610',
        model_version='v3'
    )
    print(f"Signals on 2025-06-10: {df.count()}")
    df.show()
    
    # ==================== 7. Signals with Rates ====================
    print("\n" + "=" * 60)
    print("7. Get signals joined with rates")
    print("=" * 60)
    
    df = wrapper.get_model_signals_with_rates(
        liquidity_provider='scb-svf',
        model_version='v3',
        start_date='20250601',
        end_date='20250701',
        ccy_pair='USDCNH',
        limit=500
    )
    print(f"Signals with rates: {df.count()}")
    df.show(5)


def demo_wrapper_usage(spark):
    """
    Demonstrate SparkSQLWrapper usage.
    """
    # Initialize wrapper
    wrapper = SparkSQLWrapper(spark)
    
    # ==================== Method 1: Using QueryParams ====================
    print("=" * 60)
    print("Method 1: Using QueryParams object")
    print("=" * 60)
    
    params = QueryParams(
        liquidity_provider='scb-svf',
        start_date='20260101',
        end_date='20260201',
        deal_type='BK',
        portfolio='3000000024',
        limit=1000
    )
    
    # Exact time match (原来的 get_fx_orders_data)
    df_exact = wrapper.get_fx_orders(params, join_type=JoinType.EXACT)
    print(f"Exact match result count: {df_exact.count()}")
    
    # Latest rate before transaction (原来的 get_fx_orders_data1)
    df_latest = wrapper.get_fx_orders(params, join_type=JoinType.LATEST_BEFORE)
    print(f"Latest-before result count: {df_latest.count()}")
    
    # ==================== Method 2: Simple Interface ====================
    print("\n" + "=" * 60)
    print("Method 2: Simple interface (no QueryParams)")
    print("=" * 60)
    
    df = wrapper.get_fx_orders_simple(
        liquidity_provider='scb-svf',
        start_date='20260101',
        end_date='20260201',
        deal_type='BK',
        portfolio='3000000024',
        limit=500,
        join_type='exact'  # or 'latest'
    )
    print(f"Simple interface result count: {df.count()}")
    
    # ==================== Method 3: Schema Inspection ====================
    print("\n" + "=" * 60)
    print("Method 3: Schema inspection")
    print("=" * 60)
    
    # Print schema (原来的 df.printSchema())
    wrapper.print_schema('dal_wisefx.dm_daily_fx_rates_sec_continuous_spot_forward')
    
    # Get columns
    columns = wrapper.get_columns('dal_wisefx.dal_kjzf_fx_orders_wide_dd')
    print(f"Orders table columns: {columns[:5]}...")  # First 5
    
    # ==================== Method 4: Get Rates Only ====================
    print("\n" + "=" * 60)
    print("Method 4: Get rates data only")
    print("=" * 60)
    
    df_rates = wrapper.get_rates(
        liquidity_provider='scb-svf',
        start_date='20260101',
        end_date='20260201',
        ccy_pair='USDCNH',  # Optional filter
        limit=5000
    )
    print(f"Rates count: {df_rates.count()}")
    
    # ==================== Method 5: Get Orders Only ====================
    print("\n" + "=" * 60)
    print("Method 5: Get orders without joining rates")
    print("=" * 60)
    
    df_orders = wrapper.get_orders_only(
        start_date='20260101',
        end_date='20260201',
        deal_type='BK',
        portfolio='3000000024',
        limit=1000
    )
    print(f"Orders count: {df_orders.count()}")
    
    # ==================== Method 6: Raw SQL ====================
    print("\n" + "=" * 60)
    print("Method 6: Execute raw SQL")
    print("=" * 60)
    
    custom_query = """
    SELECT fdate, COUNT(*) as order_count
    FROM dal_wisefx.dal_kjzf_fx_orders_wide_dd
    WHERE fdate >= 20260101 AND fdate < 20260201
    GROUP BY fdate
    ORDER BY fdate
    """
    df_custom = wrapper.execute_sql(custom_query)
    df_custom.show()
    
    # ==================== Method 7: SQL with Parameters ====================
    print("\n" + "=" * 60)
    print("Method 7: SQL template with parameters")
    print("=" * 60)
    
    template = """
    SELECT fdate, COUNT(*) as cnt
    FROM {table}
    WHERE fdate >= {start_date} AND fdate < {end_date}
    GROUP BY fdate
    LIMIT {limit}
    """
    
    df_template = wrapper.execute_sql_with_params(template, {
        'table': 'dal_wisefx.dal_kjzf_fx_orders_wide_dd',
        'start_date': 20260101,
        'end_date': 20260201,
        'limit': 10
    })
    df_template.show()


def demo_query_builder(spark):
    """
    Demonstrate FXQueryBuilder (fluent interface) usage.
    """
    print("\n" + "=" * 60)
    print("FXQueryBuilder: Fluent Query Builder")
    print("=" * 60)
    
    builder = FXQueryBuilder(spark)
    
    # Example 1: Simple query
    df = (builder
        .from_orders()
        .filter_date('20260101', '20260201')
        .filter_deal_type('BK')
        .filter_portfolio('3000000024')
        .order_by('fetl_time')
        .limit(100)
        .execute())
    
    print(f"Builder result count: {df.count()}")
    
    # Example 2: With join
    df_joined = (builder
        .from_orders()
        .join_rates('scb-svf', join_type='exact')
        .filter_date('20260101', '20260201')
        .filter_deal_type('BK')
        .select(['o.forder_id', 'o.ftransaction_time', 'r.bid', 'r.ask'])
        .limit(500)
        .execute())
    
    print(f"Joined result count: {df_joined.count()}")
    
    # Example 3: Just build query (don't execute)
    query = (builder
        .from_orders()
        .join_rates('scb-svf', join_type='latest')
        .filter_date('20260101', '20260201')
        .limit(100)
        .build())
    
    print("\nGenerated SQL:")
    print(query)


# ==================== Quick Reference ====================

QUICK_REFERENCE = """
================================================================================
                        SPARK SQL WRAPPER QUICK REFERENCE
================================================================================

1. INITIALIZE:
   wrapper = SparkSQLWrapper(spark)

2. GET MODEL SIGNALS (核心表):
   df = wrapper.get_model_signals(
       model_version='v3',
       start_date='20250601',    # optional
       end_date='20250701',      # optional
       ccy_pair='USDCNH',        # optional
       is_positive=1,            # optional (1 or 0)
       limit=2000
   )

3. GET SIGNALS SUMMARY:
   df = wrapper.get_model_signals_summary(model_version='v3')

4. GET SIGNALS FOR SPECIFIC DATE:
   df = wrapper.get_model_signals_by_date(fdate='20250610', model_version='v3')

5. GET SIGNALS WITH RATES:
   df = wrapper.get_model_signals_with_rates(
       liquidity_provider='scb-svf',
       model_version='v3',
       ccy_pair='USDCNH'
   )

6. GET FX ORDERS (Exact Match) - 原 get_fx_orders_data:
   df = wrapper.get_fx_orders_simple(
       liquidity_provider='scb-svf',
       start_date='20260101',
       end_date='20260201',
       deal_type='BK',
       portfolio='3000000024',
       join_type='exact'
   )

7. GET FX ORDERS (Latest Rate) - 原 get_fx_orders_data1:
   df = wrapper.get_fx_orders_simple(
       liquidity_provider='scb-svf',
       start_date='20260101',
       end_date='20260201',
       deal_type='BK',
       portfolio='3000000024',
       join_type='latest'
   )

8. PRINT SCHEMA:
   wrapper.print_schema('dal_wisefx.daa_mr_weekend_pre_lock_price_model_predict_all')

9. EXECUTE RAW SQL:
   df = wrapper.execute_sql("SELECT * FROM table WHERE ...")

================================================================================
TABLE REFERENCE:
================================================================================
- Orders:  dal_wisefx.dal_kjzf_fx_orders_wide_dd
- Rates:   dal_wisefx.dm_daily_fx_rates_sec_continuous_spot_forward  
- Signals: dal_wisefx.daa_mr_weekend_pre_lock_price_model_predict_all (核心)
================================================================================
"""


if __name__ == "__main__":
    print(QUICK_REFERENCE)
    print("\nTo use:")
    print("  1. demo_model_signals(spark)  - 核心信号表查询示例")
    print("  2. demo_wrapper_usage(spark)  - FX订单查询示例")
    print("  3. demo_query_builder(spark)  - 流式查询构建器示例")
