# -*- coding: utf-8 -*-
"""
Bloomberg Data Provider — connects to Bloomberg Terminal via BLPAPI.
Fetches FX spot rates, implied volatility, and news headlines.
Requires: blpapi (pip install blpapi), Bloomberg Terminal running locally.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import blpapi — gracefully degrade if not available
try:
    import blpapi
    BLPAPI_AVAILABLE = True
except ImportError:
    BLPAPI_AVAILABLE = False
    logger.info("blpapi not available — Bloomberg features disabled")


class BloombergProvider:
    """
    Bloomberg Terminal data provider using BLPAPI.

    Usage:
        bbg = BloombergProvider()
        if bbg.connect():
            spots = bbg.get_fx_spot_rates(["USDVND", "USDPHP", "USDIDR"])
            vols = bbg.get_fx_vol_data(["USDVND", "USDPHP"])
            news = bbg.get_fx_news(topics=["VND", "PHP"])
            bbg.disconnect()
    """

    # Standard Bloomberg ticker format for FX
    FX_TICKER_MAP = {
        "USDCNH": "USDCNH Curncy",
        "EURUSD": "EURUSD Curncy",
        "GBPUSD": "GBPUSD Curncy",
        "USDJPY": "USDJPY Curncy",
        "AUDUSD": "AUDUSD Curncy",
        "USDVND": "USDVND Curncy",
        "USDPHP": "USDPHP Curncy",
        "USDIDR": "USDIDR Curncy",
        "USDTHB": "USDTHB Curncy",
        "USDMYR": "USDMYR Curncy",
        "USDSGD": "USDSGD Curncy",
        "USDHKD": "USDHKD Curncy",
        "USDKRW": "USDKRW Curncy",
        "USDTWD": "USDTWD Curncy",
        "USDINR": "USDINR Curncy",
        "USDMXN": "USDMXN Curncy",
        "USDBRL": "USDBRL Curncy",
        # Cross rates
        "CNHVND": "CNHVND Curncy",
        "CNHPHP": "CNHPHP Curncy",
        "CNHIDR": "CNHIDR Curncy",
        "CNHTHB": "CNHTHB Curncy",
        "CNHMYR": "CNHMYR Curncy",
        "SGDPHP": "SGDPHP Curncy",
        "SGDIDR": "SGDIDR Curncy",
        "SGDMYR": "SGDMYR Curncy",
    }

    # Vol tickers — Bloomberg implied vol convention
    FX_VOL_TENORS = {
        "vol_1w": "1W",
        "vol_1m": "1M",
        "vol_3m": "3M",
        "vol_6m": "6M",
        "vol_1y": "12M",
    }

    def __init__(self, host: str = "localhost", port: int = 8194):
        self.host = host
        self.port = port
        self.session = None
        self.connected = False

    @staticmethod
    def is_available() -> bool:
        """Check if blpapi library is installed."""
        return BLPAPI_AVAILABLE

    def connect(self) -> bool:
        """Establish connection to Bloomberg Terminal."""
        if not BLPAPI_AVAILABLE:
            logger.warning("blpapi not installed. Install with: pip install blpapi")
            return False

        try:
            session_options = blpapi.SessionOptions()
            session_options.setServerHost(self.host)
            session_options.setServerPort(self.port)

            self.session = blpapi.Session(session_options)
            if not self.session.start():
                logger.error("Failed to start Bloomberg session")
                return False

            if not self.session.openService("//blp/refdata"):
                logger.error("Failed to open //blp/refdata service")
                return False

            self.connected = True
            logger.info("Connected to Bloomberg Terminal")
            return True

        except Exception as e:
            logger.error(f"Bloomberg connection error: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Close Bloomberg session."""
        if self.session:
            try:
                self.session.stop()
            except Exception:
                pass
            self.session = None
            self.connected = False

    # ──────────────────────────────────────────────
    # FX Spot Rates
    # ──────────────────────────────────────────────
    def get_fx_spot_rates(self, pairs: List[str]) -> Dict:
        """
        Fetch current FX spot rates and changes from Bloomberg.

        Returns dict: { "USDVND": { rate, chg_1d, chg_1w, chg_1m, chg_ytd }, ... }
        """
        if not self.connected:
            return {}

        result = {}
        tickers = []
        pair_map = {}  # bloomberg_ticker -> our_pair

        for pair in pairs:
            bbg_ticker = self.FX_TICKER_MAP.get(pair, f"{pair} Curncy")
            tickers.append(bbg_ticker)
            pair_map[bbg_ticker] = pair

        if not tickers:
            return {}

        try:
            ref_service = self.session.getService("//blp/refdata")

            # Reference Data Request for current levels
            request = ref_service.createRequest("ReferenceDataRequest")
            for t in tickers:
                request.getElement("securities").appendValue(t)

            fields = [
                "PX_LAST",        # Current price
                "CHG_PCT_1D",     # 1-day % change
                "CHG_PCT_5D",     # 5-day (≈1 week) % change
                "CHG_PCT_1M",     # 1-month % change
                "CHG_PCT_YTD",    # Year-to-date % change
                "PX_HIGH",        # Day high
                "PX_LOW",         # Day low
            ]
            for f in fields:
                request.getElement("fields").appendValue(f)

            self.session.sendRequest(request)

            # Process response
            while True:
                event = self.session.nextEvent(5000)
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        for i in range(sec_data.numValues()):
                            sec = sec_data.getValueAsElement(i)
                            ticker = sec.getElementAsString("security")
                            our_pair = pair_map.get(ticker)
                            if not our_pair:
                                continue

                            field_data = sec.getElement("fieldData")
                            result[our_pair] = {
                                "rate": round(self._get_float(field_data, "PX_LAST"), 4),
                                "chg_1d": round(self._get_float(field_data, "CHG_PCT_1D"), 2),
                                "chg_1w": round(self._get_float(field_data, "CHG_PCT_5D"), 2),
                                "chg_1m": round(self._get_float(field_data, "CHG_PCT_1M"), 2),
                                "chg_ytd": round(self._get_float(field_data, "CHG_PCT_YTD"), 2),
                                "high": round(self._get_float(field_data, "PX_HIGH"), 4),
                                "low": round(self._get_float(field_data, "PX_LOW"), 4),
                                "source": "bloomberg",
                            }

                if event.eventType() == blpapi.Event.RESPONSE:
                    break

        except Exception as e:
            logger.error(f"Bloomberg spot rate error: {e}")

        return result

    # ──────────────────────────────────────────────
    # FX Implied Volatility
    # ──────────────────────────────────────────────
    def get_fx_vol_data(self, pairs: List[str]) -> Dict:
        """
        Fetch implied volatility across tenors from Bloomberg.

        Returns dict: { "USDVND": { vol_1w, vol_1m, vol_3m, vol_6m, vol_1y }, ... }
        """
        if not self.connected:
            return {}

        result = {}

        try:
            ref_service = self.session.getService("//blp/refdata")

            for pair in pairs:
                pair_vols = {}
                for vol_key, tenor in self.FX_VOL_TENORS.items():
                    # Bloomberg convention: e.g., "USDVND1MV Curncy" for 1M vol
                    vol_ticker = f"{pair}{tenor}V Curncy"

                    request = ref_service.createRequest("ReferenceDataRequest")
                    request.getElement("securities").appendValue(vol_ticker)
                    request.getElement("fields").appendValue("PX_LAST")

                    self.session.sendRequest(request)

                    while True:
                        event = self.session.nextEvent(5000)
                        for msg in event:
                            if msg.hasElement("securityData"):
                                sec_data = msg.getElement("securityData")
                                if sec_data.numValues() > 0:
                                    sec = sec_data.getValueAsElement(0)
                                    field_data = sec.getElement("fieldData")
                                    vol_val = self._get_float(field_data, "PX_LAST")
                                    if vol_val > 0:
                                        pair_vols[vol_key] = round(vol_val, 2)

                        if event.eventType() == blpapi.Event.RESPONSE:
                            break

                if pair_vols:
                    result[pair] = pair_vols

        except Exception as e:
            logger.error(f"Bloomberg vol data error: {e}")

        return result

    # ──────────────────────────────────────────────
    # FX News Headlines
    # ──────────────────────────────────────────────
    def get_fx_news(self, topics: List[str] = None, max_items: int = 15) -> List[Dict]:
        """
        Fetch FX-related news headlines from Bloomberg.

        Args:
            topics: list of currency codes to filter (e.g., ["VND", "PHP", "IDR"])
            max_items: max number of news items to return

        Returns list of dicts: [{ date, title, summary, sentiment, source, bbg: True }, ...]
        """
        if not self.connected:
            return []

        news = []

        try:
            # Use reference data to get latest news for FX tickers
            ref_service = self.session.getService("//blp/refdata")

            # Build list of relevant tickers to query news for
            query_tickers = []
            if topics:
                for t in topics:
                    for pair, bbg_ticker in self.FX_TICKER_MAP.items():
                        if t.upper() in pair.upper():
                            query_tickers.append(bbg_ticker)
                            break
            else:
                # Default: major FX pairs
                query_tickers = [
                    "EURUSD Curncy", "USDJPY Curncy", "USDCNH Curncy",
                    "DXY Curncy",
                ]

            # Get news via BDP (Bloomberg Data Point) — NEWS_STORY_COUNT field
            for ticker in query_tickers[:5]:
                request = ref_service.createRequest("ReferenceDataRequest")
                request.getElement("securities").appendValue(ticker)
                request.getElement("fields").appendValue("NEWS_STORY_COUNT_5D")
                request.getElement("fields").appendValue("LAST_NEWS_STR")
                request.getElement("fields").appendValue("LAST_NEWS_DT")

                self.session.sendRequest(request)

                while True:
                    event = self.session.nextEvent(5000)
                    for msg in event:
                        if msg.hasElement("securityData"):
                            sec_data = msg.getElement("securityData")
                            for i in range(sec_data.numValues()):
                                sec = sec_data.getValueAsElement(i)
                                field_data = sec.getElement("fieldData")

                                headline = self._get_string(field_data, "LAST_NEWS_STR")
                                news_date = self._get_string(field_data, "LAST_NEWS_DT")

                                if headline:
                                    # Extract pair name from ticker
                                    pair_name = ticker.replace(" Curncy", "")
                                    news.append({
                                        "date": news_date or datetime.now().strftime("%Y-%m-%d"),
                                        "title": headline,
                                        "summary": headline,
                                        "sentiment": self._infer_sentiment(headline),
                                        "sentiment_score": 0,
                                        "source": "Bloomberg",
                                        "relevance": f"FOREX:{pair_name}",
                                        "bbg": True,
                                    })

                    if event.eventType() == blpapi.Event.RESPONSE:
                        break

        except Exception as e:
            logger.error(f"Bloomberg news error: {e}")

        return news[:max_items]

    # ──────────────────────────────────────────────
    # Historical Data (for charts)
    # ──────────────────────────────────────────────
    def get_fx_historical(self, pair: str, days: int = 90) -> List[Dict]:
        """
        Fetch historical daily FX rates from Bloomberg.

        Returns list of dicts: [{ date, open, high, low, close }, ...]
        """
        if not self.connected:
            return []

        result = []
        bbg_ticker = self.FX_TICKER_MAP.get(pair, f"{pair} Curncy")

        try:
            ref_service = self.session.getService("//blp/refdata")
            request = ref_service.createRequest("HistoricalDataRequest")
            request.getElement("securities").appendValue(bbg_ticker)
            request.getElement("fields").appendValue("PX_OPEN")
            request.getElement("fields").appendValue("PX_HIGH")
            request.getElement("fields").appendValue("PX_LOW")
            request.getElement("fields").appendValue("PX_LAST")

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            request.set("startDate", start_date.strftime("%Y%m%d"))
            request.set("endDate", end_date.strftime("%Y%m%d"))
            request.set("periodicitySelection", "DAILY")

            self.session.sendRequest(request)

            while True:
                event = self.session.nextEvent(5000)
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        if sec_data.hasElement("fieldData"):
                            field_data_arr = sec_data.getElement("fieldData")
                            for i in range(field_data_arr.numValues()):
                                bar = field_data_arr.getValueAsElement(i)
                                result.append({
                                    "date": str(bar.getElementAsDatetime("date")),
                                    "open": self._get_float(bar, "PX_OPEN"),
                                    "high": self._get_float(bar, "PX_HIGH"),
                                    "low": self._get_float(bar, "PX_LOW"),
                                    "close": self._get_float(bar, "PX_LAST"),
                                })

                if event.eventType() == blpapi.Event.RESPONSE:
                    break

        except Exception as e:
            logger.error(f"Bloomberg historical data error: {e}")

        return result

    # ──────────────────────────────────────────────
    # Economic Calendar
    # ──────────────────────────────────────────────
    def get_economic_calendar(self, countries: List[str] = None, days_ahead: int = 14) -> List[Dict]:
        """
        Fetch upcoming economic events from Bloomberg ECO calendar.

        Args:
            countries: list of country codes (e.g., ["VN", "PH", "ID", "US"])
            days_ahead: number of days to look ahead
        """
        if not self.connected:
            return []

        events = []
        # Economic calendar via Bloomberg uses specific tickers
        # This is a simplified approach — full implementation would use BEQS
        eco_tickers = {
            "US": ["NFP TCH Index", "CPI YOY Index", "GDP CQOQ Index"],
            "VN": ["VNRGDPY Index", "VNCPIYOY Index"],
            "PH": ["PHGDPY Index", "PHCPIY Index"],
            "ID": ["IDGDPY Index", "IDCPI Index"],
            "TH": ["THGDPY Index", "THCPI Index"],
            "MY": ["MYGDPY Index", "MYCPI Index"],
            "BR": ["BZGDYOY Index", "BZPIIPCY Index"],
        }

        try:
            ref_service = self.session.getService("//blp/refdata")

            target_countries = countries or ["US", "VN", "PH", "ID"]
            for country in target_countries:
                for ticker in eco_tickers.get(country, []):
                    request = ref_service.createRequest("ReferenceDataRequest")
                    request.getElement("securities").appendValue(ticker)
                    request.getElement("fields").appendValue("ECO_RELEASE_DT")
                    request.getElement("fields").appendValue("LONG_COMP_NAME")

                    self.session.sendRequest(request)

                    while True:
                        event = self.session.nextEvent(5000)
                        for msg in event:
                            if msg.hasElement("securityData"):
                                sec_data = msg.getElement("securityData")
                                for i in range(sec_data.numValues()):
                                    sec = sec_data.getValueAsElement(i)
                                    fd = sec.getElement("fieldData")
                                    release_date = self._get_string(fd, "ECO_RELEASE_DT")
                                    name = self._get_string(fd, "LONG_COMP_NAME")
                                    if release_date and name:
                                        events.append({
                                            "date": release_date,
                                            "event": name,
                                            "impact": "High" if "GDP" in name or "CPI" in name else "Medium",
                                            "currency": country,
                                            "source": "bloomberg",
                                        })

                        if event.eventType() == blpapi.Event.RESPONSE:
                            break

        except Exception as e:
            logger.error(f"Bloomberg eco calendar error: {e}")

        events.sort(key=lambda x: x.get("date", ""))
        return events

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────
    @staticmethod
    def _get_float(element, field: str, default: float = 0.0) -> float:
        try:
            if element.hasElement(field):
                return float(element.getElementAsFloat(field))
        except Exception:
            pass
        return default

    @staticmethod
    def _get_string(element, field: str, default: str = "") -> str:
        try:
            if element.hasElement(field):
                return str(element.getElementAsString(field))
        except Exception:
            pass
        return default

    @staticmethod
    def _infer_sentiment(headline: str) -> str:
        """Simple keyword-based sentiment inference for news headlines."""
        headline_lower = headline.lower()
        bullish_keywords = [
            "surge", "rally", "gain", "rise", "strengthen", "support",
            "upgrade", "bullish", "recover", "boost", "improve", "advance",
        ]
        bearish_keywords = [
            "fall", "drop", "decline", "weak", "plunge", "sell",
            "downgrade", "bearish", "crash", "cut", "concern", "risk",
            "pressure", "slump", "retreat",
        ]

        bull_score = sum(1 for kw in bullish_keywords if kw in headline_lower)
        bear_score = sum(1 for kw in bearish_keywords if kw in headline_lower)

        if bull_score > bear_score:
            return "Bullish"
        elif bear_score > bull_score:
            return "Bearish"
        return "Neutral"
