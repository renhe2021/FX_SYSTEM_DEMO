# -*- coding: utf-8 -*-
"""
Client Portal — Data Model & JSON File Storage Layer
=====================================================
Manages FX client profiles with full CRUD operations.
Storage: JSON files in data/clients/ directory.
Backward-compatible with legacy config.yaml profiles.
"""
import json
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from copy import deepcopy

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data" / "clients"


# ──────────────────────────────────────────────
# Enums / Allowed values for validation
# ──────────────────────────────────────────────
VALID_CLIENT_TYPES = [
    "PSP", "银行", "企业", "金融科技", "电商",
    "汇款", "游戏", "旅游", "SaaS/科技", "交易", "加密货币", "其他"
]

VALID_TIERS = ["一级", "二级", "三级", "潜在客户"]

VALID_STATUS = ["活跃", "入驻中", "停用", "流失"]

VALID_REGIONS = [
    "东南亚", "东亚", "南亚", "拉丁美洲",
    "中东与非洲", "欧洲", "北美", "全球"
]

VALID_INDUSTRIES = [
    "支付/PSP", "银行", "电商", "汇款/转账",
    "游戏", "旅游", "SaaS/科技", "交易", "加密货币", "其他"
]

VALID_HEDGING_POLICIES = ["不对冲", "部分对冲", "全额对冲", "动态对冲"]
VALID_PRICING_MODELS = ["加价", "点差", "佣金", "混合"]
VALID_RISK_APPETITES = ["保守", "适中", "激进"]
VALID_REPORT_FREQUENCIES = ["每日", "每周", "双周", "每月", "按需"]
VALID_REPORT_LANGUAGES = ["en", "zh", "vi", "th", "id", "pt"]
VALID_REPORT_FORMATS = ["HTML", "PDF", "两者"]
VALID_CORRIDOR_DIRECTIONS = ["inbound", "outbound", "both"]
VALID_CORRIDOR_PRIORITIES = ["Primary", "Secondary", "Occasional"]
VALID_KYC_STATUS = ["待审核", "进行中", "已验证", "已过期", "已拒绝"]
VALID_AML_RISK = ["低", "中", "高"]
VALID_SANCTIONS = ["通过", "标记", "待复审"]
VALID_ACCESS_LEVELS = ["Signer", "Trader", "Viewer", "Admin"]


# ──────────────────────────────────────────────
# Country → Region mapping
# ──────────────────────────────────────────────
COUNTRY_REGION_MAP = {
    "Vietnam": "东南亚", "Philippines": "东南亚",
    "Indonesia": "东南亚", "Thailand": "东南亚",
    "Malaysia": "东南亚", "Singapore": "东南亚",
    "Myanmar": "东南亚", "Cambodia": "东南亚",
    "China": "东亚", "Hong Kong": "东亚",
    "Japan": "东亚", "South Korea": "东亚", "Taiwan": "东亚",
    "India": "南亚", "Bangladesh": "南亚",
    "Pakistan": "南亚", "Sri Lanka": "南亚",
    "Brazil": "拉丁美洲", "Mexico": "拉丁美洲",
    "Argentina": "拉丁美洲", "Colombia": "拉丁美洲",
    "UAE": "中东与非洲", "Saudi Arabia": "中东与非洲",
    "Nigeria": "中东与非洲", "South Africa": "中东与非洲",
    "UK": "欧洲", "Germany": "欧洲", "France": "欧洲", "Turkey": "欧洲",
    "US": "北美", "Canada": "北美",
    "Global": "全球",
}

COUNTRY_CODE_MAP = {
    "Vietnam": "VN", "Philippines": "PH", "Indonesia": "ID",
    "Thailand": "TH", "Malaysia": "MY", "Singapore": "SG",
    "Myanmar": "MM", "Cambodia": "KH",
    "China": "CN", "Hong Kong": "HK", "Japan": "JP",
    "South Korea": "KR", "Taiwan": "TW",
    "India": "IN", "Bangladesh": "BD", "Pakistan": "PK", "Sri Lanka": "LK",
    "Brazil": "BR", "Mexico": "MX", "Argentina": "AR", "Colombia": "CO",
    "UAE": "AE", "Saudi Arabia": "SA", "Nigeria": "NG", "South Africa": "ZA",
    "UK": "GB", "Germany": "DE", "France": "FR", "Turkey": "TR",
    "US": "US", "Canada": "CA", "Global": "GL",
}

REGION_FLAGS = {
    "Vietnam": "\U0001f1fb\U0001f1f3", "Philippines": "\U0001f1f5\U0001f1ed",
    "Indonesia": "\U0001f1ee\U0001f1e9", "Thailand": "\U0001f1f9\U0001f1ed",
    "Malaysia": "\U0001f1f2\U0001f1fe", "Singapore": "\U0001f1f8\U0001f1ec",
    "Brazil": "\U0001f1e7\U0001f1f7", "Mexico": "\U0001f1f2\U0001f1fd",
    "India": "\U0001f1ee\U0001f1f3", "Japan": "\U0001f1ef\U0001f1f5",
    "South Korea": "\U0001f1f0\U0001f1f7", "China": "\U0001f1e8\U0001f1f3",
    "Hong Kong": "\U0001f1ed\U0001f1f0", "Taiwan": "\U0001f1f9\U0001f1fc",
    "UAE": "\U0001f1e6\U0001f1ea", "UK": "\U0001f1ec\U0001f1e7",
    "Global": "\U0001f30d",
}


def _generate_client_id(country: str) -> str:
    """Generate a unique client ID like CLT-VN-001."""
    code = COUNTRY_CODE_MAP.get(country, "XX")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Find next sequence number
    existing = list(DATA_DIR.glob(f"CLT-{code}-*.json"))
    if existing:
        nums = []
        for f in existing:
            match = re.search(r"CLT-\w+-(\d+)", f.stem)
            if match:
                nums.append(int(match.group(1)))
        next_num = max(nums) + 1 if nums else 1
    else:
        next_num = 1

    return f"CLT-{code}-{next_num:03d}"


def _default_client() -> dict:
    """Return a blank client template with all fields."""
    now = datetime.now().isoformat()
    return {
        # A. Basic Info
        "client_id": "",
        "name": "",
        "short_name": "",
        "legal_entity": "",
        "client_type": "PSP",
        "tier": "二级",
        "status": "活跃",
        "onboarding_date": "",
        "logo_url": "",

        # B. KYC / AML Compliance
        "kyc_status": "待审核",
        "kyc_expiry_date": "",
        "aml_risk_rating": "低",
        "pep_status": False,
        "sanctions_screening": "通过",
        "ubo_structure": "",
        "tax_id": "",
        "incorporation_country": "",
        "incorporation_date": "",
        "compliance_notes": "",

        # C. Region & Regulatory
        "region": "东南亚",
        "country": "",
        "operating_countries": [],
        "timezone": "",
        "local_regulator": "",
        "license_type": "",
        "central_bank": "",
        "fx_purpose_codes": [],
        "local_tax_requirements": "",
        "regulatory_notes": "",

        # D. Business Overview
        "industry": "支付/PSP",
        "business_model": "",
        "main_products": [],
        "monthly_volume_usd": 0,
        "volume_tier": "",
        "annual_revenue_usd": 0,
        "employee_count": "",
        "website": "",

        # E. FX Requirements
        "base_currency": "USD",
        "settlement_currencies": [],
        "focus_pairs": [],
        "fx_products_used": [],
        "product_complexity": "",
        "tenor_preferences": [],
        "hedging_policy": "No Hedge",
        "hedging_ratio": "",
        "hedging_horizon": "",
        "pricing_model": "Markup",
        "current_markup_bps": 0,
        "volume_based_tiering": False,
        "benchmark_rate_source": "",
        "preferred_liquidity_providers": [],
        "preferred_bank_routing": "",
        "settlement_cycle": "T+2",
        "preferred_execution_window": "",

        # F. Corridor Configuration
        "corridors": [],

        # G. Credit & Limits
        "credit_line_usd": 0,
        "credit_line_utilized_pct": 0,
        "credit_line_expiry": "",
        "net_exposure_limit_usd": 0,
        "unhedged_exposure_alert_pct": 0,
        "collateral_type": "",
        "collateral_amount_usd": 0,
        "payment_terms": "",

        # H. Risk Preferences
        "risk_appetite": "Moderate",
        "max_single_trade_usd": 0,
        "daily_limit_usd": 0,
        "stop_loss_threshold": "",
        "var_limit": "",
        "key_concerns": [],
        "sensitivity_factors": [],

        # I. Report Preferences (→ flows into Reporting Settings UI)
        "report_frequency": "Weekly",
        "report_language": "en",
        "report_format": "HTML",
        "report_delivery": "Email",
        "sections_enabled": {
            "executive_summary": True,
            "client_corridor": True,
            "market_overview": True,
            "volatility_analysis": True,
            "flow_analysis": True,
            "macro_outlook": True,
            "risk_monitor": True,
        },
        "include_charts": True,
        "include_corridor_analysis": True,
        "include_cost_analysis": False,
        "custom_benchmarks": [],
        "news_topics": [],
        "alert_thresholds": {},

        # J. Contacts
        "contacts": [],

        # K. Notes & Tags
        "tags": [],
        "internal_notes": "",
        "key_events": [],
        "relationship_manager": "",
        "last_review_date": "",
        "next_review_date": "",
        "created_at": now,
        "updated_at": now,
    }


class ClientStore:
    """JSON file-based client data store with full CRUD operations."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_index()

    def _ensure_index(self):
        """Create index file if it doesn't exist."""
        idx_path = self.data_dir / "_index.json"
        if not idx_path.exists():
            self._save_index({"version": "1.0", "clients": []})

    def _load_index(self) -> dict:
        idx_path = self.data_dir / "_index.json"
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"version": "1.0", "clients": []}

    def _save_index(self, index: dict):
        idx_path = self.data_dir / "_index.json"
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _update_index_entry(self, client: dict):
        """Add or update a client's entry in the index."""
        index = self._load_index()
        clients = index.get("clients", [])

        # Remove existing entry if present
        clients = [c for c in clients if c["client_id"] != client["client_id"]]

        # Add new entry
        clients.append({
            "client_id": client["client_id"],
            "name": client.get("name", ""),
            "short_name": client.get("short_name", ""),
            "region": client.get("region", ""),
            "country": client.get("country", ""),
            "client_type": client.get("client_type", ""),
            "tier": client.get("tier", ""),
            "status": client.get("status", ""),
            "base_currency": client.get("base_currency", ""),
            "updated_at": client.get("updated_at", ""),
        })

        index["clients"] = clients
        self._save_index(index)

    def _remove_from_index(self, client_id: str):
        """Remove a client from the index."""
        index = self._load_index()
        index["clients"] = [c for c in index.get("clients", []) if c["client_id"] != client_id]
        self._save_index(index)

    # ──────────────────────────────────────────────
    # CRUD Operations
    # ──────────────────────────────────────────────

    def list_clients(self, region: str = None, client_type: str = None,
                     tier: str = None, status: str = None, search: str = None) -> list:
        """List all clients, optionally filtered."""
        index = self._load_index()
        clients = index.get("clients", [])

        if region:
            clients = [c for c in clients if c.get("region") == region]
        if client_type:
            clients = [c for c in clients if c.get("client_type") == client_type]
        if tier:
            clients = [c for c in clients if c.get("tier") == tier]
        if status:
            clients = [c for c in clients if c.get("status") == status]
        if search:
            q = search.lower()
            clients = [c for c in clients if (
                q in c.get("name", "").lower() or
                q in c.get("short_name", "").lower() or
                q in c.get("country", "").lower() or
                q in c.get("base_currency", "").lower()
            )]

        # Add flag emoji for display
        for c in clients:
            c["flag"] = REGION_FLAGS.get(c.get("country", ""), "")

        return clients

    def get_client(self, client_id: str) -> dict:
        """Get a single client's full profile."""
        path = self.data_dir / f"{client_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                client = json.load(f)
            client["flag"] = REGION_FLAGS.get(client.get("country", ""), "")
            return client
        except Exception as e:
            logger.error(f"Failed to load client {client_id}: {e}")
            return None

    def create_client(self, data: dict) -> dict:
        """Create a new client. Returns the created client with generated ID."""
        client = _default_client()
        client.update(data)

        # Generate ID if not provided
        if not client.get("client_id"):
            client["client_id"] = _generate_client_id(client.get("country", "全球"))

        # Auto-fill region from country
        if client.get("country") and not client.get("region"):
            client["region"] = COUNTRY_REGION_MAP.get(client["country"], "全球")

        now = datetime.now().isoformat()
        client["created_at"] = now
        client["updated_at"] = now

        # Save
        self._save_client(client)
        self._update_index_entry(client)

        return client

    def update_client(self, client_id: str, data: dict) -> dict:
        """Update an existing client. Returns updated client."""
        existing = self.get_client(client_id)
        if not existing:
            return None

        # Remove display-only field
        existing.pop("flag", None)

        # Merge updates
        existing.update(data)
        existing["client_id"] = client_id  # Prevent ID overwrite
        existing["updated_at"] = datetime.now().isoformat()

        # Auto-update region if country changed
        if "country" in data:
            existing["region"] = COUNTRY_REGION_MAP.get(data["country"], existing.get("region", "全球"))

        self._save_client(existing)
        self._update_index_entry(existing)

        return existing

    def delete_client(self, client_id: str) -> bool:
        """Delete a client."""
        path = self.data_dir / f"{client_id}.json"
        if path.exists():
            path.unlink()
            self._remove_from_index(client_id)
            return True
        return False

    def _save_client(self, client: dict):
        """Save client data to JSON file."""
        # Remove transient display fields before saving
        save_data = {k: v for k, v in client.items() if k not in ("flag",)}
        path = self.data_dir / f"{client['client_id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

    # ──────────────────────────────────────────────
    # Legacy compatibility — for existing report system
    # ──────────────────────────────────────────────

    def get_as_legacy_profile(self, client_id: str) -> dict:
        """Convert a client to the legacy config.yaml profile format.
        This is the key bridge — maps new 80+ field model to the fields
        that data_provider.py, news_ai_provider.py, and report_generator.py expect.

        Legacy profile fields used downstream:
        - name, short_name, region, base_currency  → cover page, commentary, AI prompts
        - corridors [{from, to, direction, label}]  → corridor data, charts
        - focus_pairs [str]                          → spot table, vol chart, heatmap
        - key_concerns [str]                         → commentary, key concerns list
        - central_bank                               → commentary, cover page
        - key_events [str]                           → risk monitor
        """
        client = self.get_client(client_id)
        if not client:
            return None

        # Convert corridors to legacy format
        legacy_corridors = []
        for c in client.get("corridors", []):
            legacy_corridors.append({
                "from": c.get("from_currency", c.get("from", "")),
                "to": c.get("to_currency", c.get("to", "")),
                "direction": c.get("direction", "inbound"),
                "label": c.get("label", ""),
            })

        return {
            "name": client.get("name", ""),
            "short_name": client.get("short_name", ""),
            "region": client.get("country", client.get("region", "全球")),
            "base_currency": client.get("base_currency", "USD"),
            "corridors": legacy_corridors,
            "focus_pairs": client.get("focus_pairs", []),
            "key_concerns": client.get("key_concerns", []),
            "central_bank": client.get("central_bank", ""),
            "key_events": client.get("key_events", []),
            # Extended fields for enhanced reports
            "_client_id": client.get("client_id", ""),
            "_tier": client.get("tier", ""),
            "_client_type": client.get("client_type", ""),
            "_industry": client.get("industry", ""),
            "_hedging_policy": client.get("hedging_policy", ""),
            "_risk_appetite": client.get("risk_appetite", ""),
            "_report_language": client.get("report_language", "en"),
            "_report_format": client.get("report_format", "HTML"),
            "_sections_enabled": client.get("sections_enabled", {}),
        }

    def get_all_as_legacy_profiles(self) -> dict:
        """Return all clients in the legacy {key: profile} dict format.
        Compatible with CONFIG.get('client_profiles', {})."""
        result = {}
        for entry in self.list_clients():
            client_id = entry["client_id"]
            profile = self.get_as_legacy_profile(client_id)
            if profile:
                # Use client_id as key (replacing spaces/dashes for compatibility)
                key = client_id.lower().replace("-", "_")
                result[key] = profile
        return result

    def get_report_preferences(self, client_id: str) -> dict:
        """Get report preferences for a client — used to populate Reporting Settings UI.
        This is the key output that flows from Client Portal → Reporting Settings."""
        client = self.get_client(client_id)
        if not client:
            return {}

        return {
            "report_frequency": client.get("report_frequency", "Weekly"),
            "report_language": client.get("report_language", "en"),
            "report_format": client.get("report_format", "HTML"),
            "sections_enabled": client.get("sections_enabled", {}),
            "include_charts": client.get("include_charts", True),
            "include_corridor_analysis": client.get("include_corridor_analysis", True),
            "include_cost_analysis": client.get("include_cost_analysis", False),
            "custom_benchmarks": client.get("custom_benchmarks", []),
            "news_topics": client.get("news_topics", []),
            "alert_thresholds": client.get("alert_thresholds", {}),
            # Additional context from profile for populating UI
            "base_currency": client.get("base_currency", "USD"),
            "focus_pairs": client.get("focus_pairs", []),
            "central_bank": client.get("central_bank", ""),
            "key_concerns": client.get("key_concerns", []),
        }

    # ──────────────────────────────────────────────
    # Seed data — migrate from config.yaml
    # ──────────────────────────────────────────────

    def seed_from_config(self, config: dict):
        """Migrate existing config.yaml client_profiles to Client Portal JSON files.
        Only creates clients that don't already exist (exact short_name match)."""
        profiles = config.get("client_profiles", {})
        if not profiles:
            return

        # Build set of existing short_names by scanning all JSON files (exact match)
        existing_short_names = set()
        for f in self.data_dir.glob("CLT-*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                sn = data.get("short_name", "")
                if sn:
                    existing_short_names.add(sn)
            except Exception:
                continue

        created = 0
        for key, profile in profiles.items():
            country = profile.get("region", "Global")
            short_name = profile.get("short_name", key)
            # Exact match — skip if this short_name already exists
            if short_name in existing_short_names:
                logger.debug(f"Seed skip (exists): {short_name}")
                continue

            # Map legacy profile to new data model
            client_data = {
                "name": profile.get("name", key),
                "short_name": profile.get("short_name", key),
                "client_type": "PSP" if "psp" in key.lower() else "其他",
                "tier": "二级",
                "status": "活跃",
                "region": COUNTRY_REGION_MAP.get(country, "全球"),
                "country": country,
                "base_currency": profile.get("base_currency", "USD"),
                "industry": "支付/PSP" if "psp" in key.lower() else "其他",
                "central_bank": profile.get("central_bank", ""),
                "focus_pairs": profile.get("focus_pairs", []),
                "key_concerns": profile.get("key_concerns", []),
                "key_events": profile.get("key_events", []),
                "corridors": [],
            }

            # Convert corridors
            for c in profile.get("corridors", []):
                client_data["corridors"].append({
                    "from_currency": c.get("from", ""),
                    "to_currency": c.get("to", ""),
                    "direction": c.get("direction", "inbound"),
                    "label": c.get("label", ""),
                    "avg_ticket_size_usd": 0,
                    "monthly_volume_usd": 0,
                    "priority": "Primary",
                    "purpose": "",
                    "purpose_code": "",
                })

            self.create_client(client_data)
            created += 1
            logger.info(f"Seeded client: {client_data['short_name']} ({client_data['client_id'] if 'client_id' in client_data else 'new'})")

        if created:
            logger.info(f"Seeded {created} clients from config.yaml")

    # ──────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return summary statistics for the portal dashboard."""
        clients = self.list_clients()
        by_region = {}
        by_type = {}
        by_tier = {}
        by_status = {}

        for c in clients:
            r = c.get("region", "未知")
            by_region[r] = by_region.get(r, 0) + 1
            t = c.get("client_type", "未知")
            by_type[t] = by_type.get(t, 0) + 1
            tier = c.get("tier", "未知")
            by_tier[tier] = by_tier.get(tier, 0) + 1
            s = c.get("status", "未知")
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "total": len(clients),
            "by_region": by_region,
            "by_type": by_type,
            "by_tier": by_tier,
            "by_status": by_status,
        }

    # ──────────────────────────────────────────────
    # Enum / dropdown options for the UI
    # ──────────────────────────────────────────────

    @staticmethod
    def get_field_options() -> dict:
        """Return all enum/dropdown options for the frontend form builder."""
        return {
            "client_types": VALID_CLIENT_TYPES,
            "tiers": VALID_TIERS,
            "statuses": VALID_STATUS,
            "regions": VALID_REGIONS,
            "industries": VALID_INDUSTRIES,
            "hedging_policies": VALID_HEDGING_POLICIES,
            "pricing_models": VALID_PRICING_MODELS,
            "risk_appetites": VALID_RISK_APPETITES,
            "report_frequencies": VALID_REPORT_FREQUENCIES,
            "report_languages": VALID_REPORT_LANGUAGES,
            "report_formats": VALID_REPORT_FORMATS,
            "corridor_directions": VALID_CORRIDOR_DIRECTIONS,
            "corridor_priorities": VALID_CORRIDOR_PRIORITIES,
            "kyc_statuses": VALID_KYC_STATUS,
            "aml_risk_ratings": VALID_AML_RISK,
            "sanctions_statuses": VALID_SANCTIONS,
            "access_levels": VALID_ACCESS_LEVELS,
            "countries": list(COUNTRY_CODE_MAP.keys()),
            "country_flags": REGION_FLAGS,
        }
