# -*- coding: utf-8 -*-
"""
Tools - 索罗斯 Agent 的工具注册表
================================
定义可调用的外部工具/函数，每个工具都有标准化的 schema

数据源优先级:
  1. Bloomberg Terminal (BLPAPI) — 专业级实时数据，含隐含波动率
  2. Frankfurter API (ECB) — 免费汇率降级方案
  3. ExchangeRate-API — 补充币种覆盖
  4. Perplexity AI (sonar) — 实时新闻搜索
"""

import json
import yaml
import requests
import logging
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 延迟加载的全局单例
_memory_system = None
_wedata_tools = None
_config_cache = None
_bbg_provider = None

def _get_config():
    """加载 fx-report/config.yaml 配置"""
    global _config_cache
    if _config_cache is None:
        cfg_path = Path(__file__).parent.parent.parent / "fx-report" / "config.yaml"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                _config_cache = yaml.safe_load(f)
        else:
            _config_cache = {}
    return _config_cache

def _get_bbg():
    """延迟加载 Bloomberg Provider — 单例，自动连接"""
    global _bbg_provider
    if _bbg_provider is None:
        try:
            import sys
            fx_report_path = str(Path(__file__).parent.parent.parent / "fx-report")
            if fx_report_path not in sys.path:
                sys.path.insert(0, fx_report_path)
            from bloomberg_provider import BloombergProvider
            
            cfg = _get_config()
            host = cfg.get("data", {}).get("bbg", {}).get("host", "localhost")
            port = cfg.get("data", {}).get("bbg", {}).get("port", 8194)
            
            bbg = BloombergProvider(host=host, port=port)
            if bbg.is_available() and bbg.connect():
                _bbg_provider = bbg
                logger.info("Bloomberg Terminal connected successfully")
            else:
                logger.info("Bloomberg not available, using fallback data sources")
        except Exception as e:
            logger.warning(f"Bloomberg init failed: {e}")
    return _bbg_provider

def _get_memory():
    """延迟加载 MemorySystem"""
    global _memory_system
    if _memory_system is None:
        from memory import get_memory
        base_dir = Path(__file__).parent
        _memory_system = get_memory(base_dir)
    return _memory_system

def _get_wedata():
    """延迟加载 Wedata 工具"""
    global _wedata_tools
    if _wedata_tools is None:
        from tools_wedata import get_wedata_tools
        _wedata_tools = get_wedata_tools()
    return _wedata_tools


# ═══════════════════════════════════════════════
# Tool Schema Definitions
# ═══════════════════════════════════════════════

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_spot_rates",
            "description": "获取实时外汇汇率。用于查询任意货币对的当前价格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pairs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "货币对列表，如 ['USD/CNH', 'EUR/USD', 'GBP/USD']"
                    }
                },
                "required": ["pairs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vol_data",
            "description": "获取货币对的波动率数据，包括隐含波动率和历史波动率。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pairs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "货币对列表，如 ['USD/CNH', 'EUR/USD']"
                    }
                },
                "required": ["pairs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "获取外汇市场新闻和央行动态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "关注的主题，如 ['Fed', 'ECB', 'China', 'USD']"
                    },
                    "max_items": {
                        "type": "integer",
                        "description": "返回的新闻数量，默认 10"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_economic_calendar",
            "description": "获取即将发布的重大经济数据和经济事件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "countries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "国家代码，如 ['US', 'CN', 'EU', 'JP']"
                    },
                    "days_ahead": {
                        "type": "integer",
                        "description": "查询未来多少天的事件，默认 7"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_reflexivity",
            "description": "使用反射性理论分析当前市场状态。输入市场数据和观察，返回分析结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "market_data": {
                        "type": "object",
                        "description": "市场数据，包括价格趋势、波动率、资金流向等"
                    },
                    "observations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "你的市场观察列表"
                    }
                },
                "required": ["observations"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_insight",
            "description": "保存重要市场洞察到知识库，供后续参考。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "洞察类别，如 'fx_view', 'central_bank', 'risk_signal'"
                    },
                    "key": {
                        "type": "string",
                        "description": "洞察的关键词或标题"
                    },
                    "insight": {
                        "type": "string",
                        "description": "洞察的具体内容"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "标签列表"
                    }
                },
                "required": ["category", "key", "insight"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_reflection",
            "description": "保存一次自我反思，用于记录交易决策的复盘。",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "反思的主题"
                    },
                    "reflection": {
                        "type": "string",
                        "description": "反思的具体内容"
                    },
                    "context": {
                        "type": "object",
                        "description": "相关上下文，如交易决策、市场判断等"
                    }
                },
                "required": ["topic", "reflection"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_prediction",
            "description": "保存市场预测，用于后续验证准确率。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "预测目标货币对，如 'USD/CNH'"
                    },
                    "direction": {
                        "type": "string",
                        "description": "预测方向: 'up'(上涨), 'down'(下跌), 'sideways'(震荡)"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "预测时间框架，如 '1周', '1个月'"
                    },
                    "rationale": {
                        "type": "string",
                        "description": "预测的主要理由"
                    }
                },
                "required": ["target", "direction", "timeframe", "rationale"]
            }
        }
    },
    # ═══ 深度研究与事实验证工具 ═══
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "通用网络搜索工具。搜索任何话题的最新信息 — 不限于金融，时事、政策、科技、历史什么都能搜。当你需要了解任何最新情况时，用这个。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，尽量具体和有针对性，如 'latest Fed interest rate decision March 2026' 或 '特朗普最新贸易政策'"
                    },
                    "topic_type": {
                        "type": "string",
                        "enum": ["finance", "economics", "politics", "technology", "general"],
                        "description": "话题类型，帮助优化搜索结果"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deep_research",
            "description": "深度研究工具。当你不确定某个事实、数据、历史事件或市场机制时，必须调用此工具搜索权威信息。绝不能凭印象编造。返回带有引用来源的研究结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "需要研究的问题，尽量具体，如 '2024年日本央行YCC政策调整的具体时间线和市场反应'"
                    },
                    "context": {
                        "type": "string",
                        "description": "为什么需要研究这个问题，提供对话上下文"
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["quick", "standard", "deep"],
                        "description": "研究深度：quick(快速确认事实)、standard(标准分析)、deep(深度研究)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_claim",
            "description": "事实验证工具。当用户提出一个断言、或你自己要做一个判断时，调用此工具验证其真实性。返回验证结果和可信度评分。",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "需要验证的断言，如 '美联储2024年降息了3次'"
                    },
                    "source_hint": {
                        "type": "string",
                        "description": "可能的信息来源提示，如 'Fed official statements, FOMC minutes'"
                    }
                },
                "required": ["claim"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "搜索索罗斯自己的知识库，检索过往的洞察、预测和反思。在做新分析前先看看自己之前说过什么。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如 'USD/CNH 预测' 或 '美联储政策'"
                    },
                    "category": {
                        "type": "string",
                        "description": "知识类别筛选，如 'fx_view', 'central_bank', 'insights'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "review_predictions",
            "description": "回顾自己过去的预测记录，检查哪些对了哪些错了。用于保持诚实和校准认知。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "特定货币对，如 'USD/CNH'，留空则查看所有"
                    },
                    "include_stats": {
                        "type": "boolean",
                        "description": "是否包含准确率统计"
                    }
                }
            }
        }
    },
    # Wedata 工具
    {
        "type": "function",
        "function": {
            "name": "query_us_task",
            "description": "查询腾讯大数据 US 平台离线任务状态。需提供任务ID。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "US任务ID"},
                    "instance_time": {"type": "string", "description": "实例时间，如 '2026-02-03'"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_yarn_app",
            "description": "查询 YARN Application 状态和失败原因。",
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "string", "description": "YARN Application ID，如 'application_1740xxx_1234'"}
                },
                "required": ["application_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_oceanus_task",
            "description": "查询 Oceanus 实时任务状态和异常信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Oceanus任务ID"},
                    "instance_id": {"type": "string", "description": "实例ID（可选）"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_tdbank",
            "description": "查询 TDBank 表信息，如分区数、字段信息等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "bid": {"type": "string", "description": "表名，如 'b_teg_tube_index'"},
                    "query_type": {"type": "string", "description": "查询类型：'info'(表信息) 或 'partitions'(分区数)"}
                },
                "required": ["bid"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_starrocks",
            "description": "查询 StarRocks 集群负载状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cluster": {"type": "string", "description": "集群名称，如 'starrocks-gz0-teg-common-txt-v33'"},
                    "query_type": {"type": "string", "description": "查询类型：'status' 或 'load'"}
                },
                "required": ["cluster"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_supersql",
            "description": "查询 SuperSql Session 状态或执行结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "SuperSql Session ID"},
                    "query_type": {"type": "string", "description": "查询类型：'status'(状态) 或 'results'(结果)"}
                },
                "required": ["session_id"]
            }
        }
    }
]


# ═══════════════════════════════════════════════
# Tool Implementations
# ═══════════════════════════════════════════════

class ToolRegistry:
    """工具注册表 - 管理所有可用工具"""
    
    def __init__(self, fx_report_url: str = "http://localhost:8080"):
        self.fx_report_url = fx_report_url
        self.tools: Dict[str, Callable] = {
            "get_spot_rates": self._get_spot_rates,
            "get_vol_data": self._get_vol_data,
            "get_news": self._get_news,
            "get_economic_calendar": self._get_economic_calendar,
            "analyze_reflexivity": self._analyze_reflexivity,
            "save_insight": self._save_insight,
            "save_reflection": self._save_reflection,
            "save_prediction": self._save_prediction,
            # 深度研究与事实验证
            "search_web": self._search_web,
            "deep_research": self._deep_research,
            "verify_claim": self._verify_claim,
            "search_knowledge_base": self._search_knowledge_base,
            "review_predictions": self._review_predictions,
            # Wedata 工具
            "query_us_task": self._query_us_task,
            "query_yarn_app": self._query_yarn_app,
            "query_oceanus_task": self._query_oceanus_task,
            "query_tdbank": self._query_tdbank,
            "query_starrocks": self._query_starrocks,
            "query_supersql": self._query_supersql,
        }
    
    def get_schemas(self) -> List[Dict]:
        """获取所有工具的 schema"""
        return TOOL_SCHEMAS
    
    def get_tool_names(self) -> List[str]:
        """获取工具名称列表"""
        return list(self.tools.keys())
    
    def execute(self, tool_name: str, arguments: Dict) -> Any:
        """执行工具调用"""
        tool = self.tools.get(tool_name)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            result = tool(**arguments)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    # ═══════════════════════════════════════════════
    # 真实 API 工具实现
    # ═══════════════════════════════════════════════
    
    def _get_spot_rates(self, pairs: List[str]) -> Dict:
        """获取实时汇率 — 优先 Bloomberg Terminal，降级到 Frankfurter/ExchangeRate-API"""
        
        # ── 尝试 Bloomberg（专业级数据，含日/周/月变化） ──
        bbg = _get_bbg()
        if bbg and bbg.connected:
            try:
                # 标准化货币对名称: "USD/CNH" → "USDCNH"
                bbg_pairs = [p.replace("/", "").replace(" ", "").upper() for p in pairs]
                spots = bbg.get_fx_spot_rates(bbg_pairs)
                if spots:
                    return {
                        "rates": spots,
                        "count": len(spots),
                        "source": "Bloomberg Terminal",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                logger.warning(f"Bloomberg spot rates failed: {e}")
        
        # ── 降级: Frankfurter (ECB) + ExchangeRate-API ──
        results = {}
        errors = []
        
        # 解析货币对
        parsed_pairs = []
        for pair in pairs:
            pair = pair.replace("/", "").replace(" ", "").upper()
            # 标准化: USDCNH -> USDCNY (Frankfurter用ISO代码)
            pair = pair.replace("CNH", "CNY")
            if len(pair) >= 6:
                base = pair[:3]
                quote = pair[3:6]
                parsed_pairs.append((base, quote, pair))
        
        # 按 base 分组减少API调用
        base_groups = {}
        for base, quote, orig in parsed_pairs:
            base_groups.setdefault(base, []).append((quote, orig))
        
        # 方法1: Frankfurter API (ECB数据, 最可靠)
        for base, quotes in base_groups.items():
            symbols = ",".join(q for q, _ in quotes)
            try:
                url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={symbols}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    rates = data.get("rates", {})
                    for quote, orig in quotes:
                        if quote in rates:
                            # 恢复CNH显示
                            display_pair = orig.replace("CNY", "CNH")
                            results[display_pair] = {
                                "rate": rates[quote],
                                "base": base,
                                "quote": quote.replace("CNY", "CNH"),
                                "date": data.get("date"),
                                "source": "ECB/Frankfurter"
                            }
            except Exception as e:
                errors.append(f"Frankfurter({base}): {str(e)}")
        
        # 方法2: ExchangeRate-API 补充（覆盖更多币种如VND/IDR/THB）
        missing = [(b, q, o) for b, q, o in parsed_pairs 
                   if o.replace("CNY", "CNH") not in results]
        
        if missing:
            missing_bases = {}
            for base, quote, orig in missing:
                missing_bases.setdefault(base, []).append((quote, orig))
            
            for base, quotes in missing_bases.items():
                try:
                    url = f"https://api.exchangerate-api.com/v4/latest/{base}"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        rates = data.get("rates", {})
                        for quote, orig in quotes:
                            if quote in rates:
                                display_pair = orig.replace("CNY", "CNH")
                                results[display_pair] = {
                                    "rate": rates[quote],
                                    "base": base,
                                    "quote": quote.replace("CNY", "CNH"),
                                    "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
                                    "source": "ExchangeRate-API"
                                }
                except Exception as e:
                    errors.append(f"ExchangeRate({base}): {str(e)}")
        
        return {
            "rates": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat(),
            "errors": errors if errors else None
        }
    
    def _get_vol_data(self, pairs: List[str]) -> Dict:
        """获取波动率数据 — 优先 Bloomberg 隐含波动率，降级到 ECB 历史计算"""
        
        # ── 尝试 Bloomberg（专业级隐含波动率，含期限结构） ──
        bbg = _get_bbg()
        if bbg and bbg.connected:
            try:
                bbg_pairs = [p.replace("/", "").replace(" ", "").upper() for p in pairs]
                vols = bbg.get_fx_vol_data(bbg_pairs)
                
                # 同时获取 spot 数据补充价格信息
                spots = bbg.get_fx_spot_rates(bbg_pairs)
                
                if vols:
                    # 合并 spot + vol 数据
                    combined = {}
                    for pair in bbg_pairs:
                        combined[pair] = {}
                        if pair in vols:
                            combined[pair].update(vols[pair])
                            combined[pair]["type"] = "implied"
                        if pair in spots:
                            combined[pair]["current"] = spots[pair].get("rate")
                            combined[pair]["chg_1d"] = spots[pair].get("chg_1d")
                            combined[pair]["chg_1m"] = spots[pair].get("chg_1m")
                        combined[pair]["source"] = "Bloomberg Terminal (implied vol)"
                    
                    return {
                        "volatility": combined,
                        "note": "Bloomberg 隐含波动率(Implied Vol)，含1W/1M/3M/6M/1Y期限结构",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                logger.warning(f"Bloomberg vol data failed: {e}")
        
        # ── 降级: 基于 ECB 历史数据计算已实现波动率 ──
        results = {}
        
        for pair in pairs:
            pair_clean = pair.replace("/", "").replace(" ", "").upper().replace("CNH", "CNY")
            if len(pair_clean) < 6:
                continue
            base = pair_clean[:3]
            quote = pair_clean[3:6]
            display_pair = pair.replace("CNY", "CNH")
            
            try:
                # 获取90天历史数据计算波动率
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                url = (f"https://api.frankfurter.dev/v1/"
                       f"{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
                       f"?base={base}&symbols={quote}")
                resp = requests.get(url, timeout=15)
                
                if resp.status_code == 200:
                    data = resp.json()
                    rates_dict = data.get("rates", {})
                    
                    # 提取每日收盘价
                    prices = []
                    dates = sorted(rates_dict.keys())
                    for d in dates:
                        if quote in rates_dict[d]:
                            prices.append(rates_dict[d][quote])
                    
                    if len(prices) >= 20:
                        # 计算日收益率
                        returns = [(prices[i] / prices[i-1]) - 1 for i in range(1, len(prices))]
                        
                        import statistics
                        # 30日年化波动率
                        vol_30d = statistics.stdev(returns[-30:]) * (252 ** 0.5) * 100 if len(returns) >= 30 else None
                        # 90日年化波动率
                        vol_90d = statistics.stdev(returns) * (252 ** 0.5) * 100
                        # 最近价格
                        current = prices[-1]
                        high_90d = max(prices)
                        low_90d = min(prices)
                        chg_pct = ((prices[-1] / prices[0]) - 1) * 100
                        
                        results[display_pair] = {
                            "vol_30d": round(vol_30d, 2) if vol_30d else None,
                            "vol_90d": round(vol_90d, 2),
                            "current": round(current, 4),
                            "high_90d": round(high_90d, 4),
                            "low_90d": round(low_90d, 4),
                            "range_pct": round(((high_90d - low_90d) / low_90d) * 100, 2),
                            "chg_90d_pct": round(chg_pct, 2),
                            "data_points": len(prices),
                            "source": "ECB/Frankfurter (realized vol)"
                        }
                    else:
                        results[display_pair] = {"error": "数据点不足", "data_points": len(prices)}
                        
            except Exception as e:
                results[display_pair] = {"error": str(e)}
        
        return {
            "volatility": results,
            "note": "已实现波动率(Realized Vol)，基于ECB日度数据计算，年化",
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_news(self, topics: List[str] = None, max_items: int = 10) -> Dict:
        """获取外汇新闻 — Bloomberg 新闻 + Perplexity AI 实时搜索"""
        all_news = []
        
        # ── 尝试 Bloomberg 新闻 ──
        bbg = _get_bbg()
        if bbg and bbg.connected:
            try:
                bbg_news = bbg.get_fx_news(topics=topics, max_items=max_items)
                if bbg_news:
                    all_news.extend(bbg_news)
            except Exception as e:
                logger.warning(f"Bloomberg news failed: {e}")
        
        # ── Perplexity AI 补充实时新闻 ──
        cfg = _get_config()
        pplx_key = cfg.get("ai", {}).get("perplexity", {}).get("api_key", "")
        
        if not pplx_key:
            return {"error": "Perplexity API key 未配置", "news": []}
        
        # 构建搜索查询
        if topics:
            topic_str = ", ".join(topics)
            query = f"Latest foreign exchange market news about {topic_str}. Focus on central bank policy, currency movements, and market-moving events. Provide 5-8 key headlines with brief summaries in Chinese."
        else:
            query = "Latest global FX market news today. Key currency movements, central bank decisions, and macro events. Provide 5-8 key headlines with brief summaries in Chinese."
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {pplx_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": cfg.get("ai", {}).get("perplexity", {}).get("model", "sonar"),
                "messages": [
                    {"role": "system", "content": "你是一个外汇市场新闻分析师。请用JSON格式返回新闻列表，每条包含 title, summary, impact (positive/negative/neutral), currencies_affected 字段。"},
                    {"role": "user", "content": query}
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            # 尝试解析JSON，如果失败就返回原文
            try:
                # 提取JSON部分
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    news_list = json.loads(json_match.group())
                else:
                    news_list = [{"title": "市场快讯", "summary": content}]
            except:
                news_list = [{"title": "市场快讯", "summary": content}]
            
            all_news.extend(news_list)
            
            return {
                "news": all_news[:max_items],
                "count": len(all_news[:max_items]),
                "sources": citations[:5] if citations else [],
                "query_topics": topics,
                "source": "Bloomberg + Perplexity AI" if any(n.get("bbg") for n in all_news) else "Perplexity AI (sonar)",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            # 如果 Perplexity 失败但有 Bloomberg 新闻，仍然返回
            if all_news:
                return {
                    "news": all_news[:max_items],
                    "count": len(all_news[:max_items]),
                    "source": "Bloomberg Terminal",
                    "timestamp": datetime.now().isoformat()
                }
            return {"error": f"新闻获取失败: {str(e)}", "news": []}
    
    def _get_economic_calendar(self, countries: List[str] = None, days_ahead: int = 7) -> Dict:
        """获取经济日历 — 通过 Perplexity 搜索 + 本地宏观事件数据"""
        events = []
        
        # 方法1: 尝试加载本地宏观事件数据
        macro_path = Path(__file__).parent.parent.parent / "fx-report" / "data" / "macro_events.json"
        if macro_path.exists():
            try:
                with open(macro_path, "r", encoding="utf-8") as f:
                    local_events = json.load(f)
                if isinstance(local_events, list):
                    events.extend(local_events[:20])
            except:
                pass
        
        # 方法2: Perplexity 搜索最新经济日历
        cfg = _get_config()
        pplx_key = cfg.get("ai", {}).get("perplexity", {}).get("api_key", "")
        
        if pplx_key:
            country_str = ", ".join(countries) if countries else "US, China, EU, Japan"
            query = (f"What are the most important economic data releases and central bank events "
                     f"for {country_str} in the next {days_ahead} days? "
                     f"Include exact dates, event names, previous values, and market expectations. "
                     f"Format as a list in Chinese.")
            
            try:
                url = "https://api.perplexity.ai/chat/completions"
                headers = {"Authorization": f"Bearer {pplx_key}", "Content-Type": "application/json"}
                payload = {
                    "model": cfg.get("ai", {}).get("perplexity", {}).get("model", "sonar"),
                    "messages": [
                        {"role": "system", "content": "你是经济数据日历助手。请列出即将发布的重要经济数据和央行事件，包含日期、事件名、前值和预期值。"},
                        {"role": "user", "content": query}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.1
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                citations = data.get("citations", [])
                
                return {
                    "calendar": content,
                    "local_events": events if events else None,
                    "countries": countries or ["US", "CN", "EU", "JP"],
                    "days_ahead": days_ahead,
                    "sources": citations[:3] if citations else [],
                    "source": "Perplexity AI",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                pass
        
        # Fallback: 返回本地数据
        return {
            "calendar": "经济日历数据暂时通过AI搜索获取",
            "local_events": events if events else None,
            "countries": countries or ["US", "CN", "EU", "JP"],
            "days_ahead": days_ahead,
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_reflexivity(self, market_data: Dict = None, observations: List[str] = None) -> Dict:
        """反射性分析 — 使用 LLM 进行深度分析"""
        if not observations:
            observations = []
        
        cfg = _get_config()
        llm_key = cfg.get("llm", {}).get("api_key", "")
        llm_url = cfg.get("llm", {}).get("base_url", "")
        llm_model = cfg.get("llm", {}).get("model", "claude-opus-4-20250514")
        
        obs_text = "\n".join(f"- {o}" for o in observations)
        market_str = json.dumps(market_data, ensure_ascii=False, indent=2) if market_data else "无额外数据"
        
        # 如果有LLM，使用AI分析
        if llm_key and llm_url:
            try:
                prompt = f"""作为索罗斯，运用反射性理论(Reflexivity Theory)分析以下市场观察：

## 市场观察
{obs_text}

## 市场数据
{market_str}

请从以下维度分析（每个维度2-3句话）：
1. **当前反射性阶段**: 正反馈（自我强化）还是负反馈（自我修正）？处于泡沫哪个阶段？
2. **认知偏差识别**: 市场参与者存在什么认知偏差？主流叙事是什么？
3. **央行博弈**: 各央行的"痛点"和政策意图是什么？
4. **非对称机会**: 有没有风险有限但回报巨大的交易机会？
5. **风险信号**: 什么事件可能打破当前平衡？

最后给出一个明确的结论和操作建议。"""

                url = f"{llm_url}/chat/completions"
                headers = {"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"}
                resp = requests.post(url, headers=headers, json={
                    "model": llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.5
                }, timeout=60)
                resp.raise_for_status()
                
                data = resp.json()
                analysis = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return {
                    "analysis": analysis,
                    "framework": "reflexivity (AI-powered)",
                    "observations_count": len(observations),
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                pass  # 降级到规则引擎
        
        # Fallback: 规则引擎
        obs_joined = " ".join(observations)
        if any(w in obs_joined for w in ["上涨", "牛市", "泡沫", "飙升", "涌入"]):
            phase = "正反馈阶段（自我强化）"
            signal = "可能处于泡沫形成期，关注拥挤度"
        elif any(w in obs_joined for w in ["下跌", "熊市", "恐慌", "抛售", "暴跌"]):
            phase = "负反馈阶段（自我修正）"
            signal = "可能接近底部，关注流动性"
        else:
            phase = "均衡状态"
            signal = "暂无明显趋势信号"
        
        return {
            "analysis": f"**当前阶段**: {phase}\n**信号解读**: {signal}",
            "phase": phase,
            "signal": signal,
            "framework": "reflexivity (rule-based fallback)"
        }
    
    def _save_insight(self, category: str, key: str, insight: str, tags: List[str] = None) -> Dict:
        """保存洞察到知识库"""
        try:
            memory = _get_memory()
            result_path = memory.save_knowledge(category, key, {
                "content": insight,
                "tags": tags or []
            })
            return {
                "status": "saved",
                "category": category,
                "key": key,
                "saved_at": result_path
            }
        except Exception as e:
            return {"error": f"Failed to save insight: {str(e)}"}
    
    def _save_reflection(self, topic: str, reflection: str, context: Dict = None) -> Dict:
        """保存反思"""
        try:
            memory = _get_memory()
            reflection_id = memory.save_reflection(topic, reflection, context or {})
            return {
                "status": "saved",
                "topic": topic,
                "reflection_id": reflection_id,
                "saved_at": "memory/reflections"
            }
        except Exception as e:
            return {"error": f"Failed to save reflection: {str(e)}"}
    
    def _save_prediction(
        self,
        target: str,
        direction: str,
        timeframe: str,
        rationale: str
    ) -> Dict:
        """保存市场预测"""
        try:
            memory = _get_memory()
            prediction_id = memory.save_prediction(
                target=target,
                direction=direction,
                timeframe=timeframe,
                rationale=rationale
            )
            return {
                "status": "saved",
                "prediction_id": prediction_id,
                "target": target,
                "direction": direction,
                "timeframe": timeframe,
                "saved_at": "memory/predictions"
            }
        except Exception as e:
            return {"error": f"Failed to save prediction: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # 深度研究与事实验证工具实现
    # ═══════════════════════════════════════════════
    
    def _search_web(self, query: str, topic_type: str = "general") -> Dict:
        """
        通用网络搜索 — 搜索任何话题的最新信息
        使用 Perplexity sonar 做快速网络搜索
        """
        cfg = _get_config()
        pplx_key = cfg.get("ai", {}).get("perplexity", {}).get("api_key", "")
        
        if not pplx_key:
            return self._research_via_llm(query, f"Web search for: {topic_type}")
        
        # 根据话题类型优化 system prompt
        topic_prompts = {
            "finance": "你是金融市场分析师，专注于外汇、利率、大宗商品等市场动态。",
            "economics": "你是宏观经济研究员，关注各国经济数据、政策变化和经济趋势。",
            "politics": "你是国际政治分析师，关注地缘政治、贸易政策和政治事件对市场的影响。",
            "technology": "你是科技行业分析师，关注技术发展趋势和其对经济的影响。",
            "general": "你是一个全能的信息搜索助手，提供准确、最新的信息。"
        }
        
        system_msg = (
            f"{topic_prompts.get(topic_type, topic_prompts['general'])} "
            "请提供准确的、有时效性的信息。"
            "包含具体的日期、数字和来源。"
            "如果信息不确定或有争议，明确说明。"
            "用中文回答，关键术语保留英文。"
        )
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {pplx_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": query}
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            return {
                "search_result": content,
                "citations": citations[:8] if citations else [],
                "query": query,
                "topic_type": topic_type,
                "source": "Perplexity AI (sonar) — 实时网络搜索",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return self._research_via_llm(query, f"Web search fallback for: {topic_type}")
    
    def _deep_research(self, query: str, context: str = "", depth: str = "standard") -> Dict:
        """
        深度研究工具 — 当不确定某个事实时，主动搜索权威信息
        使用 Perplexity sonar-pro 进行深度搜索，返回带引用的结果
        """
        cfg = _get_config()
        pplx_key = cfg.get("ai", {}).get("perplexity", {}).get("api_key", "")
        
        if not pplx_key:
            # 降级：用主 LLM 做研究（明确标注这是基于训练数据，非实时）
            return self._research_via_llm(query, context)
        
        # 根据深度选择模型和 token 限制
        depth_config = {
            "quick": {"model": "sonar", "max_tokens": 1000, "temperature": 0.1},
            "standard": {"model": "sonar-pro", "max_tokens": 2500, "temperature": 0.1},
            "deep": {"model": "sonar-pro", "max_tokens": 4000, "temperature": 0.2},
        }
        config = depth_config.get(depth, depth_config["standard"])
        
        # 构建研究 prompt
        system_msg = (
            "You are a professional financial research analyst. "
            "Provide factual, well-sourced information. "
            "Always cite specific dates, numbers, and sources. "
            "If information is uncertain or conflicting, clearly state that. "
            "Respond in Chinese, but keep technical terms in English. "
            "Structure your response with clear sections and bullet points."
        )
        
        user_msg = query
        if context:
            user_msg = f"Research context: {context}\n\nResearch question: {query}"
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {pplx_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "max_tokens": config["max_tokens"],
                "temperature": config["temperature"]
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            return {
                "research_result": content,
                "citations": citations[:10] if citations else [],
                "query": query,
                "depth": depth,
                "source": f"Perplexity AI ({config['model']})",
                "confidence": "high" if citations else "medium",
                "note": "基于实时网络搜索的研究结果，附有引用来源",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            # 降级到 LLM
            logger.warning(f"Perplexity research failed: {e}, falling back to LLM")
            return self._research_via_llm(query, context)
    
    def _research_via_llm(self, query: str, context: str = "") -> Dict:
        """LLM 降级研究 — 明确标注这不是实时数据"""
        cfg = _get_config()
        llm_key = cfg.get("llm", {}).get("api_key", "")
        llm_url = cfg.get("llm", {}).get("base_url", "")
        llm_model = cfg.get("llm", {}).get("model", "claude-opus-4-20250514")
        
        if not llm_key or not llm_url:
            return {"error": "研究工具不可用：Perplexity 和 LLM 都未配置"}
        
        prompt = f"""请基于你的知识回答以下研究问题。

重要要求：
1. 只回答你确定知道的事实
2. 对于不确定的信息，明确标注"[需验证]"
3. 标注你的知识截止日期
4. 给出具体的数据点、日期和来源（如果知道的话）
5. 用中文回答，关键术语保留英文

{'研究上下文: ' + context if context else ''}

研究问题: {query}"""
        
        try:
            url = f"{llm_url}/chat/completions"
            headers = {"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json={
                "model": llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.2
            }, timeout=60)
            resp.raise_for_status()
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return {
                "research_result": content,
                "citations": [],
                "query": query,
                "depth": "llm_fallback",
                "source": f"LLM ({llm_model}) — 基于训练数据，非实时",
                "confidence": "medium",
                "note": "⚠️ 此结果基于 LLM 训练数据，非实时搜索。重要决策请交叉验证。",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"研究失败: {str(e)}"}
    
    def _verify_claim(self, claim: str, source_hint: str = "") -> Dict:
        """
        事实验证工具 — 验证一个断言的真实性
        """
        cfg = _get_config()
        pplx_key = cfg.get("ai", {}).get("perplexity", {}).get("api_key", "")
        
        if not pplx_key:
            return {
                "claim": claim,
                "verdict": "unable_to_verify",
                "reason": "验证工具不可用（Perplexity 未配置）",
                "suggestion": "请自行查证此断言的真实性"
            }
        
        system_msg = (
            "You are a fact-checker. Your job is to verify claims about financial markets, "
            "economics, central bank policies, and related topics. "
            "For each claim, provide: "
            "1. VERDICT: true / mostly_true / partially_true / misleading / false / unverifiable "
            "2. EVIDENCE: specific facts and data that support or contradict the claim "
            "3. NUANCE: important context that might be missing "
            "4. SOURCES: where the information comes from "
            "Respond in Chinese, keep technical terms in English."
        )
        
        user_msg = f"请验证以下断言的真实性：\n\n「{claim}」"
        if source_hint:
            user_msg += f"\n\n可能的信息来源提示：{source_hint}"
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {pplx_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            return {
                "claim": claim,
                "verification": content,
                "citations": citations[:5] if citations else [],
                "source": "Perplexity AI (sonar-pro)",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "claim": claim,
                "verdict": "verification_failed",
                "error": str(e)
            }
    
    def _search_knowledge_base(self, query: str, category: str = None) -> Dict:
        """搜索索罗斯自己的知识库 — 过往洞察、反思、预测"""
        try:
            memory = _get_memory()
            
            # 搜索知识库
            results = memory.search_knowledge(query, category=category, limit=5)
            
            # 搜索最近反思
            reflections = memory.load_recent_reflections(limit=5)
            relevant_reflections = []
            query_lower = query.lower()
            for r in reflections:
                if query_lower in json.dumps(r, ensure_ascii=False).lower():
                    relevant_reflections.append({
                        "topic": r.get("topic"),
                        "reflection": r.get("reflection", "")[:300],
                        "date": r.get("created_at")
                    })
            
            return {
                "knowledge_results": results,
                "relevant_reflections": relevant_reflections[:3],
                "query": query,
                "category": category,
                "total_found": len(results) + len(relevant_reflections),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"知识库搜索失败: {str(e)}"}
    
    def _review_predictions(self, target: str = None, include_stats: bool = True) -> Dict:
        """回顾过去的预测记录 — 保持诚实，校准认知"""
        try:
            memory = _get_memory()
            
            # 获取预测记录
            predictions = memory.load_predictions(target=target, limit=20)
            
            # 获取统计
            stats = memory.get_prediction_stats() if include_stats else None
            
            # 格式化输出
            formatted = []
            for p in predictions:
                entry = {
                    "target": p.get("target"),
                    "direction": p.get("direction"),
                    "timeframe": p.get("timeframe"),
                    "rationale": p.get("rationale", "")[:200],
                    "date": p.get("created_at"),
                    "verified": p.get("verified", False),
                }
                if p.get("verified"):
                    entry["correct"] = p.get("correct")
                    entry["outcome"] = p.get("outcome")
                formatted.append(entry)
            
            return {
                "predictions": formatted,
                "total": len(formatted),
                "stats": stats,
                "target_filter": target,
                "message": f"共找到 {len(formatted)} 条预测记录" + 
                          (f"（准确率: {stats['accuracy']}%）" if stats and stats.get('total') > 0 else ""),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"预测记录查询失败: {str(e)}"}
    
    # ═══════════════════════════════════════════════
    # Wedata 工具实现
    # ═══════════════════════════════════════════════
    
    def _query_us_task(self, task_id: str, instance_time: str = None) -> Dict:
        """查询 US 离线任务"""
        try:
            wedata = _get_wedata()
            return wedata.query_us_task(task_id, instance_time)
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}
    
    def _query_yarn_app(self, application_id: str) -> Dict:
        """查询 YARN Application"""
        try:
            wedata = _get_wedata()
            return wedata.query_yarn_app(application_id)
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}
    
    def _query_oceanus_task(self, task_id: str, instance_id: str = None) -> Dict:
        """查询 Oceanus 实时任务"""
        try:
            wedata = _get_wedata()
            return wedata.query_oceanus_task(task_id, instance_id)
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}
    
    def _query_tdbank(self, bid: str, query_type: str = "partitions") -> Dict:
        """查询 TDBank 表信息"""
        try:
            wedata = _get_wedata()
            if query_type == "info":
                return wedata.query_tdbank_table_info(bid)
            else:
                return wedata.query_tdbank_partitions(bid)
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}
    
    def _query_starrocks(self, cluster: str, query_type: str = "status") -> Dict:
        """查询 StarRocks 集群"""
        try:
            wedata = _get_wedata()
            if query_type == "load":
                return wedata.query_starrocks_load(cluster)
            else:
                return wedata.query_starrocks_cluster(cluster)
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}
    
    def _query_supersql(self, session_id: str, query_type: str = "status") -> Dict:
        """查询 SuperSql"""
        try:
            wedata = _get_wedata()
            if query_type == "results":
                return wedata.query_supersql_results(session_id)
            else:
                return wedata.query_supersql_session(session_id)
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}


# 全局实例
_tool_registry = None

def get_tool_registry(fx_report_url: str = "http://localhost:8080") -> ToolRegistry:
    """获取工具注册表实例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry(fx_report_url)
    return _tool_registry
