# 演示准备 Checklist v2
> 别慌，照着走一遍就好。
> 基于 v1 升级，新增 Financial Calendar、林徽因 Agent，调整演示优先级

---

## 前一天做的事

### 确保能跑
- [ ] 代码是最新的（`git pull`）
- [ ] 本地所有模块能正常启动
- [ ] 网络没问题（内网能不能访问外部 API？）
- [ ] VPN 如果要用的话，先连上试试
- [ ] **Node.js 环境确认**（Financial Calendar 需要 npm）

### 各模块跑一遍

**板块一：分析提效**
- [ ] Portal（8899）：`python portal.py` 能起来
- [ ] PnL Analysis（5005）：文件上传能分析
- [ ] Markup Pricing（8891）：加价能算

**板块二：交易决策**
- [ ] Strategy Lab（8888）：回测能跑
- [ ] BMAD Quant（5001/5002）：Bloomberg 连不连得上（有降级方案）
- [ ] Financial Calendar（5173）：`cd financial-calendar && python run.py`（首次需 npm install）

**板块四：Agent 探索**
- [ ] Soros Agent（8901）：能正常聊天
- [ ] 林徽因 Agent（8902）：能正常聊天（验证框架通用性）

**可选/弱化**
- [ ] FX Report Hub（8890）：一笔带过，不演示也行

### Financial Calendar 首次准备（⚠️ 重要）
```bash
cd financial-calendar
# 如果是第一次跑，需要安装依赖
npm install
# 启动
python run.py
# 或者直接 npx vite
# 访问 http://localhost:5173
```

### 备用截图（这个很重要！）
- [ ] 截图存到 `demo/screenshots/`
  - [ ] PnL Analysis 结果页（板块一主演示）
  - [ ] Strategy Lab 热力图（板块二演示）
  - [ ] Soros Agent 聊天 + 工具调用链（板块四演示）
  - [ ] Financial Calendar 事件模拟（板块二快带）
  - [ ] BMAD Quant Web 界面（板块二快带）
  - [ ] Markup Pricing 结果（可选）
- [ ] PPT 文件存一份在本地（断网也能用）

### 数据确认
- [ ] PnL Analysis 的示例 CSV 准备好了（演示用）
- [ ] Before/After 的对比数字想好了（"从 2 小时 → 2 分钟"）
- [ ] Strategy Lab 周五夜盘策略数据跑出来了

---

## 一小时前做的事

### 按演示优先级启动

```bash
# 工作目录
cd c:\Users\tencentren\CodeBuddy\FX_SYSTEM_DEMO

# 1. Portal 入口
python portal.py
# http://localhost:8899

# 2. PnL Analysis（板块一主演示 P1）
cd pnl-analysis && python app.py
# http://localhost:5005

# 3. Strategy Lab（板块二演示 P2）
cd strategy-lab && python app.py
# http://localhost:8888

# 4. Soros Agent（板块四演示 P3）
cd agents/soros && python app.py
# http://localhost:8901

# 5. Financial Calendar（板块二快带）
cd financial-calendar && python run.py
# http://localhost:5173

# 6. BMAD Quant（备用）
cd bmad-quant-system && python main.py web
# http://localhost:5002

# 7. Markup Pricing（备用）
cd markup-pricing && python markup_app.py
# http://localhost:8891

# 8. 林徽因 Agent（板块四备用）
cd agents/linhuiyin && python app.py
# http://localhost:8902
```

### API Key
- [ ] Claude API Key 还有效吧
- [ ] Perplexity API Key 还有效吧
- [ ] Bloomberg Terminal 连不连得上

### 预热一下（别让现场第一次跑就翻车）

**PnL Analysis**（P1 演示）：
```
上传示例 CSV，确认 9 个维度分析正常出结果
下载 Excel 看看格式对不对
```

**Strategy Lab**（P2 演示）：
```
跑一个周五夜盘策略回测
确认热力图正常出来
```

**Soros Agent**（P3 演示）：
```
问一句：今天 USD/CNH 大概在什么位置？
看看能不能 1-2 分钟内回复，工具调用链正常
```

**Financial Calendar**：
```
选一个 ECB 利率决议事件
点播放看看 spread 拉宽动画正常不
```

### 网络 Plan B
- [ ] 手机热点准备好（万一 WiFi 不行）
- [ ] Bloomberg 不行的话，Frankfurter API 能不能用

---

## 5 分钟前

- [ ] 所有服务都能访问
- [ ] PPT 打开了，停在第一页
- [ ] 备用截图放在容易找到的地方（桌面最好）
- [ ] `demo_script_v2.md` 打开着（对照用）

### 设备
- [ ] 投影/屏幕共享正常
- [ ] 外接显示器设置好了（如果用的话）

### 心态
- [ ] 深呼吸。这是分享，不是面试
- [ ] 出了问题不慌，反正有截图兜底
- [ ] 不知道的问题就说"好问题，我回去看看"

---

## 快速参考

### 端口速查表

| 模块 | 启动命令 | 端口 | 演示优先级 |
|------|---------|------|-----------|
| Portal | `python portal.py` | 8899 | — |
| PnL Analysis | `cd pnl-analysis && python app.py` | 5005 | P1 |
| Strategy Lab | `cd strategy-lab && python app.py` | 8888 | P2 |
| Soros Agent | `cd agents/soros && python app.py` | 8901 | P3 |
| Financial Calendar | `cd financial-calendar && python run.py` | 5173 | 快带 |
| BMAD Quant | `cd bmad-quant-system && python main.py web` | 5002 | 备用 |
| Markup Pricing | `cd markup-pricing && python markup_app.py` | 8891 | 备用 |
| 林徽因 Agent | `cd agents/linhuiyin && python app.py` | 8902 | 备用 |
| FX Report Hub | `cd fx-report && python app.py` | 8890 | 不演示 |

### 演示流程速览

| 板块 | 主演示 | 备选 | 截图兜底 |
|------|--------|------|---------|
| 分析提效 | PnL Analysis 拖 CSV | Markup Pricing | ✅ |
| 交易决策 | Strategy Lab 热力图 | Financial Calendar | ✅ |
| Agent 探索 | Soros Agent 对话 | 林徽因 Agent | ✅ |

---

## 翻车了怎么办

| 出了啥事 | 怎么办 |
|---------|--------|
| 某个服务起不来 | 跳过，用截图讲 |
| Soros 回复太慢 | "网有点卡"，切截图 |
| 热力图加载不出来 | 用备用截图 |
| Financial Calendar 报错 | npm install 后重试，或用截图 |
| 全挂了 | 只讲 PPT 就行，核心是方法论不是工具 |
| 被问不会的 | "好问题，我回去研究一下" |

---

## 当天速览

**前一天** ✅ 代码最新 / 截图准备好 / 数据确认 / npm install

**一小时前** ✅ 8 个服务启动 / API 有效 / 预热跑通

**5 分钟前** ✅ PPT 第一页 / 截图就位 / 深呼吸

---

*最后更新：2026-03-19 | v2.0*
