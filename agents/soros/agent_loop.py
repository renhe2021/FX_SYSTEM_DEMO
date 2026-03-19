# -*- coding: utf-8 -*-
"""
Agent Loop - 索罗斯 Agent 的核心推理循环
=========================================
完整流程：理解 → 检索记忆 → 规划 → 调用工具 → 生成响应 → 反思存储

借鉴 OPENCLAW 框架理念，实现结构化的 Agent 工作流
"""

import json
import re
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path


class AgentLoop:
    """
    索罗斯 Agent 的核心推理循环
    
    工作流程：
    1. 理解 (Understand): 解析用户意图，提取关键实体
    2. 检索 (Retrieve): 从记忆系统中检索相关信息
    3. 规划 (Plan): 确定需要调用的工具和顺序
    4. 执行 (Execute): 调用工具获取数据
    5. 生成 (Generate): 基于所有信息生成响应
    6. 反思 (Reflect): 评估分析质量，存储重要洞察
    """
    
    def __init__(
        self,
        memory_system,
        tool_registry,
        llm_config: Dict[str, str],
        system_prompt: str
    ):
        self.memory = memory_system
        self.tools = tool_registry
        self.llm_config = llm_config
        self.system_prompt = system_prompt
        
        # 可配置的回调函数
        self.on_tool_call: Optional[Callable] = None
        self.on_thinking: Optional[Callable] = None
        self.on_reflect: Optional[Callable] = None
    
    # ═══════════════════════════════════════════════
    # 核心工作流
    # ═══════════════════════════════════════════════
    
    def run(
        self,
        user_message: str,
        session_id: str,
        conversation_history: List[Dict],
        stream_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        执行完整的 Agent Loop
        
        Args:
            user_message: 用户当前消息
            session_id: 会话 ID
            conversation_history: 对话历史
            stream_callback: 流式输出回调
            
        Returns:
            Dict包含: response(最终响应), tool_calls(工具调用记录), reflection(反思结果)
        """
        results = {
            "response": "",
            "tool_calls": [],
            "reflection": None,
            "thinking": []
        }
        
        # Step 1: 理解用户意图
        understanding = self._understand(user_message)
        results["thinking"].append({"step": "understand", "result": understanding})
        
        # Step 2: 检索记忆
        context = self._retrieve_context(session_id, user_message, conversation_history)
        
        # Step 3: 构建消息列表
        messages = self._build_messages(
            user_message, 
            conversation_history, 
            context,
            understanding
        )
        
        # Step 4: 规划工具调用
        tools = self.tools.get_schemas()
        
        # Step 5: 执行 LLM 调用（可能多轮工具调用）
        tool_call_history = []
        
        # 第一轮：LLM 生成响应，可能带有工具调用
        llm_response = self._call_llm(messages, tools=tools)
        
        # 处理工具调用
        if "tool_calls" in llm_response and llm_response["tool_calls"]:
            tool_calls = llm_response["tool_calls"]
            results["tool_calls"] = tool_calls
            
            # 通知回调
            if self.on_tool_call:
                self.on_tool_call(tool_calls)
            
            # 执行工具调用
            for tc in tool_calls:
                tool_name = tc.get("function", {}).get("name")
                tool_args = tc.get("function", {}).get("arguments", "{}")
                
                try:
                    args = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                except:
                    args = {}
                
                # 执行工具
                tool_result = self.tools.execute(tool_name, args)
                tool_call_history.append({
                    "tool": tool_name,
                    "args": args,
                    "result": tool_result
                })
                
                # 将工具结果添加到消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                })
            
            # 第二轮：基于工具结果生成最终响应
            final_response = self._call_llm(messages, tools=None)
            results["response"] = final_response.get("content", "") if isinstance(final_response, dict) else str(final_response)
        else:
            # 无工具调用，直接获取响应
            results["response"] = llm_response.get("content", "") if isinstance(llm_response, dict) else str(llm_response)
        
        # Step 6: 反思与存储
        if self._should_reflect(user_message, results["response"]):
            reflection = self._reflect(user_message, results["response"], understanding, tool_call_history)
            results["reflection"] = reflection
            
            if self.on_reflect:
                self.on_reflect(reflection)
        
        return results
    
    def run_stream(
        self,
        user_message: str,
        session_id: str,
        conversation_history: List[Dict],
        tool_registry
    ):
        """
        流式版本的 Agent Loop
        
        Yields:
            SSE 格式的数据块
        """
        import requests
        
        # 构建上下文
        context = self._retrieve_context(session_id, user_message, conversation_history)
        messages = self._build_messages(user_message, conversation_history, context)
        tools = self.tools.get_schemas()
        
        full_response = ""
        tool_calls = []
        
        # 流式调用 LLM
        url = f"{self.llm_config['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.llm_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_config["model"],
            "messages": messages,
            "max_tokens": self.llm_config.get("max_tokens", 8192),
            "temperature": self.llm_config.get("temperature", 0.4),
            "stream": True,
        }
        
        if tools:
            payload["tools"] = tools
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
            resp.raise_for_status()
            
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8", errors="replace")
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        # 执行工具调用
                        if tool_calls:
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
                                
                                # 发送工具执行事件
                                yield f"data: {json.dumps({'event': 'tool_result', 'tool': tool_name, 'result': result})}\n\n"
                                
                                # 添加到消息历史
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc.get("id"),
                                    "content": result_str
                                })
                            
                            # 继续获取最终响应
                            final_resp = self._call_llm(messages, tools=None)
                            if isinstance(final_resp, dict):
                                final_content = final_resp.get("content", "")
                                if final_content:
                                    full_response = final_content
                                    yield f"data: {json.dumps({'content': final_content})}\n\n"
                        
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        return
                    
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        
                        # 处理 content
                        content = delta.get("content", "")
                        if content:
                            full_response += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                        
                        # 处理 tool_calls
                        tc = delta.get("tool_calls")
                        if tc:
                            tool_calls.extend(tc)
                            yield f"data: {json.dumps({'event': 'tool_call', 'tool_calls': tc})}\n\n"
                    
                    except:
                        pass
        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    # ═══════════════════════════════════════════════
    # 步骤实现
    # ═══════════════════════════════════════════════
    
    def _understand(self, user_message: str) -> Dict[str, Any]:
        """理解用户意图"""
        # 简单的意图识别
        intent = "general"
        entities = []
        
        # 货币对识别
        currency_pairs = re.findall(r'[A-Z]{3}/[A-Z]{3}|[A-Z]{6}', user_message.upper())
        if currency_pairs:
            entities.extend(currency_pairs)
            intent = "currency_query"
        
        # 央行关键词
        if any(w in user_message for w in ["央行", "美联储", "Fed", "ECB", "日本银行"]):
            intent = "central_bank"
        
        # 趋势/预测关键词
        if any(w in user_message for w in ["走势", "预测", "分析", "趋势", "会涨", "会跌"]):
            intent = "analysis"
        
        return {
            "intent": intent,
            "entities": entities,
            "original": user_message
        }
    
    def _retrieve_context(
        self, 
        session_id: str, 
        user_message: str,
        conversation_history: List[Dict]
    ) -> str:
        """检索记忆上下文"""
        return self.memory.build_context(session_id)
    
    def _build_messages(
        self,
        user_message: str,
        conversation_history: List[Dict],
        context: str,
        understanding: Dict = None
    ) -> List[Dict]:
        """构建 LLM 消息列表"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # 添加上下文
        if context:
            messages.append({
                "role": "system",
                "content": f"<context>\n{context}\n</context>"
            })
        
        # 添加对话历史
        messages.extend(conversation_history[-15:])
        
        # 添加用户当前消息
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _call_llm(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """调用 LLM"""
        import requests
        
        if not self.llm_config.get("api_key"):
            return {"content": "LLM 未配置"}
        
        url = f"{self.llm_config['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.llm_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_config.get("model", "claude-opus-4-20250514"),
            "messages": messages,
            "max_tokens": self.llm_config.get("max_tokens", 8192),
            "temperature": self.llm_config.get("temperature", 0.4),
        }
        
        if tools:
            payload["tools"] = tools
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json().get("choices", [{}])[0].get("message", {})
        except Exception as e:
            return {"content": f"LLM 调用失败: {str(e)}"}
    
    def _should_reflect(self, user_message: str, response: str) -> bool:
        """判断是否需要反思"""
        # 深度分析类消息需要反思
        if len(response) > 500:
            return True
        if any(w in user_message for w in ["分析", "预测", "看法", "判断"]):
            return True
        return False
    
    def _reflect(
        self,
        user_message: str,
        response: str,
        understanding: Dict,
        tool_calls: List[Dict]
    ) -> Dict:
        """反思与知识沉淀"""
        # 构建反思内容
        topic = f"分析: {user_message[:50]}..."
        reflection = f"""
## 这次分析的质量评估

### 用户意图
{understanding.get('intent', 'unknown')}

### 分析要点
{response[:500]}...

### 工具调用
{json.dumps(tool_calls, ensure_ascii=False, indent=2) if tool_calls else '无'}

### 自我反思
- 这次分析是否基于充分的数据？
- 预测是否有明确的逻辑支撑？
- 下次如何改进？
"""
        
        # 保存反思
        reflection_id = self.memory.save_reflection(
            topic=topic,
            reflection=reflection,
            context={
                "understanding": understanding,
                "tool_calls": tool_calls,
                "response_length": len(response)
            }
        )
        
        return {
            "id": reflection_id,
            "topic": topic,
            "reflection": reflection
        }
    
    # ═══════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════
    
    def set_thinking_callback(self, callback: Callable):
        """设置思考过程回调"""
        self.on_thinking = callback
    
    def set_tool_call_callback(self, callback: Callable):
        """设置工具调用回调"""
        self.on_tool_call = callback
    
    def set_reflect_callback(self, callback: Callable):
        """设置反思回调"""
        self.on_reflect = callback


def create_agent_loop(memory_system, tool_registry, llm_config, system_prompt) -> AgentLoop:
    """创建 Agent Loop 实例"""
    return AgentLoop(memory_system, tool_registry, llm_config, system_prompt)
