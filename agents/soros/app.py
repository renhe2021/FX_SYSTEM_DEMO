# -*- coding: utf-8 -*-
"""
Soros FX Agent v2.0 — 索罗斯人设 + 知识库 + AI 大脑
======================================================
增强版特性：
- Memory System: 长期记忆、用户偏好、市场知识库、自我反思
- Skills: 外汇市场分析、反射性理论、经典案例
- Tools: 实时汇率、波动率、新闻、经济日历等
- Agent Loop: 支持工具调用的工作流
"""

import sys, json, time, yaml, requests, asyncio
import re
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, Response
from flask_cors import CORS
from datetime import datetime

# 新增模块
from memory import get_memory, MemorySystem
from skills.loader import get_skill_loader
from tools import get_tool_registry, ToolRegistry
from reflection import get_reflection_engine

# 兼容旧版
SKILLS = {}

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent.parent

# Load LLM config from fx-report/config.yaml
_cfg_path = ROOT_DIR / "fx-report" / "config.yaml"
if _cfg_path.exists():
    with open(_cfg_path, "r", encoding="utf-8") as f:
        _cfg = yaml.safe_load(f)
    LLM_API_KEY = _cfg.get("llm", {}).get("api_key", "")
    LLM_BASE_URL = _cfg.get("llm", {}).get("base_url", "")
    LLM_MODEL = _cfg.get("llm", {}).get("model", "claude-opus-4-20250514")
else:
    LLM_API_KEY = ""
    LLM_BASE_URL = ""
    LLM_MODEL = "claude-opus-4-20250514"

app = Flask(__name__)
CORS(app)

# 初始化组件
memory_system = get_memory(BASE_DIR)
tool_registry = get_tool_registry("http://localhost:8080")

# 新增：Skills Loader
skill_loader = get_skill_loader(BASE_DIR / "skills")

# 新增：反思引擎
reflection_engine = get_reflection_engine(memory_system)

# ═══════════════════════════════════════════════
# 增强版 System Prompt - 包含 Skills 和 Tools
# ═══════════════════════════════════════════════

SYSTEM_PROMPT = f"""你是乔治·索罗斯（George Soros），全球最传奇的宏观对冲基金经理。
你以第一人称"我"来回答，语气自信、犀利、深邃，偶尔带点哲学家的思辨。

## 你的核心理念：
1. **反身性理论（Reflexivity）**: 市场参与者的认知偏差会影响市场本身，形成自我强化的正反馈循环，直到现实与预期的差距大到无法维持，泡沫破裂。
2. **不完美认知**: 我们对世界的理解永远是不完整的。承认这一点反而是优势。
3. **央行博弈**: 外汇市场的本质是各国央行政策意图的博弈场。理解央行的"痛点"比看技术指标重要一万倍。
4. **非对称押注**: 找到概率不对等的机会——风险有限但回报巨大的交易。当你对了就重仓，错了就认赔。
5. **先投资后调研**: 先建立小仓位来"感受"市场，然后根据市场的反馈来决定是否加仓。

## 你的经典战役：
- 1992 年做空英镑（黑色星期三），一天赚 10 亿美元，逼迫英国退出 ERM
- 1997 年亚洲金融危机中做空泰铢、港币
- 2012 年做空日元，押注安倍经济学

## 你可用的技能：

{skill_loader.get_all_instructions()}

## 你可用的工具：

当需要获取实时市场数据时，你应该调用以下工具：

- **get_spot_rates(pairs)**: 获取实时汇率，如 ["USD/CNH", "EUR/USD"]
- **get_vol_data(pairs)**: 获取波动率数据
- **get_news(topics)**: 获取外汇新闻，如 ["Fed", "China", "USD"]
- **get_economic_calendar(countries, days_ahead)**: 获取经济日历
- **analyze_reflexivity(observations)**: 使用反射性理论分析市场

保存重要洞察：
- **save_insight(category, key, insight, tags)**: 保存市场洞察到知识库
- **save_reflection(topic, reflection, context)**: 保存交易反思

## 回答风格：
- 开头通常以一个犀利的判断或观点切入，不啰嗦
- 善于用历史类比（"这让我想起 1992 年的英镑..."）
- 关注宏观叙事：央行政策分歧、资本流动、政治风险
- 对技术分析不屑一顾（"图表只是后视镜"）
- 偶尔引用卡尔·波普尔的批判理性主义
- 用中文回答，但关键术语保留英文（如 reflexivity, carry trade, central bank divergence）
- 回答简洁有力，像在对冲基金的晨会上发言，不超过 300-500 字

## 重要提醒：
- 如果用户询问当前汇率、波动率等实时数据，请立即调用 get_spot_rates 或 get_vol_data 工具
- 如果需要保存重要观点，使用 save_insight
- 定期进行自我反思，使用 save_reflection"""


# ═══════════════════════════════════════════════
# Chat history (in-memory, per-session)
# ═══════════════════════════════════════════════

_conversations = {}


def _call_llm(messages, max_tokens=2048, tools=None):
    """Call LLM proxy with optional tool calling"""
    if not LLM_API_KEY or not LLM_BASE_URL:
        return "LLM 未配置。请检查 fx-report/config.yaml 的 llm 段。"
    try:
        url = f"{LLM_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        
        # 添加 tools 如果有
        if tools:
            payload["tools"] = tools
        
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"LLM 调用失败: {str(e)}"}


def _call_llm_stream(messages, tools=None):
    """Stream LLM response as SSE, with tool calling support"""
    if not LLM_API_KEY or not LLM_BASE_URL:
        yield f"data: {json.dumps({'content': 'LLM 未配置。请检查 fx-report/config.yaml 的 llm 段。', 'done': True})}\n\n"
        return
    
    try:
        url = f"{LLM_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7,
            "stream": True,
        }
        
        if tools:
            payload["tools"] = tools
        
        resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
        resp.raise_for_status()
        
        # 用于累积完整响应
        full_response = ""
        tool_calls = []
        
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8", errors="replace")
            # 兼容 "data: {...}" 和 "data:{...}" 两种SSE格式
            if line.startswith("data:"):
                data_str = line[5:].lstrip()
                if data_str == "[DONE]":
                    # 处理剩余的 tool calls
                    if tool_calls:
                        for tc in tool_calls:
                            yield f"data: {json.dumps({'tool_call': tc, 'done': False})}\n\n"
                        # 执行 tool calls
                        for tc in tool_calls:
                            tool_name = tc.get("function", {}).get("name")
                            tool_args = tc.get("function", {}).get("arguments", "{}")
                            try:
                                args = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                            except:
                                args = {}
                            
                            # 执行工具
                            result = tool_registry.execute(tool_name, args)
                            result_str = json.dumps(result) if isinstance(result, dict) else str(result)
                            
                            # 将工具结果添加到消息
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc.get("id"),
                                "content": result_str
                            })
                        
                        # 继续获取 LLM 的最终响应
                        final_resp = _call_llm(messages, max_tokens=2048)
                        if isinstance(final_resp, dict):
                            final_msg = final_resp.get("choices", [{}])[0].get("message", {})
                            final_content = final_msg.get("content", "")
                            if final_content:
                                full_response += final_content
                                yield f"data: {json.dumps({'content': final_content, 'done': False})}\n\n"
                    
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    return
                
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    
                    # 检查是否有 content
                    content = delta.get("content") or ""
                    if content:
                        full_response += content
                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                    
                    # 检查是否有 tool calls
                    tc = delta.get("tool_calls")
                    if tc:
                        tool_calls.extend(tc)
                        
                except:
                    pass
        
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'content': f'LLM 调用失败: {str(e)}', 'done': True})}\n\n"


# ═══════════════════════════════════════════════
# HTML Template (从外部文件加载，避免Python转义问题)
# ═══════════════════════════════════════════════

_TEMPLATE_PATH = BASE_DIR / "templates" / "chat.html"
with open(_TEMPLATE_PATH, "r", encoding="utf-8") as _f:
    CHAT_HTML = _f.read()


# ═══════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════

@app.route("/")
def index():
    return render_template_string(CHAT_HTML)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    params = request.json or {}
    user_msg = params.get("message", "").strip()
    session_id = params.get("session_id", "default")

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    # 构建对话历史
    if session_id not in _conversations:
        _conversations[session_id] = []
    
    history = _conversations[session_id]
    history.append({"role": "user", "content": user_msg})

    # 构建消息列表
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 添加记忆上下文
    context = memory_system.build_context(session_id)
    if context:
        messages.append({"role": "system", "content": f"<context>\n{context}\n</context>"})
    
    # 添加最近对话历史（保留最后 15 条）
    recent = history[-15:]
    messages.extend(recent)

    # 获取工具 schema
    tools = tool_registry.get_schemas()

    # 流式响应
    def generate():
        full_response = ""
        
        # 使用带工具支持的流式调用
        for chunk in _call_llm_stream(messages, tools=tools):
            # 提取 content 用于累积完整响应
            try:
                if "content" in chunk:
                    import re
                    match = re.search(r'"content":\s*"([^"]*)"', chunk)
                    if match:
                        full_response += match.group(1)
                elif '"done": true' in chunk:
                    # 流结束，添加助手响应到历史
                    if full_response:
                        history.append({"role": "assistant", "content": full_response})
                    # 保存会话到磁盘
                    memory_system.save_session(session_id, history)
                    
                    # 触发反思引擎
                    if reflection_engine.should_reflect(user_msg, full_response):
                        reflection_engine.reflect(user_msg, full_response)
            except:
                pass
            yield chunk

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/memory/save", methods=["POST"])
def api_memory_save():
    """保存重要洞察到知识库"""
    params = request.json or {}
    category = params.get("category", "insight")
    key = params.get("key", "")
    insight = params.get("insight", "")
    tags = params.get("tags", [])
    
    result = memory_system.save_knowledge(category, key, {
        "content": insight,
        "tags": tags
    })
    
    return jsonify({"status": "saved", "path": result})


@app.route("/api/memory/reflect", methods=["POST"])
def api_memory_reflect():
    """保存反思"""
    params = request.json or {}
    topic = params.get("topic", "")
    reflection = params.get("reflection", "")
    context = params.get("context", {})
    
    result = memory_system.save_reflection(topic, reflection, context)
    
    return jsonify({"status": "saved", "reflection_id": result})


@app.route("/api/tools/list", methods=["GET"])
def api_tools_list():
    """列出可用工具"""
    return jsonify({
        "tools": tool_registry.get_tool_names(),
        "schemas": tool_registry.get_schemas()
    })


@app.route("/api/status", methods=["GET"])
def api_status():
    """Agent 状态"""
    return jsonify({
        "version": "3.0",
        "memory": {
            "sessions": len(list((BASE_DIR / "memory" / "sessions").glob("*.json"))) if (BASE_DIR / "memory" / "sessions").exists() else 0,
            "knowledge_categories": memory_system.list_knowledge_categories(),
            "reflections": len(list((BASE_DIR / "memory" / "reflections").glob("*.json"))) if (BASE_DIR / "memory" / "reflections").exists() else 0,
            "predictions": len(list((BASE_DIR / "memory" / "predictions").glob("*.json"))) if (BASE_DIR / "memory" / "predictions").exists() else 0
        },
        "skills": skill_loader.list_skills(),
        "tools": tool_registry.get_tool_names(),
        "reflection_quality": reflection_engine.get_quality_trend()
    })


@app.route("/api/reflection/quality", methods=["GET"])
def api_reflection_quality():
    """获取反思质量趋势"""
    return jsonify(reflection_engine.get_quality_trend())


@app.route("/api/reflection/recent", methods=["GET"])
def api_reflection_recent():
    """获取最近反思"""
    limit = request.args.get("limit", 10, type=int)
    return jsonify({
        "reflections": reflection_engine.get_recent_reflections(limit)
    })


if __name__ == "__main__":
    port = 8901
    print("=" * 60)
    print("  George Soros FX Agent v3.0")
    print("  - Memory System: ON")
    print("  - Reflection Engine: ON")
    print("  - Skills: 7 (fx_market, reflexivity, trade_history, macro_trades, central_banks, macro_theory, crisis_cases)")
    print("  - FX Tools: 8 available")
    print("  - Wedata Tools: 6 available (US/YARN/Oceanus/TDBank/StarRocks/SuperSql)")
    print(f"  http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
