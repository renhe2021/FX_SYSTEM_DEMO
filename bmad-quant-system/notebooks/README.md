# Notebooks 实验目录

此目录用于存放所有的 Jupyter Notebook 实验和分析文件。

## 目录结构

```
notebooks/
├── README.md                        # 本文件
├── weekend_backtest_v3.ipynb       # 周末定价策略回测 (修正版)
├── drafts/                          # 草稿实验
│   ├── draft_001_USD_JPY_PnL.ipynb # USD/JPY PnL分析
│   └── ...
└── __init__.py
```

## 已有实验

### 正式实验

| Notebook | 描述 | 创建日期 |
|:---------|:-----|:---------|
| `weekend_backtest_v3.ipynb` | 周末JPYCNH定价策略完整回测，使用max(hour_0, hour_6)策略，PnL计算已修正 | 2026-01-30 |

### 草稿 (drafts/)

| Notebook | 描述 |
|:---------|:-----|
| `draft_001_USD_JPY_PnL.ipynb` | USD/JPY PnL初步分析 |

## 使用方法

```bash
cd notebooks
jupyter notebook
```

或者直接在 VS Code 中打开 `.ipynb` 文件。

## 数据目录

- 回测输出数据: `../output/`
- 草稿数据: `./drafts/data/`

## 命名规范

- 正式实验: `<主题>_<版本>.ipynb` (如 `weekend_backtest_v3.ipynb`)
- 草稿实验: `draft_<编号>_<描述>.ipynb` (如 `draft_001_USD_JPY_PnL.ipynb`)
