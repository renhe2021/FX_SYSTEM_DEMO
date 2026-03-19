# Financial Calendar System - Design & Demo

## 金融日历系统 — 设计文档与交互式Dashboard

> **用途**：展示金融日历（Financial Calendar）如何驱动外汇交易系统的两大核心响应机制：
> - **PAMAS** (Pricing Agent & Market Making System) → Spread Widening（点差拉宽）
> - **ROMS** (Risk & Order Management System) → Exposure Flattening（敞口平仓）

---

## 📁 项目结构

```
project-root/
├── docs/                                    # 设计文档
│   ├── financial-calendar-design.md         # 金融日历系统完整设计说明书
│   └── diagrams/
│       ├── system-architecture.drawio       # 系统架构图（Draw.io格式）
│       └── sequence-flow.drawio             # 事件触发时序图（Draw.io格式）
├── dashboard/                               # Web Dashboard Demo（React）
│   ├── src/
│   │   ├── components/                      # UI组件
│   │   ├── engine/                          # 模拟引擎
│   │   ├── data/                            # 数据源
│   │   └── types/                           # TypeScript类型
│   └── ...
└── README.md                                # 本文件
```

---

## 📖 设计文档阅读指引

### 核心文档

| 文档 | 路径 | 内容 |
|------|------|------|
| **设计说明书** | `docs/financial-calendar-design.md` | 完整的系统设计文档，含架构概述、PAMAS/ROMS集成方案、8项关键考虑点 |
| **系统架构图** | `docs/diagrams/system-architecture.drawio` | Financial Calendar与PAMAS Pipeline/ROMS Signal的集成关系拓扑图 |
| **事件时序图** | `docs/diagrams/sequence-flow.drawio` | 从事件调度到spread widening和敞口平仓的完整时序流程 |

### 文档关键章节

1. **系统概述** — 金融日历在PAMAS和ROMS中的定位
2. **PAMAS Pipeline集成** — Calendar IPA的设计、Pipeline中的位置、三阶段spread计算
3. **ROMS信号模块集成** — 信号触发→敞口计算→自动对冲的完整流程
4. **事件影响等级与参数映射** — High/Medium/Low事件的拉宽倍数和时间窗口配置
5. **关键设计考虑点** — 事件冲突处理、手动覆盖、回测验证、容错降级

---

## 🖥️ Dashboard Demo

### 启动方式

```bash
cd dashboard
npm install
npm run dev
```

访问 http://localhost:5173 即可打开Dashboard。

### Dashboard功能

| 区域 | 功能 | 交互 |
|------|------|------|
| **Economic Calendar** (左上) | 展示经济事件列表，按时间排序 | 点击事件启动模拟 |
| **Event Configuration** (左下) | 展示选中事件的拉宽参数配置 | 拖动滑块手动覆盖倍数 |
| **Spread Timeline** (中央) | Recharts折线图展示spread变化 | 随时间线自动更新 |
| **Timeline Player** (顶部) | 播放/暂停/拖动时间线 | 支持0.5x/1x/2x/5x倍速 |
| **PAMAS Pipeline** (底部) | 可视化Pipeline链路 | Calendar IPA高亮+实时倍数 |
| **ROMS Signals** (右上) | 展示敞口平仓信号和进度 | 实时执行进度条 |
| **Exposure Monitor** (右下) | 圆形仪表盘展示敞口水平 | 动态展示敞口减少过程 |

### 演示流程

1. 从左侧日历选择一个经济事件（如 "ECB Interest Rate Decision"）
2. 点击播放按钮，观察时间线推进
3. 中央图表展示选中事件影响的各币种对spread如何在事件前后变化
4. 右侧面板实时展示ROMS信号触发和敞口变化
5. 底部Pipeline图展示Calendar IPA何时被激活及当前拉宽倍数
6. 可拖动左下角滑块手动覆盖拉宽倍数（模拟交易员干预）

---

## 🏗️ 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.3 | UI框架 |
| TypeScript | 5.6 | 类型安全 |
| Vite | 5.4 | 构建工具 |
| Tailwind CSS | 3.4 | 样式方案 |
| Recharts | 3.x | 图表库 |
| Lucide React | latest | 图标库 |

---

## 🔑 核心概念

### PAMAS Spread Widening（点差拉宽）

```
正常状态 → 事件前拉宽(渐进) → 峰值(最大倍数) → 恢复(指数衰减) → 正常
  1.0x         1.0x → 3.0x          3.0x          3.0x → 1.0x       1.0x
```

### ROMS Exposure Flattening（敞口平仓）

| 事件影响 | ROMS动作 | 平仓比例 |
|---------|---------|---------|
| High | Flatten | 100% |
| Medium | Reduce | 50% |
| Low | Monitor | 0% (仅监控) |

---

## 📊 Draw.io 图表查看

Draw.io文件可通过以下方式打开：
- **在线**：访问 [draw.io](https://app.diagrams.net/) → File → Open from → Device
- **VS Code**：安装 "Draw.io Integration" 扩展
- **桌面端**：下载 [draw.io Desktop](https://github.com/jgraph/drawio-desktop/releases)
