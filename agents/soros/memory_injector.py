# -*- coding: utf-8 -*-
"""
memory_injector.py
索罗斯 AI 记忆注入系统

功能：
- 在每次对话开始时，自动读取知识库内容
- 将历史洞察、规则、预测注入到 System Prompt
- 实现跨对话的"记忆"能力

作者：索罗斯 AI 自我改造项目
版本：v1.0

适配说明：
- knowledge 目录结构：knowledge/{category}/*.json
- content 字段是嵌套对象：{"content": "...", "tags": [...]}
- 路径基于 BASE_DIR（agents/soros/）
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict


# ============================================================
# 配置区
# ============================================================

# 知识库根目录（相对于本文件所在目录）
MEMORY_BASE = Path(os.getenv(
    "SOROS_MEMORY_PATH",
    str(Path(__file__).parent / "memory")
))

# 注入内容的最大字符数（避免 context 太长）
MAX_CONTEXT_LENGTH = 3000

# 各类记忆的最大条数
MAX_PLAYBOOK_RULES = 10
MAX_REFLECTIONS = 3
MAX_PREDICTIONS = 5
MAX_INSIGHTS = 5


# ============================================================
# 核心读取函数（已适配实际项目数据结构）
# ============================================================

def _load_json_files(directory: Path) -> List[Dict]:
    """通用 JSON 文件加载器，递归扫描目录"""
    items = []
    if not directory.exists():
        return items
    for f in sorted(directory.rglob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
                items.append(data)
        except Exception:
            continue
    return items


def load_playbook_rules() -> List[Dict]:
    """
    读取 Playbook 规则
    实际路径：memory/knowledge/playbook/*.json
    数据结构：{"category": "playbook", "key": "...", "content": {"content": "...", "tags": [...]}, "created_at": "..."}
    """
    rules = []
    playbook_path = MEMORY_BASE / "knowledge" / "playbook"
    
    for data in _load_json_files(playbook_path):
        # 提取嵌套的 content
        inner_content = data.get("content", {})
        if isinstance(inner_content, dict):
            text = inner_content.get("content", "")
        else:
            text = str(inner_content)
        
        rules.append({
            "key": data.get("key", ""),
            "insight": text[:300],  # 截断避免太长
            "timestamp": data.get("created_at", data.get("updated_at", ""))
        })
    
    # 按时间倒序，取最新的
    rules.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return rules[:MAX_PLAYBOOK_RULES]


def load_recent_insights() -> List[Dict]:
    """
    读取最近的市场洞察（非 playbook 类）
    扫描 knowledge/ 下除 playbook 以外的所有子目录
    """
    insights = []
    knowledge_path = MEMORY_BASE / "knowledge"
    
    if not knowledge_path.exists():
        return insights
    
    for subdir in sorted(knowledge_path.iterdir()):
        if not subdir.is_dir() or subdir.name == "playbook":
            continue
        
        for data in _load_json_files(subdir):
            # 提取嵌套的 content
            inner_content = data.get("content", {})
            if isinstance(inner_content, dict):
                # insights 的 key_points 或 content 字段
                text = inner_content.get("content", "")
                if not text:
                    key_points = inner_content.get("key_points", [])
                    if key_points:
                        text = key_points[0][:300] if isinstance(key_points[0], str) else str(key_points[0])[:300]
            else:
                text = str(inner_content)
            
            insights.append({
                "key": data.get("key", ""),
                "insight": text[:300],
                "category": data.get("category", subdir.name),
                "timestamp": data.get("created_at", data.get("updated_at", ""))
            })
    
    insights.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return insights[:MAX_INSIGHTS]


def load_recent_reflections() -> List[Dict]:
    """
    读取最近的自我反思
    路径：memory/reflections/*.json
    数据结构：{"id": "...", "topic": "...", "reflection": "...", "context": {...}, "created_at": "..."}
    """
    reflections = []
    reflection_path = MEMORY_BASE / "reflections"
    
    for data in _load_json_files(reflection_path):
        reflections.append({
            "topic": data.get("topic", ""),
            "reflection": data.get("reflection", "")[:200],  # 截断
            "timestamp": data.get("created_at", "")
        })
    
    reflections.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return reflections[:MAX_REFLECTIONS]


def load_pending_predictions() -> List[Dict]:
    """
    读取未验证的预测
    路径：memory/predictions/*.json
    数据结构：{"id": "...", "target": "...", "direction": "...", "timeframe": "...", 
               "rationale": "...", "verified": false, "created_at": "..."}
    """
    predictions = []
    prediction_path = MEMORY_BASE / "predictions"
    
    for data in _load_json_files(prediction_path):
        if not data.get("verified", False):
            predictions.append({
                "target": data.get("target", ""),
                "direction": data.get("direction", ""),
                "timeframe": data.get("timeframe", ""),
                "rationale": data.get("rationale", "")[:150],
                "timestamp": data.get("created_at", "")[:10] if data.get("created_at") else ""
            })
    
    predictions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return predictions[:MAX_PREDICTIONS]


# ============================================================
# 格式化函数
# ============================================================

def format_memory_context() -> str:
    """
    把所有记忆格式化成可注入 System Prompt 的字符串
    """
    sections = []
    
    # --- Section 1: Playbook 规则 ---
    playbooks = load_playbook_rules()
    if playbooks:
        lines = ["## 我的核心交易规则（Playbook）\n"]
        for i, rule in enumerate(playbooks, 1):
            lines.append(f"{i}. **{rule['key']}**: {rule['insight']}")
        sections.append("\n".join(lines))
    
    # --- Section 2: 待验证预测 ---
    predictions = load_pending_predictions()
    if predictions:
        lines = ["## 待验证的预测（我应该检查这些是否兑现了）\n"]
        for p in predictions:
            lines.append(
                f"- {p['target']} {p['direction']} ({p['timeframe']}) "
                f"— 发表于 {p['timestamp']}"
            )
        sections.append("\n".join(lines))
    
    # --- Section 3: 最近反思 ---
    reflections = load_recent_reflections()
    if reflections:
        lines = ["## 最近的市场反思\n"]
        for r in reflections:
            lines.append(f"### {r['topic']}\n{r['reflection']}\n")
        sections.append("\n".join(lines))
    
    # --- Section 4: 最新市场洞察 ---
    insights = load_recent_insights()
    if insights:
        lines = ["## 最新市场洞察\n"]
        for ins in insights:
            lines.append(f"- **[{ins['category']}] {ins['key']}**: {ins['insight']}")
        sections.append("\n".join(lines))
    
    if not sections:
        return ""
    
    full_context = "\n\n".join(sections)
    
    # 超长截断保护
    if len(full_context) > MAX_CONTEXT_LENGTH:
        full_context = full_context[:MAX_CONTEXT_LENGTH] + "\n\n[...记忆内容已截断，避免超出上下文限制]"
    
    return full_context


# ============================================================
# 主注入函数 — 这是对外暴露的核心接口
# ============================================================

def inject_memory(base_prompt: str) -> str:
    """
    将记忆上下文注入到 System Prompt
    
    用法：
        from memory_injector import inject_memory
        
        SYSTEM_PROMPT = "你是索罗斯..."
        enriched_prompt = inject_memory(SYSTEM_PROMPT)
        # 把 enriched_prompt 传给 LLM
    
    Args:
        base_prompt: 原始 System Prompt 字符串
    
    Returns:
        注入了记忆上下文的 System Prompt
    """
    memory_context = format_memory_context()
    
    if not memory_context:
        return base_prompt
    
    injected = (
        base_prompt
        + "\n\n"
        + "## 我的长期记忆（跨对话持久化）\n\n"
        + "<persistent_memory>\n"
        + memory_context
        + "\n</persistent_memory>"
    )
    
    return injected


def get_memory_summary() -> dict:
    """
    返回记忆系统的摘要统计
    用于调试和监控
    """
    return {
        "playbook_rules": len(load_playbook_rules()),
        "pending_predictions": len(load_pending_predictions()),
        "recent_reflections": len(load_recent_reflections()),
        "recent_insights": len(load_recent_insights()),
        "memory_base_path": str(MEMORY_BASE),
        "memory_base_exists": MEMORY_BASE.exists(),
        "knowledge_subdirs": [
            d.name for d in (MEMORY_BASE / "knowledge").iterdir() if d.is_dir()
        ] if (MEMORY_BASE / "knowledge").exists() else [],
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# 调试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  索罗斯 AI 记忆注入系统 — 诊断报告")
    print("=" * 60)
    print()
    
    summary = get_memory_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
    
    print()
    print("=" * 60)
    print("  生成的注入内容预览")
    print("=" * 60)
    print()
    
    context = format_memory_context()
    if context:
        print(context)
        print()
        print(f"  [总字符数: {len(context)}]")
    else:
        print("  （知识库为空，无内容注入）")
    
    print()
    print("=" * 60)
    print("  注入测试")
    print("=" * 60)
    print()
    
    test_prompt = "你是索罗斯...（测试用简短 prompt）"
    result = inject_memory(test_prompt)
    if result != test_prompt:
        print(f"  ✅ 注入成功！Prompt 从 {len(test_prompt)} 字符 → {len(result)} 字符")
    else:
        print("  ⚠️ 无记忆可注入（知识库可能为空）")
