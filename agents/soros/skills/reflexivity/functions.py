# -*- coding: utf-8 -*-
"""
反射性理论分析函数
==================
"""


def _func_detect_phase(observations: list) -> dict:
    """检测反射性阶段"""
    obs_text = " ".join(observations).lower()
    
    positive_words = ["上涨", "牛市", "泡沫", "飙升", "涌入", "抢购", "乐观", "创新高"]
    negative_words = ["下跌", "熊市", "恐慌", "抛售", "暴跌", "悲观", "创新低", "崩溃"]
    
    pos_count = sum(1 for w in positive_words if w in obs_text)
    neg_count = sum(1 for w in negative_words if w in obs_text)
    
    if pos_count > neg_count + 1:
        phase = "正反馈阶段（自我强化）"
        description = "市场可能处于泡沫形成期，关注拥挤度和杠杆"
    elif neg_count > pos_count + 1:
        phase = "负反馈阶段（自我修正）"
        description = "市场可能接近底部，关注流动性"
    else:
        phase = "均衡状态"
        description = "暂无明显趋势信号"
    
    return {
        "phase": phase,
        "description": description,
        "positive_signals": pos_count,
        "negative_signals": neg_count
    }


def _func_assess_risk(indicators: dict) -> dict:
    """评估市场风险"""
    risk_score = 0
    signals = []
    
    # 杠杆风险
    leverage = indicators.get("leverage", 0)
    if leverage > 5:
        risk_score += 30
        signals.append("高杠杆：市场脆弱")
    
    # 拥挤度
    crowding = indicators.get("crowding", 0)
    if crowding > 0.8:
        risk_score += 25
        signals.append("高拥挤：易踩踏")
    
    # 波动率
    vol = indicators.get("volatility", 0)
    if vol > 20:
        risk_score += 20
        signals.append("高波动：风险加剧")
    
    # 估值偏离
    deviation = indicators.get("valuation_deviation", 0)
    if abs(deviation) > 30:
        risk_score += 25
        signals.append(f"估值偏离：{deviation}%")
    
    level = "low" if risk_score < 25 else "medium" if risk_score < 55 else "high"
    
    return {
        "risk_score": risk_score,
        "risk_level": level,
        "signals": signals
    }


def _func_find_asymmetric(opportunity: dict) -> dict:
    """寻找非对称押注机会"""
    base_scenario = opportunity.get("base_scenario", "")
    upside = opportunity.get("upside_potential", 0)  # 潜在上涨 %
    downside = opportunity.get("downside_risk", 0)   # 潜在下跌 %
    
    if upside > downside * 2 and upside > 20:
        recommendation = "强烈推荐：非对称机会"
        rationale = f"上涨空间 {upside}% > 下跌风险 {downside}% 的2倍"
    elif upside > downside:
        recommendation = "可以考虑：风险收益不对称"
        rationale = f"上涨空间 {upside}% 略大于下跌风险 {downside}%"
    else:
        recommendation = "不建议：风险收益不对称"
        rationale = "下跌风险大于上涨空间"
    
    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "upside": upside,
        "downside": downside
    }
