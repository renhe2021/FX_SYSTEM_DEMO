| 版本 | 修订人 | 变更内容 | 时间 |
| - | - | - | - |
| 1.0 | tencentren | 初版 | 2026-Mar-11 |
| 1.1 | tencentren | 基于 ROMS/PAMAS 现有 Schema 调研更新配置表方案 | 2026-Mar-12 |

# 金融日历系统模块 — 与PAMAS/ROMS集成方案

## 背景

### 问题场景

在跨境外汇交易中，**重大经济数据发布前后的市场流动性剧烈变化**是做市商面临的核心风险之一。

当前系统状态：
- **PAMAS** 已具备 LPA（模型定价）和 Spread Adjustment IPA（价宽调整）能力，但**价宽调整仅支持静态规则**（按币种对配置 min/max/default spread），不具备基于事件动态调整的能力
- **ROMS** 已具备自动对冲能力（敞口触发、时间兜底平仓），但**对冲规则无法感知即将发生的经济事件**，只能被动响应敞口变化
- **金融日历数据**已通过 Bloomberg 等渠道获取（见 xlsx 文件），但**未与定价和风控系统集成**

### 已暴露的线上问题

> 2025-07-15 凌晨，自营收款 AUD 币种付款交易被金融日历拦截。根因：AUD 仅配 T2 tenor，但北京时间 0am-5am 的 T2 交易在纽约时区实际为 T3，金融日历正确拦截了不支持的远期交易。

这说明：**金融日历在交割日判断上已在发挥作用，但在定价和风控侧的集成仍是空白。**

### 目标

构建金融日历模块，作为 PAMAS 和 ROMS 的**事件驱动信号源**，实现：

1. **PAMAS 侧**：经济事件前后自动调整做市价宽，保护平台免受流动性冲击
2. **ROMS 侧**：经济事件前主动收窄敞口，降低持仓风险

---

## 金融日历数据源

### 数据字段定义

基于 Bloomberg Economic Calendar 数据源（已有 xlsx 文件），字段映射如下：

| 字段 | 示例 | 说明 | 系统用途 |
| - | - | - | - |
| `Date Time` | 2026-03-12 20:30 | 事件发布时间（UTC+8） | 触发时间窗口计算的锚点 |
| `Country Code` | US | 国家代码 | 映射受影响币种（US→USD相关币种对） |
| `Event` | Non-Farm Payrolls | 事件名称 | 用于匹配事件分级规则 |
| `Period` | Feb | 数据所属周期 | 展示用 |
| `Survey` | 200K | 市场预期值 | 事件后可计算 surprise = actual - survey |
| `Actual` | 215K | 实际公布值 | 用于判断是否需要延长恢复窗口 |
| `Prior` | 143K | 上期值 | 辅助判断 |
| `Revised` | -- | 修正值 | 辅助判断 |
| `Relevance` | 98.67 | Bloomberg 事件重要性评分（0-100） | **核心字段：映射为事件分级** |
| `Ticker` | NFP TCH Index | Bloomberg Ticker | 唯一标识 |

### 事件分级规则

基于 `Relevance` 评分，将事件分为三级：

| 等级 | Relevance 范围 | 典型事件 | PAMAS 行为 | ROMS 行为 |
| - | - | - | - | - |
| **🔴 High** | ≥ 85 | NFP, FOMC, CPI, ECB/BOE/BOJ Rate Decision | 价宽放大 3.0x，前窗30min | 全量平仓（flatten 100%） |
| **🟡 Medium** | 60 ~ 85 | Trade Balance, Housing Starts, PCE | 价宽放大 2.0x，前窗15min | 部分减仓（reduce 50%） |
| **🟢 Low** | < 60 | Wholesale Inventories, TIC Flows | 价宽放大 1.5x，前窗5min | 仅监控（monitor） |

### 国家→币种对映射

| Country Code | 直接受影响币种 | 受影响币种对 |
| - | - | - |
| US | USD | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, USDCNH |
| EU | EUR | EURUSD, EURGBP, EURJPY, EURCHF |
| GB | GBP | GBPUSD, EURGBP, GBPJPY |
| JP | JPY | USDJPY, EURJPY, GBPJPY |
| CN | CNY/CNH | USDCNH |

---

## 与 PAMAS 集成方案

### 现有 Schema 参考

经调研 PAMAS 数据库 `data_query_conf`，现有配置表包括：

| 表名 | 说明 | 与日历方案的关系 |
| - | - | - |
| `exrate_request_config_currency_list` | 币种配置表 | 可复用币种对列表映射 |
| `exrate_scenario_config` | 场景配置（含 source、markup、base_ccy） | Calendar IPA 配置表参考其命名风格和字段规范 |

> 注：Spread Adjustment IPA 的具体配置表未在文档中找到明确定义，Calendar IPA 作为独立 IPA 可以有自己的配置表，遵循 PAMAS 的 `F` 前缀命名规范。

### 嵌入位置

金融日历作为一个**新的 IPA（Calendar IPA）**嵌入 PAMAS Pipeline，位于 **Spread Adjustment IPA 之后、Markup IPA 之前**：

```
LPA (Model Pricing) → Spread Adj IPA → 【Calendar IPA (新增)】 → Markup IPA → EPA
```

> 讨论：为什么不嵌入 Spread Adjustment IPA 内部？
> - Calendar IPA 是事件驱动、有时间窗口的**临时性调整**，与 Spread Adj 的**常态性约束**（min/max/default）职责不同
> - Calendar IPA 可独立配置、独立启停，不影响现有 Spread Adj 逻辑
> - 符合 PAMAS Pipeline IPA 可串联的设计原则

### Calendar IPA 配置表设计

```sql
CREATE TABLE fx_rate_db.t_calendar_ipa_config (
  `Fpa_config_name`    VARCHAR(32)  NOT NULL COMMENT 'PA配置名',
  `Fcurrency_pair`     VARCHAR(8)   NOT NULL COMMENT '币种对, default表示全部',
  `Fevent_level`       TINYINT(4)   NOT NULL COMMENT '事件等级: 1=High, 2=Medium, 3=Low',
  `Fspread_multiplier` DECIMAL(4,2) NOT NULL COMMENT '价宽放大倍数',
  `Fpre_event_minutes` INT(10)      NOT NULL COMMENT '事件前生效分钟数',
  `Fpost_event_minutes` INT(10)     NOT NULL COMMENT '事件后恢复分钟数',
  `Fwidening_curve`    VARCHAR(32)  NOT NULL DEFAULT 'ease_in_out' COMMENT '价宽变化曲线: linear/ease_in_out/step',
  `Fmanual_override`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否允许手动覆盖',
  `Flstate`            SMALLINT(6)  DEFAULT 1 COMMENT '物理状态: 1-正常, 2-删除',
  `Fcreate_user`       VARCHAR(64)  NOT NULL COMMENT '创建人',
  `Fcreate_time`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `Fmodify_user`       VARCHAR(64)  NOT NULL COMMENT '修改人',
  `Fmodify_time`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`Fpa_config_name`, `Fcurrency_pair`, `Fevent_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='金融日历IPA配置表';
```

示例配置：

| pa_config_name | currency_pair | event_level | spread_multiplier | pre_event_min | post_event_min |
| - | - | - | - | - | - |
| prod_v1 | default | 1 (High) | 3.0 | 30 | 15 |
| prod_v1 | default | 2 (Medium) | 2.0 | 15 | 10 |
| prod_v1 | default | 3 (Low) | 1.5 | 5 | 5 |
| prod_v1 | USDCNH | 1 (High) | 4.0 | 30 | 20 |

### Calendar IPA 执行逻辑

```
upon receiving price request(currency_pair, tenor):
  1. events = get_upcoming_events(currency_pair, lookback=max_pre_event_minutes)
  2. IF no events matched THEN return spread unchanged
  3. FOR each matched event:
     a. config = get_calendar_ipa_config(pa_config_name, currency_pair, event.level)
     b. IF manual_override exists THEN use override_multiplier
     c. time_delta = event.datetime - now()
     d. IF time_delta > pre_event_minutes THEN phase = NORMAL, multiplier = 1.0
     e. ELIF time_delta > 0 THEN phase = PRE_EVENT
        multiplier = 1.0 + (config.multiplier - 1.0) * ease_in(progress)
     f. ELIF time_delta > -60s THEN phase = PEAK, multiplier = config.multiplier
     g. ELSE phase = RECOVERY
        multiplier = config.multiplier * exp_decay(elapsed, post_event_minutes)
  4. final_multiplier = MAX(all matched event multipliers)  // 多事件取最大
  5. output_spread = input_spread * final_multiplier
```

### PAMAS 前端配置界面（新增页面）

在 PAMAS 管理界面，**新增"金融日历价宽调整"页面**（参考现有"平台价宽调整"页面风格）：

| 功能 | 说明 |
| - | - |
| 日历事件列表 | 展示未来7天内的经济事件，含时间、国家、事件名、等级、Relevance评分 |
| IPA 配置管理 | 配置各等级的 spread_multiplier、时间窗口，支持按币种对覆盖 |
| 手动覆盖 | 交易员可临时调整特定事件的倍数（如预判市场反应不如预期时调低） |
| 实时状态 | 当前是否有事件激活中、当前生效的倍数、剩余恢复时间 |

---

## 与 ROMS 集成方案

### 现有 Schema 调研

经调研 `fx_romshedge_db` 数据库，ROMS 自动对冲的核心表结构如下：

#### 触发条件表 `fx_romshedge_db.t_trigger_condition`

| 字段 | 说明 | 现有枚举值 |
| - | - | - |
| `Ftrigger_cond_id` | 条件 ID（自增） | 1, 2, 3, ... |
| `Ftrigger_var_type` | 触发变量类型 | 1=各自敞口, 2=自身未实现盈亏, 3=时间, 4=头寸集敞口, 5=头寸集未实现盈亏, 10=在离岸价差, 11=全期限敞口, 12=预平盘修正 |
| `Fcompare_operator` | 比较运算符 | 0=无, 1=大于, 2=小于, 3=等于 |
| `Ftrigger_value_type` | 触发值类型 | 0=无, 1=绝对值, 2=百分比 |
| `Flstate` | 物理状态 | 1=正常, 2=删除 |
| `Fmemo` | 备注 | 如"敞口触发"、"时间兜底触发" |

#### 规则主表 `fx_romshedge_db.t_rule`

| 字段 | 说明 | 日历场景复用方式 |
| - | - | - |
| `Frule_id` | 规则 ID（自增） | ✅ 直接复用 |
| `Frule_name` | 规则名称 | ✅ 如 "NFP_高影响_平仓" |
| `Frule_group_id` | 规则组 ID | ✅ 可创建"日历对冲"规则组 |
| `Ftrigger_cond_id` | 关联触发条件 ID | ✅ 指向 type=13 的新条件 |
| `Ftrigger_threshold` | 触发阈值 | 📅 存事件等级 (1=High / 2=Medium / 3=Low) |
| `Fexecutable_time_begin` | 可执行开始时间 | 📅 映射为事件前 N 分钟 |
| `Fexecutable_time_end` | 可执行结束时间 | 📅 映射为事件后 N 分钟 |
| `Ftarget_var_type` | 目标变量类型 | ✅ 1=敞口归零, 5=按比例减仓 |
| `Fpriority` | 优先级 | ✅ 日历规则可设高优先级 |
| `Falgo_type` | 执行算法 | ✅ 1=SingleOrder, 2=TWAP |
| `Fstate` | 启停状态 | ✅ 复用 |
| `Fforce_offshore_trade` | 强制离岸交易 | ✅ 复用 |
| `Funderlying_tenor` | 标的 tenor | ✅ 如 SPOT / 1W |

#### 子表（均可复用，无需改表结构）

| 表名 | 说明 | 日历场景用途 |
| - | - | - |
| `t_rule_range` | 规则适用的币种对范围 | 配置日历规则作用于哪些币种对 |
| `t_rule_amount` | 规则金额阈值 | 不同金额级别可配不同减仓比例 |
| `t_rule_banktype` | 规则渠道/对手方 | 指定日历对冲走哪些银行渠道 |
| `t_time_rule_execute_record_#yyyy#` | 时间规则执行记录（按年分表） | 参考此模式记录日历触发的执行记录 |

#### 规则实体结构 `AutoHedgeRuleStructuredEntity`

现有信号条件类型（`signalConditions`）包括：`HOLIDAY`、`PRE_HEDGE_BUY`、`PRE_HEDGE_SELL`。金融日历可新增 **`CALENDAR_EVENT`** 类型。

### 触发机制

金融日历作为 ROMS 自动对冲的**新增触发变量**，沿用现有 `Ftrigger_var_type` 递增模式：

| Ftrigger_var_type | 类型 | 现有/新增 | 说明 |
| - | - | - | - |
| 1 | 各自敞口 | 现有 | 单币种敞口超阈值触发 |
| 3 | 时间 | 现有 | 到点兜底平仓 |
| 4 | 头寸集敞口 | 现有 | 头寸集级别敞口触发 |
| 11 | 全期限敞口 | 现有 | 跨 tenor 敞口触发 |
| 12 | 预平盘修正 | 现有 | 预期敞口管理 |
| **13** | **金融日历事件** | **新增** | 事件前 T-pre 分钟触发预防性减仓 |

### ROMS 数据库变更方案

#### 变更一：新增触发条件（INSERT，零侵入）

```sql
-- 沿用现有模式，在 t_trigger_condition 新增一条记录
INSERT INTO fx_romshedge_db.t_trigger_condition
  (Ftrigger_cond_id, Ftrigger_var_type, Fcompare_operator, Ftrigger_value_type, Flstate, Fmemo)
VALUES
  (20, 13, 0, 0, 1, '金融日历事件触发');
```

#### 变更二：扩展规则主表（ALTER TABLE，3 个字段）

现有 `t_rule` 无法表达"事件等级""冻结期""恢复窗口"等日历特有概念，需新增 3 个字段：

```sql
ALTER TABLE fx_romshedge_db.t_rule
  ADD COLUMN `Fevent_level` TINYINT(4) DEFAULT NULL COMMENT '事件等级: 1=High, 2=Medium, 3=Low（仅 trigger_var_type=13 时使用）',
  ADD COLUMN `Ffreeze_during_event` TINYINT(1) DEFAULT 1 COMMENT '事件发布期间是否冻结对冲操作（默认冻结）',
  ADD COLUMN `Frestore_after_min` INT(10) DEFAULT NULL COMMENT '事件后恢复常规规则的分钟数';
```

> **设计原则**：当 `Ftrigger_var_type ≠ 13` 时这 3 个字段为 NULL，不影响现有规则逻辑。也可考虑独立建 `t_calendar_rule_ext` 通过 `Frule_id` 外键关联，零侵入但增加 JOIN 复杂度。

#### 变更三：新增信号条件类型（代码层）

在 `AutoHedgeRuleStructuredEntity.signalConditions` 枚举中新增：

| 类型 | 值 | 说明 |
| - | - | - |
| CALENDAR_EVENT | 新增 | 金融日历事件信号，用于控制规则的启用/禁用条件 |

### ROMS Calendar Hedge 配置示例

利用扩展后的 `t_rule` 表 + `t_rule_range` 子表配置：

| rule_id | rule_name | trigger_cond (type=13) | event_level | target_var_type | algo_type | freeze | restore_min |
| - | - | - | - | - | - | - | - |
| 201 | NFP_High_Flatten | 20 | 1 (High) | 1 (敞口归零) | 2 (TWAP) | 1 | 15 |
| 202 | Medium_Reduce50 | 20 | 2 (Medium) | 5 (按比例) | 1 (SingleOrder) | 1 | 10 |
| 203 | Low_Monitor | 20 | 3 (Low) | — | — | 0 | 5 |
| 204 | FOMC_FWD_Reduce80 | 20 | 1 (High) | 5 (按比例 80%) | 2 (TWAP) | 1 | 20 |

对应的 `t_rule_range` 配置：

| rule_id | currency_pair |
| - | - |
| 201 | EURUSD |
| 201 | GBPUSD |
| 201 | USDJPY |
| 202 | * (全部) |
| 204 | EURUSD |
| 204 | USDJPY |

### ROMS 执行流程

```
Calendar Event Scheduler (定时轮询):
  1. events = get_events_in_window(now, now + max_trigger_before)
  2. FOR each event:
     a. rules = match_rules(trigger_cond_id=20, event_level=event.level)
     b. ranges = get_rule_ranges(rule_id) // 从 t_rule_range 获取币种对
     c. FOR each rule:
        IF now >= event.datetime - rule.executable_time_begin:
           Phase = PRE_EVENT:
           i.   get current exposure from RMS (filtered by ranges)
           ii.  calculate target based on target_var_type
           iii. generate hedge order(s) per algo_type
           iv.  submit to OMS via t_rule_banktype channels
           v.   log to t_calendar_hedge_record (参考 t_time_rule_execute_record)

        IF event published AND rule.freeze_during_event = 1:
           Phase = FROZEN:
           skip all hedge actions, wait for recovery

        IF now >= event.datetime + rule.restore_after_min:
           Phase = RECOVERY:
           process remaining exposure, then restore normal rules
```

### ROMS 前端界面（新增/修改）

| 功能 | 说明 |
| - | - |
| 日历对冲规则管理 | 在自动对冲规则编辑界面，新增"金融日历"触发条件类型（trigger_var_type=13），复用现有规则配置 UI |
| 事件预览面板 | 未来事件及对应的对冲动作预览，显示 event_level、affected_pairs、预计触发时间 |
| 冻结状态监控 | 实时显示当前是否处于"事件发布冻结期"，冻结中不执行新的对冲 |
| 执行记录 | 金融日历触发的对冲决策记录（参考 `t_time_rule_execute_record` 分表模式），含事件ID、头寸集、执行金额、执行状态 |

---

## 场景分析

### 场景一：NFP（非农就业数据）发布

> **事件**：Non-Farm Payrolls, 2026-03-06 13:30 UTC
> **Relevance**：98.67 → High Impact
> **受影响币种**：EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD

**时间线：**

| 时间 | 阶段 | PAMAS | ROMS |
| - | - | - | - |
| T-35min | 常态 | Spread 正常 | 正常对冲规则生效 |
| **T-30min** | **事件预警** | Calendar IPA 激活，价宽开始逐步放大 | 触发 flatten 指令，开始 TWAP 平仓减敞口 |
| T-15min | 加价中 | 价宽已达 ~2.5x | 平仓进度 50%，持续减仓 |
| T-1min | 接近峰值 | 价宽接近 3.0x | 预减仓完成，敞口已降至目标水平 |
| **T-0** | **事件发布** | 价宽锁定 3.0x 约1分钟 | **冻结 — 不做新的平仓操作**，等待数据消化 |
| T+1min | 恢复期开始 | 价宽开始衰减 | **开始处理剩余敞口**，根据 actual vs survey 偏差决定力度 |
| T+5min | 恢复中 | 价宽约 1.8x | 如偏差大（>20%），延长对冲窗口 |
| **T+15min** | **恢复正常** | 价宽恢复 1.0x | 恢复常规对冲规则 |

### 场景二：FOMC 利率决议（声明+新闻发布会）

> **特殊性**：FOMC 18:00 公布决议 + 18:30 主席新闻发布会 = 两个事件窗口可能重叠

**处理原则**：多事件取最大倍数。18:00 事件的恢复期与 18:30 事件的预热期重叠时，spread 保持在较高水平不下降。

### 场景三：夜间交割日切时段（0am-5am 北京时间）

> **已暴露问题复现**：AUD T2 交易在此时段实际为 T3
> **金融日历的作用**：标记此时段为"交割受限窗口"，PAMAS 可自动切换 tenor 或加宽 spread，ROMS 可暂停该币种的自动对冲

### 场景四：多事件同时发生

> 2026-03-12 20:30 同时有 7 个美国经济指标发布（Trade Balance, Initial Claims, Housing Starts 等）

**处理原则**：
- 取所有事件中 Relevance 最高的作为主事件
- 时间窗口取并集（最早的 pre_event 到最晚的 post_event）
- 如果 Trade Balance (Relevance=84.77) + Initial Claims (Relevance=98.67) 同时发布，按 High 级别处理

---

## 关键考虑点

| # | 考虑点 | 方案 |
| - | - | - |
| 1 | **多事件时间窗口重叠** | 取最大倍数，窗口取并集 |
| 2 | **Surprise 动态调整** | 事件发布后，if \|actual - survey\| / survey > 20% 则延长 post_event 窗口 50% |
| 3 | **手动覆盖** | 交易员可随时覆盖 Calendar IPA 倍数，覆盖记录需审计 |
| 4 | **交割日切兼容** | 考虑纽约时区 5pm 日切，避免出现类似 AUD T2→T3 的问题 |
| 5 | **容错降级** | 金融日历数据源不可用时，Calendar IPA 自动 bypass，报警通知 |
| 6 | **回测验证** | 上线前需基于历史事件数据回测 spread 和 P&L 影响 |
| 7 | **监控告警** | Calendar IPA 激活/恢复事件推送至运营群，异常倍数触发告警 |
| 8 | **与现有 Spread Adj 的交互** | Calendar IPA 输出的 spread 仍需经过 Spread Adj 的 min/max 约束 |

---

## 版本规划

| 分期 | 模块 | 工作概述 | 工期评估 | 备注 |
| - | - | - | - | - |
| **P0 基础能力** | 金融日历数据接入 | Bloomberg 数据解析、事件分级、存储 | 3d | 依赖现有 xlsx 数据源 |
|  | PAMAS Calendar IPA | IPA 实现 + 配置表 + 管理界面 | 5d | 嵌入现有 Pipeline |
|  | ROMS Calendar Hedge | 新增触发条件 + 规则配置 + 执行逻辑 | 5d | 复用现有对冲框架 |
| **P1 增强** | Surprise 动态调整 | actual 公布后动态调整恢复窗口 | 2d | |
|  | 多事件冲突处理 | 窗口合并、倍数择优 | 2d | |
|  | 手动覆盖 + 审计 | 覆盖 UI + 审计日志 | 3d | |
| **P2 高级** | 回测框架 | 历史事件回测 spread/P&L 影响 | 5d | |
|  | 交割日切集成 | 纽约时区日切 + tenor 联动 | 3d | |

---

## 附录

### A. xlsx 数据字段样例

```
Date Time          | Country | Event                      | Survey  | Actual  | Prior   | Relevance | Ticker
2026-03-12 20:30   | US      | Initial Jobless Claims     | 215k    | --      | 213k    | 98.67     | INJCJC Index
2026-03-12 20:30   | US      | Trade Balance              | -$66.0b | --      | -$70.3b | 84.77     | USTBTOT Index
2026-03-12 20:30   | US      | Housing Starts             | 1341k   | --      | 1404k   | 88.74     | NHSPSTOT Index
2026-03-18 02:00   | US      | FOMC Rate Decision (Upper) | 4.50%   | --      | 4.50%   | 99.34     | FDTR Index
2026-03-18 02:00   | US      | FOMC Rate Decision (Lower) | 4.25%   | --      | 4.25%   | 96.36     | FDTRMID Index
```

### B. 参考文档

- PAMAS Stage II 技术方案：Model Pricing LPA + Spread Adjustment IPA
- ROMS 自动对冲掉期方案：对冲规则、执行标的、触发变量体系
- ROMS 预平盘交易方案：预期敞口管理系统
- 金融日历拦截问题复盘：AUD T2/T3 交割日切问题

### C. Schema 调研来源

| 来源 | 内容 | 备注 |
| - | - | - |
| `fx_romshedge_db.t_trigger_condition` | 触发条件表结构及现有 var_type 枚举 | 新增 type=13 遵循递增模式 |
| `fx_romshedge_db.t_rule` | 自动对冲规则主表完整字段 | 新增 3 字段扩展日历功能 |
| `fx_romshedge_db.t_rule_range / t_rule_amount / t_rule_banktype` | 规则子表 | 直接复用无需改表 |
| `fx_romshedge_db.t_time_rule_execute_record_#yyyy#` | 时间规则执行记录（按年分表） | 参考分表模式设计日历执行记录表 |
| `AutoHedgeRuleStructuredEntity` | ROMS 规则实体结构 | 信号条件枚举新增 CALENDAR_EVENT |
| `data_query_conf.exrate_scenario_config` | PAMAS 场景配置表 | Calendar IPA 配置表参考其风格 |
