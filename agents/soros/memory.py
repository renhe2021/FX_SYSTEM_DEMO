# -*- coding: utf-8 -*-
"""
Memory System - 索罗斯 Agent 的长期记忆系统
============================================
支持多种记忆类型：会话记忆、用户偏好、市场知识库、自我反思
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import hashlib


class MemorySystem:
    """索罗斯 Agent 的记忆系统"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.memory_dir = base_dir / "memory"
        
        # 创建子目录
        self.sessions_dir = self.memory_dir / "sessions"
        self.users_dir = self.memory_dir / "users"
        self.knowledge_dir = self.memory_dir / "knowledge"
        self.reflections_dir = self.memory_dir / "reflections"
        self.predictions_dir = self.memory_dir / "predictions"  # 新增：预测追踪
        
        for d in [self.sessions_dir, self.users_dir, self.knowledge_dir, self.reflections_dir, self.predictions_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def _hash_id(self, text: str) -> str:
        """生成短哈希 ID"""
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    # ═══════════════════════════════════════════════
    # Session Memory - 会话记忆
    # ═══════════════════════════════════════════════
    
    def save_session(self, session_id: str, messages: List[Dict], user_id: str = "default") -> str:
        """保存会话记忆"""
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": messages
        }
        
        filename = f"{session_id}.json"
        filepath = self.sessions_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """加载会话记忆"""
        filepath = self.sessions_dir / f"{session_id}.json"
        if not filepath.exists():
            return None
        
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    
    def get_recent_sessions(self, user_id: str = "default", limit: int = 10) -> List[Dict]:
        """获取最近的会话列表"""
        sessions = []
        for f in self.sessions_dir.glob("*.json"):
            try:
                with open(f, encoding="utf-8") as fp:
                    data = json.load(fp)
                    if data.get("user_id") == user_id:
                        sessions.append({
                            "session_id": data["session_id"],
                            "created_at": data.get("created_at"),
                            "message_count": data.get("message_count", 0),
                            "preview": data.get("messages", [{}])[-1].get("content", "")[:100]
                        })
            except:
                continue
        
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions[:limit]
    
    # ═══════════════════════════════════════════════
    # User Preference - 用户偏好
    # ═══════════════════════════════════════════════
    
    def save_user_preference(self, user_id: str, preferences: Dict) -> None:
        """保存用户偏好"""
        filepath = self.users_dir / f"{user_id}.json"
        
        existing = {}
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                existing = json.load(f)
        
        existing.update({
            "user_id": user_id,
            "updated_at": datetime.now().isoformat(),
            "preferences": preferences
        })
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    
    def load_user_preference(self, user_id: str) -> Dict:
        """加载用户偏好"""
        filepath = self.users_dir / f"{user_id}.json"
        if not filepath.exists():
            return {}
        
        with open(filepath, encoding="utf-8") as f:
            return json.load(f).get("preferences", {})
    
    # ═══════════════════════════════════════════════
    # Market Knowledge Base - 市场知识库
    # ═══════════════════════════════════════════════
    
    def save_knowledge(self, category: str, key: str, content: Dict) -> str:
        """保存知识到知识库"""
        category_dir = self.knowledge_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = category_dir / f"{self._hash_id(key)}.json"
        knowledge_entry = {
            "category": category,
            "key": key,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(knowledge_entry, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def load_knowledge(self, category: str, key: str) -> Optional[Dict]:
        """加载特定知识"""
        filepath = self.knowledge_dir / category / f"{self._hash_id(key)}.json"
        if not filepath.exists():
            return None
        
        with open(filepath, encoding="utf-8") as f:
            return json.load(f).get("content")
    
    def search_knowledge(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """搜索知识库"""
        results = []
        search_dir = self.knowledge_dir if not category else self.knowledge_dir / category
        
        if not search_dir.exists():
            return results
        
        query_lower = query.lower()
        for filepath in search_dir.rglob("*.json"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    content = data.get("content", {})
                    # 简单关键词匹配
                    text = json.dumps(content).lower()
                    if query_lower in text:
                        results.append({
                            "category": data.get("category"),
                            "key": data.get("key"),
                            "content": content,
                            "updated_at": data.get("updated_at")
                        })
            except:
                continue
        
        # 按更新时间排序，返回最近的 limit 条
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results[:limit]
    
    def list_knowledge_categories(self) -> List[str]:
        """列出知识库分类"""
        if not self.knowledge_dir.exists():
            return []
        return [d.name for d in self.knowledge_dir.iterdir() if d.is_dir()]
    
    # ═══════════════════════════════════════════════
    # Reflection - 自我反思
    # ═══════════════════════════════════════════════
    
    def save_reflection(self, topic: str, reflection: str, context: Dict = None) -> str:
        """保存反思记录"""
        reflection_id = self._hash_id(f"{topic}_{datetime.now().isoformat()}")
        
        reflection_data = {
            "id": reflection_id,
            "topic": topic,
            "reflection": reflection,
            "context": context or {},
            "created_at": datetime.now().isoformat()
        }
        
        filepath = self.reflections_dir / f"{reflection_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(reflection_data, f, ensure_ascii=False, indent=2)
        
        return reflection_id
    
    def load_recent_reflections(self, limit: int = 10) -> List[Dict]:
        """加载最近的反思"""
        reflections = []
        for f in self.reflections_dir.glob("*.json"):
            try:
                with open(f, encoding="utf-8") as fp:
                    reflections.append(json.load(fp))
            except:
                continue
        
        reflections.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return reflections[:limit]
    
    def get_reflection_summary(self) -> str:
        """获取反思摘要（用于 LLM 上下文）"""
        recent = self.load_recent_reflections(5)
        if not recent:
            return ""
        
        summary_parts = ["## 最近的市场反思："]
        for r in recent:
            summary_parts.append(f"\n### {r.get('topic', 'Unknown')}")
            summary_parts.append(r.get("reflection", ""))
        
        return "\n".join(summary_parts)
    
    # ═══════════════════════════════════════════════
    # Prediction Tracking - 预测追踪
    # ═══════════════════════════════════════════════
    
    def save_prediction(
        self,
        target: str,  # 如 "USD/CNH"
        direction: str,  # "up" / "down" / "sideways"
        timeframe: str,  # 如 "1周", "1个月"
        rationale: str,  # 预测理由
        context: Dict = None
    ) -> str:
        """保存市场预测"""
        prediction_id = self._hash_id(f"{target}_{datetime.now().isoformat()}")
        
        prediction_data = {
            "id": prediction_id,
            "target": target,
            "direction": direction,
            "timeframe": timeframe,
            "rationale": rationale,
            "context": context or {},
            "created_at": datetime.now().isoformat(),
            "outcome": None,  # 待验证
            "verified": False
        }
        
        filepath = self.predictions_dir / f"{prediction_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(prediction_data, f, ensure_ascii=False, indent=2)
        
        return prediction_id
    
    def verify_prediction(
        self,
        prediction_id: str,
        actual_direction: str,  # 实际走势
        actual_price: float = None,
        notes: str = None
    ) -> bool:
        """验证预测结果"""
        filepath = self.predictions_dir / f"{prediction_id}.json"
        if not filepath.exists():
            return False
        
        with open(filepath, encoding="utf-8") as f:
            prediction = json.load(f)
        
        # 判断预测是否正确
        prediction["outcome"] = {
            "actual_direction": actual_direction,
            "actual_price": actual_price,
            "verified_at": datetime.now().isoformat(),
            "notes": notes
        }
        
        # 计算是否正确
        pred_dir = prediction.get("direction", "").lower()
        actual_dir = actual_direction.lower()
        
        if pred_dir == actual_dir:
            prediction["correct"] = True
        elif pred_dir == "sideways" and actual_dir in ["up", "down"]:
            # 区间震荡算一半对
            prediction["correct"] = None
        else:
            prediction["correct"] = False
        
        prediction["verified"] = True
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(prediction, f, ensure_ascii=False, indent=2)
        
        return True
    
    def load_predictions(self, target: str = None, verified_only: bool = False, limit: int = 20) -> List[Dict]:
        """加载预测记录"""
        predictions = []
        
        for f in self.predictions_dir.glob("*.json"):
            try:
                with open(f, encoding="utf-8") as fp:
                    pred = json.load(fp)
                    
                    # 筛选
                    if target and pred.get("target") != target:
                        continue
                    if verified_only and not pred.get("verified"):
                        continue
                    
                    predictions.append(pred)
            except:
                continue
        
        # 按时间排序
        predictions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return predictions[:limit]
    
    def get_prediction_stats(self) -> Dict:
        """获取预测准确率统计"""
        predictions = self.load_predictions(verified_only=True)
        
        if not predictions:
            return {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0
            }
        
        total = len(predictions)
        correct = sum(1 for p in predictions if p.get("correct") == True)
        
        return {
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0.0,
            "by_target": self._get_accuracy_by_target(predictions)
        }
    
    def _get_accuracy_by_target(self, predictions: List[Dict]) -> Dict:
        """按目标货币对统计准确率"""
        by_target = {}
        for pred in predictions:
            target = pred.get("target", "unknown")
            if target not in by_target:
                by_target[target] = {"total": 0, "correct": 0}
            by_target[target]["total"] += 1
            if pred.get("correct"):
                by_target[target]["correct"] += 1
        
        # 计算准确率
        for target, stats in by_target.items():
            stats["accuracy"] = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0.0
        
        return by_target
    
    # ═══════════════════════════════════════════════
    # Context Builder - 上下文构建
    # ═══════════════════════════════════════════════
    
    def build_context(self, session_id: str, user_id: str = "default") -> str:
        """构建 LLM 上下文提示 — 增强版：含预测追踪、知识库精华"""
        context_parts = []
        
        # 1. 用户偏好
        prefs = self.load_user_preference(user_id)
        if prefs:
            context_parts.append("## 用户偏好：")
            context_parts.append(json.dumps(prefs, ensure_ascii=False, indent=2))
        
        # 2. 预测追踪统计（让索罗斯知道自己的准确率）
        stats = self.get_prediction_stats()
        if stats.get("total", 0) > 0:
            context_parts.append("## 我的预测追踪：")
            context_parts.append(f"- 总预测数: {stats['total']}, 正确: {stats['correct']}, 准确率: {stats['accuracy']}%")
            if stats.get("by_target"):
                for target, ts in stats["by_target"].items():
                    context_parts.append(f"  - {target}: {ts['correct']}/{ts['total']} ({ts['accuracy']}%)")
        
        # 3. 最近未验证的预测（提醒索罗斯去验证）
        unverified = self.load_predictions(verified_only=False, limit=5)
        unverified = [p for p in unverified if not p.get("verified")]
        if unverified:
            context_parts.append("## 待验证的预测（我应该检查这些是否兑现了）：")
            for p in unverified[:3]:
                context_parts.append(
                    f"- {p.get('target')} {p.get('direction')} ({p.get('timeframe')}) "
                    f"— 发表于 {p.get('created_at', 'unknown')[:10]}"
                )
        
        # 4. 最近反思
        reflection_summary = self.get_reflection_summary()
        if reflection_summary:
            context_parts.append(reflection_summary)
        
        # 5. 相关知识检索（基于最新用户消息）
        session = self.load_session(session_id)
        if session and session.get("messages"):
            last_user_msg = None
            for msg in reversed(session["messages"]):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            
            if last_user_msg:
                # 搜索相关知识
                related = self.search_knowledge(last_user_msg, limit=3)
                if related:
                    context_parts.append("## 相关市场知识：")
                    for item in related:
                        context_parts.append(f"### {item.get('key')}")
                        context_parts.append(json.dumps(item.get("content"), ensure_ascii=False, indent=2))
        
        return "\n\n".join(context_parts)


# 全局实例
_memory_instance = None

def get_memory(base_dir: Path = None) -> MemorySystem:
    """获取记忆系统实例"""
    global _memory_instance
    if _memory_instance is None:
        if base_dir is None:
            base_dir = Path(__file__).parent
        _memory_instance = MemorySystem(base_dir)
    return _memory_instance
