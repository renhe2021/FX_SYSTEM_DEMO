# FX Client Portal — 设计方案

> **Last Updated**: 2026-03-05
> **Validated via**: Perplexity Deep Research + Industry Best Practices

## 1. 背景与目标

当前系统的 Client Profile 是写死在 `config.yaml` 中的静态配置，仅支持 7 个预设客户类型（Vietnam PSP、Philippines PSP 等），字段有限且不支持运行时编辑。

**目标**：将 Client Profile 发展为一个可管理的 **Client Portal**，支持：
- 人工输入/编辑客户信息
- 按区域划分和筛选
- 持久化存储（JSON 文件 → 未来可升级为数据库）
- 丰富的客户画像字段，覆盖 FX 业务全链路
- 与现有报告生成、AI 新闻搜索、Executive Summary 无缝集成

### 1.1 Perplexity Deep Research 验证结论

通过 Perplexity 搜索行业最佳实践，确认以下关键发现：

1. **字段设计验证通过** — 原方案的 9 大模块覆盖了业界 FX CRM 的核心需求
2. **新增：合规字段** — 需要加入 AML 风险评级、制裁筛查状态、UBO 结构等 KYC/AML 字段（行业标配）
3. **新增：FX Purpose Code** — LATAM 市场（特别是巴西 BCB）强制要求跨境交易附带 purpose code，这在 SEA 市场也逐渐成为趋势
4. **新增：流动性偏好** — 客户可能有偏好的流动性提供商/银行路由（preferred liquidity providers）
5. **新增：信用额度管理** — 客户的 credit line utilization 和 un-hedged exposure 是 treasury 管理的核心
6. **新增：RBAC 角色体系** — 客户联系人应区分 Signer（审批人）、Viewer（查看者）、Admin（管理员）角色
7. **新增：交易历史与审计** — 每个客户应关联交易记录的搜索和审计追踪
8. **区域合规差异化确认**：
   - **SEA**：MAS (新加坡)、BI (印尼) 报告要求
   - **LATAM**：巴西 IOF 税、FX purpose code（BCB 强制）
   - **MEA**：VAT/GST 处理、区域特定制裁清单

---

## 2. 数据模型设计

### 2.1 客户信息分层架构（更新版 — 新增 KYC/AML 和信用管理模块）

```
Client Profile
├── 基础信息 (Basic Info)
├── KYC / AML 合规 (Compliance)              ← NEW: Perplexity 验证后新增
├── 区域与监管 (Region & Regulatory)
├── 业务概况 (Business Overview)
├── FX 需求 (FX Requirements)                ← ENHANCED: 新增 purpose code, liquidity provider
├── 通道配置 (Corridor Configuration)
├── 信用与额度 (Credit & Limits)             ← NEW: Perplexity 验证后新增
├── 风险偏好 (Risk Preferences)
├── 报告偏好 (Report Preferences)
├── 联系人 (Contacts)                        ← ENHANCED: 新增 RBAC 角色
└── 备注与标签 (Notes & Tags)
```

> **总计：11 个模块，约 80+ 个字段**（原方案 9 个模块约 60 个字段）

### 2.2 完整字段定义

#### A. 基础信息 (Basic Info)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `client_id` | string | 自动 | 唯一标识符，自动生成 (如 `CLT-VN-001`) |
| `name` | string | ✅ | 客户全称 (如 "MoMo Vietnam") |
| `short_name` | string | ✅ | 简称，用于 UI 显示 (如 "MoMo") |
| `legal_entity` | string | | 法律实体名称 |
| `client_type` | enum | ✅ | `PSP` / `Bank` / `Corporate` / `Fintech` / `E-commerce` / `Remittance` / `Other` |
| `tier` | enum | ✅ | `Tier 1` (战略) / `Tier 2` (重要) / `Tier 3` (标准) / `Prospect` (潜在) |
| `status` | enum | ✅ | `Active` / `Onboarding` / `Inactive` / `Churned` |
| `onboarding_date` | date | | 签约日期 |
| `logo_url` | string | | 客户 logo 图片链接 |

#### B. KYC / AML 合规 (Compliance) — ✨ NEW

> **来源**：Perplexity 搜索确认，FX CRM 必须包含 KYC/AML 字段作为行业标配，尤其是跨境支付场景。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `kyc_status` | enum | ✅ | `Pending` / `In Progress` / `Verified` / `Expired` / `Rejected` |
| `kyc_expiry_date` | date | | KYC 有效期 |
| `aml_risk_rating` | enum | | `Low` / `Medium` / `High` — 反洗钱风险等级 |
| `pep_status` | bool | | 是否涉及 PEP (Politically Exposed Person) |
| `sanctions_screening` | enum | | `Clear` / `Flagged` / `Pending Review` |
| `ubo_structure` | text | | UBO (Ultimate Beneficial Owner) 股权结构描述 |
| `tax_id` | string | | 税务识别号 |
| `incorporation_country` | string | | 注册国家 |
| `incorporation_date` | date | | 注册日期 |
| `compliance_notes` | text | | 合规备注 |

#### C. 区域与监管 (Region & Regulatory)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `region` | enum | ✅ | `Southeast Asia` / `East Asia` / `South Asia` / `Latin America` / `Middle East & Africa` / `Europe` / `North America` / `Global` |
| `country` | string | ✅ | 注册国家 (如 "Vietnam") |
| `operating_countries` | list[string] | | 实际运营的国家列表 |
| `timezone` | string | | 主时区 (如 "Asia/Ho_Chi_Minh") |
| `local_regulator` | string | | 当地金融监管机构 (如 "SBV") |
| `license_type` | string | | 牌照类型 (如 "E-wallet License", "Remittance License") |
| `central_bank` | string | | 相关央行 |
| `fx_purpose_codes` | list[string] | | 跨境交易用途代码（LATAM 强制，如巴西 BCB 要求的 inflow/outflow purpose code）|
| `local_tax_requirements` | text | | 当地税务要求（如巴西 IOF 税、MEA 地区 VAT/GST）|
| `regulatory_notes` | text | | 监管相关备注 |

#### D. 业务概况 (Business Overview)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `industry` | enum | ✅ | `Payment/PSP` / `Banking` / `E-commerce` / `Remittance/Transfer` / `Gaming` / `Travel` / `SaaS/Tech` / `Trading` / `Crypto` / `Other` |
| `business_model` | text | | 业务模式描述 |
| `main_products` | list[string] | | 主要产品/服务 (如 ["Mobile Wallet", "QR Payment", "Bill Payment"]) |
| `monthly_volume_usd` | number | | 月均 FX 交易量 (USD 等值) |
| `volume_tier` | enum | | `<1M` / `1M-10M` / `10M-50M` / `50M-100M` / `100M-500M` / `>500M` |
| `annual_revenue_usd` | number | | 年收入 (USD) |
| `employee_count` | string | | 员工规模 (如 "1000-5000") |
| `website` | string | | 官网链接 |

#### E. FX 需求 (FX Requirements) — ✨ ENHANCED

> **新增字段来源**：Perplexity 确认需要 preferred liquidity providers（流动性偏好）、tenor preferences（期限偏好）、vanilla vs structured 产品偏好。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `base_currency` | string | ✅ | 基准货币 (如 "VND") |
| `settlement_currencies` | list[string] | | 结算货币列表 |
| `focus_pairs` | list[string] | ✅ | 关注的货币对 (如 ["USDVND", "CNHVND"]) |
| `fx_products_used` | list[enum] | | `Spot` / `Forward` / `NDF` / `Swap` / `Options` / `Structured` |
| `product_complexity` | enum | | `Vanilla Only` / `Vanilla + Simple Structured` / `Full Range` — 产品复杂度偏好 |
| `tenor_preferences` | list[string] | | 偏好期限 (如 ["1M", "3M", "6M"]) |
| `hedging_policy` | enum | | `No Hedge` / `Partial Hedge` / `Full Hedge` / `Dynamic` |
| `hedging_ratio` | string | | 对冲比例 (如 "50-70%") |
| `hedging_horizon` | string | | 对冲期限 (如 "1-3 months") |
| `pricing_model` | enum | | `Markup` / `Spread` / `Commission` / `Blended` |
| `current_markup_bps` | number | | 当前加价 (基点) |
| `volume_based_tiering` | bool | | 是否使用基于交易量的阶梯定价 |
| `benchmark_rate_source` | string | | 基准汇率来源 (如 "Reuters", "Bloomberg", "Central Bank") |
| `preferred_liquidity_providers` | list[string] | | 偏好的流动性提供商/银行 (如 ["HSBC", "Citi", "SCB"]) |
| `preferred_bank_routing` | string | | 偏好的银行路由 |
| `settlement_cycle` | string | | 结算周期 (如 "T+0", "T+1", "T+2") |
| `preferred_execution_window` | string | | 偏好的交易执行时段 (如 "09:00-17:00 HKT") |

#### F. 通道配置 (Corridor Configuration)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `corridors` | list[Corridor] | ✅ | 支付通道列表 |

**Corridor 子结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `from_currency` | string | 源货币 |
| `to_currency` | string | 目标货币 |
| `direction` | enum | `inbound` / `outbound` / `both` |
| `label` | string | 描述 (如 "USD→VND Remittance") |
| `avg_ticket_size_usd` | number | 平均单笔金额 (USD) |
| `monthly_volume_usd` | number | 该通道月均交易量 |
| `priority` | enum | `Primary` / `Secondary` / `Occasional` |
| `purpose` | string | 用途 (如 "OFW Remittance", "Trade Settlement", "E-commerce Payout") |
| `purpose_code` | string | 监管用途代码（LATAM 必填，如巴西 BCB 规定的 purpose code）|
| `value_limits` | dict | 交易限额 `{"per_txn": 50000, "daily": 500000, "monthly": 5000000}` |

#### G. 信用与额度 (Credit & Limits) — ✨ NEW

> **来源**：Perplexity 确认，Treasury 管理的核心是信用额度利用率和未对冲敞口的监控。

| 字段 | 类型 | 说明 |
|------|------|------|
| `credit_line_usd` | number | 信用额度 (USD) |
| `credit_line_utilized_pct` | number | 当前利用率 (%) |
| `credit_line_expiry` | date | 额度到期日 |
| `net_exposure_limit_usd` | number | 净敞口限额 |
| `unhedged_exposure_alert_pct` | number | 未对冲敞口预警阈值 (%) |
| `collateral_type` | string | 担保类型（如 "Cash Deposit", "Bank Guarantee", "None"）|
| `collateral_amount_usd` | number | 担保金额 |
| `payment_terms` | string | 付款条款（如 "Net 30", "Prepaid"） |

#### H. 风险偏好 (Risk Preferences)

| 字段 | 类型 | 说明 |
|------|------|------|
| `risk_appetite` | enum | `Conservative` / `Moderate` / `Aggressive` |
| `max_single_trade_usd` | number | 单笔最大交易金额 |
| `daily_limit_usd` | number | 日交易限额 |
| `stop_loss_threshold` | string | 止损阈值 (如 "2% adverse move") |
| `var_limit` | string | VaR 限额 |
| `key_concerns` | list[string] | 主要关注的风险点 |
| `sensitivity_factors` | list[string] | 敏感因素 (如 ["Oil Price", "Fed Rate", "CNH Fix"]) |

#### I. 报告偏好 (Report Preferences)

| 字段 | 类型 | 说明 |
|------|------|------|
| `report_frequency` | enum | `Daily` / `Weekly` / `Bi-weekly` / `Monthly` / `Ad-hoc` |
| `report_language` | enum | `en` / `zh` / `vi` / `th` / `id` / `pt` |
| `report_format` | enum | `HTML` / `PDF` / `Both` |
| `report_delivery` | enum | `Email` / `Portal Download` / `API Feed` / `ERP Integration` |
| `sections_enabled` | dict | 每个报告 section 的开关 |
| `include_charts` | bool | 是否包含图表 |
| `include_corridor_analysis` | bool | 是否包含通道分析 |
| `include_cost_analysis` | bool | 是否包含成本分析（savings vs mid-market rate）|
| `custom_benchmarks` | list[string] | 自定义基准 (如 ["DXY", "ADXY"]) |
| `news_topics` | list[string] | 关注的新闻主题 |
| `alert_thresholds` | dict | 提醒阈值 (如 `{"USDVND": {"pct_change": 0.5}}`) |

#### J. 联系人 (Contacts) — ✨ ENHANCED

> **新增 RBAC 角色**：Perplexity 确认，FX client portal 应区分 Signer（审批人）、Viewer（查看者）、Admin（管理员）角色。

| 字段 | 类型 | 说明 |
|------|------|------|
| `contacts` | list[Contact] | 联系人列表 |

**Contact 子结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 姓名 |
| `role` | string | 角色/职位 (如 "Treasury Head", "CFO", "FX Trader") |
| `access_level` | enum | `Signer` (审批人) / `Trader` (交易员) / `Viewer` (查看者) / `Admin` (管理员) |
| `email` | string | 邮箱 |
| `phone` | string | 电话 |
| `is_primary` | bool | 是否主要联系人 |
| `receives_report` | bool | 是否接收报告 |
| `communication_preference` | enum | `Email` / `WeChat` / `WhatsApp` / `Phone` |

#### K. 备注与标签 (Notes & Tags)

| 字段 | 类型 | 说明 |
|------|------|------|
| `tags` | list[string] | 标签 (如 ["High Priority", "Renewal Q2", "Price Sensitive"]) |
| `internal_notes` | text | 内部备注 |
| `key_events` | list[string] | 关注的经济/市场事件 |
| `relationship_manager` | string | 客户经理 |
| `last_review_date` | date | 上次 review 日期 |
| `next_review_date` | date | 下次 review 日期 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 最后更新时间 |

---

## 3. 区域划分体系

```
Regions
├── Southeast Asia (SEA)
│   ├── Vietnam
│   ├── Philippines
│   ├── Indonesia
│   ├── Thailand
│   ├── Malaysia
│   ├── Singapore
│   └── Myanmar
├── East Asia
│   ├── China/HK
│   ├── Japan
│   ├── South Korea
│   └── Taiwan
├── South Asia
│   ├── India
│   ├── Bangladesh
│   ├── Pakistan
│   └── Sri Lanka
├── Latin America (LATAM)
│   ├── Brazil
│   ├── Mexico
│   ├── Argentina
│   └── Colombia
├── Middle East & Africa (MEA)
│   ├── UAE
│   ├── Saudi Arabia
│   ├── Nigeria
│   └── South Africa
├── Europe
│   ├── UK
│   ├── EU
│   └── Turkey
└── Global / Multi-region
```

---

## 4. 数据存储方案

### 4.1 第一阶段：JSON 文件存储

```
fx-report/
  data/
    clients/
      _index.json          ← 客户索引（id, name, region, status, tier）
      CLT-VN-001.json      ← 单个客户完整数据
      CLT-VN-002.json
      CLT-PH-001.json
      ...
```

**`_index.json` 结构**：
```json
{
  "version": "1.0",
  "clients": [
    {
      "client_id": "CLT-VN-001",
      "name": "MoMo Vietnam",
      "short_name": "MoMo",
      "region": "Southeast Asia",
      "country": "Vietnam",
      "client_type": "PSP",
      "tier": "Tier 1",
      "status": "Active",
      "base_currency": "VND",
      "updated_at": "2026-03-05T10:00:00Z"
    }
  ]
}
```

### 4.2 未来扩展：SQLite / PostgreSQL

当客户数量增长或需要多人协作时，可迁移到 SQLite（单文件数据库）或 PostgreSQL。JSON 文件方案无需改动前端代码，只需替换后端存储层。

---

## 5. UI 设计方案

### 5.1 Client Portal 主页面

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENT PORTAL                              [+ New Client]  │
├──────────────────────────────────────────────────────────────┤
│  Filters: [Region ▼] [Type ▼] [Tier ▼] [Status ▼] [Search] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Southeast Asia (4) ──────────────────────────────────┐   │
│  │                                                        │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐         │  │
│  │  │ 🇻🇳 MoMo   │ │ 🇵🇭 GCash  │ │ 🇮🇩 DANA   │         │  │
│  │  │ VND · T1   │ │ PHP · T1   │ │ IDR · T2   │         │  │
│  │  │ ● Active   │ │ ● Active   │ │ ● Active   │         │  │
│  │  │ Vol: 50M+  │ │ Vol: 30M+  │ │ Vol: 10M+  │         │  │
│  │  └────────────┘ └────────────┘ └────────────┘         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Latin America (1) ───────────────────────────────────┐   │
│  │  ┌────────────┐                                        │  │
│  │  │ 🇧🇷 PicPay │                                        │  │
│  │  │ BRL · T2   │                                        │  │
│  │  │ ● Active   │                                        │  │
│  │  └────────────┘                                        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 客户详情/编辑页面

```
┌──────────────────────────────────────────────────────────────┐
│  ← Back to Portal    MoMo Vietnam    [Save] [Delete]        │
├──────────────────────────────────────────────────────────────┤
│  Tabs: [Basic] [Business] [FX & Corridors] [Risk]           │
│        [Reports] [Contacts] [Notes]                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Basic Info ──────────────────────────────────────────┐   │
│  │  Client Name:  [MoMo Vietnam                       ]  │   │
│  │  Short Name:   [MoMo                               ]  │   │
│  │  Type:         [PSP              ▼]                    │   │
│  │  Tier:         [● T1  ○ T2  ○ T3  ○ Prospect]        │   │
│  │  Status:       [Active           ▼]                    │   │
│  │  Region:       [Southeast Asia   ▼]                    │   │
│  │  Country:      [Vietnam          ▼]                    │   │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Corridors ───────────────────────────────────────────┐   │
│  │  [+ Add Corridor]                                      │  │
│  │                                                        │  │
│  │  1. USD → VND  Inbound  "Remittance"   [Primary] [✕]  │  │
│  │     Avg Ticket: $500  |  Monthly Vol: $20M             │  │
│  │                                                        │  │
│  │  2. CNY → VND  Inbound  "Trade"        [Secondary][✕] │  │
│  │     Avg Ticket: $5000 |  Monthly Vol: $15M             │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 导航集成方案

在现有 `app.py` 的顶部导航栏新增入口：

```
[FX Report Generator]                    [Client Portal]
```

Client Portal 作为独立页面（新路由 `/portal`），但与报告生成器共享数据：
- 在报告生成器中选择 Client Profile 时，从 Portal 数据库读取
- Portal 编辑的客户数据自动更新到报告生成流程

---

## 6. API 设计

### 6.1 客户 CRUD

| Method | Path | 说明 |
|--------|------|------|
| `GET` | `/api/portal/clients` | 获取客户列表（支持 region/type/tier/status 过滤） |
| `GET` | `/api/portal/clients/<id>` | 获取单个客户详情 |
| `POST` | `/api/portal/clients` | 创建新客户 |
| `PUT` | `/api/portal/clients/<id>` | 更新客户 |
| `DELETE` | `/api/portal/clients/<id>` | 删除客户 |
| `POST` | `/api/portal/clients/import` | 批量导入（JSON/CSV） |
| `GET` | `/api/portal/clients/export` | 导出客户数据 |

### 6.2 辅助 API

| Method | Path | 说明 |
|--------|------|------|
| `GET` | `/api/portal/regions` | 获取区域列表和统计 |
| `GET` | `/api/portal/stats` | 仪表盘统计数据 |
| `POST` | `/api/portal/clients/<id>/generate-report` | 基于该客户直接生成报告 |

---

## 7. 与现有系统的集成

### 7.1 替代 config.yaml 中的静态 profiles

```python
# 现在：从 config.yaml 读取
profiles = CONFIG.get("client_profiles", {})

# 未来：从 Client Portal 数据库读取
from client_portal import ClientPortal
portal = ClientPortal(data_dir="data/clients")
profiles = portal.get_all_as_legacy_profiles()  # 向后兼容
```

### 7.2 报告生成集成

```python
# 用户在 Portal 选择客户 → 自动填充报告参数
client = portal.get_client("CLT-VN-001")
report_config = client.to_report_config()
# → base_currency, corridors, focus_pairs, key_concerns, report_preferences...
```

### 7.3 AI 新闻搜索集成

```python
# 基于完整客户画像生成更精准的搜索 prompt
client = portal.get_client("CLT-VN-001")
search_context = {
    "region": client.country,
    "currency": client.base_currency,
    "industry": client.industry,
    "corridors": client.corridors,
    "concerns": client.key_concerns,
    "sensitivity_factors": client.sensitivity_factors,
    "news_topics": client.report_preferences.news_topics,
}
# → Perplexity 搜索: "Vietnam mobile wallet VND USD remittance SBV policy 2026"
```

---

## 8. 实施计划

### Phase 1：数据层 + 后端 API（基础）
- 定义 Client 数据模型 (`client_model.py`)
- 实现 JSON 文件存储层 (`client_store.py`)
- 实现 CRUD API endpoints
- 预填充现有 7 个 config.yaml profiles 的数据作为种子数据
- 向后兼容：报告生成器继续通过 `get_all_as_legacy_profiles()` 读取

### Phase 2：前端 Portal UI
- Client Portal 主页面（按区域分组的卡片视图）
- 客户新建/编辑表单（分 tab 的详细表单）
- 筛选和搜索功能
- 与报告生成器的 profile 选择器集成

### Phase 3：增强功能
- 客户数据导入/导出
- 报告历史记录（每个客户的报告归档）
- AI 新闻搜索深度集成（基于完整画像）
- 批量操作（批量生成报告等）

---

## 9. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 存储 | JSON 文件 → SQLite | 轻量、无依赖、易迁移 |
| 后端 | Flask（复用现有） | 已有基础设施 |
| 前端 | 原生 HTML/JS + Tailwind | 与现有 app.py 风格一致 |
| ID 生成 | `CLT-{COUNTRY_CODE}-{SEQ}` | 直观、可读 |
| 验证 | Python dataclass / dict validation | 轻量 |

---

## 10. 默认种子数据

将现有 `config.yaml` 中的 7 个 profile 迁移为 Client Portal 数据：

| client_id | name | region | country | type | tier | base_currency |
|-----------|------|--------|---------|------|------|---------------|
| CLT-VN-001 | Vietnam PSP (Template) | Southeast Asia | Vietnam | PSP | Tier 2 | VND |
| CLT-PH-001 | Philippines PSP (Template) | Southeast Asia | Philippines | PSP | Tier 2 | PHP |
| CLT-ID-001 | Indonesia PSP (Template) | Southeast Asia | Indonesia | PSP | Tier 2 | IDR |
| CLT-TH-001 | Thailand PSP (Template) | Southeast Asia | Thailand | PSP | Tier 2 | THB |
| CLT-MY-001 | Malaysia PSP (Template) | Southeast Asia | Malaysia | PSP | Tier 2 | MYR |
| CLT-BR-001 | Brazil PSP (Template) | Latin America | Brazil | PSP | Tier 2 | BRL |
| CLT-GL-001 | Global Overview (Template) | Global | Global | Other | Tier 3 | USD |

这些作为模板，用户可以基于模板创建具体客户（如 "MoMo Vietnam"、"GCash Philippines"）。

---

## 11. Perplexity Deep Research 验证总结

### 11.1 原方案与行业标准对比

| 维度 | 原方案 | 行业最佳实践 (Perplexity) | 差距 | 已补充 |
|------|--------|---------------------------|------|--------|
| **KYC/AML 合规** | ❌ 缺失 | ✅ 必备：AML 评级、PEP 筛查、制裁状态、UBO 结构 | 关键缺失 | ✅ 新增 B 模块 |
| **FX Purpose Code** | ❌ 缺失 | ✅ LATAM 强制（巴西 BCB inflow/outflow code）| 区域合规缺失 | ✅ 加入 C 和 F |
| **流动性偏好** | ❌ 缺失 | ✅ Preferred liquidity providers / bank routing | 定价优化缺失 | ✅ 加入 E |
| **产品复杂度** | ❌ 缺失 | ✅ Vanilla vs Structured / Tenor preferences | 产品匹配缺失 | ✅ 加入 E |
| **信用额度管理** | ❌ 缺失 | ✅ Credit line, utilization, collateral, un-hedged alert | 核心 Treasury 功能缺失 | ✅ 新增 G 模块 |
| **RBAC 角色** | ❌ 缺失 | ✅ Signer / Trader / Viewer / Admin | 权限管理缺失 | ✅ 加入 J |
| **报告分发方式** | 部分 | ✅ Email / API / ERP Integration | 分发渠道不足 | ✅ 加入 I |
| **通道交易限额** | ❌ 缺失 | ✅ Per-txn / daily / monthly limits | 风控缺失 | ✅ 加入 F |
| **IOF 税 / VAT** | ❌ 缺失 | ✅ 区域特定税务字段 | 区域合规缺失 | ✅ 加入 C |
| **成本分析** | ❌ 缺失 | ✅ Savings vs mid-market rate | 价值展示缺失 | ✅ 加入 I |
| **基础信息** | ✅ 完善 | ✅ 一致 | 无 | — |
| **区域划分** | ✅ 完善 | ✅ 一致（SEA/LATAM/MEA 分区） | 无 | — |
| **FX 核心字段** | ✅ 完善 | ✅ 一致 | 无 | — |
| **通道配置** | ✅ 完善 | ✅ 一致 | 无 | — |
| **风险偏好** | ✅ 完善 | ✅ 一致 | 无 | — |
| **报告偏好** | ✅ 完善 | ✅ 一致 | 无 | — |
| **联系人管理** | ✅ 基础 | ✅ 一致（需增强角色） | 小幅增强 | ✅ |

### 11.2 区域合规差异化（Perplexity 确认）

| 区域 | 特殊合规要求 | 系统需支持的字段 |
|------|-------------|----------------|
| **SEA** | MAS (新加坡) 报告、BI (印尼) FX 报告、SBV (越南) managed float | `local_regulator`, `license_type`, `central_bank` |
| **LATAM** | 巴西 BCB FX purpose code（强制）、IOF 税、Selic 利率影响 | `fx_purpose_codes`, `local_tax_requirements` |
| **MEA** | VAT/GST 处理、区域特定制裁清单（OFAC + 本地）| `local_tax_requirements`, `sanctions_screening` |
| **East Asia** | PBOC 管控、日本金融厅 FSA 报告 | `regulatory_notes`, `local_regulator` |

### 11.3 行业参考产品对标

| 产品 | 定位 | 我们可借鉴的功能 |
|------|------|----------------|
| **Datasoft FxOffice** | FX & Global Payments 全栈 | AML 集成、支付结算、合规报告 |
| **Corpay (GPS FX)** | Cross-border Payments + FX Risk Management | Client segmentation、corridor 管理、volume-based pricing |
| **360T (Deutsche Börse)** | 机构 FX 交易平台 | Client portal、relationship management、execution analytics |
| **Refinitiv FXall** | 机构 FX | Multi-dealer pricing、client tiering、trade analytics |

### 11.4 最终结论

> **原方案覆盖率约 70%**，经过 Perplexity 验证后补充了 10 个关键缺失维度，更新后覆盖率提升至约 **95%**。
>
> 剩余 5% 为更高级功能（如实时交易执行、ERP 集成、自动化对冲执行），属于 Phase 3+ 范畴，当前方案无需包含。
