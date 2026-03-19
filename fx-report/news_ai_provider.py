# -*- coding: utf-8 -*-
"""
News AI Provider — Perplexity for news search + Claude for Executive Summary generation.

Flow:
1. Based on client profile → generate search prompts (optionally refined by Claude)
2. Call Perplexity sonar API to fetch real-time FX news
3. Feed news + market context to Claude → generate Executive Summary
"""
import json
import logging
import requests
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "cache"


# ──────────────────────────────────────────────
# Prompt templates per client profile
# ──────────────────────────────────────────────
PROFILE_SEARCH_PROMPTS = {
    "vietnam_psp": {
        "queries": [
            "Vietnam Dong VND exchange rate news today USD/VND SBV policy",
            "Vietnam central bank State Bank SBV foreign exchange intervention {date}",
            "Vietnam remittance inflow FDI capital flow {date}",
            "CNY VND cross border trade settlement China Vietnam",
        ],
        "context": "Vietnam PSP client focused on VND corridors. Key pairs: USDVND, CNHVND. Concerns: SBV managed float, VND depreciation pressure, remittance seasonality, capital controls.",
    },
    "philippines_psp": {
        "queries": [
            "Philippine Peso PHP exchange rate news today USD/PHP BSP policy",
            "BSP Bangko Sentral monetary policy rate decision Philippines {date}",
            "OFW remittance Philippines overseas workers flow {date}",
            "Philippines BPO industry foreign exchange demand current account",
        ],
        "context": "Philippines PSP client focused on PHP corridors. Key pairs: USDPHP, SGDPHP. Concerns: BSP policy, OFW remittances (10%+ GDP), PHP volatility, BPO FX demand.",
    },
    "indonesia_psp": {
        "queries": [
            "Indonesian Rupiah IDR exchange rate news today USD/IDR Bank Indonesia",
            "Bank Indonesia BI rate decision FX intervention {date}",
            "Indonesia commodity export palm oil coal nickel revenue IDR impact",
            "Indonesia foreign bond flow capital account rupiah stability {date}",
        ],
        "context": "Indonesia PSP client focused on IDR corridors. Key pairs: USDIDR, SGDIDR, CNHIDR. Concerns: BI intervention, IDR stability, commodity revenues, foreign bond holdings.",
    },
    "thailand_psp": {
        "queries": [
            "Thai Baht THB exchange rate news today USD/THB BOT policy",
            "Bank of Thailand BOT rate decision monetary policy {date}",
            "Thailand tourism revenue Chinese tourist arrivals THB impact {date}",
            "Thailand trade balance export CNY THB cross border {date}",
        ],
        "context": "Thailand PSP client focused on THB corridors. Key pairs: USDTHB, CNHTHB. Concerns: BOT policy, tourism recovery, Chinese arrivals, export competitiveness.",
    },
    "malaysia_psp": {
        "queries": [
            "Malaysian Ringgit MYR exchange rate news today USD/MYR BNM policy",
            "Bank Negara Malaysia BNM rate decision ringgit repatriation {date}",
            "Malaysia semiconductor electronics export MYR impact {date}",
            "SGD MYR cross border trade Malaysia Singapore {date}",
        ],
        "context": "Malaysia PSP client focused on MYR corridors. Key pairs: USDMYR, SGDMYR, CNHMYR. Concerns: BNM policy, oil price correlation, E&E exports, ringgit repatriation.",
    },
    "brazil_psp": {
        "queries": [
            "Brazilian Real BRL exchange rate news today USD/BRL BCB Selic",
            "Banco Central do Brasil BCB Selic rate decision {date}",
            "Brazil fiscal policy debt BRL carry trade {date}",
            "CNY BRL bilateral trade settlement China Brazil {date}",
        ],
        "context": "Brazil PSP client focused on BRL corridors. Key pairs: USDBRL, CNHBRL. Concerns: BCB Selic path, carry trade, commodity prices, fiscal concerns, PIX growth.",
    },
    "global_overview": {
        "queries": [
            "USD dollar index DXY Federal Reserve rate decision FX market {date}",
            "USDCNH CNH yuan exchange rate China PBOC policy {date}",
            "Global FX market emerging market currency risk sentiment {date}",
            "US China trade relations tariff impact FX market {date}",
        ],
        "context": "Global overview for FX research. Key pairs: USDCNH, EURUSD, GBPUSD, USDJPY. Concerns: Fed policy, US-China trade, global risk sentiment, DXY trend.",
    },
}


class NewsAIProvider:
    """Fetches news via Perplexity and generates Executive Summary via Claude.
    
    LLM call priority:
    1. Internal LLM Proxy (fit-ai.woa.com) — OpenAI-compatible format
    2. Anthropic Claude direct API — requires anthropic SDK + API key
    """

    def __init__(self, config: dict):
        self.config = config
        ai_config = config.get("ai", {})
        self.perplexity_key = ai_config.get("perplexity", {}).get("api_key", "")
        self.perplexity_model = ai_config.get("perplexity", {}).get("model", "sonar")
        self.client_profile_key = config.get("_active_client_profile", "")
        self.client_profiles = config.get("client_profiles", {})
        self.specific_requirements = config.get("_specific_requirements", "")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # ── LLM Proxy (priority 1) ──
        llm_config = config.get("llm", {})
        self.llm_enabled = llm_config.get("enabled", False)
        self.llm_api_key = llm_config.get("api_key", "")
        self.llm_base_url = llm_config.get("base_url", "")
        self.llm_model = llm_config.get("model", "claude-sonnet-4-20250514")
        self.llm_temperature = llm_config.get("temperature", 0.1)
        self.llm_max_tokens = llm_config.get("max_tokens", 4096)
        self.llm_timeout = llm_config.get("timeout", 120)

        # ── Claude Direct (priority 2 / fallback) ──
        self.claude_key = ai_config.get("claude", {}).get("api_key", "")
        self.claude_model = ai_config.get("claude", {}).get("model", "claude-sonnet-4-20250514")

        # Determine which LLM backend is available
        self.use_llm_proxy = self.llm_enabled and self.llm_api_key and self.llm_base_url
        self.use_claude_direct = bool(self.claude_key)
        self.llm_available = self.use_llm_proxy or self.use_claude_direct

        if self.use_llm_proxy:
            logger.info(f"LLM backend: fit-ai proxy ({self.llm_base_url}), model={self.llm_model}")
        elif self.use_claude_direct:
            logger.info(f"LLM backend: Anthropic Claude direct, model={self.claude_model}")
        else:
            logger.warning("No LLM backend configured — executive summary generation disabled")

    def get_profile(self) -> dict:
        if self.client_profile_key and self.client_profile_key in self.client_profiles:
            return self.client_profiles[self.client_profile_key]
        return None

    # ──────────────────────────────────────────────
    # Step 1: Generate search prompts based on client profile
    # ──────────────────────────────────────────────
    def generate_search_prompts(self, refine_with_claude: bool = False) -> list:
        """Generate search prompts for Perplexity based on client profile.
        Optionally refine with Claude for better targeting."""
        profile_key = self.client_profile_key or "global_overview"
        profile = self.get_profile()
        today = datetime.now().strftime("%Y-%m")

        # Get base prompts from template
        prompt_config = PROFILE_SEARCH_PROMPTS.get(profile_key, PROFILE_SEARCH_PROMPTS["global_overview"])
        base_queries = [q.replace("{date}", today) for q in prompt_config["queries"]]

        if not refine_with_claude or not self.llm_available:
            return base_queries

        # Use Claude to refine prompts based on current context
        try:
            refined = self._claude_refine_prompts(base_queries, profile, prompt_config["context"])
            if refined:
                return refined
        except Exception as e:
            logger.warning(f"Claude prompt refinement failed, using base prompts: {e}")

        return base_queries

    def _claude_refine_prompts(self, base_queries: list, profile: dict, context: str) -> list:
        """Use LLM to refine search prompts for better news targeting."""
        today = datetime.now().strftime("%Y-%m-%d")
        profile_info = ""
        if profile:
            profile_info = f"""
Client: {profile.get('name', 'Unknown')}
Region: {profile.get('region', 'Global')}
Base Currency: {profile.get('base_currency', 'USD')}
Corridors: {', '.join(c.get('label','') for c in profile.get('corridors', []))}
Key Concerns: {', '.join(profile.get('key_concerns', []))}
Central Bank: {profile.get('central_bank', 'N/A')}
"""

        prompt = f"""You are an FX research analyst at a cross-border payments company. Today is {today}.

{context}

{profile_info}

I need 4-5 search queries optimized for Perplexity AI to find the most relevant and recent FX news for this client. The queries should:
1. Focus on the specific currencies and corridors this client cares about
2. Include recent central bank actions or upcoming decisions
3. Cover macro events that impact their FX flows
4. Be specific enough to get actionable news, not generic results

Here are the base queries I have:
{json.dumps(base_queries, indent=2)}

{('IMPORTANT — The user has provided specific analysis requirements. Incorporate these into the search queries to ensure relevant news is found:' + chr(10) + self.specific_requirements + chr(10)) if self.specific_requirements else ''}Return ONLY a JSON array of 4-5 refined search query strings. No explanation, just the JSON array."""

        text = self._llm_call(prompt, max_tokens=800)
        if not text:
            return None

        # Parse JSON array from response
        if text.startswith("["):
            return json.loads(text)
        # Try to extract JSON from markdown code block
        if "```" in text:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        return None

    def _llm_call(self, prompt: str, system: str = None, max_tokens: int = None) -> str:
        """Unified LLM call: tries proxy first, then falls back to direct Anthropic.
        Returns the raw text response, or None on failure.
        """
        max_tokens = max_tokens or self.llm_max_tokens

        # ── Priority 1: LLM Proxy (OpenAI-compatible) ──
        if self.use_llm_proxy:
            try:
                result = self._call_llm_proxy(prompt, system=system, max_tokens=max_tokens)
                if result:
                    return result
                logger.warning("LLM proxy returned empty, falling back to Claude direct")
            except Exception as e:
                logger.warning(f"LLM proxy call failed: {e}, falling back to Claude direct")

        # ── Priority 2: Claude Direct API ──
        if self.use_claude_direct:
            try:
                return self._call_claude_direct(prompt, system=system, max_tokens=max_tokens)
            except Exception as e:
                logger.error(f"Claude direct call also failed: {e}")

        logger.error("No LLM backend available or all backends failed")
        return None

    def _call_llm_proxy(self, prompt: str, system: str = None, max_tokens: int = 4096) -> str:
        """Call LLM via internal fit-ai proxy (OpenAI-compatible /chat/completions)."""
        url = f"{self.llm_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": self.llm_temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=self.llm_timeout)
        resp.raise_for_status()
        data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() if content else None

    def _call_claude_direct(self, prompt: str, system: str = None, max_tokens: int = 4096) -> str:
        """Call Claude via Anthropic SDK directly."""
        import anthropic
        client = anthropic.Anthropic(api_key=self.claude_key)

        kwargs = {
            "model": self.claude_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        message = client.messages.create(**kwargs)
        return message.content[0].text.strip()

    # ──────────────────────────────────────────────
    # Step 2: Fetch news from Perplexity
    # ──────────────────────────────────────────────
    def fetch_news_from_perplexity(self, queries: list = None, refine_prompts: bool = False) -> list:
        """Fetch real-time FX news using Perplexity sonar API.
        Returns a list of news items with title, summary, source, date, sentiment."""
        if not self.perplexity_key:
            return [{"_error": "Perplexity API key not configured. Enter it in Report Settings or config.yaml under ai.perplexity.api_key"}]

        if not queries:
            queries = self.generate_search_prompts(refine_with_claude=refine_prompts)

        all_news = []
        seen_titles = set()
        profile = self.get_profile()
        profile_context = ""
        if profile:
            profile_context = f" relevant to {profile.get('region', 'global')} / {profile.get('base_currency', 'USD')} market"

        for query in queries:
            try:
                news_items = self._perplexity_search(query, profile_context)
                for item in news_items:
                    title = item.get("title", "")
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        all_news.append(item)
            except Exception as e:
                logger.warning(f"Perplexity search failed for query '{query}': {e}")

        if not all_news:
            return [{"_error": "No news found from Perplexity. Check API key and network connectivity."}]

        # Sort by relevance (Perplexity results already somewhat ranked)
        # Limit to top 15
        return all_news[:15]

    def _perplexity_search(self, query: str, context: str = "") -> list:
        """Call Perplexity sonar API for a single query."""
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }

        system_prompt = f"""You are an FX market news analyst. Search for the most recent and relevant foreign exchange market news{context}. 
For each news item found, provide:
- title: headline
- summary: 1-2 sentence summary
- source: publication name
- date: publication date (YYYY-MM-DD format)
- sentiment: one of "Bullish", "Bearish", or "Neutral" for the relevant currency
- relevance: which currency pair(s) this impacts

Return the results as a JSON array. Return ONLY the JSON array, no other text. If no relevant news found, return an empty array []."""

        payload = {
            "model": self.perplexity_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "max_tokens": 1500,
            "temperature": 0.1,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = data.get("citations", [])

        # Parse JSON from response
        news_items = self._parse_news_json(content)

        # Attach citations if available
        for i, item in enumerate(news_items):
            if i < len(citations):
                item["url"] = citations[i]
            item["source_api"] = "perplexity"

        return news_items

    def _parse_news_json(self, text: str) -> list:
        """Parse news items JSON from Perplexity response."""
        text = text.strip()
        # Direct JSON array
        if text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Extract from markdown code block
        if "```" in text:
            for block_type in ["```json", "```"]:
                if block_type in text:
                    start = text.find(block_type) + len(block_type)
                    end = text.find("```", start)
                    if end > start:
                        try:
                            return json.loads(text[start:end].strip())
                        except json.JSONDecodeError:
                            pass

        # Try to find any JSON array in the text
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        # Fallback: return single item with the raw text
        if len(text) > 20:
            return [{"title": "Market Update", "summary": text[:500], "source": "Perplexity", "date": datetime.now().strftime("%Y-%m-%d"), "sentiment": "Neutral"}]

        return []

    # ──────────────────────────────────────────────
    # Step 3: Generate Executive Summary with Claude
    # ──────────────────────────────────────────────
    def generate_executive_summary(self, news: list, spot_rates: dict = None, language: str = "en") -> dict:
        """Use LLM to generate Executive Summary based on real news and market data.
        Returns dict with executive_summary, market_view, risk_assessment, outlook.
        Priority: LLM Proxy → Claude Direct."""
        if not self.llm_available:
            return {"_error": "No LLM backend configured. Set llm.api_key in config.yaml (recommended) or ai.claude.api_key for direct Anthropic access."}

        # Filter out error items
        valid_news = [n for n in news if not n.get("_error")]
        if not valid_news:
            return {"_error": "No valid news to generate summary from. Fetch news first."}

        profile = self.get_profile()
        today = datetime.now().strftime("%Y-%m-%d")

        # Build context
        profile_context = self._build_profile_context(profile)
        news_context = self._build_news_context(valid_news)
        rates_context = self._build_rates_context(spot_rates, profile)

        lang_instruction = ""
        if language == "zh":
            lang_instruction = "\n\nIMPORTANT: Write the entire response in Chinese (简体中文). All four sections must be in Chinese."

        # Build specific requirements section if provided
        requirements_section = ""
        if self.specific_requirements:
            requirements_section = f"""

## Specific Analysis Requirements (from the user)
The user has provided the following specific requirements for this report. You MUST address these in your analysis — weave them into the relevant sections (executive_summary, market_view, risk_assessment, or outlook) as appropriate:

{self.specific_requirements}
"""

        prompt = f"""You are a senior FX research analyst at Tenpay Global, a cross-border payments company. Today is {today}.

{profile_context}

## Recent Market News (from real-time search)
{news_context}

{rates_context}
{requirements_section}
Based on the above real news and market data, write a professional FX research executive summary for this client. The summary should be:
- Data-driven: reference specific numbers, rates, and events from the news
- Actionable: highlight what matters for this client's FX corridors
- Forward-looking: include near-term outlook
- Professional tone: suitable for a client-facing FX research report
{('- Address the specific analysis requirements provided by the user' + chr(10)) if self.specific_requirements else ''}
Return EXACTLY this JSON structure (no markdown, no code blocks, just raw JSON):
{{
  "executive_summary": "2-3 paragraph overview covering key market developments this period, with specific reference to news events and data points",
  "market_view": "2-3 paragraphs on current FX dynamics, key drivers, central bank policies, and how they affect this client's corridors",
  "risk_assessment": "1-2 paragraphs on key risks for this client's FX exposures, based on current news and events",
  "outlook": "1-2 paragraphs on near-term forward view for key currency pairs"
}}{lang_instruction}"""

        try:
            text = self._llm_call(prompt, max_tokens=2000)
            if not text:
                return {"_error": "LLM returned empty response"}
            return self._parse_summary_json(text)
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return {"_error": f"LLM API error: {str(e)}"}

    def _build_profile_context(self, profile: dict) -> str:
        if not profile:
            return "## Client: Global Overview\nGeneral FX research for cross-border payments."
        return f"""## Client Profile
- Name: {profile.get('name', 'N/A')}
- Region: {profile.get('region', 'Global')}
- Base Currency: {profile.get('base_currency', 'USD')}
- Key Corridors: {', '.join(c.get('label','') for c in profile.get('corridors', []))}
- Central Bank: {profile.get('central_bank', 'N/A')}
- Key Concerns: {', '.join(profile.get('key_concerns', []))}"""

    def _build_news_context(self, news: list) -> str:
        lines = []
        for i, n in enumerate(news[:12], 1):
            sentiment = n.get("sentiment", "Neutral")
            date = n.get("date", "N/A")
            title = n.get("title", "N/A")
            summary = n.get("summary", "")
            source = n.get("source", "")
            lines.append(f"{i}. [{date}] [{sentiment}] {title}\n   {summary}\n   Source: {source}")
        return "\n".join(lines)

    def _build_rates_context(self, spot_rates: dict, profile: dict) -> str:
        if not spot_rates or "_error" in spot_rates:
            return ""
        focus_pairs = profile.get("focus_pairs", []) if profile else []
        pairs_to_show = focus_pairs if focus_pairs else list(spot_rates.keys())[:8]
        lines = ["## Current Spot Rates"]
        for pair in pairs_to_show:
            rate_info = spot_rates.get(pair)
            if not rate_info or isinstance(rate_info, str):
                continue
            rate = rate_info.get("rate", "N/A")
            chg_1d = rate_info.get("chg_1d")
            chg_1w = rate_info.get("chg_1w")
            chg_1m = rate_info.get("chg_1m")
            line = f"- {pair}: {rate}"
            if chg_1d is not None:
                line += f" (1D: {chg_1d:+.2f}%)"
            if chg_1w is not None:
                line += f" (1W: {chg_1w:+.2f}%)"
            if chg_1m is not None:
                line += f" (1M: {chg_1m:+.2f}%)"
            lines.append(line)
        return "\n".join(lines) if len(lines) > 1 else ""

    def _parse_summary_json(self, text: str) -> dict:
        """Parse the executive summary JSON from Claude's response."""
        text = text.strip()
        # Direct JSON
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        # Extract from code block
        if "```" in text:
            for block_type in ["```json", "```"]:
                if block_type in text:
                    start = text.find(block_type) + len(block_type)
                    end = text.find("```", start)
                    if end > start:
                        try:
                            return json.loads(text[start:end].strip())
                        except json.JSONDecodeError:
                            pass
        # Try to find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        # Fallback
        return {"executive_summary": text, "market_view": "", "risk_assessment": "", "outlook": ""}

    # ──────────────────────────────────────────────
    # Convenience: full pipeline
    # ──────────────────────────────────────────────
    def fetch_news_and_generate_summary(self, spot_rates: dict = None, language: str = "en", refine_prompts: bool = True) -> dict:
        """Full pipeline: generate prompts → fetch news → generate summary.
        Returns dict with 'news' list and 'commentary' dict."""
        result = {"news": [], "commentary": {}, "search_prompts": [], "errors": []}

        # Step 1: Generate prompts
        prompts = self.generate_search_prompts(refine_with_claude=refine_prompts)
        result["search_prompts"] = prompts

        # Step 2: Fetch news
        news = self.fetch_news_from_perplexity(queries=prompts, refine_prompts=False)
        result["news"] = news

        if news and news[0].get("_error"):
            result["errors"].append(news[0]["_error"])
            return result

        # Step 3: Generate executive summary
        if self.llm_available:
            commentary = self.generate_executive_summary(news, spot_rates=spot_rates, language=language)
            if commentary.get("_error"):
                result["errors"].append(commentary["_error"])
            else:
                result["commentary"] = commentary
        else:
            result["errors"].append("No LLM backend configured — news fetched but executive summary not generated. Set llm section in config.yaml.")

        # Cache results
        self._cache_results(result)
        return result

    def _cache_results(self, result: dict):
        """Cache news and commentary for reuse."""
        try:
            cache_path = CACHE_DIR / "ai_news_commentary.json"
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "profile": self.client_profile_key,
                    "news": result.get("news", []),
                    "commentary": result.get("commentary", {}),
                    "search_prompts": result.get("search_prompts", []),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache AI results: {e}")

    def load_cached_results(self) -> dict:
        """Load previously cached news/commentary."""
        try:
            cache_path = CACHE_DIR / "ai_news_commentary.json"
            if cache_path.exists():
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None
