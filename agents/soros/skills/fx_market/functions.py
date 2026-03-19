# -*- coding: utf-8 -*-
"""
外汇市场分析技能函数
====================
"""


def _func_calculate_pip_value(pair: str, lot_size: float = 100000) -> dict:
    """计算货币对的点值"""
    # 简化计算
    base_currency = pair.split("/")[0]
    
    pip_values = {
        "USD": 10,
        "EUR": 10,
        "GBP": 10,
        "JPY": 1000,
        "CNY": 100,
    }
    
    return {
        "pair": pair,
        "pip_value": pip_values.get(base_currency, 10),
        "lot_size": lot_size,
        "note": "点值取决于账户货币和报价货币"
    }


def _func_format_rate_change(old_rate: float, new_rate: float) -> dict:
    """计算汇率变化"""
    if not old_rate or old_rate == 0:
        return {"error": "Invalid old rate"}
    
    change = new_rate - old_rate
    change_pct = (change / old_rate) * 100
    
    direction = "上涨" if change > 0 else "下跌"
    
    return {
        "old_rate": old_rate,
        "new_rate": new_rate,
        "change": round(change, 5),
        "change_pct": round(change_pct, 2),
        "direction": direction
    }


def _func_estimate_volatility_category(iv: float) -> str:
    """根据隐含波动率分类风险等级"""
    if iv is None:
        return "unknown"
    
    if iv < 7:
        return "low"  # 低波动，适合区间交易
    elif iv < 12:
        return "normal"  # 正常波动
    elif iv < 20:
        return "elevated"  #  elevated波动，风险较高
    else:
        return "high"  # 高波动，可能有突破机会
