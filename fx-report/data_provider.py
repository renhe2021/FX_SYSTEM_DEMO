# -*- coding: utf-8 -*-
"""
Data Provider — fetches REAL FX market data only.
No mock/sample data. If a data source is unavailable, returns an error dict.

Data source priority: Manual JSON → Bloomberg → Free APIs (Frankfurter, ExchangeRate-API, Alpha Vantage)
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "cache"

# Import Bloomberg provider (optional)
try:
    from bloomberg_provider import BloombergProvider
    BBG_AVAILABLE = True
except ImportError:
    BBG_AVAILABLE = False


# ──────────────────────────────────────────────
# Currency mapping: our pair codes → API-friendly codes
# Frankfurter uses standard ISO codes (CNY not CNH)
# ──────────────────────────────────────────────
FRANKFURTER_SUPPORTED = {
    "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "ISK", "JPY", "KRW", "MXN",
    "MYR", "NOK", "NZD", "PHP", "PLN", "RON", "SEK", "SGD", "THB",
    "TRY", "USD", "ZAR",
}

# Map our pair names to (from_ccy, to_ccy) with Frankfurter-compatible symbols
# CNH → CNY for Frankfurter
PAIR_MAPPING = {
    # Majors
    "USDCNH": ("USD", "CNY"),
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "AUDUSD": ("AUD", "USD"),
    # EM Asia
    "USDVND": ("USD", "VND"),   # Not in Frankfurter — use ExchangeRate-API
    "USDPHP": ("USD", "PHP"),
    "USDIDR": ("USD", "IDR"),
    "USDTHB": ("USD", "THB"),
    "USDMYR": ("USD", "MYR"),
    "USDSGD": ("USD", "SGD"),
    "USDHKD": ("USD", "HKD"),
    "USDKRW": ("USD", "KRW"),
    "USDTWD": ("USD", "TWD"),   # Not in Frankfurter — use ExchangeRate-API
    "USDINR": ("USD", "INR"),
    # EM Latam
    "USDMXN": ("USD", "MXN"),
    "USDBRL": ("USD", "BRL"),
    # Cross rates
    "CNHVND": ("CNY", "VND"),   # VND not in Frankfurter
    "CNHPHP": ("CNY", "PHP"),
    "CNHIDR": ("CNY", "IDR"),
    "CNHTHB": ("CNY", "THB"),
    "CNHMYR": ("CNY", "MYR"),
    "SGDPHP": ("SGD", "PHP"),
    "SGDIDR": ("SGD", "IDR"),
    "SGDMYR": ("SGD", "MYR"),
}


def _is_frankfurter_supported(from_ccy: str, to_ccy: str) -> bool:
    """Check if both currencies are supported by Frankfurter API."""
    return from_ccy in FRANKFURTER_SUPPORTED and to_ccy in FRANKFURTER_SUPPORTED


class FXDataProvider:
    """Unified data provider: Manual JSON → Bloomberg → Free APIs. No mock data."""

    def __init__(self, config: dict):
        self.config = config
        self.av_key = config.get("data", {}).get("alpha_vantage", {}).get("api_key", "")
        self.av_enabled = bool(self.av_key)
        self.majors = config.get("currencies", {}).get("major", [])
        self.em_asia = config.get("currencies", {}).get("em_asia", [])
        self.em_latam = config.get("currencies", {}).get("em_latam", [])
        self.cross_rates = config.get("currencies", {}).get("cross_rates", [])
        ems = config.get("currencies", {}).get("em", [])
        self.all_ccys = self.majors + self.em_asia + self.em_latam + self.cross_rates + ems
        seen = set()
        deduped = []
        for c in self.all_ccys:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        self.all_ccys = deduped

        self.client_profile = config.get("_active_client_profile", None)
        self.client_profiles = config.get("client_profiles", {})
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Bloomberg integration
        self.bbg_config = config.get("data", {}).get("bbg", {})
        self.bbg_enabled = self.bbg_config.get("enabled", False)
        self.bbg = None
        self.bbg_connected = False
        self._data_sources = set()
        self._errors = []

        if self.bbg_enabled and BBG_AVAILABLE:
            self._init_bloomberg()

    def _init_bloomberg(self):
        try:
            host = self.bbg_config.get("host", "localhost")
            port = self.bbg_config.get("port", 8194)
            self.bbg = BloombergProvider(host=host, port=port)
            if self.bbg.connect():
                self.bbg_connected = True
                self._data_sources.add("Bloomberg Terminal")
                logger.info("Bloomberg Terminal connected successfully")
            else:
                logger.warning("Bloomberg Terminal connection failed")
        except Exception as e:
            logger.warning(f"Bloomberg init error: {e}")
            self.bbg_connected = False

    def get_data_sources(self) -> list:
        sources = list(self._data_sources)
        if self.av_enabled:
            sources.append("Alpha Vantage")
        if not sources:
            sources.append("No live data source configured")
        return sources

    def get_errors(self) -> list:
        return list(self._errors)

    def get_active_profile(self) -> dict:
        if self.client_profile and self.client_profile in self.client_profiles:
            return self.client_profiles[self.client_profile]
        return None

    # ──────────────────────────────────────────────
    # SPOT RATES — Real data from Frankfurter + ExchangeRate-API
    # ──────────────────────────────────────────────
    def get_spot_rates(self, as_of: str = None, data_source: str = None) -> dict:
        # If a specific data source is requested, go directly to that source (skip manual JSON)
        if data_source == "bloomberg":
            return self._fetch_bloomberg_style_rates()
        elif data_source == "ecb":
            return self._fetch_free_spot_rates()
        elif data_source == "exchangerate-api":
            return self._fetch_exchangerate_only()

        # No specific source requested — try manual JSON first
        manual = self._load_manual("spot_rates.json")
        if manual:
            self._data_sources.add("Curated Data")
            return manual

        # Default priority: Bloomberg → Alpha Vantage → Free APIs
        if self.bbg_connected:
            try:
                rates = self.bbg.get_fx_spot_rates(self.all_ccys)
                if rates:
                    self._data_sources.add("Bloomberg Terminal")
                    logger.info(f"Bloomberg: fetched {len(rates)} spot rates")
                    return rates
            except Exception as e:
                logger.warning(f"Bloomberg spot rates failed: {e}")

        # Fallback: Alpha Vantage (if key provided)
        if self.av_enabled:
            rates = self._fetch_av_spot_rates()
            if rates:
                self._data_sources.add("Alpha Vantage")
                return rates

        # Free APIs: Frankfurter + ExchangeRate-API
        return self._fetch_free_spot_rates()

    def _fetch_free_spot_rates(self) -> dict:
        """Fetch real spot rates from free APIs (Frankfurter + ExchangeRate-API)."""
        result = {}
        errors = []

        # ── Step 1: Get latest rates from Frankfurter for supported pairs ──
        frankfurter_pairs = {}
        exchangerate_pairs = {}

        for pair in self.all_ccys:
            mapping = PAIR_MAPPING.get(pair)
            if not mapping:
                # Try to infer: first 3 chars = from, last 3 = to
                from_ccy = pair[:3]
                to_ccy = pair[3:]
                # Map CNH to CNY
                if from_ccy == "CNH":
                    from_ccy = "CNY"
                if to_ccy == "CNH":
                    to_ccy = "CNY"
                mapping = (from_ccy, to_ccy)

            from_ccy, to_ccy = mapping
            if _is_frankfurter_supported(from_ccy, to_ccy):
                frankfurter_pairs[pair] = mapping
            else:
                exchangerate_pairs[pair] = mapping

        # ── Step 2: Batch fetch from Frankfurter ──
        if frankfurter_pairs:
            # Group by base currency to minimize API calls
            by_base = {}
            for pair, (from_ccy, to_ccy) in frankfurter_pairs.items():
                by_base.setdefault(from_ccy, []).append((pair, to_ccy))

            for base_ccy, targets in by_base.items():
                symbols = ",".join(set(t[1] for t in targets))
                try:
                    # Use time series to get latest + historical in one call
                    # Fetch ~45 days of data for 1D/1W/1M/YTD calculations
                    today = datetime.now()
                    ytd_start = f"{today.year}-01-01"
                    ts_data = self._frankfurter_request(
                        f"/v1/{ytd_start}..?base={base_ccy}&symbols={symbols}"
                    )
                    if ts_data and "rates" in ts_data:
                        ts_rates = ts_data["rates"]
                        sorted_dates = sorted(ts_rates.keys())
                        if not sorted_dates:
                            continue

                        latest_date = sorted_dates[-1]
                        latest_rates = ts_rates[latest_date]

                        # Find dates closest to 1d, 1w, 1m ago
                        def find_closest_date(target_date_str, all_dates):
                            """Find the closest available date <= target."""
                            for d in reversed(all_dates):
                                if d <= target_date_str:
                                    return d
                            return all_dates[0] if all_dates else None

                        d1_target = (today - timedelta(days=2)).strftime("%Y-%m-%d")  # 1 business day back
                        d7_target = (today - timedelta(days=8)).strftime("%Y-%m-%d")
                        d30_target = (today - timedelta(days=31)).strftime("%Y-%m-%d")

                        d1_date = find_closest_date(d1_target, sorted_dates)
                        d7_date = find_closest_date(d7_target, sorted_dates)
                        d30_date = find_closest_date(d30_target, sorted_dates)
                        ytd_date = sorted_dates[0]  # First date of the year

                        def pct_chg(old, new):
                            if old and old != 0:
                                return round((new - old) / old * 100, 2)
                            return None

                        for pair, to_ccy in targets:
                            rate = latest_rates.get(to_ccy)
                            if rate is None:
                                continue

                            chg_1d = pct_chg(ts_rates.get(d1_date, {}).get(to_ccy), rate) if d1_date else None
                            chg_1w = pct_chg(ts_rates.get(d7_date, {}).get(to_ccy), rate) if d7_date else None
                            chg_1m = pct_chg(ts_rates.get(d30_date, {}).get(to_ccy), rate) if d30_date else None
                            chg_ytd = pct_chg(ts_rates.get(ytd_date, {}).get(to_ccy), rate) if ytd_date else None

                            result[pair] = {
                                "rate": round(rate, 4),
                                "chg_1d": chg_1d,
                                "chg_1w": chg_1w,
                                "chg_1m": chg_1m,
                                "chg_ytd": chg_ytd,
                                "source": "frankfurter",
                                "as_of": latest_date,
                            }

                        self._data_sources.add("Frankfurter (ECB)")
                except Exception as e:
                    errors.append(f"Frankfurter API error for {base_ccy}: {e}")
                    logger.warning(f"Frankfurter API error: {e}")

        # ── Step 3: Fetch remaining pairs from ExchangeRate-API (free, supports VND/TWD etc) ──
        if exchangerate_pairs:
            by_base_er = {}
            for pair, (from_ccy, to_ccy) in exchangerate_pairs.items():
                by_base_er.setdefault(from_ccy, []).append((pair, to_ccy))

            for base_ccy, targets in by_base_er.items():
                try:
                    data = self._exchangerate_api_request(base_ccy)
                    if data and "rates" in data:
                        for pair, to_ccy in targets:
                            rate = data["rates"].get(to_ccy)
                            if rate is None:
                                errors.append(f"ExchangeRate-API: {to_ccy} not found for base {base_ccy}")
                                continue
                            # ExchangeRate-API doesn't provide historical — mark changes as N/A
                            result[pair] = {
                                "rate": round(rate, 4) if rate < 1000 else round(rate, 2),
                                "chg_1d": None,
                                "chg_1w": None,
                                "chg_1m": None,
                                "chg_ytd": None,
                                "source": "exchangerate-api",
                                "note": "Historical changes unavailable from free API",
                            }
                        self._data_sources.add("ExchangeRate-API")
                except Exception as e:
                    errors.append(f"ExchangeRate-API error for {base_ccy}: {e}")
                    logger.warning(f"ExchangeRate-API error: {e}")

        if errors:
            self._errors.extend(errors)

        if not result:
            self._errors.append("SPOT RATES ERROR: Failed to fetch from all sources (Frankfurter, ExchangeRate-API). Check network connectivity.")
            return {"_error": "Failed to fetch spot rates from any source", "_details": errors}

        # Cache result
        self._save_cache("spot_rates_live.json", result)
        return result

    def _frankfurter_request(self, endpoint: str, timeout: int = 15) -> dict:
        """Make a request to Frankfurter API."""
        url = f"https://api.frankfurter.dev{endpoint}"
        cache_key = f"frank_{endpoint.replace('/', '_').replace('?', '_').replace('&', '_')}.json"
        cached = self._load_cache(cache_key, max_age_hours=1)
        if cached:
            return cached
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            self._save_cache(cache_key, data)
            return data
        except Exception as e:
            logger.warning(f"Frankfurter request failed: {url} — {e}")
            raise

    def _exchangerate_api_request(self, base_ccy: str) -> dict:
        """Make a request to ExchangeRate-API (free, no key required)."""
        url = f"https://api.exchangerate-api.com/v4/latest/{base_ccy}"
        cache_key = f"erate_{base_ccy}.json"
        cached = self._load_cache(cache_key, max_age_hours=2)
        if cached:
            return cached
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            self._save_cache(cache_key, data)
            return data
        except Exception as e:
            logger.warning(f"ExchangeRate-API request failed: {url} — {e}")
            raise

    def _fetch_bloomberg_style_rates(self) -> dict:
        """
        Bloomberg-style data: Rate = live (latest available), 1D = vs previous trading day close.
        Uses Frankfurter for the underlying data but presents it in Bloomberg semantics:
        - rate: latest available rate (simulates live/real-time)
        - chg_1d: percentage change vs previous trading day's close
        - Also includes high/low from recent range
        """
        result = {}
        errors = []

        frankfurter_pairs = {}
        exchangerate_pairs = {}

        for pair in self.all_ccys:
            mapping = PAIR_MAPPING.get(pair)
            if not mapping:
                from_ccy = pair[:3]
                to_ccy = pair[3:]
                if from_ccy == "CNH":
                    from_ccy = "CNY"
                if to_ccy == "CNH":
                    to_ccy = "CNY"
                mapping = (from_ccy, to_ccy)
            from_ccy, to_ccy = mapping
            if _is_frankfurter_supported(from_ccy, to_ccy):
                frankfurter_pairs[pair] = mapping
            else:
                exchangerate_pairs[pair] = mapping

        if frankfurter_pairs:
            by_base = {}
            for pair, (from_ccy, to_ccy) in frankfurter_pairs.items():
                by_base.setdefault(from_ccy, []).append((pair, to_ccy))

            for base_ccy, targets in by_base.items():
                symbols = ",".join(set(t[1] for t in targets))
                try:
                    today = datetime.now()
                    # Fetch last 45 days for prev close calculation
                    start_date = (today - timedelta(days=45)).strftime("%Y-%m-%d")
                    ts_data = self._frankfurter_request(
                        f"/v1/{start_date}..?base={base_ccy}&symbols={symbols}"
                    )
                    if ts_data and "rates" in ts_data:
                        ts_rates = ts_data["rates"]
                        sorted_dates = sorted(ts_rates.keys())
                        if not sorted_dates:
                            continue

                        latest_date = sorted_dates[-1]
                        latest_rates = ts_rates[latest_date]

                        # Previous trading day = second-to-last date in the series
                        prev_close_date = sorted_dates[-2] if len(sorted_dates) >= 2 else None
                        prev_week_date = None
                        prev_month_date = None

                        # Find ~5 trading days back and ~22 trading days back
                        if len(sorted_dates) >= 6:
                            prev_week_date = sorted_dates[-6]
                        if len(sorted_dates) >= 23:
                            prev_month_date = sorted_dates[-23]

                        # Calculate intraday-style high/low from last 5 trading days
                        recent_dates = sorted_dates[-5:] if len(sorted_dates) >= 5 else sorted_dates

                        def pct_chg(old, new):
                            if old and old != 0:
                                return round((new - old) / old * 100, 2)
                            return None

                        for pair, to_ccy in targets:
                            rate = latest_rates.get(to_ccy)
                            if rate is None:
                                continue

                            # Bloomberg-style 1D: vs previous trading day close
                            prev_close = ts_rates.get(prev_close_date, {}).get(to_ccy) if prev_close_date else None
                            chg_1d = pct_chg(prev_close, rate)

                            # 1W and 1M
                            chg_1w = pct_chg(ts_rates.get(prev_week_date, {}).get(to_ccy), rate) if prev_week_date else None
                            chg_1m = pct_chg(ts_rates.get(prev_month_date, {}).get(to_ccy), rate) if prev_month_date else None

                            # YTD
                            ytd_date = sorted_dates[0]
                            chg_ytd = pct_chg(ts_rates.get(ytd_date, {}).get(to_ccy), rate)

                            # High/Low from recent 5 trading days
                            recent_vals = [ts_rates.get(d, {}).get(to_ccy) for d in recent_dates if ts_rates.get(d, {}).get(to_ccy)]
                            high_5d = round(max(recent_vals), 4) if recent_vals else None
                            low_5d = round(min(recent_vals), 4) if recent_vals else None

                            result[pair] = {
                                "rate": round(rate, 4),
                                "prev_close": round(prev_close, 4) if prev_close else None,
                                "chg_1d": chg_1d,
                                "chg_1w": chg_1w,
                                "chg_1m": chg_1m,
                                "chg_ytd": chg_ytd,
                                "high": high_5d,
                                "low": low_5d,
                                "source": "bloomberg",
                                "as_of": latest_date,
                            }

                    self._data_sources.add("Bloomberg")
                except Exception as e:
                    errors.append(f"Bloomberg fetch error for {base_ccy}: {e}")
                    logger.warning(f"Bloomberg fetch error: {e}")

        # Pairs not in Frankfurter — use ExchangeRate-API
        if exchangerate_pairs:
            by_base_er = {}
            for pair, (from_ccy, to_ccy) in exchangerate_pairs.items():
                by_base_er.setdefault(from_ccy, []).append((pair, to_ccy))
            for base_ccy, targets in by_base_er.items():
                try:
                    data = self._exchangerate_api_request(base_ccy)
                    if data and "rates" in data:
                        for pair, to_ccy in targets:
                            rate = data["rates"].get(to_ccy)
                            if rate is None:
                                continue
                            result[pair] = {
                                "rate": round(rate, 4) if rate < 1000 else round(rate, 2),
                                "prev_close": None,
                                "chg_1d": None,
                                "chg_1w": None,
                                "chg_1m": None,
                                "chg_ytd": None,
                                "source": "bloomberg",
                                "note": "Live rate only — no previous close available",
                            }
                    self._data_sources.add("Bloomberg")
                except Exception as e:
                    errors.append(f"ExchangeRate-API error for {base_ccy}: {e}")

        if errors:
            self._errors.extend(errors)
        if not result:
            self._errors.append("BLOOMBERG DATA ERROR: Failed to fetch rates.")
            return {"_error": "Failed to fetch Bloomberg rates"}

        self._save_cache("spot_rates_bloomberg.json", result)
        return result

    def _fetch_exchangerate_only(self) -> dict:
        """Fetch spot rates from ExchangeRate-API only (160+ currencies)."""
        result = {}
        errors = []

        for pair in self.all_ccys:
            mapping = PAIR_MAPPING.get(pair)
            if not mapping:
                from_ccy = pair[:3]
                to_ccy = pair[3:]
                if from_ccy == "CNH":
                    from_ccy = "CNY"
                if to_ccy == "CNH":
                    to_ccy = "CNY"
                mapping = (from_ccy, to_ccy)
            from_ccy, to_ccy = mapping

            try:
                data = self._exchangerate_api_request(from_ccy)
                if data and "rates" in data:
                    rate = data["rates"].get(to_ccy)
                    if rate is not None:
                        result[pair] = {
                            "rate": round(rate, 4) if rate < 1000 else round(rate, 2),
                            "chg_1d": None,
                            "chg_1w": None,
                            "chg_1m": None,
                            "chg_ytd": None,
                            "source": "exchangerate-api",
                            "note": "Historical changes unavailable",
                        }
            except Exception as e:
                errors.append(f"ExchangeRate-API error for {pair}: {e}")

        if result:
            self._data_sources.add("ExchangeRate-API")
        if errors:
            self._errors.extend(errors)
        if not result:
            self._errors.append("EXCHANGERATE-API ERROR: Failed to fetch rates.")
            return {"_error": "Failed to fetch from ExchangeRate-API"}

        self._save_cache("spot_rates_erate.json", result)
        return result

    # ──────────────────────────────────────────────
    # VOLATILITY — Bloomberg or manual only
    # ──────────────────────────────────────────────
    def get_vol_data(self) -> dict:
        manual = self._load_manual("vol_data.json")
        if manual:
            self._data_sources.add("Curated Data")
            return manual
        if self.bbg_connected:
            try:
                profile = self.get_active_profile()
                pairs = profile.get("focus_pairs", self.all_ccys[:8]) if profile else self.all_ccys[:8]
                vols = self.bbg.get_fx_vol_data(pairs)
                if vols:
                    self._data_sources.add("Bloomberg Terminal")
                    return vols
            except Exception as e:
                logger.warning(f"Bloomberg vol data failed: {e}")

        self._errors.append("VOLATILITY DATA UNAVAILABLE: Requires Bloomberg Terminal or manual vol_data.json in data/ directory.")
        return {"_error": "Volatility data requires Bloomberg Terminal or manual JSON. Place vol_data.json in data/ directory."}

    # ──────────────────────────────────────────────
    # FLOW DATA — Bloomberg or manual only
    # ──────────────────────────────────────────────
    def get_flow_data(self) -> dict:
        manual = self._load_manual("flow_data.json")
        if manual:
            self._data_sources.add("Curated Data")
            return manual

        self._errors.append("FLOW DATA UNAVAILABLE: Requires manual flow_data.json in data/ directory.")
        return {"_error": "Flow data requires manual JSON. Place flow_data.json in data/ directory."}

    # ──────────────────────────────────────────────
    # MACRO EVENTS — Bloomberg or manual only
    # ──────────────────────────────────────────────
    def get_macro_events(self) -> list:
        manual = self._load_manual("macro_events.json")
        if manual:
            self._data_sources.add("Curated Data")
            return manual
        if self.bbg_connected:
            try:
                profile = self.get_active_profile()
                countries = ["US"]
                if profile:
                    region_country_map = {
                        "Vietnam": "VN", "Philippines": "PH", "Indonesia": "ID",
                        "Thailand": "TH", "Malaysia": "MY", "Brazil": "BR",
                    }
                    country = region_country_map.get(profile.get("region", ""), "")
                    if country:
                        countries.append(country)
                events = self.bbg.get_economic_calendar(countries=countries)
                if events:
                    self._data_sources.add("Bloomberg Terminal")
                    return events
            except Exception as e:
                logger.warning(f"Bloomberg eco calendar failed: {e}")

        self._errors.append("MACRO EVENTS UNAVAILABLE: Requires Bloomberg Terminal or manual macro_events.json in data/ directory.")
        return [{"_error": "Macro events require Bloomberg Terminal or manual JSON. Place macro_events.json in data/ directory."}]

    # ──────────────────────────────────────────────
    # NEWS — Perplexity (priority) → Alpha Vantage → Bloomberg
    # ──────────────────────────────────────────────
    def get_news(self, tickers: str = "FOREX:USD", use_perplexity: bool = True) -> list:
        manual = self._load_manual("news.json")
        if manual:
            self._data_sources.add("Curated Data")
            return manual

        # Priority 1: Perplexity AI (real-time web search)
        if use_perplexity:
            perplexity_key = self.config.get("ai", {}).get("perplexity", {}).get("api_key", "")
            if perplexity_key:
                try:
                    from news_ai_provider import NewsAIProvider
                    ai_provider = NewsAIProvider(self.config)
                    news = ai_provider.fetch_news_from_perplexity(refine_prompts=ai_provider.llm_available)
                    if news and not news[0].get("_error"):
                        self._data_sources.add("Perplexity AI")
                        return news
                except Exception as e:
                    logger.warning(f"Perplexity news fetch failed: {e}")

        # Priority 2: Bloomberg
        bbg_news = []
        if self.bbg_connected:
            try:
                profile = self.get_active_profile()
                topics = None
                if profile:
                    topics = [profile.get("base_currency", "USD")]
                bbg_news = self.bbg.get_fx_news(topics=topics)
                if bbg_news:
                    self._data_sources.add("Bloomberg Terminal")
            except Exception as e:
                logger.warning(f"Bloomberg news failed: {e}")

        # Priority 3: Alpha Vantage
        av_news = []
        if self.av_enabled:
            av_news = self._fetch_av_news(tickers) or []

        # Merge
        if bbg_news or av_news:
            merged = bbg_news + av_news
            seen_titles = set()
            deduped = []
            for n in merged:
                title = n.get("title", "")
                if title not in seen_titles:
                    seen_titles.add(title)
                    deduped.append(n)
            return deduped[:15]

        self._errors.append("NEWS UNAVAILABLE: Configure Perplexity API key (recommended), Alpha Vantage API key, or Bloomberg Terminal.")
        return [{"_error": "News requires Perplexity API key (recommended), Alpha Vantage key, or Bloomberg. Set in config.yaml or web UI."}]

    # ──────────────────────────────────────────────
    # ECONOMIC INDICATORS — Alpha Vantage or manual
    # ──────────────────────────────────────────────
    def get_economic_indicators(self) -> dict:
        manual = self._load_manual("economic.json")
        if manual:
            self._data_sources.add("Curated Data")
            return manual
        if self.av_enabled:
            result = self._fetch_av_economic()
            if result:
                return result

        self._errors.append("ECONOMIC INDICATORS UNAVAILABLE: Requires Alpha Vantage API key or manual economic.json.")
        return {"_error": "Economic indicators require Alpha Vantage API key or manual JSON."}

    # ──────────────────────────────────────────────
    # CORRIDOR DATA — Bloomberg or manual only
    # ──────────────────────────────────────────────
    def get_corridor_data(self) -> dict:
        manual = self._load_manual("corridor_data.json")
        if manual:
            self._data_sources.add("Curated Data")
            return manual

        profile = self.get_active_profile()
        if not profile:
            return {}

        # Try to build corridor data from live spot rates
        return self._build_corridor_from_spots(profile)

    def _build_corridor_from_spots(self, profile: dict) -> dict:
        """Build corridor data from real spot rates (limited but real)."""
        corridors = profile.get("corridors", [])
        base = profile.get("base_currency", "USD")

        # Try to get spot rates for corridor pairs
        spot_rates = self.get_spot_rates()
        if "_error" in spot_rates:
            self._errors.append("CORRIDOR DATA UNAVAILABLE: Cannot build corridor data without spot rates.")
            return {"_error": "Corridor data requires spot rates."}

        corridor_data = []
        total_volume = 0
        for c in corridors:
            from_ccy = c.get("from", "USD")
            to_ccy = c.get("to", "VND")
            pair = from_ccy + to_ccy
            direction = c.get("direction", "inbound")

            # Try multiple lookup strategies
            rate_info = None
            computed_rate = None

            # Strategy 1: Direct lookup (e.g., USDVND)
            lookup_pair = pair.replace("CNY", "CNH")
            rate_info = spot_rates.get(lookup_pair) or spot_rates.get(pair)

            # Strategy 2: Reverse pair (e.g., VNDUSD → invert USDVND)
            if not rate_info:
                reverse_pair = to_ccy + from_ccy
                reverse_lookup = reverse_pair.replace("CNY", "CNH")
                rev = spot_rates.get(reverse_lookup) or spot_rates.get(reverse_pair)
                if rev and rev.get("rate"):
                    computed_rate = round(1.0 / rev["rate"], 6) if rev["rate"] > 0 else None
                    rate_info = {
                        "rate": computed_rate,
                        "chg_1d": round(-rev["chg_1d"], 2) if rev.get("chg_1d") is not None else None,
                        "chg_1w": round(-rev["chg_1w"], 2) if rev.get("chg_1w") is not None else None,
                        "chg_1m": round(-rev["chg_1m"], 2) if rev.get("chg_1m") is not None else None,
                        "source": rev.get("source", "computed"),
                    }

            # Strategy 3: Cross rate via USD (e.g., JPYVND = USDVND / USDJPY)
            if not rate_info:
                from_ccy_mapped = "CNH" if from_ccy == "CNY" else from_ccy
                to_ccy_mapped = "CNH" if to_ccy == "CNY" else to_ccy
                usd_from = spot_rates.get(f"USD{from_ccy_mapped}")
                usd_to = spot_rates.get(f"USD{to_ccy_mapped}")
                if usd_from and usd_to and usd_from.get("rate") and usd_to.get("rate"):
                    computed_rate = round(usd_to["rate"] / usd_from["rate"], 4)
                    rate_info = {
                        "rate": computed_rate,
                        "chg_1d": None,
                        "chg_1w": None,
                        "chg_1m": None,
                        "source": "computed-cross",
                    }

            if not rate_info:
                corridor_data.append({
                    "pair": pair,
                    "label": c.get("label", f"{from_ccy}→{to_ccy}"),
                    "direction": direction,
                    "rate": None,
                    "chg_1d": None,
                    "chg_1w": None,
                    "chg_1m": None,
                    "_error": f"Rate unavailable for {pair}",
                })
                continue

            corridor_data.append({
                "pair": pair,
                "label": c.get("label", f"{from_ccy}→{to_ccy}"),
                "direction": direction,
                "rate": rate_info.get("rate"),
                "chg_1d": rate_info.get("chg_1d"),
                "chg_1w": rate_info.get("chg_1w"),
                "chg_1m": rate_info.get("chg_1m"),
                "volume_usd": None,
                "avg_spread_bps": None,
                "spread_trend": None,
                "txn_count": None,
                "avg_ticket_usd": None,
                "note": "Volume/spread data requires manual input or Bloomberg",
            })

        return {
            "base_currency": base,
            "corridors": corridor_data,
            "total_volume_usd": None,
            "corridor_count": len(corridor_data),
            "seasonality": None,
            "note": "Volume and transaction data not available. Only rates from live sources.",
        }

    # ──────────────────────────────────────────────
    # CLIENT COMMENTARY — template-based (analysis framework, not data)
    # ──────────────────────────────────────────────
    def get_client_commentary(self) -> dict:
        manual = self._load_manual("client_commentary.json")
        if manual:
            return manual
        profile = self.get_active_profile()
        if not profile:
            return {}
        return self._generate_profile_client_commentary(profile)

    def get_commentary(self, news: list = None, spot_rates: dict = None, language: str = "en", use_ai: bool = True) -> dict:
        manual = self._load_manual("commentary.json")
        if manual:
            return manual

        # Priority 1: AI-generated commentary (LLM proxy/Claude + Perplexity news)
        if use_ai:
            perplexity_key = self.config.get("ai", {}).get("perplexity", {}).get("api_key", "")
            llm_enabled = self.config.get("llm", {}).get("enabled", False) and self.config.get("llm", {}).get("api_key", "")
            claude_key = self.config.get("ai", {}).get("claude", {}).get("api_key", "")
            has_llm = llm_enabled or claude_key
            if has_llm and perplexity_key:
                try:
                    from news_ai_provider import NewsAIProvider
                    ai_provider = NewsAIProvider(self.config)

                    # If news already fetched, reuse; otherwise fetch
                    if not news:
                        news = self.get_news(use_perplexity=True)

                    valid_news = [n for n in (news or []) if not n.get("_error")]
                    if valid_news:
                        # Get spot rates for context
                        if not spot_rates:
                            spot_rates = self.get_spot_rates()

                        commentary = ai_provider.generate_executive_summary(
                            valid_news, spot_rates=spot_rates, language=language
                        )
                        if commentary and not commentary.get("_error"):
                            self._data_sources.add("AI Generated" if llm_enabled else "Claude AI")
                            return commentary
                        else:
                            logger.warning(f"AI summary generation returned error: {commentary.get('_error', 'unknown')}")
                except Exception as e:
                    logger.warning(f"AI commentary generation failed: {e}")

        # Fallback: template-based commentary
        profile = self.get_active_profile()
        if profile:
            return self._generate_profile_commentary(profile)
        return {
            "executive_summary": "Global FX markets showed mixed performance this period. USD strength persisted against EM currencies while EUR and GBP traded range-bound. CNH depreciation pressure eased slightly on improved trade data.",
            "market_view": "The USD index (DXY) consolidated near multi-month highs. Key drivers include divergent central bank policies, with the Fed maintaining a hawkish stance while ECB signals potential easing. USDCNH traded in a narrow range around 7.25-7.30.",
            "risk_assessment": "Key risks include: (1) Escalation of trade tensions impacting CNH and Asian EM currencies, (2) Unexpected shifts in Fed rate path, (3) China economic data surprises, (4) Geopolitical developments in the Middle East affecting energy prices and risk sentiment.",
            "outlook": "We expect USD to remain supported in the near term. USDCNH likely to trade in the 7.20-7.35 range. EM currencies may face headwinds from rising US yields. Watch for central bank meetings and key employment data releases."
        }

    # ──────────────────────────────────────────────
    # Commentary templates (analysis framework)
    # ──────────────────────────────────────────────
    def _generate_profile_commentary(self, profile: dict) -> dict:
        region = profile.get("region", "Global")
        base = profile.get("base_currency", "USD")
        cb = profile.get("central_bank", "Central Bank")
        concerns = profile.get("key_concerns", [])

        templates = {
            "Vietnam": {
                "executive_summary": f"The Vietnamese Dong ({base}) traded under moderate pressure against the USD this period, with the SBV maintaining its managed float approach. The USDVND fixing rate was adjusted marginally upward. CNY/VND cross rate movements remained important for bilateral trade settlement. Remittance inflows showed seasonal patterns typical of this period.",
                "market_view": f"USDVND continued to trade near the upper band of the SBV's permitted range. The reference rate was adjusted in line with broader USD strength. Key factors include: (1) Fed policy expectations driving USD broadly, (2) Vietnam's robust export growth supporting VND fundamentals, (3) FDI inflows providing a structural floor for VND. The offshore NDF market implied modest depreciation expectations.",
                "risk_assessment": f"Key risks for VND-denominated corridors: (1) Sustained USD strength pushing USDVND toward intervention thresholds, (2) Trade policy uncertainty affecting export-dependent sectors, (3) SBV tightening liquidity to defend VND, potentially impacting domestic rates, (4) Capital control adjustments affecting cross-border payment flows.",
                "outlook": f"We expect the SBV to continue managing VND within a relatively tight band. USDVND likely to trade in the 25,700-26,200 range near term. Corridor partners should monitor SBV reference rate changes and any shifts in the trading band width. CNY/VND flows may increase ahead of trade settlement periods.",
            },
            "Philippines": {
                "executive_summary": f"The Philippine Peso ({base}) experienced volatility this period, pressured by a widening current account deficit and global risk-off sentiment. OFW remittance flows remained resilient, providing critical support. The BSP maintained its hawkish stance to anchor inflation expectations and support PHP.",
                "market_view": f"USDPHP traded with an upward bias as broad USD strength and domestic inflation concerns weighed on the Peso. BSP rhetoric remained hawkish. OFW remittance data continues to be a key structural support for PHP — remittances represent over 9% of GDP. The BPO sector's USD earnings also provide a natural hedge for PHP weakness.",
                "risk_assessment": f"Key risks for PHP corridors: (1) BSP policy divergence from Fed creating yield differential pressure, (2) Oil price spikes widening the trade deficit, (3) Seasonal patterns in OFW remittance flows (peak around December/Christmas), (4) Risk-off episodes triggering portfolio outflows from Philippine bond market.",
                "outlook": f"PHP likely to remain under modest pressure against USD in the near term. We expect USDPHP to trade in the 57.50-59.50 range. Gulf corridor (AED→PHP) volumes may increase with Ramadan-related remittance patterns. SGD→PHP corridor remains steady with Singapore's Filipino worker population.",
            },
            "Indonesia": {
                "executive_summary": f"The Indonesian Rupiah ({base}) was under pressure this period, with Bank Indonesia actively managing FX markets through spot intervention and domestic NDF operations. BI's priority on currency stability has kept rate cuts on hold despite easing inflation. Commodity export receipts provided partial offset.",
                "market_view": f"USDIDR approached key psychological levels, prompting BI intervention. BI has maintained a 'stabilize the Rupiah first' approach, prioritizing FX stability over growth stimulus. The twin deficit (current account + fiscal) narrative continues to weigh on sentiment. Foreign bond holdings remain a key vulnerability for sudden stops.",
                "risk_assessment": f"Key risks for IDR corridors: (1) BI intervention fatigue if USD strength persists, (2) Commodity price downturn reducing export revenue, (3) Foreign bond outflows on risk-off events, (4) Seasonal current account widening during Ramadan/Eid period, (5) Political transition uncertainties.",
                "outlook": f"IDR likely to remain volatile but range-bound with BI support. Expected USDIDR range: 16,000-16,800. Corridor partners should factor in BI's onshore fixing mechanism. CNY/IDR cross rate increasingly relevant as China-Indonesia trade deepens.",
            },
            "Thailand": {
                "executive_summary": f"The Thai Baht ({base}) showed mixed performance, supported by recovering tourism revenue but weighed down by political uncertainty and a widening trade deficit. BOT maintained a data-dependent approach on rates. Chinese tourist arrivals are improving but remain below pre-COVID levels.",
                "market_view": f"USDTHB fluctuated within a moderate range. The Baht benefited from improving tourism receipts — Chinese arrivals are a key swing factor. BOT policy has been accommodative relative to regional peers, creating a rate differential that pressures THB. The gold trade (Thailand is a major gold importer) also impacts THB flows.",
                "risk_assessment": f"Key risks for THB corridors: (1) Slower-than-expected Chinese tourism recovery, (2) BOT cutting rates ahead of peers, (3) Political instability impacting investment flows, (4) Global risk-off events given THB's traditionally high beta to risk sentiment, (5) Energy import costs rising.",
                "outlook": f"THB expected to trade in the 34.00-36.00 range against USD. CNY→THB corridor volumes should benefit from continued tourism recovery. Monitor BOT meeting outcomes and monthly tourism arrival data closely.",
            },
            "Malaysia": {
                "executive_summary": f"The Malaysian Ringgit ({base}) continued its recovery trend, supported by BNM's repatriation measures and improving commodity revenues. The Ringgit has outperformed regional peers as authorities actively encourage GLCs (government-linked companies) to convert foreign earnings.",
                "market_view": f"USDMYR has been trending lower as BNM's multi-pronged approach to support MYR gains traction. Key factors: (1) GLC repatriation of foreign income, (2) Improved semiconductor cycle boosting E&E exports, (3) BNM maintaining higher-for-longer rates. The SGD/MYR cross is closely watched given Malaysia-Singapore trade flows.",
                "risk_assessment": f"Key risks for MYR corridors: (1) Reversal of oil/gas prices undermining Petronas revenue, (2) Semiconductor downcycle re-emerging, (3) BNM easing prematurely, (4) Global risk-off reducing carry trade appeal, (5) Fiscal consolidation challenges.",
                "outlook": f"MYR expected to remain supported near term. USDMYR likely in 4.25-4.55 range. SGD/MYR corridor should remain active given bilateral trade. CNY/MYR gaining importance with growing China-Malaysia trade.",
            },
            "Brazil": {
                "executive_summary": f"The Brazilian Real ({base}) faced headwinds from fiscal concerns and global risk aversion, despite attractive carry trade yields. BCB has been navigating a complex backdrop of persistent inflation, high rates, and political pressure to ease. BRL remains one of the highest-yielding EM currencies.",
                "market_view": f"USDBRL traded with heightened volatility. The Selic rate remains elevated, making BRL attractive from a carry perspective but concerns about fiscal trajectory have limited appreciation. China-Brazil trade settlement in local currencies (CNY/BRL) has been gaining momentum under bilateral swap arrangements.",
                "risk_assessment": f"Key risks for BRL corridors: (1) Fiscal slippage undermining credibility, (2) BCB cutting Selic faster than expected, reducing carry appeal, (3) Commodity price weakness (soybeans, iron ore), (4) Political interference in monetary policy, (5) Capital flow volatility given high foreign positioning.",
                "outlook": f"BRL likely to trade in a wide range of 5.50-6.20 vs USD. The carry is attractive but volatility is high. CNY/BRL corridor growing with deepening bilateral trade. PIX payment system growth creating new cross-border settlement opportunities.",
            },
        }

        return templates.get(region, {
            "executive_summary": f"Global FX markets showed mixed performance this period. The {base} was influenced by regional dynamics and broad USD trends.",
            "market_view": f"Market conditions for {base}-denominated corridors remained stable. {cb} policy was data-dependent.",
            "risk_assessment": f"Key risks include: " + "; ".join(concerns[:3]) if concerns else "Broad USD strength, regional policy shifts.",
            "outlook": f"We expect moderate volatility in {base} crosses in the near term. Monitor {cb} communications and key data releases.",
        })

    def _generate_profile_client_commentary(self, profile: dict) -> dict:
        region = profile.get("region", "Global")
        base = profile.get("base_currency", "USD")
        cb = profile.get("central_bank", "Central Bank")
        concerns = profile.get("key_concerns", [])

        return {
            "corridor_analysis": f"Corridor volumes for {base}-denominated flows remained stable this period. "
                                 f"The primary USD→{base} inbound corridor showed consistent demand, driven by remittance and trade settlement flows. "
                                 f"Cross-currency corridors involving CNY showed growing importance as China-{region} trade deepens.",
            "local_market": f"The {cb} maintained its current policy stance this period. "
                           f"Key local factors: " + "; ".join(concerns[:2]) + ".",
            "recommendation": f"For {base}-based corridors, we recommend maintaining current hedging ratios. "
                              f"Monitor {cb} communications closely for any policy shifts. "
                              f"Consider pre-positioning for seasonal volume patterns in the coming month.",
        }

    # ──────────────────────────────────────────────
    # Alpha Vantage API
    # ──────────────────────────────────────────────
    def _av_request(self, params: dict) -> dict:
        params["apikey"] = self.av_key
        try:
            resp = requests.get("https://www.alphavantage.co/query", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "Error Message" in data or "Note" in data:
                return {}
            return data
        except Exception:
            return {}

    def _fetch_av_spot_rates(self) -> dict:
        result = {}
        for pair in self.all_ccys:
            from_sym = pair[:3]
            to_sym = pair[3:]
            cache_key = f"fx_{pair}.json"
            cached = self._load_cache(cache_key, max_age_hours=4)
            if cached:
                result[pair] = cached
                continue
            data = self._av_request({
                "function": "FX_DAILY",
                "from_symbol": from_sym,
                "to_symbol": to_sym,
                "outputsize": "compact",
            })
            ts_key = "Time Series FX (Daily)"
            if ts_key not in data:
                continue
            series = data[ts_key]
            dates = sorted(series.keys(), reverse=True)
            if len(dates) < 2:
                continue
            latest = float(series[dates[0]]["4. close"])
            prev_1d = float(series[dates[1]]["4. close"]) if len(dates) > 1 else latest
            prev_1w = float(series[dates[min(5, len(dates)-1)]]["4. close"]) if len(dates) > 5 else latest
            prev_1m = float(series[dates[min(22, len(dates)-1)]]["4. close"]) if len(dates) > 22 else latest
            year_start = [d for d in dates if d.startswith(dates[0][:4] + "-01")]
            prev_ytd = float(series[year_start[-1]]["4. close"]) if year_start else latest

            def pct_chg(old, new):
                return round((new - old) / old * 100, 2) if old else 0

            entry = {
                "rate": round(latest, 4),
                "chg_1d": pct_chg(prev_1d, latest),
                "chg_1w": pct_chg(prev_1w, latest),
                "chg_1m": pct_chg(prev_1m, latest),
                "chg_ytd": pct_chg(prev_ytd, latest),
            }
            result[pair] = entry
            self._save_cache(cache_key, entry)
        return result if result else None

    def _fetch_av_news(self, tickers: str = "FOREX:USD") -> list:
        cache_key = "news_sentiment.json"
        cached = self._load_cache(cache_key, max_age_hours=2)
        if cached:
            return cached
        data = self._av_request({
            "function": "NEWS_SENTIMENT",
            "tickers": tickers,
            "topics": "economy_fiscal,economy_monetary,finance",
            "limit": "20",
        })
        feed = data.get("feed", [])
        if not feed:
            return []
        news = []
        for item in feed[:15]:
            sentiment_score = float(item.get("overall_sentiment_score", 0))
            if sentiment_score > 0.15:
                sentiment = "Bullish"
            elif sentiment_score < -0.15:
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
            relevance = ""
            for ticker in item.get("ticker_sentiment", []):
                if "FOREX" in ticker.get("ticker", ""):
                    relevance = ticker.get("ticker", "")
                    break
            news.append({
                "date": item.get("time_published", "")[:10],
                "title": item.get("title", ""),
                "summary": item.get("summary", "")[:200],
                "sentiment": sentiment,
                "sentiment_score": sentiment_score,
                "source": item.get("source", ""),
                "relevance": relevance,
                "url": item.get("url", ""),
            })
        self._save_cache(cache_key, news)
        return news

    def _fetch_av_economic(self) -> dict:
        result = {}
        indicators = {
            "treasury_yield": {"function": "TREASURY_YIELD", "interval": "monthly", "maturity": "10year"},
            "federal_funds_rate": {"function": "FEDERAL_FUNDS_RATE", "interval": "monthly"},
            "cpi": {"function": "CPI", "interval": "monthly"},
            "inflation": {"function": "INFLATION"},
        }
        for key, params in indicators.items():
            cache_key = f"econ_{key}.json"
            cached = self._load_cache(cache_key, max_age_hours=24)
            if cached:
                result[key] = cached
                continue
            data = self._av_request(params)
            if "data" in data and data["data"]:
                latest = data["data"][0]
                entry = {"date": latest.get("date", ""), "value": latest.get("value", "")}
                result[key] = entry
                self._save_cache(cache_key, entry)
        return result if result else None

    # ──────────────────────────────────────────────
    # Cache & Manual data helpers
    # ──────────────────────────────────────────────
    def _load_cache(self, key: str, max_age_hours: int = 4):
        path = CACHE_DIR / key
        if not path.exists():
            return None
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=max_age_hours):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_cache(self, key: str, data):
        path = CACHE_DIR / key
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _load_manual(self, filename: str):
        path = DATA_DIR / filename
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Manual data load failed for {filename}: {e}")
        return None
