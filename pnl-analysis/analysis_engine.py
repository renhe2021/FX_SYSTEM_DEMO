# -*- coding: utf-8 -*-
"""
analysis_engine.py - 损益分析引擎
==================================
提供多维度汇总：按渠道/业务/产品/商户/币种，
支持单月、多月累计、月度对比等分析视角。
"""

import pandas as pd
import numpy as np
from typing import Optional


def _agg_cols():
    return {"损益金额": "sum", "其中WX": "sum", "FIT": "sum"}


def _add_total_row(df: pd.DataFrame, label_col: str, label_val: str = "合计") -> pd.DataFrame:
    """给汇总表追加合计行。"""
    total = {label_col: label_val}
    for col in ["损益金额", "其中WX", "FIT"]:
        if col in df.columns:
            total[col] = df[col].sum()
    return pd.concat([df, pd.DataFrame([total])], ignore_index=True)


# ===================== 各维度汇总 =====================

def summary_by_entity(df: pd.DataFrame) -> pd.DataFrame:
    """按损益归属主体汇总。"""
    agg = df.groupby("损益实际归属主体", sort=False).agg(_agg_cols()).reset_index()
    agg.rename(columns={"损益实际归属主体": "损益归属"}, inplace=True)
    agg.sort_values("损益金额", ascending=False, inplace=True)
    return _add_total_row(agg, "损益归属")


def summary_by_business(df: pd.DataFrame) -> pd.DataFrame:
    """按所属业务汇总。"""
    agg = df.groupby("所属业务", sort=False).agg(_agg_cols()).reset_index()
    agg.sort_values("损益金额", ascending=False, inplace=True)
    return _add_total_row(agg, "所属业务")


def summary_by_product(df: pd.DataFrame) -> pd.DataFrame:
    """按产品类型汇总。"""
    agg = df.groupby("产品类型", sort=False).agg(_agg_cols()).reset_index()
    agg.sort_values("损益金额", ascending=False, inplace=True)
    return _add_total_row(agg, "产品类型")


def summary_by_currency(df: pd.DataFrame) -> pd.DataFrame:
    """按原币种汇总。"""
    agg = df.groupby("原币种", sort=False).agg(_agg_cols()).reset_index()
    agg.sort_values("损益金额", ascending=False, inplace=True)
    return _add_total_row(agg, "原币种")


def summary_by_merchant_type(df: pd.DataFrame) -> pd.DataFrame:
    """按商户类型汇总。"""
    agg = df.groupby("商户类型", sort=False).agg(_agg_cols()).reset_index()
    agg.sort_values("损益金额", ascending=False, inplace=True)
    return _add_total_row(agg, "商户类型")


def summary_by_entity_business(df: pd.DataFrame) -> pd.DataFrame:
    """按损益归属 × 所属业务交叉汇总。"""
    agg = df.groupby(["损益实际归属主体", "所属业务"], sort=False).agg(_agg_cols()).reset_index()
    agg.rename(columns={"损益实际归属主体": "损益归属"}, inplace=True)

    rows = []
    for entity, grp in agg.groupby("损益归属", sort=False):
        grp_sorted = grp.sort_values("损益金额", ascending=False)
        for _, row in grp_sorted.iterrows():
            rows.append(row.to_dict())
        rows.append({
            "损益归属": f"{entity} 小计", "所属业务": "",
            **{c: grp[c].sum() for c in ["损益金额", "其中WX", "FIT"]},
        })

    rows.append({
        "损益归属": "合计", "所属业务": "",
        **{c: agg[c].sum() for c in ["损益金额", "其中WX", "FIT"]},
    })
    return pd.DataFrame(rows)


def summary_by_entity_currency(df: pd.DataFrame) -> pd.DataFrame:
    """按损益归属 × 币种交叉汇总。"""
    agg = df.groupby(["损益实际归属主体", "原币种"], sort=False).agg(_agg_cols()).reset_index()
    agg.rename(columns={"损益实际归属主体": "损益归属"}, inplace=True)

    rows = []
    for entity, grp in agg.groupby("损益归属", sort=False):
        grp_sorted = grp.sort_values("损益金额", ascending=False)
        for _, row in grp_sorted.iterrows():
            rows.append(row.to_dict())
        rows.append({
            "损益归属": f"{entity} 小计", "原币种": "",
            **{c: grp[c].sum() for c in ["损益金额", "其中WX", "FIT"]},
        })

    rows.append({
        "损益归属": "合计", "原币种": "",
        **{c: agg[c].sum() for c in ["损益金额", "其中WX", "FIT"]},
    })
    return pd.DataFrame(rows)


def summary_by_merchant(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    """按商户号汇总（TOP N by 绝对值）。"""
    agg = (
        df.groupby(["损益实际归属主体", "所属业务", "商户号", "商户类型"], sort=False)
        .agg(_agg_cols()).reset_index()
    )
    agg.rename(columns={"损益实际归属主体": "损益归属"}, inplace=True)

    agg["_abs"] = agg["损益金额"].abs()
    agg.sort_values("_abs", ascending=False, inplace=True)
    agg.drop(columns="_abs", inplace=True)

    if top_n and len(agg) > top_n:
        agg = agg.head(top_n).copy()

    return _add_total_row(agg, "损益归属")


def detail_table(df: pd.DataFrame) -> pd.DataFrame:
    """明细汇总表：归属→产品→业务→商户号，带分组小计。"""
    merchant_agg = (
        df.groupby(["损益实际归属主体", "产品类型", "所属业务", "商户号"], sort=False)
        .agg(_agg_cols()).reset_index()
    )

    rows = []
    for entity, entity_group in merchant_agg.groupby("损益实际归属主体", sort=False):
        entity_total = {"损益金额": 0.0, "其中WX": 0.0, "FIT": 0.0}
        for (prod_type, biz), biz_group in entity_group.groupby(["产品类型", "所属业务"], sort=False):
            for _, row in biz_group.iterrows():
                rows.append({
                    "损益归属": entity, "产品类型": prod_type, "所属业务": biz,
                    "商户号": row["商户号"],
                    "损益金额": row["损益金额"], "其中WX": row["其中WX"], "FIT": row["FIT"],
                })
                for k in entity_total:
                    entity_total[k] += row[k]
        rows.append({
            "损益归属": f"{entity} 汇总", "产品类型": "", "所属业务": "", "商户号": "",
            **entity_total,
        })

    grand = merchant_agg[["损益金额", "其中WX", "FIT"]].sum()
    rows.append({
        "损益归属": "合计", "产品类型": "", "所属业务": "", "商户号": "",
        "损益金额": grand["损益金额"], "其中WX": grand["其中WX"], "FIT": grand["FIT"],
    })
    return pd.DataFrame(rows)


# ===================== 多月对比 =====================

def monthly_comparison(period_dfs: list[tuple[str, pd.DataFrame]], group_col: str) -> pd.DataFrame:
    """
    多月份并排对比。
    
    Args:
        period_dfs: [(label, df), ...]
        group_col: 分组列名，如 '损益实际归属主体'、'所属业务' 等
    
    Returns:
        合并后的 DataFrame，每个月的损益/WX/FIT 并排展示 + 累计列
    """
    labels = [label for label, _ in period_dfs]
    agg_list = []

    for label, df in period_dfs:
        agg = df.groupby(group_col, sort=False).agg(_agg_cols()).reset_index()
        agg.rename(columns={
            "损益金额": f"{label}-损益金额",
            "其中WX": f"{label}-其中WX",
            "FIT": f"{label}-FIT",
        }, inplace=True)
        agg_list.append(agg)

    merged = agg_list[0]
    for agg in agg_list[1:]:
        merged = merged.merge(agg, on=group_col, how="outer")
    merged.fillna(0, inplace=True)

    # 累计列
    for metric in ["损益金额", "其中WX", "FIT"]:
        merged[f"累计-{metric}"] = sum(merged[f"{l}-{metric}"] for l in labels)

    # 按累计损益金额排序
    merged.sort_values("累计-损益金额", ascending=False, inplace=True)

    return merged


# ===================== 统一入口 =====================

def run_all_analysis(df: pd.DataFrame) -> dict:
    """
    运行所有维度的分析，返回结果字典。
    
    Returns:
        {
            'overview': {...总览指标},
            'by_entity': DataFrame,
            'by_business': DataFrame,
            'by_product': DataFrame,
            'by_currency': DataFrame,
            'by_merchant_type': DataFrame,
            'by_entity_business': DataFrame,
            'by_entity_currency': DataFrame,
            'by_merchant': DataFrame,
            'detail': DataFrame,
        }
    """
    total_pnl = df["损益金额"].sum()
    total_wx = df["其中WX"].sum()
    total_fit = df["FIT"].sum()

    overview = {
        "total_pnl": total_pnl,
        "total_wx": total_wx,
        "total_fit": total_fit,
        "record_count": len(df),
        "entity_count": df["损益实际归属主体"].nunique(),
        "business_count": df["所属业务"].nunique(),
        "currency_count": df["原币种"].nunique(),
        "merchant_count": df["商户号"].nunique(),
        "pnl_positive_count": (df["损益金额"] > 0).sum(),
        "pnl_negative_count": (df["损益金额"] < 0).sum(),
        "pnl_zero_count": (df["损益金额"] == 0).sum(),
    }

    return {
        "overview": overview,
        "by_entity": summary_by_entity(df),
        "by_business": summary_by_business(df),
        "by_product": summary_by_product(df),
        "by_currency": summary_by_currency(df),
        "by_merchant_type": summary_by_merchant_type(df),
        "by_entity_business": summary_by_entity_business(df),
        "by_entity_currency": summary_by_entity_currency(df),
        "by_merchant": summary_by_merchant(df),
        "detail": detail_table(df),
    }
