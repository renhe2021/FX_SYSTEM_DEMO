# FX_SYSTEM — Tenpay Global FX Platform

## Quick Start

```bash
# Clone
git clone https://github.com/renhe2021/bmad-quant-system.git
cd bmad-quant-system

# Install Python dependencies (pick the module you need)
pip install -r fx-report/requirements.txt
pip install -r bmad-quant-system/requirements.txt
pip install -r pnl-analysis/requirements.txt
pip install -r strategy-lab/requirements.txt
```

## Modules

| Module | Port | Description | Start Command |
|--------|------|-------------|---------------|
| **fx-report** | 8890 | FX Research Report Generator (AI-powered) | `cd fx-report && python app.py` |
| **bmad-quant-system** | 8891 | Weekend Prelock Quant Backtesting | `cd bmad-quant-system/backtest/dashboard && python app.py` |
| **pnl-analysis** | 8080 | PnL Analysis Dashboard | `cd pnl-analysis && python app.py` |
| **strategy-lab** | 5000 | Strategy Lab | `cd strategy-lab && python app.py` |
| **markup-pricing** | 8501 | FX Markup Pricing Engine | `cd markup-pricing && python markup_app.py` |

## Key Config Files

- `fx-report/config.yaml` — API keys (Perplexity, fit-ai LLM proxy), client profiles, report settings
- `bmad-quant-system/backtest/dashboard/config.yaml` — Backtest dashboard LLM config
- `bmad-quant-system/configs/` — Strategy YAML configs

## AI Integration (fx-report)

The FX Report Generator uses:
- **Perplexity API** (sonar model) — real-time FX news search
- **fit-ai LLM Proxy** — Executive Summary generation (Claude/GPT/Gemini via internal proxy)
- Configured in `fx-report/config.yaml` under `ai:` and `llm:` sections
