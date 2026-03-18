# -*- coding: utf-8 -*-
"""
Reflection Engine - 反思引擎
=============================
自动评估分析质量、追踪预测准确性、驱动策略优化

功能：
1. 质量评估 - 每次深度分析后自动评估
2. 预测追踪 - 记录预测 vs 实际走势
3. 知识归档 - 将高质量分析存入知识库
4. 策略进化 - 基于反思调整分析权重
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class ReflectionEngine:
    """
    索罗斯 Agent 的反思引擎
    
    核心功能：
    - 自动触发反思流程
    - 评估分析质量（数据完整性、逻辑性、准确性）
    - 追踪预测与实际走势
    - 将高质量分析归档为可检索知识
    """
    
    def __init__(self, memory_system):
        self.memory = memory_system
        
        # 反思触发条件配置
        self.triggers = {
            "deep_analysis": True,       # 深度分析后触发
            "prediction_made": True,     # 做出预测后触发
            "error_detected": False,     # 检测到错误时触发
            "manual": True,              # 手动触发
        }
        
        # 分析质量评分权重
        self.quality_weights = {
            "data_completeness": 0.3,    # 数据完整性
            "logical_coherence": 0.3,    # 逻辑连贯性
            "evidence_quality": 0.2,     # 证据质量
            "actionability": 0.2,        # 可操作性
        }
    
    # ═══════════════════════════════════════════════
    # 核心反思流程
    # ═══════════════════════════════════════════════
    
    def should_reflect(self, user_message: str, response: str) -> bool:
        """
        判断是否需要触发反思
        
        触发条件：
        - 用户请求深度分析（关键词匹配）
        - 响应长度超过阈值（深度分析的标志）
        - 包含预测性内容
        - 工具调用后生成了数据驱动的分析
        """
        # 深度分析关键词
        deep_analysis_keywords = [
            "分析", "预测", "走势", "判断", "看法",
            "评估", "展望", "趋势", "机会", "风险"
        ]
        
        # 检查关键词
        if any(kw in user_message for kw in deep_analysis_keywords):
            return True
        
        # 检查响应长度（深度分析通常较长）
        if len(response) > 500:
            return True
        
        # 检查是否包含预测性内容
        prediction_keywords = ["会涨", "会跌", "将", "预计", "预期", "上看", "下看"]
        if any(kw in response for kw in prediction_keywords):
            return True
        
        return False
    
    def reflect(
        self,
        user_message: str,
        response: str,
        context: Dict = None
    ) -> Dict:
        """
        执行完整反思流程
        
        Args:
            user_message: 用户原始消息
            response: Agent 的响应
            context: 额外上下文（工具调用历史、理解结果等）
            
        Returns:
            反思结果
        """
        context = context or {}
        
        # Step 1: 质量评估
        quality = self._assess_quality(user_message, response, context)
        
        # Step 2: 提取预测
        predictions = self._extract_predictions(response)
        
        # Step 3: 生成反思内容
        reflection = self._generate_reflection(
            user_message, 
            response, 
            quality,
            predictions,
            context
        )
        
        # Step 4: 保存反思
        reflection_id = self.memory.save_reflection(
            topic=self._extract_topic(user_message),
            reflection=reflection,
            context={
                "quality": quality,
                "predictions": predictions,
                "response_length": len(response),
                "has_data": bool(context.get("tool_results"))
            }
        )
        
        # Step 5: 如果质量高，归档到知识库
        if quality["overall_score"] >= 0.7:
            self._archive_insight(user_message, response, quality, predictions)
        
        return {
            "id": reflection_id,
            "quality": quality,
            "predictions": predictions,
            "reflection": reflection
        }
    
    # ═══════════════════════════════════════════════
    # 质量评估
    # ═══════════════════════════════════════════════
    
    def _assess_quality(
        self,
        user_message: str,
        response: str,
        context: Dict
    ) -> Dict:
        """评估分析质量"""
        
        scores = {}
        
        # 1. 数据完整性 - 检查是否有数据支撑
        data_indicators = ["%", "点", "利率", "汇率", "波动率", "数据"]
        has_data = any(indicator in response for indicator in data_indicators)
        has_citation = "来源" in response or "根据" in response or "数据显示" in response
        scores["data_completeness"] = 0.8 if has_data else 0.3
        if has_data and has_citation:
            scores["data_completeness"] = 1.0
        
        # 2. 逻辑连贯性 - 检查分析结构
        has_structure = all(marker in response for marker in ["首先", "但是", "因此"]) or \
                       all(marker in response for marker in ["1", "2", "3"])
        scores["logical_coherence"] = 0.8 if has_structure else 0.5
        
        # 3. 证据质量 - 检查引用和推理
        evidence_markers = ["因为", "由于", "基于", "鉴于", "数据显示"]
        has_evidence = any(marker in response for marker in evidence_markers)
        scores["evidence_quality"] = 0.8 if has_evidence else 0.4
        
        # 4. 可操作性 - 检查是否给出具体建议
        action_markers = ["建议", "可以", "应该", "考虑", "关注"]
        has_action = any(marker in response for marker in action_markers)
        scores["actionability"] = 0.8 if has_action else 0.3
        
        # 计算加权总分
        overall = sum(
            scores[k] * self.quality_weights[k]
            for k in self.quality_weights
        )
        
        return {
            "data_completeness": scores["data_completeness"],
            "logical_coherence": scores["logical_coherence"],
            "evidence_quality": scores["evidence_quality"],
            "actionability": scores["actionability"],
            "overall_score": round(overall, 2)
        }
    
    # ═══════════════════════════════════════════════
    # 预测提取
    # ═══════════════════════════════════════════════
    
    def _extract_predictions(self, response: str) -> List[Dict]:
        """从响应中提取预测"""
        predictions = []
        
        import re
        
        # 匹配货币对预测模式
        # 例如: "USD/CNH 将上涨到 7.5" / "EUR/USD 可能下跌"
        patterns = [
            r'([A-Z]{3}/[A-Z]{3}).*?(上涨|下跌|升值|贬值|突破|跌破).*?(\d+\.?\d*)',
            r'([A-Z]{3}/[A-Z]{3}).*?(会涨|会跌|将|预计)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, response)
            for match in matches:
                predictions.append({
                    "target": match.group(1) if match.lastindex >= 1 else "unknown",
                    "direction": "up" if "涨" in match.group(0) else "down",
                    "text": match.group(0)
                })
        
        return predictions
    
    # ═══════════════════════════════════════════════
    # 反思生成
    # ═══════════════════════════════════════════════
    
    def _generate_reflection(
        self,
        user_message: str,
        response: str,
        quality: Dict,
        predictions: List[Dict],
        context: Dict
    ) -> str:
        """生成反思文本"""
        
        parts = [f"## 分析反思 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
        
        # 用户问题
        parts.append(f"\n### 问题")
        parts.append(user_message)
        
        # 质量评分
        parts.append(f"\n### 质量评估")
        parts.append(f"- 数据完整性: {quality['data_completeness']:.1f}")
        parts.append(f"- 逻辑连贯性: {quality['logical_coherence']:.1f}")
        parts.append(f"- 证据质量: {quality['evidence_quality']:.1f}")
        parts.append(f"- 可操作性: {quality['actionability']:.1f}")
        parts.append(f"- **总体评分: {quality['overall_score']:.2f}**")
        
        # 预测提取
        if predictions:
            parts.append(f"\n### 做出的预测")
            for p in predictions:
                parts.append(f"- {p['target']}: {p['direction']}")
        
        # 自我改进建议
        parts.append(f"\n### 改进建议")
        
        if quality["data_completeness"] < 0.6:
            parts.append("- 增加数据支撑，引用具体汇率或波动率")
        if quality["logical_coherence"] < 0.6:
            parts.append("- 增强分析逻辑，使用结构化表达")
        if quality["evidence_quality"] < 0.6:
            parts.append("- 添加更多证据和推理过程")
        if quality["actionability"] < 0.6:
            parts.append("- 给出更具体的交易建议")
        
        if all(v >= 0.6 for v in [
            quality["data_completeness"],
            quality["logical_coherence"],
            quality["evidence_quality"],
            quality["actionability"]
        ]):
            parts.append("- 分析质量良好，保持当前风格")
        
        return "\n".join(parts)
    
    # ═══════════════════════════════════════════════
    # 知识归档
    # ═══════════════════════════════════════════════
    
    def _archive_insight(
        self,
        user_message: str,
        response: str,
        quality: Dict,
        predictions: List[Dict]
    ):
        """将高质量分析归档到知识库"""
        
        # 提取关键洞察
        key_points = []
        
        # 从响应中提取关键句子
        sentences = response.split("。")
        for sentence in sentences:
            if any(kw in sentence for kw in ["建议", "观点", "判断", "认为", "预计"]):
                if len(sentence) > 10:
                    key_points.append(sentence.strip())
        
        if key_points:
            # 保存到知识库
            self.memory.save_knowledge(
                category="insights",
                key=f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                content={
                    "user_query": user_message,
                    "key_points": key_points,
                    "predictions": predictions,
                    "quality_score": quality["overall_score"],
                    "archived_at": datetime.now().isoformat()
                }
            )
    
    # ═══════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════
    
    def _extract_topic(self, user_message: str) -> str:
        """提取反思主题"""
        if len(user_message) > 50:
            return user_message[:50] + "..."
        return user_message
    
    def get_recent_reflections(self, limit: int = 10) -> List[Dict]:
        """获取最近的反思"""
        return self.memory.load_recent_reflections(limit)
    
    def get_quality_trend(self, days: int = 7) -> Dict:
        """获取质量趋势"""
        reflections = self.memory.load_recent_reflections(limit=100)
        
        if not reflections:
            return {"avg_quality": 0, "trend": "no_data"}
        
        # 筛选最近几天
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [r for r in reflections if r.get("created_at", "") > cutoff]
        
        if not recent:
            return {"avg_quality": 0, "trend": "no_data"}
        
        # 计算平均质量
        total = 0
        count = 0
        for r in recent:
            ctx = r.get("context", {})
            quality = ctx.get("quality", {})
            if quality:
                total += quality.get("overall_score", 0)
                count += 1
        
        avg = total / count if count > 0 else 0
        
        return {
            "avg_quality": round(avg, 2),
            "count": count,
            "days": days
        }


# 全局实例
_reflection_engine = None


def get_reflection_engine(memory_system) -> ReflectionEngine:
    """获取反思引擎实例"""
    global _reflection_engine
    if _reflection_engine is None:
        _reflection_engine = ReflectionEngine(memory_system)
    return _reflection_engine
