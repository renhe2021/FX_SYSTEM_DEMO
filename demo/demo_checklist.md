# 演示准备 Checklist
> 别慌，照着走一遍就好。

---

## 前一天做的事

### 确保能跑
- [ ] 代码是最新的
- [ ] 本地所有模块能正常启动
- [ ] 网络没问题（内网能不能访问外部 API？）
- [ ] VPN 如果要用的话，先连上试试

### 各模块跑一遍
- [ ] Portal（8899）：`python portal.py` 能起来
- [ ] Strategy Lab（8888）：回测能跑
- [ ] BMAD Quant（5002）：Bloomberg 连不连得上（连不上也没事，有降级方案）
- [ ] Markup Pricing（8891）：加价能算
- [ ] PnL Analysis（5004）：文件上传能分析
- [ ] Soros Agent（8901）：能正常聊天
- [ ] FX Report Hub（8080）：报告能生成

### 备用截图（这个很重要！）
- [ ] 截图存到 `demo/screenshots/`
  - [ ] Strategy Lab 热力图
  - [ ] Soros Agent 聊天截图
  - [ ] Markup Pricing 结果
- [ ] PPT 文件存一份在本地（断网也能用）

### 数据确认
- [ ] Friday Night Strategy 的具体数据跑出来了（胜率、Sharpe、最大回撤）
- [ ] Before/After 的对比数字想好了（比如"从 X 小时 → Y 分钟"）

---

## 一小时前做的事

### 按这个顺序启动

```bash
# 1. Portal 入口
cd /Users/tencentren/Downloads/FX_SYSTEM_DEMO && python portal.py
# 看看 http://localhost:8899

# 2. Strategy Lab（现场演示要用）
cd strategy-lab && python app.py
# http://localhost:8888

# 3. BMAD Quant（备用）
cd bmad-quant-system && python main.py web
# http://localhost:5002

# 4. Markup Pricing（可能演示）
cd markup-pricing && python markup_app.py
# http://localhost:8891

# 5. PnL Analysis（带一嘴就行）
cd pnl-analysis && python app.py
# http://localhost:5004

# 6. Soros Agent（可能演示）
cd agents/soros && python app.py
# http://localhost:8901

# 7. FX Report Hub（带一嘴就行）
cd fx-report && python app.py
# http://localhost:8080
```

### API Key
- [ ] Claude API Key 还有效吧
- [ ] Perplexity API Key 还有效吧
- [ ] Bloomberg Terminal 连不连得上

### 预热一下（别让现场第一次跑就翻车）

Soros Agent：
```
问一句：今天 USD/CNH 大概在什么位置？
看看能不能 1-2 分钟内回复
```

Strategy Lab：随便跑一个小数据集的回测，看看热力图出不出来

Markup Pricing：随便上传一个文件，看看能不能算

### 网络 Plan B
- [ ] 手机热点准备好（万一 WiFi 不行）
- [ ] Bloomberg 不行的话，Frankfurter API 能不能用

---

## 5 分钟前

- [ ] 所有服务都能访问
- [ ] PPT 打开了，停在第一页
- [ ] 备用截图放在容易找到的地方（桌面最好）
- [ ] `demo_script.md` 打开着

### 设备
- [ ] 投影/屏幕共享正常
- [ ] 外接显示器设置好了（如果用的话）

### 心态
- [ ] 深呼吸。这是分享，不是面试
- [ ] 出了问题不慌，反正有截图兜底
- [ ] 不知道的问题就说"好问题，我回去看看"

---

## 快速参考

| 模块 | 启动命令 | 端口 |
|------|---------|------|
| Portal | `python portal.py` | 8899 |
| Strategy Lab | `cd strategy-lab && python app.py` | 8888 |
| BMAD Quant | `cd bmad-quant-system && python main.py web` | 5002 |
| Markup Pricing | `cd markup-pricing && python markup_app.py` | 8891 |
| PnL Analysis | `cd pnl-analysis && python app.py` | 5004 |
| Soros Agent | `cd agents/soros && python app.py` | 8901 |
| FX Report Hub | `cd fx-report && python app.py` | 8080 |

---

## 翻车了怎么办

| 出了啥事 | 怎么办 |
|---------|--------|
| 某个服务起不来 | 跳过，用截图讲 |
| Soros 回复太慢 | "网有点卡"，切截图 |
| 热力图加载不出来 | 用备用截图 |
| 全挂了 | 只讲 PPT 就行，核心是方法论不是工具 |
| 被问不会的 | "好问题，我回去研究一下" |

---

## 当天速览

**前一天** ✅ 代码最新 / 截图准备好 / 数据确认

**一小时前** ✅ 7 个服务启动 / API 有效 / 预热跑通

**5 分钟前** ✅ PPT 第一页 / 截图就位 / 深呼吸

---

*最后更新：2026-03-19*