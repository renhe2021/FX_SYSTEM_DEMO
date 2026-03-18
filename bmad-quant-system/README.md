# BMAD Quant System

**Bloomberg Market Analysis & Data Quantitative Trading System**

一个集成的量化交易系统，专注于外汇市场（特别是USDCNH）的数据获取、策略开发和回测分析。

## 🚀 主要功能

### 1. Bloomberg 数据工具箱
- **实时数据下载**: 支持K线、Tick、Bid/Ask等多种数据类型
- **数据可视化**: 友好的Web界面进行数据探索和分析
- **格式转换**: 支持CSV、Excel等多种导出格式
- **时区处理**: 自动处理UTC到北京时间的转换

### 2. 策略回测系统
- **周五夜盘策略**: 专门针对USDCNH周五21:00-周六02:00的交易策略
- **多策略支持**: 移动平均、动量等多种策略模板
- **风险管理**: 内置止损、止盈和仓位管理
- **性能分析**: 详细的回测报告和可视化

### 3. Web界面
- **策略管理**: 在线配置和管理交易策略
- **实时监控**: 实时查看策略运行状态
- **回测分析**: 交互式回测结果展示
- **数据管理**: 在线数据下载和管理

### 4. 微信小程序
- **移动端监控**: 随时随地查看策略状态
- **推送通知**: 重要事件实时推送
- **简洁界面**: 专为移动端优化的用户体验

## 📦 安装和使用

### 环境要求
```bash
Python 3.8+
Bloomberg Terminal (用于实时数据)
```

### 安装依赖
```bash
pip install -r quant_system/requirements.txt
```

### 快速开始

#### 1. 启动数据探索器
```bash
python bmad_main.py data-explorer --port 5001
```
访问 http://127.0.0.1:5001 查看Bloomberg数据工具箱

#### 2. 启动Web UI
```bash
python bmad_main.py web --port 8080
```
访问 http://127.0.0.1:8080 查看策略管理界面

#### 3. 下载Bloomberg数据
```bash
python bmad_main.py fetch-data --start 2024-01-01 --end 2024-12-31 --interval 15
```

#### 4. 运行策略回测
```bash
python bmad_main.py backtest --config configs/friday_bbg.yaml
```

### 传统方式启动
```bash
# 数据探索器
python run_data_explorer.py

# Web UI
python run_web.py

# 回测
python run.py --config configs/friday_bbg.yaml

# 数据下载
python fetch_bbg_data.py
```

## 📁 项目结构

```
bmad-quant-system/
├── bmad_main.py              # 统一入口脚本
├── run_data_explorer.py      # 数据探索器入口
├── run_web.py               # Web UI入口
├── run.py                   # 回测系统入口
├── fetch_bbg_data.py        # Bloomberg数据下载
├── configs/                 # 策略配置文件
│   ├── friday_bbg.yaml     # Bloomberg数据配置
│   ├── friday_local.yaml   # 本地数据配置
│   └── friday_template.yaml # 配置模板
├── quant_system/           # 核心系统
│   ├── agent/              # 回测引擎
│   ├── base/               # 数据源抽象
│   ├── config/             # 配置管理
│   ├── display/            # 可视化
│   ├── model/              # 策略模型
│   │   └── strategies/     # 具体策略
│   ├── storage/            # 数据存储
│   ├── tools/              # Bloomberg工具
│   └── web/                # Web界面
├── miniprogram/            # 微信小程序
├── output/                 # 输出文件
└── README.md
```

## 🎯 核心策略

### 周五夜盘策略 (Friday Night Strategy)
- **交易时间**: 周五21:00 - 周六02:00 (北京时间)
- **交易品种**: USDCNH
- **策略逻辑**: 基于周五夜盘特殊流动性特征的趋势跟踪
- **风险控制**: 动态止损、固定止盈、时间止损

## 📊 数据支持

### Bloomberg API
- **K线数据**: 1分钟到日线多个周期
- **Tick数据**: 逐笔成交记录
- **Bid/Ask**: 买卖盘报价数据
- **参考数据**: 合约信息、基本面数据

### 本地数据
- **CSV格式**: 标准OHLCV格式
- **Excel格式**: 多sheet支持
- **数据库**: SQLite/MySQL支持

## 🔧 配置说明

### 策略配置 (configs/friday_bbg.yaml)
```yaml
strategy:
  name: "friday_night"
  symbol: "USDCNH Curncy"
  
data_source:
  type: "bloomberg"
  host: "localhost"
  port: 8194
  
risk_management:
  stop_loss: 0.002
  take_profit: 0.004
  max_position: 1000000
```

## 📈 性能监控

- **实时PnL**: 实时损益计算
- **风险指标**: VaR、最大回撤、夏普比率
- **交易统计**: 胜率、平均盈亏、交易频率
- **可视化图表**: K线图、权益曲线、回撤分析

## 🛠️ 开发指南

### 添加新策略
1. 在 `quant_system/model/strategies/` 创建策略文件
2. 继承 `BaseStrategy` 类
3. 实现 `generate_signals()` 方法
4. 在配置文件中注册策略

### 添加新数据源
1. 在 `quant_system/base/` 实现数据源类
2. 继承 `BaseDataSource` 抽象类
3. 实现必要的接口方法

## 📞 联系方式

- **GitHub**: https://github.com/renhe2021/bmad-quant-system
- **Email**: renhe2021@gmail.com

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

**免责声明**: 本系统仅供学习和研究使用，不构成投资建议。使用本系统进行实盘交易的风险由用户自行承担。