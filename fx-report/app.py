# -*- coding: utf-8 -*-
"""
FX Research Report Generator — Flask Web Application
=====================================================
Web UI for editing commentary, selecting sections, client profiles, and generating PDF reports.
Investment-bank grade design with client-profile-aware corridor analysis.
"""
import os
import sys
import yaml
import json
import socket
import subprocess
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, render_template_string, jsonify, request, send_file, Response
from flask_cors import CORS

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from report_generator import ReportGenerator
from data_provider import FXDataProvider
from client_store import ClientStore

app = Flask(__name__)
CORS(app)

with open(BASE_DIR / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize Client Portal store and seed from config.yaml
CLIENT_STORE = ClientStore()
CLIENT_STORE.seed_from_config(CONFIG)

# Load official logo as base64 for Web UI embedding
LOGO_B64 = ""
_logo_path = BASE_DIR / "data" / "WXWorkCapture_17724263838761.png"
if _logo_path.exists():
    import base64
    LOGO_B64 = base64.b64encode(_logo_path.read_bytes()).decode("ascii")

# ──────────────────────────────────────────────────────────────
WEB_UI = r"""
<!DOCTYPE html>
<html lang="zh" id="htmlRoot">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TenPay 智研 · FX Intelligence</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Serif+Display&family=Noto+Sans+SC:wght@300;400;500;700&family=Noto+Serif+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
<script>
tailwind.config = {
  theme: {
    extend: {
      colors: {
        brand: {
          dark:'#0F172A',
          primary:'#0052D9',
          accent:'#2563EB',
          light:'#EFF6FF',
          hover:'#1D4ED8',
          gold:'#B8860B',
          bg:'#F8FAFC',
          muted:'#64748B',
        },
      },
      fontFamily: {
        serif: ['Noto Serif SC', 'DM Serif Display', 'Georgia', 'serif'],
        sans: ['Inter', 'Noto Sans SC', 'PingFang SC', '-apple-system', 'BlinkMacSystemFont', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
    }
  }
}
</script>
<style>
  body { font-family: 'Inter', 'Noto Sans SC', 'PingFang SC', '-apple-system', 'BlinkMacSystemFont', 'Helvetica Neue', 'Arial', sans-serif; background: #F8FAFC; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility; line-height: 1.6; letter-spacing: 0.01em; }
  .font-serif { font-family: 'Noto Serif SC', 'DM Serif Display', 'Georgia', serif; }
  h1, h2, h3, h4 { letter-spacing: 0.02em; }
  .header-bar { background: white; border-bottom: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02); }
  .accent-line { background: linear-gradient(90deg, #0052D9, #2563EB, #7C3AED); height: 3px; }
  textarea { resize: vertical; }
  .spinner { animation: spin 1s linear infinite; }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  .card { background: white; border-radius: 14px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.03), 0 1px 2px rgba(0,0,0,0.02); transition: box-shadow 0.2s, transform 0.15s; }
  .card:hover { box-shadow: 0 8px 25px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.03); }
  .section-toggle { transition: all 0.2s; }
  .section-toggle:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .fade-in { animation: fadeIn 0.4s ease-out; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
  .tab-btn { transition: all 0.2s; border-radius: 8px; }
  .tab-btn.active { background: #0F172A; color: white; box-shadow: 0 1px 3px rgba(15,23,42,0.2); }
  .news-card { transition: all 0.2s; }
  .news-card:hover { background: #EFF6FF; }
  .profile-card { transition: all 0.15s; cursor: pointer; border: 2px solid transparent; }
  .profile-card:hover { border-color: #0052D9; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,82,217,0.12); }
  .profile-card.selected { border-color: #0052D9; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); }
  .corridor-badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600; }
  .corridor-inbound { background: #D1FAE5; color: #065F46; }
  .corridor-outbound { background: #FEF0EF; color: #991B1B; }
  .bbg-badge { display: inline-block; padding: 1px 6px; border-radius: 8px; font-size: 9px; font-weight: 700; background: #FEF3C7; color: #92400e; margin-left: 4px; }
  .data-source-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
  input:focus, select:focus, textarea:focus { outline: none; box-shadow: 0 0 0 3px rgba(0,82,217,0.12); border-color: #0052D9; }
  .lang-btn { transition: all 0.15s; cursor: pointer; padding: 3px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid #E2E8F0; color: #64748B; background: white; }
  .lang-btn:hover { background: #F1F5F9; color: #0F172A; }
  .lang-btn.active { background: #0F172A; border-color: #0F172A; color: white; }
  .gen-btn { background: linear-gradient(135deg, #0052D9 0%, #2563EB 50%, #1D4ED8 100%); transition: all 0.2s; }
  .gen-btn:hover { background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 50%, #1E3A8A 100%); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,82,217,0.3); }
  .gen-btn:active { transform: translateY(0); }
  .section-label { font-size: 11px; font-weight: 500; letter-spacing: 0.12em; color: #64748B; font-family: 'Noto Sans SC', 'Inter', sans-serif; }
  .card p, .card span, .card label, .card div { font-feature-settings: 'kern' 1, 'liga' 1; }
  select, input, textarea { font-family: 'Inter', 'Noto Sans SC', 'PingFang SC', sans-serif; letter-spacing: 0.01em; }
  button { font-family: 'Inter', 'Noto Sans SC', 'PingFang SC', sans-serif; letter-spacing: 0.02em; }
</style>
</head>
<body class="min-h-screen">

<!-- Header -->
<div class="accent-line"></div>
<div class="header-bar">
  <div class="max-w-7xl mx-auto px-8 py-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-5">
        <!-- TenPay Global Official Logo -->
        <img src="data:image/png;base64,__LOGO_B64__" style="height:42px;width:auto;" alt="TenPay Global" class="flex-shrink-0">
        <div class="h-10 w-px bg-gray-200"></div>
        <div>
          <h1 class="text-xl text-brand-dark" style="font-family:'Noto Serif SC','DM Serif Display','Georgia',serif; font-weight:600; letter-spacing:0.06em;" id="uiTitle">TenPay 智研</h1>
          <p class="text-[11px] mt-1" style="color:#94A3B8; font-weight:300; letter-spacing:0.08em;" id="uiSubtitle">跨境支付 · 走廊洞察 · 市场研判 · 定制研报</p>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-1">
          <button class="lang-btn" id="langEN" onclick="switchLang('en')">EN</button>
          <button class="lang-btn active" id="langZH" onclick="switchLang('zh')">中</button>
        </div>
        <div class="h-6 w-px bg-gray-200"></div>
        <div class="text-right">
          <div class="text-[11px] text-brand-muted" id="currentDate"></div>
          <div class="flex items-center gap-1.5 mt-0.5 justify-end">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
            <span class="text-[10px] text-brand-muted" id="dataSourceLabel">样本数据</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="max-w-7xl mx-auto px-8 py-8">

  <!-- Status bar -->
  <div id="statusBar" class="hidden mb-6 p-4 rounded-xl text-sm font-medium fade-in"></div>

  <!-- ═══ CLIENT PROFILE SELECTOR ═══ -->
  <div class="card p-6 mb-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="section-label" data-i18n="client_profile">客户档案</h3>
        <p class="text-[10px] text-gray-400 mt-0.5" data-i18n="client_profile_desc">选择目标客户以定制报告内容、走廊和基础货币</p>
      </div>
      <div class="flex items-center gap-2">
        <div id="selectedProfileBadge" class="hidden px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-xs font-semibold text-blue-800"></div>
        <button onclick="openPortalModal()" class="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-md transition-all font-semibold border border-slate-200" title="打开客户门户管理客户">
          管理客户
        </button>
      </div>
    </div>
    <!-- Region filter tabs -->
    <div class="flex gap-1 mb-3 flex-wrap" id="regionTabs">
      <button class="text-[9px] font-semibold px-2.5 py-1 rounded-md bg-brand-dark text-white region-tab" onclick="filterRegion('', this)">全部</button>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2" id="profileGrid"></div>
  </div>

  <!-- ═══ CLIENT CORRIDORS (shown when profile selected) ═══ -->
  <div id="corridorPanel" class="card p-6 mb-6 hidden fade-in">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="section-label" data-i18n="active_corridors">活跃走廊</h3>
        <p class="text-[10px] text-gray-400 mt-0.5"><span data-i18n="base_currency">基础货币</span>: <span id="baseCurrencyLabel" class="font-bold text-brand-dark">—</span></p>
      </div>
      <div class="text-[10px] text-gray-400">央行: <span id="centralBankLabel" class="font-medium text-gray-600">—</span></div>
    </div>
    <div id="corridorList" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2"></div>
    <div class="mt-4 pt-3 border-t border-gray-100">
      <h4 class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">关键关注点</h4>
      <div id="concernsList" class="text-xs text-gray-600 space-y-1"></div>
    </div>

    <!-- ═══ SPECIFIC REQUIREMENTS (shown when profile selected) ═══ -->
    <div class="mt-4 pt-3 border-t border-gray-100">
      <div class="flex items-center justify-between mb-2">
        <h4 class="text-[10px] font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
          <span style="color:#7C3AED;">&#x2728;</span> AI Analysis Requirements
        </h4>
        <button onclick="openRequirementsDialog()" class="text-[9px] font-medium px-2 py-1 rounded-md text-purple-600 bg-purple-50 border border-purple-200 hover:bg-purple-100 transition-all">
          编辑
        </button>
      </div>
      <div id="requirementsPreview" class="text-[10px] text-gray-400 italic">未设置特定需求 — Claude 将使用默认分析</div>
    </div>
  </div>

  <!-- ═══ SPECIFIC REQUIREMENTS DIALOG ═══ -->
  <div id="requirementsDialog" class="fixed inset-0 z-50 hidden" style="backdrop-filter: blur(2px);">
    <div class="absolute inset-0 bg-black/30" onclick="closeRequirementsDialog()"></div>
    <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-purple-50 to-white">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-sm font-serif text-brand-dark flex items-center gap-2">
              <span style="color:#7C3AED;">&#x2728;</span> 特定分析需求
            </h3>
            <p class="text-[10px] text-gray-400 mt-0.5" id="reqDialogSubtitle">为 Claude AI 提供自定义指令以增强报告内容</p>
          </div>
          <button onclick="closeRequirementsDialog()" class="text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
        </div>
      </div>
      <div class="p-6">
        <div class="mb-4">
          <label class="block text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">自定义需求 / 提示词</label>
          <textarea id="specificRequirementsText" rows="6"
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-700 focus:ring-2 focus:ring-purple-400 focus:border-purple-400 resize-y leading-relaxed"
            placeholder="示例：&#10;&#10;&#x2022; 分析近期美国关税公告对东南亚货币的影响&#10;&#x2022; 分析未来3个月VND贬值风险及对冲建议&#10;&#x2022; 比较我们的走廊成本与市场基准&#10;&#x2022; 包含CNH/VND交叉汇率波动率分析&#10;&#x2022; 评估越南外汇市场监管变化及对我们结算流的潜在影响"></textarea>
        </div>
        <div class="mb-4">
          <label class="block text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">快速模板</label>
          <div class="flex flex-wrap gap-1.5">
            <button onclick="appendRequirement('分析对冲策略，并针对当前市场状况提供具体建议')" class="text-[9px] px-2 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-600 hover:bg-purple-50 hover:border-purple-200 hover:text-purple-600 transition-all">对冲策略</button>
            <button onclick="appendRequirement('关注未来30天内可能影响我们外汇走廊的监管和央行政策变化')" class="text-[9px] px-2 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-600 hover:bg-purple-50 hover:border-purple-200 hover:text-purple-600 transition-all">监管聚焦</button>
            <button onclick="appendRequirement('提供成本优化分析 — 比较当前加价与竞争对手基准，识别节约机会')" class="text-[9px] px-2 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-600 hover:bg-purple-50 hover:border-purple-200 hover:text-purple-600 transition-all">成本优化</button>
            <button onclick="appendRequirement('包含季节性资金流分析及下一季度预测')" class="text-[9px] px-2 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-600 hover:bg-purple-50 hover:border-purple-200 hover:text-purple-600 transition-all">季节性规律</button>
            <button onclick="appendRequirement('评估地缘政治风险（贸易摩擦、制裁、选举）及其对我们货币敞口的潜在影响')" class="text-[9px] px-2 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-600 hover:bg-purple-50 hover:border-purple-200 hover:text-purple-600 transition-all">地缘政治风险</button>
            <button onclick="appendRequirement('分析新兴市场货币压力指标，提供预警信号')" class="text-[9px] px-2 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-600 hover:bg-purple-50 hover:border-purple-200 hover:text-purple-600 transition-all">新兴市场压力</button>
          </div>
        </div>
        <div class="flex items-center justify-between pt-3 border-t border-gray-100">
          <button onclick="clearRequirements()" class="text-[10px] text-gray-400 hover:text-red-500 transition-all">全部清除</button>
          <div class="flex gap-2">
            <button onclick="closeRequirementsDialog()" class="text-[10px] px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-all font-medium">取消</button>
            <button onclick="saveRequirements()" class="text-[10px] px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700 transition-all font-medium shadow-sm">保存需求</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══ MAIN LAYOUT ═══ -->
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

    <!-- LEFT SIDEBAR: Settings (3 cols) -->
    <div class="lg:col-span-3 space-y-5">

      <div class="card p-5">
        <h3 class="section-label mb-4" data-i18n="report_settings">报告设置</h3>
        <label class="block text-xs font-medium text-gray-500 mb-1">报告日期</label>
        <input type="date" id="reportDate" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-primary focus:border-brand-primary">

        <label class="block text-xs font-medium text-gray-500 mt-4 mb-1">输出格式</label>
        <select id="outputFormat" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-primary">
          <option value="pdf">PDF 报告</option>
          <option value="html" selected>HTML（浏览器打印为 PDF）</option>
        </select>

        <label class="block text-xs font-medium text-gray-500 mt-4 mb-1">Alpha Vantage API 密钥</label>
        <input type="text" id="apiKey" placeholder="可选 — 启用实时数据"
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-brand-primary font-mono">
        <p class="text-[10px] text-gray-400 mt-1">免费获取 <a href="https://www.alphavantage.co/support/#api-key" target="_blank" class="text-brand-primary underline">alphavantage.co</a></p>
      </div>

      <!-- AI Integration Settings -->
      <div class="card p-5 border-purple-100">
        <h3 class="section-label mb-3" style="color:#7C3AED;">AI 集成</h3>
        <label class="block text-xs font-medium text-gray-500 mb-1">Perplexity API 密钥</label>
        <input type="text" id="perplexityKey" placeholder="AI 新闻搜索必需"
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-purple-400 font-mono">
        <p class="text-[10px] text-gray-400 mt-1">获取密钥 <a href="https://www.perplexity.ai/settings/api" target="_blank" class="text-purple-600 underline">perplexity.ai/settings/api</a></p>

        <label class="block text-xs font-medium text-gray-500 mt-3 mb-1">Claude API 密钥</label>
        <input type="text" id="claudeKey" placeholder="AI 摘要生成必需"
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-purple-400 font-mono">
        <p class="text-[10px] text-gray-400 mt-1">获取密钥 <a href="https://console.anthropic.com/settings/keys" target="_blank" class="text-purple-600 underline">console.anthropic.com</a></p>
      </div>

      <div class="card p-5">
        <h3 class="section-label mb-3">报告章节</h3>
        <div class="space-y-1.5" id="sectionsContainer"></div>
      </div>

      <button id="generateBtn" onclick="generateReport()"
        class="gen-btn w-full text-white font-semibold py-3.5 px-6 rounded-xl shadow-lg text-sm tracking-wide" data-i18n="generate">
        Generate Report
      </button>

      <div id="resultPanel" class="hidden card p-5 fade-in">
        <h3 class="section-label mb-3">输出</h3>
        <div class="space-y-2">
          <a id="downloadLink" href="#" class="gen-btn block w-full text-center text-white py-2.5 px-4 rounded-lg text-sm font-semibold">
            下载报告
          </a>
          <a id="previewLink" href="#" target="_blank" class="block w-full text-center border border-gray-200 hover:bg-gray-50 text-gray-600 py-2 px-4 rounded-lg text-xs font-medium transition-all">
            在新标签页打开
          </a>
        </div>
        <p id="resultInfo" class="text-[10px] text-gray-400 mt-2 font-mono"></p>
      </div>
    </div>

    <!-- MIDDLE: Commentary Editor (5 cols) -->
    <div class="lg:col-span-5 space-y-5">
      <div class="flex gap-1 bg-gray-100 p-1 rounded-lg">
        <button class="tab-btn active flex-1 text-xs font-semibold py-2 px-3 rounded-md" onclick="switchTab('commentary', this)">评论编辑</button>
        <button class="tab-btn flex-1 text-xs font-semibold py-2 px-3 rounded-md text-gray-500 hover:text-gray-700" onclick="switchTab('news', this)">新闻与事件</button>
      </div>

      <div id="tab-commentary" class="space-y-5">
        <div class="card p-6">
          <h3 class="section-label mb-1" data-i18n="commentary">报告评论</h3>
          <p class="text-[10px] text-gray-400 mb-5">自定义叙述章节。留空则使用基于客户画像自动生成的内容。</p>
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">执行摘要</label>
              <textarea id="exec_summary" rows="4" placeholder="基于所选客户画像自动生成..."
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm leading-relaxed focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"></textarea>
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">市场观点</label>
              <textarea id="market_view" rows="4" placeholder="当前市场动态、关键驱动因素、央行政策..."
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm leading-relaxed focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"></textarea>
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">风险评估</label>
              <textarea id="risk_assessment" rows="3" placeholder="该客户走廊的主要风险..."
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm leading-relaxed focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"></textarea>
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">展望</label>
              <textarea id="outlook" rows="3" placeholder="关键货币对的前瞻性分析..."
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm leading-relaxed focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"></textarea>
            </div>
          </div>
        </div>
      </div>

      <div id="tab-news" class="space-y-5 hidden">
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="section-label">市场新闻与情绪</h3>
            <div class="flex items-center gap-2">
              <button onclick="loadAINews()" class="text-[10px] bg-purple-50 hover:bg-purple-100 text-purple-700 px-3 py-1.5 rounded-md transition-all font-semibold border border-purple-200" title="通过 Perplexity AI 基于客户画像获取新闻">
                AI 新闻
              </button>
              <button onclick="loadNews()" class="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-md transition-all font-medium">
                获取最新
              </button>
            </div>
          </div>
          <!-- AI Search Prompts Preview -->
          <div id="aiPromptsPreview" class="hidden mb-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <div class="flex items-center justify-between mb-2">
              <p class="text-[10px] font-bold text-purple-700">使用的搜索提示词</p>
              <button onclick="document.getElementById('aiPromptsPreview').classList.add('hidden')" class="text-[9px] text-purple-400 hover:text-purple-600">隐藏</button>
            </div>
            <div id="aiPromptsList" class="text-[9px] text-purple-600 space-y-0.5"></div>
          </div>
          <div id="newsContainer" class="space-y-2">
            <p class="text-xs text-gray-400 italic py-4 text-center">点击「AI 新闻」通过 Perplexity 获取客户相关新闻，或点击「获取最新」使用 Alpha Vantage</p>
          </div>
        </div>
        <!-- AI Generate Summary Button -->
        <div class="card p-4 border-purple-100 bg-gradient-to-r from-purple-50/50 to-white">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-[10px] font-bold text-purple-700 uppercase tracking-wider">AI 执行摘要</h4>
              <p class="text-[9px] text-purple-400 mt-0.5">使用 Claude 基于已获取的新闻和市场数据生成评论</p>
            </div>
            <button onclick="generateAISummary()" id="aiSummaryBtn"
              class="text-xs bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-all font-semibold shadow-sm">
              生成摘要
            </button>
          </div>
        </div>
        <div class="card p-6">
          <h3 class="section-label mb-3">即将到来的风险事件</h3>
          <div id="eventsContainer" class="space-y-2">
            <p class="text-xs text-gray-400 italic py-4 text-center">加载中...</p>
          </div>
        </div>
      </div>
    </div>

    <!-- RIGHT: Live Data Preview (4 cols) -->
    <div class="lg:col-span-4 space-y-5">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="section-label">市场数据</h3>
          <div class="flex items-center gap-2">
            <select id="dataSourceSelect" onchange="loadPreview()" class="text-[10px] border border-gray-200 rounded-md px-2 py-1.5 bg-white font-semibold text-gray-600 focus:ring-2 focus:ring-brand-primary focus:border-brand-primary cursor-pointer">
              <option value="">自动（最优源）</option>
              <option value="bloomberg">Bloomberg</option>
              <option value="ecb">ECB (Frankfurter)</option>
              <option value="exchangerate-api">ExchangeRate-API</option>
            </select>
            <button onclick="loadPreview()" class="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-md transition-all font-medium">
              刷新
            </button>
          </div>
        </div>
        <div id="dataSourceHint" class="hidden mb-3 p-2 bg-blue-50 border border-blue-100 rounded-lg text-[9px] text-blue-700 leading-relaxed"></div>
        <div id="dataPreview" class="text-sm text-gray-600">
          <div class="py-8 text-center">
            <div class="text-gray-300 text-2xl mb-2">$</div>
            <p class="text-xs text-gray-400">点击刷新预览市场数据</p>
          </div>
        </div>
      </div>

      <div class="card p-5 border-blue-100 bg-gradient-to-br from-white to-slate-50/60">
        <h3 class="section-label mb-3" data-i18n="data_sources">数据来源</h3>
        <div class="space-y-2.5 text-xs">
          <div class="flex items-start gap-2">
            <span class="data-source-dot mt-1.5 shrink-0" style="background:#00A870;"></span>
            <div><span class="font-semibold text-gray-700">Frankfurter (ECB)</span><br><span class="text-gray-400">30+ 种货币汇率 — 免费，无需密钥</span></div>
          </div>
          <div class="flex items-start gap-2">
            <span class="data-source-dot mt-1.5 shrink-0" style="background:#2563EB;"></span>
            <div><span class="font-semibold text-gray-700">ExchangeRate-API</span><br><span class="text-gray-400">160+ 种货币含 VND、TWD — 免费，无需密钥</span></div>
          </div>
          <div class="flex items-start gap-2">
            <span class="data-source-dot bg-brand-primary mt-1.5 shrink-0"></span>
            <div><span class="font-semibold text-gray-700">Alpha Vantage</span><br><span class="text-gray-400">新闻情绪、经济指标 — 需要免费 API 密钥</span></div>
          </div>
          <div class="flex items-start gap-2">
            <span class="data-source-dot mt-1.5 shrink-0" style="background:#F5A623;"></span>
            <div><span class="font-semibold text-gray-700">Bloomberg Terminal</span> <span class="bbg-badge">BBG</span><br><span class="text-gray-400">波动率曲面、经济日历 — 需要 Bloomberg 终端</span></div>
          </div>
          <div class="flex items-start gap-2">
            <span class="data-source-dot mt-1.5 shrink-0" style="background:#7C3AED;"></span>
            <div><span class="font-semibold text-gray-700">Perplexity AI</span> <span class="bbg-badge" style="background:#EDE9FE;color:#6D28D9;">AI</span><br><span class="text-gray-400">通过 sonar 模型实时搜索新闻 — 需要 API 密钥</span></div>
          </div>
          <div class="flex items-start gap-2">
            <span class="data-source-dot mt-1.5 shrink-0" style="background:#D97706;"></span>
            <div><span class="font-semibold text-gray-700">Claude AI</span> <span class="bbg-badge" style="background:#FEF3C7;color:#92400E;">AI</span><br><span class="text-gray-400">执行摘要生成 — 需要 API 密钥</span></div>
          </div>
        </div>
        <div class="mt-3 pt-3 border-t border-gray-100">
          <p class="text-[10px] text-gray-500 font-medium mb-1">&#x1F6A8; 无模拟数据 — 数据源不可用时显示错误</p>
          <p class="text-[10px] text-gray-400">即期汇率：通过 Frankfurter + ExchangeRate-API 自动获取。新闻：需要 Alpha Vantage API 密钥。波动率/资金流：需要 Bloomberg 或 <code class="bg-gray-100 px-1 rounded">data/</code> 目录下的 JSON 文件。</p>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ CLIENT PORTAL MODAL ═══ -->
<div id="portalModal" class="fixed inset-0 z-50 hidden">
  <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick="closePortalModal()"></div>
  <div class="absolute inset-4 md:inset-8 lg:inset-12 bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden" style="max-width:1200px;margin:auto;">
    <!-- Modal Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-slate-50 to-white shrink-0">
      <div>
        <h2 class="text-lg font-serif text-brand-dark">客户门户</h2>
        <p class="text-[10px] text-gray-400 mt-0.5">管理客户档案、偏好设置和外汇走廊</p>
      </div>
      <div class="flex items-center gap-3">
        <button onclick="showPortalView('list')" id="portalListBtn" class="text-[10px] font-semibold px-3 py-1.5 rounded-md bg-brand-dark text-white">客户列表</button>
        <button onclick="startNewClient()" class="text-[10px] font-semibold px-3 py-1.5 rounded-md bg-brand-primary text-white hover:bg-brand-hover transition-all">+ 新建客户</button>
        <button onclick="closePortalModal()" class="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
      </div>
    </div>
    <!-- Modal Body -->
    <div class="flex-1 overflow-y-auto p-6" id="portalBody">
      <!-- LIST VIEW -->
      <div id="portalListView">
        <div class="flex items-center gap-3 mb-4 flex-wrap">
          <select id="portalFilterRegion" onchange="loadPortalClients()" class="text-[10px] border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white font-medium">
            <option value="">全部区域</option>
          </select>
          <select id="portalFilterType" onchange="loadPortalClients()" class="text-[10px] border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white font-medium">
            <option value="">全部类型</option>
          </select>
          <select id="portalFilterTier" onchange="loadPortalClients()" class="text-[10px] border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white font-medium">
            <option value="">全部等级</option>
          </select>
          <input type="text" id="portalSearch" onkeyup="loadPortalClients()" placeholder="搜索客户..."
            class="text-[10px] border border-gray-200 rounded-lg px-3 py-1.5 flex-1 min-w-[120px]">
        </div>
        <div id="portalClientGrid" class="space-y-3"></div>
      </div>
      <!-- EDIT VIEW -->
      <div id="portalEditView" class="hidden">
        <div class="flex items-center gap-2 mb-5">
          <button onclick="showPortalView('list')" class="text-xs text-brand-primary hover:underline font-medium">&larr; 返回列表</button>
          <span class="text-gray-300">|</span>
          <span id="editClientTitle" class="text-sm font-semibold text-brand-dark">新建客户</span>
        </div>
        <!-- Tab Navigation -->
        <div class="flex gap-1 bg-gray-100 p-1 rounded-lg mb-5 flex-wrap">
          <button class="portal-tab active text-[10px] font-semibold py-1.5 px-3 rounded-md" onclick="switchPortalTab('basic', this)">基本信息</button>
          <button class="portal-tab text-[10px] font-semibold py-1.5 px-3 rounded-md text-gray-500" onclick="switchPortalTab('business', this)">业务</button>
          <button class="portal-tab text-[10px] font-semibold py-1.5 px-3 rounded-md text-gray-500" onclick="switchPortalTab('fx', this)">外汇与走廊</button>
          <button class="portal-tab text-[10px] font-semibold py-1.5 px-3 rounded-md text-gray-500" onclick="switchPortalTab('risk', this)">风险</button>
          <button class="portal-tab text-[10px] font-semibold py-1.5 px-3 rounded-md text-gray-500" onclick="switchPortalTab('report', this)">报告偏好</button>
          <button class="portal-tab text-[10px] font-semibold py-1.5 px-3 rounded-md text-gray-500" onclick="switchPortalTab('contacts', this)">联系人</button>
          <button class="portal-tab text-[10px] font-semibold py-1.5 px-3 rounded-md text-gray-500" onclick="switchPortalTab('compliance', this)">KYC/AML</button>
          <button class="portal-tab text-[10px] font-semibold py-1.5 px-3 rounded-md text-gray-500" onclick="switchPortalTab('notes', this)">备注</button>
        </div>
        <!-- Tab Panels -->
        <div id="portalTabContent">
          <!-- BASIC INFO -->
          <div id="ptab-basic" class="portal-panel grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="portal-lbl">客户名称 *</label><input type="text" id="pf_name" class="portal-input" placeholder="如 MoMo Vietnam"></div>
            <div><label class="portal-lbl">简称 *</label><input type="text" id="pf_short_name" class="portal-input" placeholder="如 MoMo"></div>
            <div><label class="portal-lbl">法律实体</label><input type="text" id="pf_legal_entity" class="portal-input"></div>
            <div><label class="portal-lbl">客户类型</label><select id="pf_client_type" class="portal-input"></select></div>
            <div><label class="portal-lbl">等级</label><select id="pf_tier" class="portal-input"></select></div>
            <div><label class="portal-lbl">状态</label><select id="pf_status" class="portal-input"></select></div>
            <div><label class="portal-lbl">国家</label><select id="pf_country" class="portal-input" onchange="onCountryChange()"></select></div>
            <div><label class="portal-lbl">区域</label><input type="text" id="pf_region" class="portal-input bg-gray-50" readonly></div>
            <div><label class="portal-lbl">入驻日期</label><input type="date" id="pf_onboarding_date" class="portal-input"></div>
            <div><label class="portal-lbl">网站</label><input type="text" id="pf_website" class="portal-input" placeholder="https://"></div>
          </div>
          <!-- BUSINESS -->
          <div id="ptab-business" class="portal-panel hidden grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="portal-lbl">行业</label><select id="pf_industry" class="portal-input"></select></div>
            <div><label class="portal-lbl">月交易量（美元）</label><input type="number" id="pf_monthly_volume_usd" class="portal-input" placeholder="0"></div>
            <div><label class="portal-lbl">交易量等级</label><select id="pf_volume_tier" class="portal-input">
              <option value="">—</option><option>&lt;1M</option><option>1M-10M</option><option>10M-50M</option><option>50M-100M</option><option>100M-500M</option><option>&gt;500M</option>
            </select></div>
            <div><label class="portal-lbl">员工人数</label><input type="text" id="pf_employee_count" class="portal-input" placeholder="如 1000-5000"></div>
            <div class="md:col-span-2"><label class="portal-lbl">商业模式</label><textarea id="pf_business_model" class="portal-input" rows="2" placeholder="描述客户的商业模式..."></textarea></div>
            <div class="md:col-span-2"><label class="portal-lbl">主要产品（逗号分隔）</label><input type="text" id="pf_main_products" class="portal-input" placeholder="移动钱包, 二维码支付, 账单支付"></div>
          </div>
          <!-- FX & CORRIDORS -->
          <div id="ptab-fx" class="portal-panel hidden">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
              <div><label class="portal-lbl">基础货币 *</label><input type="text" id="pf_base_currency" class="portal-input" placeholder="如 VND"></div>
              <div><label class="portal-lbl">结算周期</label><select id="pf_settlement_cycle" class="portal-input"><option>T+0</option><option>T+1</option><option selected>T+2</option></select></div>
              <div><label class="portal-lbl">关注币对（逗号分隔）*</label><input type="text" id="pf_focus_pairs" class="portal-input" placeholder="USDVND, CNHVND, JPYVND"></div>
              <div><label class="portal-lbl">对冲策略</label><select id="pf_hedging_policy" class="portal-input"></select></div>
              <div><label class="portal-lbl">定价模式</label><select id="pf_pricing_model" class="portal-input"></select></div>
              <div><label class="portal-lbl">当前加价（基点）</label><input type="number" id="pf_current_markup_bps" class="portal-input" placeholder="0"></div>
              <div><label class="portal-lbl">基准汇率来源</label><input type="text" id="pf_benchmark_rate_source" class="portal-input" placeholder="Reuters, Bloomberg, 央行"></div>
              <div><label class="portal-lbl">执行窗口</label><input type="text" id="pf_preferred_execution_window" class="portal-input" placeholder="09:00-17:00 HKT"></div>
              <div class="md:col-span-2"><label class="portal-lbl">首选流动性提供商（逗号分隔）</label><input type="text" id="pf_preferred_liquidity_providers" class="portal-input" placeholder="HSBC, Citi, SCB"></div>
            </div>
            <!-- Corridors -->
            <div class="border-t border-gray-100 pt-4">
              <div class="flex items-center justify-between mb-3">
                <h4 class="text-[10px] font-bold text-gray-600 uppercase tracking-wider">走廊</h4>
                <button onclick="addCorridorRow()" class="text-[10px] bg-blue-50 text-blue-700 px-2.5 py-1 rounded-md font-semibold border border-blue-200 hover:bg-blue-100 transition-all">+ 添加走廊</button>
              </div>
              <div id="corridorRows" class="space-y-2"></div>
            </div>
          </div>
          <!-- RISK -->
          <div id="ptab-risk" class="portal-panel hidden grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="portal-lbl">风险偏好</label><select id="pf_risk_appetite" class="portal-input"></select></div>
            <div><label class="portal-lbl">央行</label><input type="text" id="pf_central_bank" class="portal-input" placeholder="如 越南国家银行 (SBV)"></div>
            <div class="md:col-span-2"><label class="portal-lbl">关键关注点（每行一个）</label><textarea id="pf_key_concerns" class="portal-input" rows="4" placeholder="SBV 管理浮动汇率制度\nVND 贬值压力\n侨汇季节性"></textarea></div>
            <div class="md:col-span-2"><label class="portal-lbl">敏感因子（逗号分隔）</label><input type="text" id="pf_sensitivity_factors" class="portal-input" placeholder="油价, 美联储利率, CNH 定盘"></div>
            <div><label class="portal-lbl">止损阈值</label><input type="text" id="pf_stop_loss_threshold" class="portal-input" placeholder="如 2% 不利波动"></div>
            <div><label class="portal-lbl">VaR 限额</label><input type="text" id="pf_var_limit" class="portal-input"></div>
          </div>
          <!-- REPORT PREFERENCES -->
          <div id="ptab-report" class="portal-panel hidden">
            <p class="text-[10px] text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4 font-medium">这些偏好会在选择该客户生成报告时自动填入报告设置。</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div><label class="portal-lbl">报告频率</label><select id="pf_report_frequency" class="portal-input"></select></div>
              <div><label class="portal-lbl">报告语言</label><select id="pf_report_language" class="portal-input"></select></div>
              <div><label class="portal-lbl">报告格式</label><select id="pf_report_format" class="portal-input"></select></div>
              <div><label class="portal-lbl">新闻主题（逗号分隔）</label><input type="text" id="pf_news_topics" class="portal-input" placeholder="央行政策, 侨汇, 贸易"></div>
              <div class="md:col-span-2"><label class="portal-lbl">自定义基准（逗号分隔）</label><input type="text" id="pf_custom_benchmarks" class="portal-input" placeholder="DXY, ADXY"></div>
            </div>
            <div class="mt-4"><label class="portal-lbl mb-2 block">报告章节</label>
              <div class="grid grid-cols-2 md:grid-cols-3 gap-2" id="portalSectionsGrid"></div>
            </div>
          </div>
          <!-- CONTACTS -->
          <div id="ptab-contacts" class="portal-panel hidden">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-[10px] font-bold text-gray-600 uppercase tracking-wider">联系人</h4>
              <button onclick="addContactRow()" class="text-[10px] bg-blue-50 text-blue-700 px-2.5 py-1 rounded-md font-semibold border border-blue-200 hover:bg-blue-100 transition-all">+ 添加联系人</button>
            </div>
            <div id="contactRows" class="space-y-3"></div>
          </div>
          <!-- KYC/AML -->
          <div id="ptab-compliance" class="portal-panel hidden grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="portal-lbl">KYC 状态</label><select id="pf_kyc_status" class="portal-input"></select></div>
            <div><label class="portal-lbl">KYC 到期日期</label><input type="date" id="pf_kyc_expiry_date" class="portal-input"></div>
            <div><label class="portal-lbl">AML 风险评级</label><select id="pf_aml_risk_rating" class="portal-input"></select></div>
            <div><label class="portal-lbl">制裁筛查</label><select id="pf_sanctions_screening" class="portal-input"></select></div>
            <div><label class="portal-lbl">税务编号</label><input type="text" id="pf_tax_id" class="portal-input"></div>
            <div><label class="portal-lbl">注册国家</label><input type="text" id="pf_incorporation_country" class="portal-input"></div>
            <div class="md:col-span-2"><label class="portal-lbl">UBO 结构</label><textarea id="pf_ubo_structure" class="portal-input" rows="2"></textarea></div>
            <div class="md:col-span-2"><label class="portal-lbl">合规备注</label><textarea id="pf_compliance_notes" class="portal-input" rows="2"></textarea></div>
            <div><label class="portal-lbl flex items-center gap-2"><input type="checkbox" id="pf_pep_status" class="accent-brand-primary"> PEP（政治公众人物）</label></div>
          </div>
          <!-- NOTES -->
          <div id="ptab-notes" class="portal-panel hidden grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><label class="portal-lbl">客户经理</label><input type="text" id="pf_relationship_manager" class="portal-input"></div>
            <div><label class="portal-lbl">标签（逗号分隔）</label><input type="text" id="pf_tags" class="portal-input" placeholder="高优先级, Q2续约"></div>
            <div class="md:col-span-2"><label class="portal-lbl">关键事件（每行一个）</label><textarea id="pf_key_events" class="portal-input" rows="3" placeholder="SBV 参考汇率调整\n越南 GDP 发布"></textarea></div>
            <div class="md:col-span-2"><label class="portal-lbl">内部备注</label><textarea id="pf_internal_notes" class="portal-input" rows="3"></textarea></div>
          </div>
        </div>
        <!-- Action bar -->
        <div class="flex items-center justify-between mt-6 pt-4 border-t border-gray-200">
          <button id="deleteClientBtn" onclick="deleteCurrentClient()" class="hidden text-[10px] text-red-500 hover:text-red-700 font-medium">删除客户</button>
          <div class="flex gap-2 ml-auto">
            <button onclick="showPortalView('list')" class="text-xs border border-gray-200 text-gray-600 hover:bg-gray-50 px-4 py-2 rounded-lg font-medium transition-all">取消</button>
            <button onclick="saveClient()" class="text-xs bg-brand-primary hover:bg-brand-hover text-white px-6 py-2 rounded-lg font-semibold transition-all shadow-sm">保存客户</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .portal-lbl { display: block; font-size: 10px; font-weight: 600; color: #64748B; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.5px; }
  .portal-input { width: 100%; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 10px; font-size: 12px; transition: all 0.15s; background: white; }
  .portal-input:focus { outline: none; border-color: #0052D9; box-shadow: 0 0 0 3px rgba(0,82,217,0.1); }
  .portal-tab { transition: all 0.15s; cursor: pointer; }
  .portal-tab.active { background: #0F172A; color: white; }
  .portal-client-row { transition: all 0.15s; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px 16px; background: white; }
  .portal-client-row:hover { border-color: #0052D9; box-shadow: 0 2px 8px rgba(0,82,217,0.08); }
  .region-tab { transition: all 0.15s; cursor: pointer; }
  .region-tab.active { background: #0F172A !important; color: white !important; }
  .corridor-row { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px 12px; }
</style>

<div class="mt-12 border-t border-gray-200 py-6 text-center text-[10px] text-gray-400 flex items-center justify-center gap-2" id="pageFooter">
  <span class="inline-block w-1 h-1 rounded-full bg-gray-300"></span>
  Tenpay Global · 外汇研究报告生成器 · 保密
  <span class="inline-block w-1 h-1 rounded-full bg-gray-300"></span>
</div>

<script>
// ── i18n bilingual label system ──
const I18N = {
  en: {
    brand_sub: 'Cross-Border Payments',
    ui_title: 'TenPay Intelligence <span style="color:#94A3B8; font-weight:300; margin:0 6px;">·</span> FX Research',
    ui_subtitle: 'Cross-Border Payments · Corridor Insights · Market Analysis · Bespoke Reports',
    client_profile: 'Client Profile',
    client_profile_desc: 'Select the target client to customize report content, corridors, and base currency',
    report_settings: 'Report Settings',
    report_date: 'Report Date',
    output_format: 'Output Format',
    generate: 'Generate Report',
    generating: 'Generating...',
    active_corridors: 'Active Corridors',
    base_currency: 'Base Currency',
    central_bank: 'Central Bank',
    key_concerns: 'Key Concerns',
    data_sources: 'Data Sources',
    sections: 'Report Sections',
    commentary: 'Commentary',
    data_preview: 'Data Preview',
    news_feed: 'News & Sentiment',
    footer: 'Tenpay Global · FX Research Report Generator · Confidential',
    sec_executive_summary: 'Executive Summary',
    sec_client_corridor: 'Client Corridor Analysis',
    sec_market_overview: 'Market Overview',
    sec_volatility: 'Volatility Analysis',
    sec_flow: 'Flow Analysis',
    sec_macro: 'Macro Outlook & News',
    sec_risk: 'Risk Monitor',
  },
  zh: {
    brand_sub: '腾讯跨境支付',
    ui_title: 'TenPay 智研',
    ui_subtitle: '跨境支付 · 走廊洞察 · 市场研判 · 定制研报',
    client_profile: '客户档案',
    client_profile_desc: '选择目标客户以定制报告内容、通道和基础货币',
    report_settings: '报告设置',
    report_date: '报告日期',
    output_format: '输出格式',
    generate: '生成报告',
    generating: '生成中...',
    active_corridors: '活跃通道',
    base_currency: '基础货币',
    central_bank: '央行',
    key_concerns: '关键关注点',
    data_sources: '数据来源',
    sections: '报告章节',
    commentary: '评论',
    data_preview: '数据预览',
    news_feed: '新闻与情绪',
    footer: 'Tenpay Global · 外汇研究报告生成器 · 保密',
    sec_executive_summary: '执行摘要',
    sec_client_corridor: '客户通道分析',
    sec_market_overview: '市场概览',
    sec_volatility: '波动率分析',
    sec_flow: '资金流分析',
    sec_macro: '宏观展望与新闻',
    sec_risk: '风险监控',
  }
};

let currentLang = 'zh';

function t(key) { return (I18N[currentLang] || I18N.en)[key] || (I18N.en[key] || key); }

function switchLang(lang) {
  currentLang = lang;
  document.getElementById('htmlRoot').lang = lang;
  document.getElementById('langEN').className = 'lang-btn' + (lang === 'en' ? ' active' : '');
  document.getElementById('langZH').className = 'lang-btn' + (lang === 'zh' ? ' active' : '');
  // Update header text
  document.getElementById('uiTitle').innerHTML = t('ui_title');
  document.getElementById('uiSubtitle').textContent = t('ui_subtitle');
  // Update card headers
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  // Update date display
  const dateLoc = lang === 'zh' ? 'zh-CN' : 'en-US';
  document.getElementById('currentDate').textContent = new Date().toLocaleDateString(dateLoc, {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  // Update footer — preserve dots structure
  document.getElementById('pageFooter').innerHTML = '<span class="inline-block w-1 h-1 rounded-full bg-gray-300"></span> ' + t('footer') + ' <span class="inline-block w-1 h-1 rounded-full bg-gray-300"></span>';
  // Update generate button if not generating
  const btn = document.getElementById('generateBtn');
  if (btn && !btn.disabled) btn.textContent = t('generate');
  // Update section labels
  SECTIONS.forEach(s => {
    const lbl = document.querySelector(`label[data-sec="${s.key}"] .sec-label`);
    if (lbl) lbl.textContent = t('sec_' + s.key);
  });
}

const SECTIONS = [
  {key: 'executive_summary', label: '执行摘要', icon: '1'},
  {key: 'client_corridor', label: '客户走廊分析', icon: 'C'},
  {key: 'market_overview', label: '市场概览', icon: '2'},
  {key: 'volatility_analysis', label: '波动率分析', icon: '3'},
  {key: 'flow_analysis', label: '资金流分析', icon: '4'},
  {key: 'macro_outlook', label: '宏观展望与新闻', icon: '5'},
  {key: 'risk_monitor', label: '风险监控', icon: '6'},
];

let PROFILES = {};
let selectedProfile = '';
let PORTAL_OPTIONS = {};
let _editingClientId = null;
let _activeRegionFilter = '';
let _specificRequirements = '';  // Custom requirements prompt for Claude AI
let _requirementsBackup = '';   // Backup for cancel operation

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('currentDate').textContent = new Date().toLocaleDateString('zh-CN', {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  document.getElementById('reportDate').valueAsDate = new Date();

  const c = document.getElementById('sectionsContainer');
  SECTIONS.forEach(s => {
    const isClient = s.key === 'client_corridor';
    c.innerHTML += `
      <label class="section-toggle flex items-center gap-2.5 p-2.5 rounded-lg border ${isClient ? 'border-blue-200 bg-blue-50/40' : 'border-gray-100 hover:bg-slate-50'} cursor-pointer" data-sec="${s.key}">
        <span class="w-5 h-5 rounded-md ${isClient ? 'bg-brand-primary' : 'bg-brand-dark'} text-white text-[10px] font-bold flex items-center justify-center shrink-0">${s.icon}</span>
        <span class="sec-label text-xs ${isClient ? 'text-brand-primary font-semibold' : 'text-gray-600'} flex-1">${s.label}</span>
        <input type="checkbox" id="sec_${s.key}" checked class="w-3.5 h-3.5 accent-[#0052D9] rounded">
      </label>`;
  });

  loadProfiles();
  loadPreview();
  loadPortalOptions();
  loadConfiguredKeys();
});

async function loadConfiguredKeys() {
  try {
    const res = await fetch('/api/keys');
    const d = await res.json();
    if (d.success) {
      if (d.perplexity_key) document.getElementById('perplexityKey').value = d.perplexity_key;
      if (d.claude_key) document.getElementById('claudeKey').value = d.claude_key;
      // Show LLM proxy status hint
      if (d.llm_enabled && d.llm_key_configured) {
        const claudeInput = document.getElementById('claudeKey');
        if (!d.claude_key) {
          claudeInput.placeholder = 'LLM Proxy 已配置 (fit-ai)，无需 Claude 直连密钥';
        }
      }
    }
  } catch(e) { console.log('keys load error', e); }
}

async function loadPortalOptions() {
  try {
    const res = await fetch('/api/portal/options');
    const d = await res.json();
    if (d.success) PORTAL_OPTIONS = d.options;
  } catch(e) { console.log('options error', e); }
}

async function loadProfiles() {
  try {
    const res = await fetch('/api/profiles');
    const d = await res.json();
    if (d.success) {
      PROFILES = d.profiles;
      renderProfileGrid();
    }
  } catch(e) { console.log('profiles error', e); }
}

function renderProfileGrid() {
  const grid = document.getElementById('profileGrid');
  const tabs = document.getElementById('regionTabs');
  grid.innerHTML = '';

  const entries = Object.entries(PROFILES);
  // Collect unique regions for filter tabs
  const regions = new Set();
  entries.forEach(([k, p]) => { if (p.region) regions.add(p.region); });

  // Render region tabs
  const COUNTRY_CN = {
    'Vietnam':'越南','Philippines':'菲律宾','Indonesia':'印度尼西亚','Thailand':'泰国',
    'Malaysia':'马来西亚','Singapore':'新加坡','Myanmar':'缅甸','Cambodia':'柬埔寨',
    'China':'中国','Hong Kong':'香港','Japan':'日本','South Korea':'韩国','Taiwan':'台湾',
    'India':'印度','Bangladesh':'孟加拉','Pakistan':'巴基斯坦','Sri Lanka':'斯里兰卡',
    'Brazil':'巴西','Mexico':'墨西哥','Argentina':'阿根廷','Colombia':'哥伦比亚',
    'UAE':'阿联酋','Saudi Arabia':'沙特阿拉伯','Nigeria':'尼日利亚','South Africa':'南非',
    'UK':'英国','Germany':'德国','France':'法国','Turkey':'土耳其',
    'US':'美国','Canada':'加拿大','Global':'全球',
  };
  tabs.innerHTML = '<button class="text-[9px] font-semibold px-2.5 py-1 rounded-md region-tab' + (!_activeRegionFilter ? ' active bg-brand-dark text-white' : ' bg-gray-100 text-gray-500') + '" onclick="filterRegion(' + "'" + "'" + ', this)">全部 (' + entries.length + ')</button>';
  [...regions].sort().forEach(r => {
    const count = entries.filter(([k,p]) => p.region === r).length;
    const isActive = _activeRegionFilter === r;
    const label = COUNTRY_CN[r] || r;
    tabs.innerHTML += '<button class="text-[9px] font-semibold px-2.5 py-1 rounded-md region-tab' + (isActive ? ' active bg-brand-dark text-white' : ' bg-gray-100 text-gray-500 hover:bg-gray-200') + '" onclick="filterRegion(' + "'" + r + "'" + ', this)">' + label + ' (' + count + ')</button>';
  });

  // Filter by region
  let filtered = entries;
  if (_activeRegionFilter) {
    filtered = entries.filter(([k, p]) => p.region === _activeRegionFilter);
  }

  // Sort: global first
  filtered.sort((a, b) => {
    if (a[1].region === '全球') return -1;
    if (b[1].region === '全球') return 1;
    return (a[1].short_name || '').localeCompare(b[1].short_name || '');
  });

  const REGION_FLAGS = {
    'Vietnam': '\u{1F1FB}\u{1F1F3}', 'Philippines': '\u{1F1F5}\u{1F1ED}',
    'Indonesia': '\u{1F1EE}\u{1F1E9}', 'Thailand': '\u{1F1F9}\u{1F1ED}',
    'Malaysia': '\u{1F1F2}\u{1F1FE}', 'Brazil': '\u{1F1E7}\u{1F1F7}',
    'Singapore': '\u{1F1F8}\u{1F1EC}', 'India': '\u{1F1EE}\u{1F1F3}',
    'Japan': '\u{1F1EF}\u{1F1F5}', 'Mexico': '\u{1F1F2}\u{1F1FD}',
    '全球': '\u{1F30D}',
  };

  filtered.forEach(([key, p]) => {
    const region = p.region || '';
    const flag = REGION_FLAGS[region] || p.flag || '';
    const displayLabel = region === '全球' ? '全球' : p.base_currency;
    const tier = p._tier || '';
    const tierBadge = tier ? '<div class="text-[8px] mt-0.5 ' + (tier === '一级' ? 'text-amber-600' : 'text-gray-400') + '">' + tier + '</div>' : '';
    grid.innerHTML += `
      <div class="profile-card p-3 rounded-xl bg-white border border-gray-100 text-center" id="prof_${key}" onclick="selectProfile('${key}')">
        <div class="text-xl mb-1">${flag}</div>
        <div class="text-[10px] font-bold text-brand-dark leading-tight">${p.short_name}</div>
        <div class="text-[9px] text-gray-400 mt-0.5">${displayLabel}</div>
        ${tierBadge}
      </div>`;
  });
}

function filterRegion(region, btn) {
  _activeRegionFilter = region;
  renderProfileGrid();
}

async function selectProfile(key) {
  if (selectedProfile === key) {
    selectedProfile = '';
    _specificRequirements = '';
    _requirementsBackup = '';
    document.querySelectorAll('.profile-card').forEach(c => c.classList.remove('selected'));
    document.getElementById('corridorPanel').classList.add('hidden');
    document.getElementById('selectedProfileBadge').classList.add('hidden');
    loadDefaults('');
    return;
  }

  selectedProfile = key;
  document.querySelectorAll('.profile-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('prof_' + key).classList.add('selected');

  const p = PROFILES[key];
  const badge = document.getElementById('selectedProfileBadge');
  badge.textContent = `${p.short_name} \u00B7 ${p.base_currency}`;
  badge.classList.remove('hidden');

  const panel = document.getElementById('corridorPanel');
  panel.classList.remove('hidden');
  document.getElementById('baseCurrencyLabel').textContent = p.base_currency;
  document.getElementById('centralBankLabel').textContent = p.central_bank || '\u2014';

  const cl = document.getElementById('corridorList');
  cl.innerHTML = '';
  (p.corridors || []).forEach(c => {
    const dirClass = c.direction === 'inbound' ? 'corridor-inbound' : 'corridor-outbound';
    cl.innerHTML += `
      <div class="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
        <span class="corridor-badge ${dirClass}">${c.direction === 'inbound' ? '\u2B07' : '\u2B06'} ${c.direction === 'inbound' ? '入境' : c.direction === 'outbound' ? '出境' : '双向'}</span>
        <div class="flex-1">
          <div class="text-xs font-semibold text-brand-dark">${c.from}\u2192${c.to}</div>
          <div class="text-[9px] text-gray-400">${c.label}</div>
        </div>
      </div>`;
  });

  const concerns = document.getElementById('concernsList');
  concerns.innerHTML = '';
  (p.key_concerns || []).forEach(c => {
    concerns.innerHTML += `<div class="flex items-start gap-1.5"><span class="text-brand-primary mt-0.5">\u25B8</span><span>${c}</span></div>`;
  });

  // ═══ KEY: Auto-fill Reporting Settings from client's report preferences ═══
  applyReportPreferences(p);

  // ═══ Show requirements dialog on client selection ═══
  updateRequirementsPreview();
  openRequirementsDialog();

  loadDefaults(key);
  loadPreview();
}

function applyReportPreferences(profile) {
  // Auto-fill sections from client's saved preferences
  const sectionsEnabled = profile._sections_enabled || {};
  if (Object.keys(sectionsEnabled).length > 0) {
    SECTIONS.forEach(s => {
      const cb = document.getElementById('sec_' + s.key);
      if (cb && sectionsEnabled[s.key] !== undefined) {
        cb.checked = sectionsEnabled[s.key];
      }
    });
  }

  // Auto-fill output format from client's report_format
  const fmt = profile._report_format;
  if (fmt) {
    const fmtSelect = document.getElementById('outputFormat');
    if (fmt === 'PDF') fmtSelect.value = 'pdf';
    else fmtSelect.value = 'html';
  }
}

// ══════════════════════════════════════════════════════════════
// Specific Requirements Dialog — Custom prompt for Claude AI
// ══════════════════════════════════════════════════════════════
function openRequirementsDialog() {
  if (!selectedProfile) return;
  const p = PROFILES[selectedProfile];
  const sub = document.getElementById('reqDialogSubtitle');
  if (sub && p) sub.textContent = p.short_name + ' 报告的自定义指令 — 发送给 Claude AI';
  document.getElementById('specificRequirementsText').value = _specificRequirements;
  _requirementsBackup = _specificRequirements;
  document.getElementById('requirementsDialog').classList.remove('hidden');
}

function closeRequirementsDialog() {
  document.getElementById('specificRequirementsText').value = _requirementsBackup;
  _specificRequirements = _requirementsBackup;
  document.getElementById('requirementsDialog').classList.add('hidden');
}

function saveRequirements() {
  _specificRequirements = document.getElementById('specificRequirementsText').value.trim();
  _requirementsBackup = _specificRequirements;
  updateRequirementsPreview();
  document.getElementById('requirementsDialog').classList.add('hidden');
}

function clearRequirements() {
  document.getElementById('specificRequirementsText').value = '';
}

function appendRequirement(text) {
  const ta = document.getElementById('specificRequirementsText');
  const current = ta.value.trim();
  if (current) {
    ta.value = current + '\n\n' + text;
  } else {
    ta.value = text;
  }
  ta.scrollTop = ta.scrollHeight;
}

function updateRequirementsPreview() {
  const preview = document.getElementById('requirementsPreview');
  if (!preview) return;
  if (_specificRequirements) {
    const truncated = _specificRequirements.length > 120 ? _specificRequirements.substring(0, 120) + '...' : _specificRequirements;
    preview.innerHTML = '<span class="text-purple-600 not-italic font-medium">' + truncated.replace(/\n/g, ' ') + '</span>';
  } else {
    preview.innerHTML = '未设置特定需求 — Claude 将使用默认分析';
  }
}

async function loadDefaults(profileKey) {
  try {
    const url = profileKey ? `/api/defaults?profile=${profileKey}` : '/api/defaults';
    const res = await fetch(url);
    const data = await res.json();
    if (data.success && data.commentary) {
      document.getElementById('exec_summary').value = data.commentary.executive_summary || '';
      document.getElementById('market_view').value = data.commentary.market_view || '';
      document.getElementById('risk_assessment').value = data.commentary.risk_assessment || '';
      document.getElementById('outlook').value = data.commentary.outlook || '';
    }
  } catch(e) { console.log('defaults error', e); }
}

function switchTab(tab, btn) {
  document.querySelectorAll('[id^="tab-"]').forEach(t => t.classList.add('hidden'));
  document.getElementById('tab-' + tab).classList.remove('hidden');
  document.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('active'); b.classList.add('text-gray-500'); });
  btn.classList.add('active'); btn.classList.remove('text-gray-500');
}

async function loadPreview() {
  const el = document.getElementById('dataPreview');
  const hintEl = document.getElementById('dataSourceHint');
  const dataSource = document.getElementById('dataSourceSelect').value;

  el.innerHTML = '<p class="text-brand-primary text-xs py-4 text-center">正在加载实时数据...</p>';

  const hints = {
    'bloomberg': '<strong>Bloomberg 模式</strong> \u2014 汇率 = 实时汇率, 1D = 相对前一交易日收盘, H/L = 5日区间',
    'ecb': '<strong>ECB 模式</strong> \u2014 汇率 = ECB 参考汇率（每日定盘）, 1D/1W = 基于 ECB 每日汇率',
    'exchangerate-api': '<strong>ExchangeRate-API</strong> \u2014 汇率 = 最新即期, 160+ 种货币，无历史变动数据',
  };
  if (hints[dataSource]) {
    hintEl.innerHTML = hints[dataSource];
    hintEl.classList.remove('hidden');
  } else {
    hintEl.classList.add('hidden');
  }

  try {
    let url = selectedProfile ? `/api/preview?profile=${selectedProfile}` : '/api/preview';
    if (dataSource) url += (url.includes('?') ? '&' : '?') + `data_source=${dataSource}`;
    const res = await fetch(url);
    const d = await res.json();
    if (d.success) {
      let h = '';
      if (d.errors && d.errors.length > 0) {
        h += '<div class="mb-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">';
        h += '<p class="text-[10px] font-bold text-amber-700 mb-1">\u26A0 数据警告</p>';
        d.errors.forEach(err => {
          h += `<p class="text-[9px] text-amber-600 leading-relaxed">\u2022 ${err}</p>`;
        });
        h += '</div>';
      }
      if (d.spot_rates && !d.spot_rates._error) {
        const isBbg = dataSource === 'bloomberg';
        const rateLabel = isBbg ? '实时' : '汇率';
        const d1Label = isBbg ? '1D (收盘)' : '1D';
        const lastCol = isBbg ? '高 / 低' : '来源';
        h += `<table class="w-full text-[11px]"><thead><tr class="border-b-2 border-brand-primary"><th class="py-1.5 text-left font-semibold text-brand-dark">币对</th><th class="py-1.5 text-right font-semibold">${rateLabel}</th><th class="py-1.5 text-right font-semibold">${d1Label}</th><th class="py-1.5 text-right font-semibold">1W</th><th class="py-1.5 text-right font-semibold">${lastCol}</th></tr></thead><tbody>`;
        const pairs = d.focus_pairs || Object.keys(d.spot_rates).filter(k => !k.startsWith('_'));
        pairs.slice(0,12).forEach(p => {
          const v = d.spot_rates[p];
          if (!v || v._error) return;
          let srcCell = '';
          if (isBbg) {
            const high = v.high || '\u2014';
            const low = v.low || '\u2014';
            srcCell = `<span class="text-[8px] font-mono text-gray-500">${high}/${low}</span>`;
          } else {
            srcCell = v.source === 'bloomberg' ? '<span class="bbg-badge">BBG</span>' : v.source === 'frankfurter' ? '<span class="text-[8px] text-emerald-600 font-bold">ECB</span>' : v.source === 'exchangerate-api' ? '<span class="text-[8px] text-blue-500 font-bold">ERA</span>' : '';
          }
          const chg1d = v.chg_1d !== null && v.chg_1d !== undefined ? `<span class="${v.chg_1d>=0?'text-green-600':'text-red-600'}">${v.chg_1d>0?'+':''}${v.chg_1d}%</span>` : '<span class="text-gray-300">无</span>';
          const chg1w = v.chg_1w !== null && v.chg_1w !== undefined ? `<span class="${v.chg_1w>=0?'text-green-600':'text-red-600'}">${v.chg_1w>0?'+':''}${v.chg_1w}%</span>` : '<span class="text-gray-300">无</span>';
          h += `<tr class="border-b border-gray-100 hover:bg-blue-50/30"><td class="py-1 font-semibold text-brand-dark">${p}</td><td class="py-1 text-right font-mono text-[10px]">${v.rate}</td><td class="py-1 text-right font-mono text-[10px]">${chg1d}</td><td class="py-1 text-right font-mono text-[10px]">${chg1w}</td><td class="py-1 text-right">${srcCell}</td></tr>`;
        });
        h += '</tbody></table>';
        if (d.focus_pairs) {
          h += `<p class="text-[9px] text-amber-600 mt-2 italic font-medium">显示 ${selectedProfile.replace('_psp','').replace('_',' ')} 的关注币对</p>`;
        }
        if (isBbg) {
          h += '<p class="text-[8px] text-gray-400 mt-1">Bloomberg \u00B7 实时 = 最新 \u00B7 1D = 相对前收盘 \u00B7 高/低 = 5日区间</p>';
        } else if (dataSource === 'exchangerate-api') {
          h += '<p class="text-[8px] text-gray-400 mt-1">ExchangeRate-API \u00B7 160+ 种货币</p>';
        } else {
          h += '<p class="text-[8px] text-gray-400 mt-1">ECB = Frankfurter/ECB \u00B7 ERA = ExchangeRate-API</p>';
        }
      } else if (d.spot_rates && d.spot_rates._error) {
        h += `<div class="p-3 bg-red-50 border border-red-200 rounded-lg"><p class="text-xs font-bold text-red-700">\u274C 即期汇率错误</p><p class="text-[10px] text-red-600 mt-1">${d.spot_rates._error}</p></div>`;
      }
      if (d.events && d.events.length > 0 && !d.events[0]._error) {
        h += '<div class="mt-4 pt-3 border-t border-gray-100"><h4 class="text-[10px] font-semibold text-brand-primary uppercase tracking-wider mb-2">近期事件</h4>';
        d.events.slice(0,4).forEach(e => {
          const cls = e.impact==='High' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200';
          h += `<div class="flex items-center gap-2 py-1.5 text-[10px]"><span class="font-mono text-gray-400 w-20 shrink-0">${(e.date||'').slice(5)}</span><span class="flex-1 text-gray-600">${e.event}</span><span class="px-1.5 py-0.5 rounded text-[8px] font-bold border ${cls}">${e.impact}</span></div>`;
        });
        h += '</div>';
      } else if (d.events && d.events.length > 0 && d.events[0]._error) {
        h += `<div class="mt-4 pt-3 border-t border-gray-100"><div class="p-2.5 bg-gray-50 border border-gray-200 rounded-lg"><p class="text-[10px] font-semibold text-gray-500">\u{1F4C5} 事件</p><p class="text-[9px] text-gray-400 mt-1">${d.events[0]._error}</p></div></div>`;
      }
      if (d.data_sources) {
        const srcLabel = d.data_sources.join(' + ');
        document.getElementById('dataSourceLabel').textContent = srcLabel;
        const dot = document.querySelector('.w-1\\.5.h-1\\.5.rounded-full');
        if (dot) dot.className = srcLabel.includes('No live') ? 'w-1.5 h-1.5 rounded-full bg-red-400 inline-block' : 'w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block';
      }
      el.innerHTML = h || '<p class="text-xs text-gray-400 italic py-4 text-center">暂无数据</p>';
    }
  } catch(e) { el.innerHTML = `<p class="text-red-500 text-xs">\u274C ${e.message}</p>`; }
}

async function loadNews() {
  const el = document.getElementById('newsContainer');
  el.innerHTML = '<p class="text-brand-primary text-xs py-4 text-center">正在获取实时新闻...</p>';
  try {
    const apiKey = document.getElementById('apiKey').value.trim();
    const perplexityKey = document.getElementById('perplexityKey').value.trim();
    let url = selectedProfile ? `/api/news?profile=${selectedProfile}` : '/api/news';
    if (apiKey) url += (url.includes('?') ? '&' : '?') + `api_key=${encodeURIComponent(apiKey)}`;
    if (perplexityKey) url += (url.includes('?') ? '&' : '?') + `perplexity_key=${encodeURIComponent(perplexityKey)}`;
    const res = await fetch(url);
    const d = await res.json();
    if (d.success && d.news) {
      renderNewsItems(d.news);
    }
  } catch(e) { el.innerHTML = `<p class="text-red-500 text-xs">\u274C ${e.message}</p>`; }
}

// Store fetched news for summary generation
let _fetchedAINews = [];

async function loadAINews() {
  const el = document.getElementById('newsContainer');
  const perplexityKey = document.getElementById('perplexityKey').value.trim();
  const claudeKey = document.getElementById('claudeKey').value.trim();

  if (!perplexityKey) {
    el.innerHTML = '<div class="p-4 bg-purple-50 border border-purple-200 rounded-lg"><p class="text-xs font-bold text-purple-700 mb-1">需要 Perplexity API 密钥</p><p class="text-[10px] text-purple-500">请在左侧面板的 AI 集成部分输入您的 Perplexity API 密钥以启用 AI 新闻搜索。</p></div>';
    return;
  }

  el.innerHTML = '<p class="text-purple-600 text-xs py-4 text-center"><svg class="spinner inline w-3 h-3 mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="30 70"></circle></svg>正在通过 Perplexity AI 搜索新闻（基于 ' + (selectedProfile ? PROFILES[selectedProfile]?.short_name : '全局') + ' 画像）...</p>';

  try {
    let url = '/api/ai_news';
    const params = new URLSearchParams();
    if (selectedProfile) params.set('profile', selectedProfile);
    params.set('perplexity_key', perplexityKey);
    if (claudeKey) params.set('claude_key', claudeKey);
    if (_specificRequirements) params.set('specific_requirements', _specificRequirements);
    url += '?' + params.toString();

    const res = await fetch(url);
    const d = await res.json();

    if (d.success) {
      // Show search prompts used
      if (d.search_prompts && d.search_prompts.length > 0) {
        const promptsEl = document.getElementById('aiPromptsPreview');
        const listEl = document.getElementById('aiPromptsList');
        listEl.innerHTML = d.search_prompts.map((p,i) => `<div>${i+1}. ${p}</div>`).join('');
        promptsEl.classList.remove('hidden');
      }

      if (d.news) {
        _fetchedAINews = d.news;
        renderNewsItems(d.news, true);
      }

      if (d.errors && d.errors.length > 0) {
        el.innerHTML += '<div class="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-[9px] text-amber-600">' + d.errors.join('<br>') + '</div>';
      }
    } else {
      el.innerHTML = `<div class="p-3 bg-red-50 border border-red-200 rounded-lg"><p class="text-xs text-red-700">${d.error || '未知错误'}</p></div>`;
    }
  } catch(e) { el.innerHTML = `<p class="text-red-500 text-xs">\u274C ${e.message}</p>`; }
}

async function generateAISummary() {
  const claudeKey = document.getElementById('claudeKey').value.trim();
  const perplexityKey = document.getElementById('perplexityKey').value.trim();
  const btn = document.getElementById('aiSummaryBtn');
  const status = document.getElementById('statusBar');

  btn.disabled = true;
  btn.innerHTML = '<svg class="spinner inline w-3 h-3 mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="30 70"></circle></svg>生成中...';

  status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-purple-50 text-purple-700 border border-purple-200';
  status.textContent = 'AI 正在通过 Claude 基于新闻和市场数据生成执行摘要...';
  status.classList.remove('hidden');

  try {
    const res = await fetch('/api/ai_summary', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        profile: selectedProfile,
        perplexity_key: perplexityKey,
        claude_key: claudeKey,
        language: currentLang,
        news: _fetchedAINews.length > 0 ? _fetchedAINews : null,
        specific_requirements: _specificRequirements || '',
      }),
    });
    const d = await res.json();

    if (d.success && d.commentary) {
      // Fill in the commentary textareas
      if (d.commentary.executive_summary) document.getElementById('exec_summary').value = d.commentary.executive_summary;
      if (d.commentary.market_view) document.getElementById('market_view').value = d.commentary.market_view;
      if (d.commentary.risk_assessment) document.getElementById('risk_assessment').value = d.commentary.risk_assessment;
      if (d.commentary.outlook) document.getElementById('outlook').value = d.commentary.outlook;

      status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-green-50 text-green-700 border border-green-200';
      status.textContent = 'AI 执行摘要生成成功！评论字段已更新。';

      // Switch to commentary tab to show results
      switchTab('commentary', document.querySelector('.tab-btn'));
    } else {
      status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-red-50 text-red-700 border border-red-200';
      status.textContent = '错误: ' + (d.error || d.commentary?._error || '未知错误');
    }
  } catch(e) {
    status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-red-50 text-red-700 border border-red-200';
    status.textContent = '错误: ' + e.message;
  }

  btn.disabled = false;
  btn.textContent = '生成摘要';
}

function renderNewsItems(news, isAI = false) {
  const el = document.getElementById('newsContainer');
  let h = '';
  if (news.length > 0 && news[0]._error) {
    h = `<div class="p-4 bg-amber-50 border border-amber-200 rounded-lg">
      <p class="text-xs font-bold text-amber-700 mb-2">\u26A0 新闻不可用</p>
      <p class="text-[10px] text-amber-600 leading-relaxed">${news[0]._error}</p>
    </div>`;
  } else {
    news.forEach(n => {
      const sClr = n.sentiment==='Bullish' ? 'text-green-600 bg-green-50' : n.sentiment==='Bearish' ? 'text-red-600 bg-red-50' : 'text-gray-500 bg-gray-50';
      const sentimentMap = {'Bullish':'看涨','Bearish':'看跌','Neutral':'中性'};
      const sentimentLabel = sentimentMap[n.sentiment] || n.sentiment || '中性';
      const aiBadge = (isAI || n.source_api === 'perplexity') ? '<span class="bbg-badge" style="background:#EDE9FE;color:#6D28D9;">AI</span>' : '';
      const bbgBadge = n.bbg ? '<span class="bbg-badge">BBG</span>' : '';
      const urlLink = n.url ? ` \u00B7 <a href="${n.url}" target="_blank" class="text-brand-primary underline">阅读</a>` : '';
      const relevance = n.relevance ? ` \u00B7 <span class="text-purple-500 font-medium">${n.relevance}</span>` : '';
      h += `<div class="news-card p-3 rounded-lg border border-gray-100"><div class="flex items-start justify-between gap-2"><div class="flex-1"><p class="text-xs font-medium text-gray-700 leading-relaxed">${n.title}</p><p class="text-[10px] text-gray-400 mt-1">${n.source || ''}${aiBadge}${bbgBadge} \u00B7 ${n.date || ''}${relevance}${urlLink}</p>${n.summary ? '<p class="text-[10px] text-gray-500 mt-1 leading-relaxed">' + n.summary + '</p>' : ''}</div><span class="px-2 py-0.5 rounded text-[9px] font-bold ${sClr} shrink-0">${sentimentLabel}</span></div></div>`;
    });
  }
  el.innerHTML = h;
}

async function generateReport() {
  const btn = document.getElementById('generateBtn');
  const status = document.getElementById('statusBar');
  btn.disabled = true;
  btn.innerHTML = '<svg class="spinner inline w-4 h-4 mr-2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="30 70"></circle></svg>' + t('generating');

  status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200';
  status.textContent = `正在生成 ${selectedProfile ? PROFILES[selectedProfile]?.short_name + ' ' : ''}报告 \u2014 收集数据、生成图表...`;
  status.classList.remove('hidden');

  const sections = {};
  SECTIONS.forEach(s => { sections[s.key] = document.getElementById('sec_'+s.key).checked; });

  const commentary = {};
  ['exec_summary:executive_summary','market_view:market_view','risk_assessment:risk_assessment','outlook:outlook'].forEach(pair => {
    const [id,key] = pair.split(':');
    const val = document.getElementById(id).value.trim();
    if (val) commentary[key] = val;
  });

  const apiKey = document.getElementById('apiKey').value.trim();
  const pplxKey = document.getElementById('perplexityKey').value.trim();
  const clKey = document.getElementById('claudeKey').value.trim();

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        report_date: document.getElementById('reportDate').value,
        output_format: document.getElementById('outputFormat').value,
        sections, commentary, api_key: apiKey,
        perplexity_key: pplxKey,
        claude_key: clKey,
        client_profile: selectedProfile,
        language: currentLang,
        specific_requirements: _specificRequirements || '',
      }),
    });
    const data = await res.json();
    if (data.success) {
      status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-green-50 text-green-700 border border-green-200';
      status.textContent = `报告生成成功！${selectedProfile ? '(' + PROFILES[selectedProfile]?.short_name + ') ' : ''}` + (data.format === 'pdf' ? 'PDF 已就绪。' : 'HTML 已就绪 — 使用浏览器打印 → 另存为 PDF。');

      const rp = document.getElementById('resultPanel');
      rp.classList.remove('hidden');
      document.getElementById('downloadLink').href = '/api/download?file=' + encodeURIComponent(data.filename);
      document.getElementById('previewLink').href = '/api/download?file=' + encodeURIComponent(data.filename);
      document.getElementById('resultInfo').textContent = data.filename;
    } else {
      status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-red-50 text-red-700 border border-red-200';
      status.textContent = '错误: ' + (data.error || '未知错误');
    }
  } catch(e) {
    status.className = 'mb-6 p-4 rounded-xl text-sm font-medium bg-red-50 text-red-700 border border-red-200';
    status.textContent = '错误: ' + e.message;
  }
  btn.disabled = false;
  btn.textContent = t('generate');
}

// ══════════════════════════════════════════════════════════════
// CLIENT PORTAL — Modal + CRUD functions
// ══════════════════════════════════════════════════════════════

function openPortalModal() {
  document.getElementById('portalModal').classList.remove('hidden');
  populatePortalDropdowns();
  showPortalView('list');
  loadPortalClients();
}

function closePortalModal() {
  document.getElementById('portalModal').classList.add('hidden');
  loadProfiles(); // Refresh profile grid after portal changes
}

function showPortalView(view) {
  document.getElementById('portalListView').classList.toggle('hidden', view !== 'list');
  document.getElementById('portalEditView').classList.toggle('hidden', view !== 'edit');
}

function switchPortalTab(tab, btn) {
  document.querySelectorAll('.portal-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('ptab-' + tab).classList.remove('hidden');
  document.querySelectorAll('.portal-tab').forEach(b => { b.classList.remove('active'); b.classList.add('text-gray-500'); });
  btn.classList.add('active'); btn.classList.remove('text-gray-500');
}

function populatePortalDropdowns() {
  const o = PORTAL_OPTIONS;
  if (!o.client_types) return;
  const fill = (id, arr, selected) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = arr.map(v => `<option value="${v}" ${v === selected ? 'selected' : ''}>${v}</option>`).join('');
  };
  fill('pf_client_type', o.client_types, 'PSP');
  fill('pf_tier', o.tiers, '二级');
  fill('pf_status', o.statuses, '活跃');
  fill('pf_industry', o.industries, '支付/PSP');
  fill('pf_hedging_policy', o.hedging_policies, '不对冲');
  fill('pf_pricing_model', o.pricing_models, '加价');
  fill('pf_risk_appetite', o.risk_appetites, '适中');
  fill('pf_report_frequency', o.report_frequencies, '每周');
  fill('pf_report_language', o.report_languages, 'zh');
  fill('pf_report_format', o.report_formats, 'HTML');
  fill('pf_kyc_status', o.kyc_statuses, '待审核');
  fill('pf_aml_risk_rating', o.aml_risk_ratings, '低');
  fill('pf_sanctions_screening', o.sanctions_statuses, '通过');

  // Countries dropdown
  const COUNTRY_NAMES_CN = {
    'Vietnam':'越南','Philippines':'菲律宾','Indonesia':'印度尼西亚','Thailand':'泰国',
    'Malaysia':'马来西亚','Singapore':'新加坡','Myanmar':'缅甸','Cambodia':'柬埔寨',
    'China':'中国','Hong Kong':'香港','Japan':'日本','South Korea':'韩国','Taiwan':'台湾',
    'India':'印度','Bangladesh':'孟加拉','Pakistan':'巴基斯坦','Sri Lanka':'斯里兰卡',
    'Brazil':'巴西','Mexico':'墨西哥','Argentina':'阿根廷','Colombia':'哥伦比亚',
    'UAE':'阿联酋','Saudi Arabia':'沙特阿拉伯','Nigeria':'尼日利亚','South Africa':'南非',
    'UK':'英国','Germany':'德国','France':'法国','Turkey':'土耳其',
    'US':'美国','Canada':'加拿大','Global':'全球',
  };
  const countryEl = document.getElementById('pf_country');
  if (countryEl && o.countries) {
    countryEl.innerHTML = '<option value="">选择...</option>' + o.countries.map(c => `<option value="${c}">${COUNTRY_NAMES_CN[c] || c}</option>`).join('');
  }

  // Filters
  const fr = document.getElementById('portalFilterRegion');
  if (fr && o.regions) fr.innerHTML = '<option value="">全部区域</option>' + o.regions.map(r => `<option>${r}</option>`).join('');
  const ft = document.getElementById('portalFilterType');
  if (ft && o.client_types) ft.innerHTML = '<option value="">全部类型</option>' + o.client_types.map(t => `<option>${t}</option>`).join('');
  const fti = document.getElementById('portalFilterTier');
  if (fti && o.tiers) fti.innerHTML = '<option value="">全部等级</option>' + o.tiers.map(t => `<option>${t}</option>`).join('');

  // Report sections grid
  const sg = document.getElementById('portalSectionsGrid');
  if (sg) {
    sg.innerHTML = '';
    SECTIONS.forEach(s => {
      sg.innerHTML += `<label class="flex items-center gap-2 text-[10px] text-gray-600 p-2 bg-gray-50 rounded-lg cursor-pointer">
        <input type="checkbox" id="pfsec_${s.key}" checked class="accent-brand-primary w-3.5 h-3.5"> ${s.label}</label>`;
    });
  }
}

function onCountryChange() {
  const country = document.getElementById('pf_country').value;
  const regionMap = {
    'Vietnam':'东南亚','Philippines':'东南亚','Indonesia':'东南亚',
    'Thailand':'东南亚','Malaysia':'东南亚','Singapore':'东南亚',
    'Myanmar':'东南亚','Cambodia':'东南亚',
    'China':'东亚','Hong Kong':'东亚','Japan':'东亚','South Korea':'东亚','Taiwan':'东亚',
    'India':'南亚','Bangladesh':'南亚','Pakistan':'南亚','Sri Lanka':'南亚',
    'Brazil':'拉丁美洲','Mexico':'拉丁美洲','Argentina':'拉丁美洲','Colombia':'拉丁美洲',
    'UAE':'中东与非洲','Saudi Arabia':'中东与非洲','Nigeria':'中东与非洲','South Africa':'中东与非洲',
    'UK':'欧洲','Germany':'欧洲','France':'欧洲','Turkey':'欧洲',
    'US':'北美','Canada':'北美','Global':'全球',
  };
  document.getElementById('pf_region').value = regionMap[country] || '';
}

async function loadPortalClients() {
  const region = document.getElementById('portalFilterRegion').value;
  const type = document.getElementById('portalFilterType').value;
  const tier = document.getElementById('portalFilterTier').value;
  const search = document.getElementById('portalSearch').value;
  try {
    const params = new URLSearchParams();
    if (region) params.set('region', region);
    if (type) params.set('type', type);
    if (tier) params.set('tier', tier);
    if (search) params.set('search', search);
    const res = await fetch('/api/portal/clients?' + params.toString());
    const d = await res.json();
    if (d.success) renderPortalClientList(d.clients);
  } catch(e) { console.log('portal error', e); }
}

function renderPortalClientList(clients) {
  const el = document.getElementById('portalClientGrid');
  if (!clients.length) {
    el.innerHTML = '<p class="text-xs text-gray-400 py-8 text-center italic">未找到客户。点击「+ 新建客户」添加。</p>';
    return;
  }
  // Group by region
  const byRegion = {};
  clients.forEach(c => {
    const r = c.region || '未知';
    if (!byRegion[r]) byRegion[r] = [];
    byRegion[r].push(c);
  });

  let h = '';
  Object.entries(byRegion).sort().forEach(([region, list]) => {
    h += `<div class="mb-4"><div class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">${region} (${list.length})</div>`;
    h += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">';
    list.forEach(c => {
      const tierColor = c.tier === '一级' ? 'text-amber-600 bg-amber-50' : c.tier === '二级' ? 'text-blue-600 bg-blue-50' : 'text-gray-500 bg-gray-100';
      const statusDot = c.status === '活跃' ? 'bg-emerald-400' : c.status === '入驻中' ? 'bg-amber-400' : 'bg-gray-400';
      h += `<div class="portal-client-row cursor-pointer flex items-center gap-3" onclick="editClient('${c.client_id}')">
        <div class="text-xl">${c.flag || ''}</div>
        <div class="flex-1 min-w-0">
          <div class="text-xs font-semibold text-brand-dark truncate">${c.short_name || c.name}</div>
          <div class="text-[9px] text-gray-400">${c.base_currency} \u00B7 ${c.country || ''}</div>
        </div>
        <div class="flex items-center gap-1.5 shrink-0">
          <span class="text-[8px] font-bold px-1.5 py-0.5 rounded ${tierColor}">${c.tier || ''}</span>
          <span class="w-1.5 h-1.5 rounded-full ${statusDot}"></span>
        </div>
      </div>`;
    });
    h += '</div></div>';
  });
  el.innerHTML = h;
}

function startNewClient() {
  _editingClientId = null;
  clearPortalForm();
  document.getElementById('editClientTitle').textContent = '新建客户';
  document.getElementById('deleteClientBtn').classList.add('hidden');
  showPortalView('edit');
  switchPortalTab('basic', document.querySelector('.portal-tab'));
}

async function editClient(clientId) {
  try {
    const res = await fetch('/api/portal/clients/' + clientId);
    const d = await res.json();
    if (d.success) {
      _editingClientId = clientId;
      populatePortalForm(d.client);
      document.getElementById('editClientTitle').textContent = d.client.short_name || d.client.name;
      document.getElementById('deleteClientBtn').classList.remove('hidden');
      showPortalView('edit');
      switchPortalTab('basic', document.querySelector('.portal-tab'));
    }
  } catch(e) { console.log('edit error', e); }
}

function clearPortalForm() {
  document.querySelectorAll('.portal-panel input[type="text"], .portal-panel input[type="number"], .portal-panel input[type="date"], .portal-panel textarea').forEach(el => el.value = '');
  document.querySelectorAll('.portal-panel input[type="checkbox"]').forEach(el => el.checked = el.id.startsWith('pfsec_'));
  document.getElementById('corridorRows').innerHTML = '';
  document.getElementById('contactRows').innerHTML = '';
}

function populatePortalForm(c) {
  clearPortalForm();
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
  const setCheck = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };

  // Basic
  set('pf_name', c.name); set('pf_short_name', c.short_name); set('pf_legal_entity', c.legal_entity);
  set('pf_client_type', c.client_type); set('pf_tier', c.tier); set('pf_status', c.status);
  set('pf_country', c.country); set('pf_region', c.region);
  set('pf_onboarding_date', c.onboarding_date); set('pf_website', c.website);

  // Business
  set('pf_industry', c.industry); set('pf_monthly_volume_usd', c.monthly_volume_usd);
  set('pf_volume_tier', c.volume_tier); set('pf_employee_count', c.employee_count);
  set('pf_business_model', c.business_model);
  set('pf_main_products', (c.main_products || []).join(', '));

  // FX
  set('pf_base_currency', c.base_currency); set('pf_settlement_cycle', c.settlement_cycle);
  set('pf_focus_pairs', (c.focus_pairs || []).join(', '));
  set('pf_hedging_policy', c.hedging_policy); set('pf_pricing_model', c.pricing_model);
  set('pf_current_markup_bps', c.current_markup_bps);
  set('pf_benchmark_rate_source', c.benchmark_rate_source);
  set('pf_preferred_execution_window', c.preferred_execution_window);
  set('pf_preferred_liquidity_providers', (c.preferred_liquidity_providers || []).join(', '));

  // Corridors
  const cr = document.getElementById('corridorRows');
  cr.innerHTML = '';
  (c.corridors || []).forEach(cor => addCorridorRow(cor));

  // Risk
  set('pf_risk_appetite', c.risk_appetite); set('pf_central_bank', c.central_bank);
  set('pf_key_concerns', (c.key_concerns || []).join('\n'));
  set('pf_sensitivity_factors', (c.sensitivity_factors || []).join(', '));
  set('pf_stop_loss_threshold', c.stop_loss_threshold); set('pf_var_limit', c.var_limit);

  // Report
  set('pf_report_frequency', c.report_frequency); set('pf_report_language', c.report_language);
  set('pf_report_format', c.report_format);
  set('pf_news_topics', (c.news_topics || []).join(', '));
  set('pf_custom_benchmarks', (c.custom_benchmarks || []).join(', '));
  const se = c.sections_enabled || {};
  SECTIONS.forEach(s => { setCheck('pfsec_' + s.key, se[s.key] !== false); });

  // Contacts
  const ctRows = document.getElementById('contactRows');
  ctRows.innerHTML = '';
  (c.contacts || []).forEach(ct => addContactRow(ct));

  // KYC
  set('pf_kyc_status', c.kyc_status); set('pf_kyc_expiry_date', c.kyc_expiry_date);
  set('pf_aml_risk_rating', c.aml_risk_rating); set('pf_sanctions_screening', c.sanctions_screening);
  set('pf_tax_id', c.tax_id); set('pf_incorporation_country', c.incorporation_country);
  set('pf_ubo_structure', c.ubo_structure); set('pf_compliance_notes', c.compliance_notes);
  setCheck('pf_pep_status', c.pep_status);

  // Notes
  set('pf_relationship_manager', c.relationship_manager);
  set('pf_tags', (c.tags || []).join(', '));
  set('pf_key_events', (c.key_events || []).join('\n'));
  set('pf_internal_notes', c.internal_notes);
}

function collectPortalForm() {
  const get = (id) => (document.getElementById(id)?.value || '').trim();
  const getNum = (id) => parseFloat(document.getElementById(id)?.value) || 0;
  const getList = (id) => get(id).split(',').map(s => s.trim()).filter(Boolean);
  const getLines = (id) => get(id).split('\n').map(s => s.trim()).filter(Boolean);
  const getCheck = (id) => document.getElementById(id)?.checked || false;

  // Collect corridors
  const corridors = [];
  document.querySelectorAll('#corridorRows .corridor-row').forEach(row => {
    corridors.push({
      from_currency: row.querySelector('.cor-from')?.value || '',
      to_currency: row.querySelector('.cor-to')?.value || '',
      direction: row.querySelector('.cor-dir')?.value || 'inbound',
      label: row.querySelector('.cor-label')?.value || '',
      priority: row.querySelector('.cor-priority')?.value || 'Primary',
      purpose: row.querySelector('.cor-purpose')?.value || '',
    });
  });

  // Collect contacts
  const contacts = [];
  document.querySelectorAll('#contactRows .contact-row').forEach(row => {
    contacts.push({
      name: row.querySelector('.ct-name')?.value || '',
      role: row.querySelector('.ct-role')?.value || '',
      email: row.querySelector('.ct-email')?.value || '',
      phone: row.querySelector('.ct-phone')?.value || '',
      access_level: row.querySelector('.ct-access')?.value || 'Viewer',
      is_primary: row.querySelector('.ct-primary')?.checked || false,
      receives_report: row.querySelector('.ct-report')?.checked || false,
    });
  });

  // Sections enabled
  const sections_enabled = {};
  SECTIONS.forEach(s => { sections_enabled[s.key] = getCheck('pfsec_' + s.key); });

  return {
    name: get('pf_name'), short_name: get('pf_short_name'), legal_entity: get('pf_legal_entity'),
    client_type: get('pf_client_type'), tier: get('pf_tier'), status: get('pf_status'),
    country: get('pf_country'), region: get('pf_region'),
    onboarding_date: get('pf_onboarding_date'), website: get('pf_website'),
    industry: get('pf_industry'), monthly_volume_usd: getNum('pf_monthly_volume_usd'),
    volume_tier: get('pf_volume_tier'), employee_count: get('pf_employee_count'),
    business_model: get('pf_business_model'), main_products: getList('pf_main_products'),
    base_currency: get('pf_base_currency'), settlement_cycle: get('pf_settlement_cycle'),
    focus_pairs: getList('pf_focus_pairs'),
    hedging_policy: get('pf_hedging_policy'), pricing_model: get('pf_pricing_model'),
    current_markup_bps: getNum('pf_current_markup_bps'),
    benchmark_rate_source: get('pf_benchmark_rate_source'),
    preferred_execution_window: get('pf_preferred_execution_window'),
    preferred_liquidity_providers: getList('pf_preferred_liquidity_providers'),
    corridors: corridors,
    risk_appetite: get('pf_risk_appetite'), central_bank: get('pf_central_bank'),
    key_concerns: getLines('pf_key_concerns'),
    sensitivity_factors: getList('pf_sensitivity_factors'),
    stop_loss_threshold: get('pf_stop_loss_threshold'), var_limit: get('pf_var_limit'),
    report_frequency: get('pf_report_frequency'), report_language: get('pf_report_language'),
    report_format: get('pf_report_format'),
    news_topics: getList('pf_news_topics'), custom_benchmarks: getList('pf_custom_benchmarks'),
    sections_enabled: sections_enabled,
    contacts: contacts,
    kyc_status: get('pf_kyc_status'), kyc_expiry_date: get('pf_kyc_expiry_date'),
    aml_risk_rating: get('pf_aml_risk_rating'), sanctions_screening: get('pf_sanctions_screening'),
    tax_id: get('pf_tax_id'), incorporation_country: get('pf_incorporation_country'),
    ubo_structure: get('pf_ubo_structure'), compliance_notes: get('pf_compliance_notes'),
    pep_status: getCheck('pf_pep_status'),
    relationship_manager: get('pf_relationship_manager'), tags: getList('pf_tags'),
    key_events: getLines('pf_key_events'), internal_notes: get('pf_internal_notes'),
  };
}

async function saveClient() {
  const data = collectPortalForm();
  if (!data.name || !data.short_name) { alert('客户名称和简称为必填项。'); return; }
  try {
    const isNew = !_editingClientId;
    const url = isNew ? '/api/portal/clients' : '/api/portal/clients/' + _editingClientId;
    const method = isNew ? 'POST' : 'PUT';
    const res = await fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
    const d = await res.json();
    if (d.success) {
      _editingClientId = d.client.client_id;
      showPortalView('list');
      loadPortalClients();
    } else {
      alert('错误: ' + (d.error || '未知错误'));
    }
  } catch(e) { alert('保存错误: ' + e.message); }
}

async function deleteCurrentClient() {
  if (!_editingClientId) return;
  if (!confirm('确定删除此客户？此操作不可撤销。')) return;
  try {
    const res = await fetch('/api/portal/clients/' + _editingClientId, { method: 'DELETE' });
    const d = await res.json();
    if (d.success) {
      _editingClientId = null;
      showPortalView('list');
      loadPortalClients();
    }
  } catch(e) { alert('删除错误: ' + e.message); }
}

// Corridor row builder
let _corridorIdx = 0;
function addCorridorRow(data) {
  _corridorIdx++;
  const d = data || {};
  const el = document.getElementById('corridorRows');
  const dirs = ['inbound','outbound','both'];
  const dirLabels = {'inbound':'入境','outbound':'出境','both':'双向'};
  const pris = ['Primary','Secondary','Occasional'];
  const priLabels = {'Primary':'主要','Secondary':'次要','Occasional':'偶尔'};
  el.innerHTML += `<div class="corridor-row flex flex-wrap gap-2 items-center" id="cor_${_corridorIdx}">
    <input type="text" class="cor-from portal-input" style="width:60px" placeholder="USD" value="${d.from_currency || d.from || ''}">
    <span class="text-gray-400 text-xs">\u2192</span>
    <input type="text" class="cor-to portal-input" style="width:60px" placeholder="VND" value="${d.to_currency || d.to || ''}">
    <select class="cor-dir portal-input" style="width:90px">${dirs.map(v => `<option value="${v}" ${v===(d.direction||'inbound')?'selected':''}>${dirLabels[v]}</option>`).join('')}</select>
    <input type="text" class="cor-label portal-input flex-1" placeholder="标签" value="${d.label || ''}">
    <select class="cor-priority portal-input" style="width:90px">${pris.map(v => `<option value="${v}" ${v===(d.priority||'Primary')?'selected':''}>${priLabels[v]}</option>`).join('')}</select>
    <input type="text" class="cor-purpose portal-input" style="width:120px" placeholder="用途" value="${d.purpose || ''}">
    <button onclick="this.parentElement.remove()" class="text-red-400 hover:text-red-600 text-sm font-bold">\u2715</button>
  </div>`;
}

// Contact row builder
let _contactIdx = 0;
function addContactRow(data) {
  _contactIdx++;
  const d = data || {};
  const accessLevels = [['Signer','签字人'],['Trader','交易员'],['Viewer','查看者'],['Admin','管理员']];
  const el = document.getElementById('contactRows');
  el.innerHTML += `<div class="contact-row bg-gray-50 border border-gray-200 rounded-lg p-3" id="ct_${_contactIdx}">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
      <div><label class="text-[9px] text-gray-400 uppercase">姓名</label><input type="text" class="ct-name portal-input" value="${d.name || ''}"></div>
      <div><label class="text-[9px] text-gray-400 uppercase">职位</label><input type="text" class="ct-role portal-input" placeholder="如 CFO" value="${d.role || ''}"></div>
      <div><label class="text-[9px] text-gray-400 uppercase">邮箱</label><input type="text" class="ct-email portal-input" value="${d.email || ''}"></div>
      <div><label class="text-[9px] text-gray-400 uppercase">电话</label><input type="text" class="ct-phone portal-input" value="${d.phone || ''}"></div>
    </div>
    <div class="flex items-center gap-4 mt-2">
      <select class="ct-access portal-input" style="width:100px">${accessLevels.map(([v,l]) => `<option value="${v}" ${v===(d.access_level||'Viewer')?'selected':''}>${l}</option>`).join('')}</select>
      <label class="text-[9px] text-gray-500 flex items-center gap-1"><input type="checkbox" class="ct-primary accent-brand-primary" ${d.is_primary ? 'checked' : ''}> 主要联系人</label>
      <label class="text-[9px] text-gray-500 flex items-center gap-1"><input type="checkbox" class="ct-report accent-brand-primary" ${d.receives_report ? 'checked' : ''}> 接收报告</label>
      <button onclick="this.closest('.contact-row').remove()" class="text-red-400 hover:text-red-600 text-[10px] ml-auto">移除</button>
    </div>
  </div>`;
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return WEB_UI.replace("__LOGO_B64__", LOGO_B64)


def _make_config_with_portal(profile_key: str = "", **overrides) -> dict:
    """Create a config dict with portal profiles injected for backward compatibility."""
    cfg = dict(CONFIG)
    portal_profiles = CLIENT_STORE.get_all_as_legacy_profiles()
    if portal_profiles:
        cfg["client_profiles"] = portal_profiles
    if profile_key:
        cfg["_active_client_profile"] = profile_key
    for k, v in overrides.items():
        cfg[k] = v
    return cfg


@app.route("/api/profiles")
def api_profiles():
    """Return client profiles for the report generator profile selector.
    Uses Client Portal data (JSON files) instead of config.yaml."""
    profiles = CLIENT_STORE.get_all_as_legacy_profiles()
    # Fallback to config.yaml if no portal clients exist
    if not profiles:
        profiles = CONFIG.get("client_profiles", {})
    return jsonify({"success": True, "profiles": profiles})


# ──────────────────────────────────────────────────────────────
# CLIENT PORTAL API — Full CRUD for client management
# ──────────────────────────────────────────────────────────────

@app.route("/api/portal/clients")
def api_portal_clients():
    """List clients with optional filters."""
    region = request.args.get("region", "")
    client_type = request.args.get("type", "")
    tier = request.args.get("tier", "")
    status = request.args.get("status", "")
    search = request.args.get("search", "")
    clients = CLIENT_STORE.list_clients(
        region=region or None,
        client_type=client_type or None,
        tier=tier or None,
        status=status or None,
        search=search or None,
    )
    return jsonify({"success": True, "clients": clients})


@app.route("/api/portal/clients/<client_id>")
def api_portal_get_client(client_id):
    """Get a single client's full profile."""
    client = CLIENT_STORE.get_client(client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found"}), 404
    return jsonify({"success": True, "client": client})


@app.route("/api/portal/clients", methods=["POST"])
def api_portal_create_client():
    """Create a new client."""
    data = request.json or {}
    if not data.get("name") or not data.get("short_name"):
        return jsonify({"success": False, "error": "name and short_name are required"}), 400
    client = CLIENT_STORE.create_client(data)
    return jsonify({"success": True, "client": client})


@app.route("/api/portal/clients/<client_id>", methods=["PUT"])
def api_portal_update_client(client_id):
    """Update an existing client."""
    data = request.json or {}
    client = CLIENT_STORE.update_client(client_id, data)
    if not client:
        return jsonify({"success": False, "error": "Client not found"}), 404
    return jsonify({"success": True, "client": client})


@app.route("/api/portal/clients/<client_id>", methods=["DELETE"])
def api_portal_delete_client(client_id):
    """Delete a client."""
    if CLIENT_STORE.delete_client(client_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Client not found"}), 404


@app.route("/api/portal/clients/<client_id>/report-preferences")
def api_portal_report_preferences(client_id):
    """Get report preferences for a client — used to populate Reporting Settings.
    This is the key bridge: Client Portal selection → Reporting Settings auto-fill."""
    prefs = CLIENT_STORE.get_report_preferences(client_id)
    if not prefs:
        return jsonify({"success": False, "error": "Client not found"}), 404
    return jsonify({"success": True, "preferences": prefs})


@app.route("/api/portal/stats")
def api_portal_stats():
    """Portal dashboard statistics."""
    return jsonify({"success": True, "stats": CLIENT_STORE.get_stats()})


@app.route("/api/portal/options")
def api_portal_options():
    """Return all enum/dropdown options for form builder."""
    return jsonify({"success": True, "options": ClientStore.get_field_options()})


@app.route("/api/keys")
def api_keys():
    """Return pre-configured API keys from config.yaml so the frontend can auto-fill."""
    pplx_key = CONFIG.get("ai", {}).get("perplexity", {}).get("api_key", "")
    claude_key = CONFIG.get("ai", {}).get("claude", {}).get("api_key", "")
    llm_enabled = CONFIG.get("llm", {}).get("enabled", False)
    llm_key = CONFIG.get("llm", {}).get("api_key", "")
    return jsonify({
        "success": True,
        "perplexity_key": pplx_key,
        "claude_key": claude_key,
        "llm_enabled": llm_enabled,
        "llm_key_configured": bool(llm_key),
    })


@app.route("/api/defaults")
def api_defaults():
    profile_key = request.args.get("profile", "")
    cfg = _make_config_with_portal(profile_key)
    provider = FXDataProvider(cfg)
    return jsonify({"success": True, "commentary": provider.get_commentary()})


@app.route("/api/preview")
def api_preview():
    profile_key = request.args.get("profile", "")
    api_key = request.args.get("api_key", "")
    data_source = request.args.get("data_source", "")
    cfg = _make_config_with_portal(profile_key)
    if api_key:
        if "data" not in cfg:
            cfg["data"] = {}
        if "alpha_vantage" not in cfg["data"]:
            cfg["data"]["alpha_vantage"] = {}
        cfg["data"]["alpha_vantage"]["api_key"] = api_key
    provider = FXDataProvider(cfg)
    spots = provider.get_spot_rates(data_source=data_source if data_source else None)
    events = provider.get_macro_events()
    profile = provider.get_active_profile()
    focus_pairs = profile.get("focus_pairs", []) if profile else None
    return jsonify({
        "success": True,
        "spot_rates": spots,
        "events": events,
        "focus_pairs": focus_pairs,
        "data_sources": provider.get_data_sources(),
        "data_source_selected": data_source or "auto",
        "errors": provider.get_errors(),
    })


@app.route("/api/news")
def api_news():
    profile_key = request.args.get("profile", "")
    api_key = request.args.get("api_key", "")
    perplexity_key = request.args.get("perplexity_key", "")
    cfg = _make_config_with_portal(profile_key)
    if api_key:
        if "data" not in cfg:
            cfg["data"] = {}
        if "alpha_vantage" not in cfg["data"]:
            cfg["data"]["alpha_vantage"] = {}
        cfg["data"]["alpha_vantage"]["api_key"] = api_key
    if perplexity_key:
        if "ai" not in cfg:
            cfg["ai"] = {}
        if "perplexity" not in cfg["ai"]:
            cfg["ai"]["perplexity"] = {}
        cfg["ai"]["perplexity"]["api_key"] = perplexity_key
    provider = FXDataProvider(cfg)
    return jsonify({
        "success": True,
        "news": provider.get_news(),
        "data_sources": provider.get_data_sources(),
        "errors": provider.get_errors(),
    })


@app.route("/api/ai_news")
def api_ai_news():
    """Fetch news via Perplexity AI with client-profile-aware search prompts."""
    profile_key = request.args.get("profile", "")
    perplexity_key = request.args.get("perplexity_key", "") or CONFIG.get("ai", {}).get("perplexity", {}).get("api_key", "")
    claude_key = request.args.get("claude_key", "") or CONFIG.get("ai", {}).get("claude", {}).get("api_key", "")
    specific_requirements = request.args.get("specific_requirements", "")

    if not perplexity_key:
        return jsonify({"success": False, "error": "Perplexity API key required"}), 400

    cfg = _make_config_with_portal(profile_key)
    if "ai" not in cfg:
        cfg["ai"] = {}
    cfg["ai"]["perplexity"] = {"api_key": perplexity_key, "model": cfg.get("ai", {}).get("perplexity", {}).get("model", "sonar")}
    if claude_key:
        cfg["ai"]["claude"] = {"api_key": claude_key, "model": cfg.get("ai", {}).get("claude", {}).get("model", "claude-sonnet-4-20250514")}
    if specific_requirements:
        cfg["_specific_requirements"] = specific_requirements

    try:
        from news_ai_provider import NewsAIProvider
        ai_provider = NewsAIProvider(cfg)
        prompts = ai_provider.generate_search_prompts(refine_with_claude=bool(claude_key))
        news = ai_provider.fetch_news_from_perplexity(queries=prompts, refine_prompts=False)

        return jsonify({
            "success": True,
            "news": news,
            "search_prompts": prompts,
            "errors": [],
        })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ai_summary", methods=["POST"])
def api_ai_summary():
    """Generate AI Executive Summary using Claude based on news + market data."""
    try:
        params = request.json or {}
        profile_key = params.get("profile", "")
        perplexity_key = params.get("perplexity_key", "") or CONFIG.get("ai", {}).get("perplexity", {}).get("api_key", "")
        claude_key = params.get("claude_key", "") or CONFIG.get("ai", {}).get("claude", {}).get("api_key", "")
        language = params.get("language", "en")
        provided_news = params.get("news", None)
        specific_requirements = params.get("specific_requirements", "")

        # LLM proxy (fit-ai) can substitute for Claude direct key
        llm_enabled = CONFIG.get("llm", {}).get("enabled", False)
        llm_key = CONFIG.get("llm", {}).get("api_key", "")
        if not claude_key and not (llm_enabled and llm_key):
            return jsonify({"success": False, "error": "Claude API key or LLM Proxy required"}), 400

        cfg = _make_config_with_portal(profile_key)
        if "ai" not in cfg:
            cfg["ai"] = {}
        cfg["ai"]["claude"] = {"api_key": claude_key, "model": cfg.get("ai", {}).get("claude", {}).get("model", "claude-sonnet-4-20250514")}
        if perplexity_key:
            cfg["ai"]["perplexity"] = {"api_key": perplexity_key, "model": cfg.get("ai", {}).get("perplexity", {}).get("model", "sonar")}
        if specific_requirements:
            cfg["_specific_requirements"] = specific_requirements

        from news_ai_provider import NewsAIProvider
        ai_provider = NewsAIProvider(cfg)

        # Use provided news or fetch fresh
        news = provided_news
        if not news or len(news) == 0:
            if perplexity_key:
                news = ai_provider.fetch_news_from_perplexity(refine_prompts=True)
            else:
                return jsonify({"success": False, "error": "No news provided and no Perplexity key to fetch. Fetch news first via 'AI News' button."}), 400

        # Get spot rates for context
        provider = FXDataProvider(cfg)
        spot_rates = provider.get_spot_rates()

        # Generate summary with specific requirements
        commentary = ai_provider.generate_executive_summary(news, spot_rates=spot_rates, language=language)

        if commentary.get("_error"):
            return jsonify({"success": False, "error": commentary["_error"]}), 500

        return jsonify({
            "success": True,
            "commentary": commentary,
        })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/generate", methods=["POST"])
def api_generate():
    try:
        params = request.json or {}
        report_date = params.get("report_date", datetime.now().strftime("%Y-%m-%d"))
        output_format = params.get("output_format", "html")
        sections = params.get("sections", {})
        commentary_overrides = params.get("commentary", {})
        api_key = params.get("api_key", "")
        perplexity_key = params.get("perplexity_key", "")
        claude_key = params.get("claude_key", "")
        client_profile = params.get("client_profile", "")
        language = params.get("language", "en")
        specific_requirements = params.get("specific_requirements", "")

        gen_config = _make_config_with_portal(client_profile)
        # Set language in report config for i18n
        if "report" not in gen_config:
            gen_config["report"] = {}
        gen_config["report"]["language"] = language
        if sections:
            gen_config["sections"] = sections
        if client_profile:
            gen_config["_active_client_profile"] = client_profile
        if api_key:
            if "data" not in gen_config:
                gen_config["data"] = {}
            if "alpha_vantage" not in gen_config["data"]:
                gen_config["data"]["alpha_vantage"] = {}
            gen_config["data"]["alpha_vantage"]["api_key"] = api_key
        if perplexity_key or claude_key:
            if "ai" not in gen_config:
                gen_config["ai"] = {}
            if perplexity_key:
                if "perplexity" not in gen_config["ai"]:
                    gen_config["ai"]["perplexity"] = {}
                gen_config["ai"]["perplexity"]["api_key"] = perplexity_key
            if claude_key:
                if "claude" not in gen_config["ai"]:
                    gen_config["ai"]["claude"] = {}
                gen_config["ai"]["claude"]["api_key"] = claude_key

        if specific_requirements:
            gen_config["_specific_requirements"] = specific_requirements

        gen = ReportGenerator(gen_config, overrides={"commentary": commentary_overrides})
        output_path = gen.generate(as_of=report_date, output_format=output_format)

        filename = os.path.basename(output_path)
        return jsonify({
            "success": True,
            "filename": filename,
            "format": output_format,
            "path": output_path,
        })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/download")
def api_download():
    filename = request.args.get("file", "")
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    mimetype = "application/pdf" if filename.endswith(".pdf") else "text/html"
    return send_file(str(filepath), mimetype=mimetype, as_attachment=False, download_name=filename)


# ──────────────────────────────────────────────────────────────
# Demo / Presentation Page (templates/demo.html)
# ──────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────
#  DASHBOARD — 工具看板
# ──────────────────────────────────────────────────────────────

TOOL_REGISTRY = [
    {
        "id": "fx-report",
        "name": "FX 研报工具",
        "desc": "客户画像 → 数据聚合 → AI 分析 → 研报生成",
        "port": 8890,
        "url": "http://localhost:8890",
        "entry": str(BASE_DIR / "app.py"),
        "cwd": str(BASE_DIR),
        "icon": "📊",
        "self": True,
    },
    {
        "id": "markup-pricing",
        "name": "Markup 加价器",
        "desc": "多主体加价分析，波动率加权，反算加价方案",
        "port": 8891,
        "url": "http://localhost:8891",
        "entry": str(BASE_DIR.parent / "markup-pricing" / "markup_app.py"),
        "cwd": str(BASE_DIR.parent / "markup-pricing"),
        "icon": "💰",
        "self": False,
    },
    {
        "id": "strategy-lab",
        "name": "策略实验室",
        "desc": "FridayNight / MA Cross 策略回测分析",
        "port": 8888,
        "url": "http://localhost:8888",
        "entry": str(BASE_DIR.parent / "strategy-lab" / "run.py"),
        "cwd": str(BASE_DIR.parent / "strategy-lab"),
        "icon": "🧪",
        "self": False,
    },
    {
        "id": "backtest-dashboard",
        "name": "回测仪表盘",
        "desc": "Weekend Pre-Lock 回测 Wizard",
        "port": 8889,
        "url": "http://localhost:8889",
        "entry": str(BASE_DIR.parent / "bmad-quant-system" / "backtest" / "dashboard" / "app.py"),
        "cwd": str(BASE_DIR.parent / "bmad-quant-system" / "backtest" / "dashboard"),
        "icon": "📈",
        "self": False,
    },
    {
        "id": "bbg-toolbox",
        "name": "Bloomberg 数据工具箱",
        "desc": "Bloomberg 数据下载与可视化",
        "port": 5001,
        "url": "http://localhost:5001",
        "entry": str(BASE_DIR.parent / "bmad-quant-system" / "start_bbg_web.py"),
        "cwd": str(BASE_DIR.parent / "bmad-quant-system"),
        "icon": "🔌",
        "self": False,
    },
    {
        "id": "quant-web",
        "name": "量化系统 Web UI",
        "desc": "策略配置与回测管理",
        "port": 8080,
        "url": "http://localhost:8080",
        "entry": str(BASE_DIR.parent / "bmad-quant-system" / "quant_system" / "web" / "app.py"),
        "cwd": str(BASE_DIR.parent / "bmad-quant-system"),
        "icon": "⚙️",
        "self": False,
    },
    {
        "id": "quant-api",
        "name": "Quant API Server",
        "desc": "回测与策略管理 RESTful 接口",
        "port": 5000,
        "url": "http://localhost:5000",
        "entry": str(BASE_DIR.parent / "bmad-quant-system" / "quant_system" / "api" / "server.py"),
        "cwd": str(BASE_DIR.parent / "bmad-quant-system"),
        "icon": "🔗",
        "self": False,
    },
    {
        "id": "wedata-notebooks",
        "name": "WeData Notebooks",
        "desc": "FX 交易数据分析 Notebook，同步到工蜂供 WeData 拉取执行",
        "port": 0,
        "url": "https://git.code.tencent.com/tencentren/FX_TRADING_TEAM",
        "entry": str(BASE_DIR.parent / "wedata-notebooks" / "sync.py"),
        "cwd": str(BASE_DIR.parent / "wedata-notebooks"),
        "icon": "📓",
        "self": False,
        "type": "git-sync",
    },
    {
        "id": "wedata-analysis",
        "name": "WeData Analysis",
        "desc": "WeData 分析项目 — 交易/定价/风控 Notebooks，同步到内网工蜂",
        "port": 0,
        "url": "https://git.woa.com/tencentren/wedata_analysis",
        "entry": str(BASE_DIR.parent / "wedata_analysis" / "sync.py"),
        "cwd": str(BASE_DIR.parent / "wedata_analysis"),
        "icon": "🔬",
        "self": False,
        "type": "git-sync",
    },
]

_launched_procs = {}


def _port_alive(port, host="127.0.0.1", timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/api/tools/status")
def tools_status():
    result = []
    for t in TOOL_REGISTRY:
        item = {
            "id": t["id"],
            "name": t["name"],
            "desc": t["desc"],
            "port": t["port"],
            "url": t["url"],
            "icon": t["icon"],
            "self": t.get("self", False),
            "type": t.get("type", "web"),
        }
        if t.get("type") == "git-sync":
            item["alive"] = True
            try:
                r = subprocess.run(
                    [sys.executable, "-c",
                     "import subprocess,os; os.chdir(r'" + t["cwd"] + "');"
                     "s=subprocess.run('git status --porcelain',shell=True,capture_output=True,text=True);"
                     "l=subprocess.run('git log -1 --format=%h %s (%ar)',shell=True,capture_output=True,text=True);"
                     "print('LAST:'+l.stdout.strip()); print('DIRTY:'+str(bool(s.stdout.strip())))"],
                    capture_output=True, text=True, timeout=5
                )
                for line in r.stdout.strip().split('\n'):
                    if line.startswith('LAST:'): item["last_commit"] = line[5:]
                    if line.startswith('DIRTY:'): item["has_changes"] = line[6:] == "True"
            except Exception:
                item["last_commit"] = "unknown"
                item["has_changes"] = False
        else:
            item["alive"] = _port_alive(t["port"])
        result.append(item)
    return jsonify(result)


@app.route("/api/tools/start/<tool_id>", methods=["POST"])
def tool_start(tool_id):
    tool = next((t for t in TOOL_REGISTRY if t["id"] == tool_id), None)
    if not tool:
        return jsonify({"ok": False, "msg": "未知工具"}), 404
    if tool.get("self"):
        return jsonify({"ok": True, "msg": "当前服务已在运行"})
    if _port_alive(tool["port"]):
        return jsonify({"ok": True, "msg": "已在运行"})
    try:
        proc = subprocess.Popen(
            [sys.executable, tool["entry"]],
            cwd=tool["cwd"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _launched_procs[tool_id] = proc
        return jsonify({"ok": True, "msg": f"已启动 (PID {proc.pid})"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/tools/sync/<tool_id>", methods=["POST"])
def tool_sync(tool_id):
    tool = next((t for t in TOOL_REGISTRY if t["id"] == tool_id and t.get("type") == "git-sync"), None)
    if not tool:
        return jsonify({"ok": False, "msg": "不是 git-sync 类型的工具"}), 400
    msg = request.json.get("message", "") if request.is_json else ""
    try:
        cmd = [sys.executable, tool["entry"]]
        if msg:
            cmd.append(msg)
        r = subprocess.run(cmd, cwd=tool["cwd"], capture_output=True, text=True, timeout=30)
        output = r.stdout + r.stderr
        return jsonify({"ok": r.returncode == 0, "msg": output.strip()})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "msg": "同步超时 (30s)"}), 500
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/demo")
def demo_page():
    """Serve the demo / presentation page (Chinese tech-style product overview)."""
    return render_template("demo.html")


if __name__ == "__main__":
    conf = CONFIG.get("server", {})
    host = conf.get("host", "0.0.0.0")
    port = conf.get("port", 8890)
    debug = conf.get("debug", True)

    print(f"\n{'='*60}")
    print(f"  FX Research Report Generator — Tenpay Global")
    print(f"  http://localhost:{port}")
    print(f"  Demo page: http://localhost:{port}/demo")
    print(f"  Client Profiles: {list(CONFIG.get('client_profiles', {}).keys())}")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=debug)
