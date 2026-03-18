"""
Bloomberg 数据工具箱 - Web UI
==============================

提供友好的Web界面进行数据下载和可视化
"""

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import os

from .data_explorer import DataExplorer

# 版本信息
APP_VERSION = "1.7.3"
APP_UPDATE_TIME = "2026-01-05 00:40"

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bloomberg 数据工具箱</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117; 
            color: #c9d1d9;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #238636 0%, #1f6feb 100%);
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }
        .header h1 { font-size: 20px; font-weight: 600; color: #fff; }
        .header-right {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .version-info {
            font-size: 11px;
            color: rgba(255,255,255,0.7);
            text-align: right;
        }
        .version-info .ver { font-weight: 600; }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #f85149;
        }
        .status-dot.connected { background: #3fb950; }
        
        .container {
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 12px;
            padding: 12px;
            max-width: 1920px;
            margin: 0 auto;
            height: calc(100vh - 56px);
        }
        
        .panel {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            overflow-y: auto;
        }
        
        .panel-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #30363d;
            color: #f0f6fc;
        }
        
        .form-group {
            margin-bottom: 12px;
        }
        .form-group label {
            display: block;
            font-size: 12px;
            color: #8b949e;
            margin-bottom: 4px;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid #30363d;
            border-radius: 6px;
            background: #0d1117;
            color: #c9d1d9;
            font-size: 13px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #58a6ff;
            box-shadow: 0 0 0 3px rgba(88,166,255,0.15);
        }
        
        .btn {
            padding: 8px 16px;
            border: 1px solid #30363d;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s;
            width: 100%;
            margin-bottom: 8px;
            background: #21262d;
            color: #c9d1d9;
        }
        .btn:hover { background: #30363d; }
        .btn-primary {
            background: #238636;
            border-color: #238636;
            color: #fff;
        }
        .btn-primary:hover { background: #2ea043; }
        
        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        
        .data-type-tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 16px;
            background: #0d1117;
            padding: 4px;
            border-radius: 6px;
        }
        .data-type-tabs button {
            flex: 1;
            padding: 8px;
            border: none;
            background: transparent;
            color: #8b949e;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
        }
        .data-type-tabs button.active {
            background: #238636;
            color: white;
        }
        .data-type-tabs button:hover:not(.active) {
            background: #21262d;
        }
        
        .right-panel {
            display: flex;
            flex-direction: column;
            gap: 0;
            overflow-y: auto;
            height: 100%;
        }
        
        .chart-section {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
            min-height: 350px;
            height: 450px;
            flex-shrink: 0;
            position: relative;
        }
        
        /* 可拖拽调节高度的分隔条 */
        .resize-handle {
            height: 8px;
            background: linear-gradient(to bottom, #21262d, #161b22);
            cursor: ns-resize;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .resize-handle:hover {
            background: linear-gradient(to bottom, #30363d, #21262d);
        }
        .resize-handle::after {
            content: '';
            width: 40px;
            height: 3px;
            background: #484f58;
            border-radius: 2px;
        }
        .resize-handle:hover::after {
            background: #58a6ff;
        }
        
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .chart-title {
            font-size: 13px;
            font-weight: 600;
            color: #f0f6fc;
        }
        .chart-type-btns {
            display: flex;
            gap: 4px;
        }
        .chart-type-btns button {
            padding: 3px 8px;
            border: 1px solid #30363d;
            background: #21262d;
            color: #8b949e;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }
        .chart-type-btns button.active {
            background: #1f6feb;
            border-color: #1f6feb;
            color: #fff;
        }
        
        .chart-container {
            height: calc(100% - 32px);
            min-height: 200px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
            flex-shrink: 0;
        }
        .stat-card {
            background: #0d1117;
            padding: 8px 10px;
            border-radius: 6px;
            border: 1px solid #30363d;
        }
        .stat-card .value {
            font-size: 15px;
            font-weight: 600;
            color: #58a6ff;
        }
        .stat-card .value.positive { color: #3fb950; }
        .stat-card .value.negative { color: #f85149; }
        .stat-card .label {
            font-size: 10px;
            color: #8b949e;
            margin-top: 2px;
        }
        
        .table-section {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
            min-height: 400px;
            height: 500px;
            flex-shrink: 0;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .table-filter {
            display: flex;
            gap: 6px;
            margin-bottom: 8px;
            align-items: center;
            flex-wrap: wrap;
            flex-shrink: 0;
        }
        .table-filter input, .table-filter select {
            padding: 4px 6px;
            border: 1px solid #30363d;
            border-radius: 4px;
            background: #0d1117;
            color: #c9d1d9;
            font-size: 11px;
        }
        .table-filter input:focus, .table-filter select:focus {
            outline: none;
            border-color: #58a6ff;
        }
        .table-filter label {
            font-size: 10px;
            color: #8b949e;
        }
        .table-filter .filter-btn {
            padding: 4px 8px;
            border: 1px solid #30363d;
            background: #21262d;
            color: #c9d1d9;
            border-radius: 4px;
            cursor: pointer;
            font-size: 10px;
        }
        .table-filter .filter-btn:hover {
            background: #30363d;
        }
        .table-filter .filter-btn.active {
            background: #1f6feb;
            border-color: #1f6feb;
        }
        .table-wrapper {
            flex: 1;
            overflow-y: auto;
            min-height: 0;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }
        .data-table th, .data-table td {
            padding: 6px 8px;
            text-align: right;
            border-bottom: 1px solid #21262d;
        }
        .data-table th {
            background: #0d1117;
            color: #8b949e;
            font-weight: 500;
            position: sticky;
            top: 0;
            z-index: 1;
            font-size: 10px;
        }
        .data-table td:first-child, .data-table th:first-child {
            text-align: left;
        }
        .data-table tbody tr:hover {
            background: #1c2128;
            cursor: pointer;
        }
        .data-table tbody tr.highlighted {
            background: #1f6feb33;
            border-left: 3px solid #1f6feb;
        }
        .data-table tbody tr.filtered-out {
            display: none;
        }
        
        .log-panel {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 10px;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 11px;
            max-height: 120px;
            overflow-y: auto;
            margin-top: 12px;
        }
        .log-entry { margin-bottom: 4px; line-height: 1.4; }
        .log-entry.success { color: #3fb950; }
        .log-entry.error { color: #f85149; }
        .log-entry.info { color: #58a6ff; }
        
        .quick-symbols {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 8px;
        }
        .quick-symbols button {
            padding: 4px 8px;
            border: 1px solid #30363d;
            background: #21262d;
            color: #8b949e;
            border-radius: 4px;
            cursor: pointer;
            font-size: 10px;
        }
        .quick-symbols button:hover {
            border-color: #58a6ff;
            color: #58a6ff;
        }
        
        /* 滚动条样式 */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }
        
        /* 模态框样式 */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            width: 90%;
            max-width: 1200px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            border-bottom: 1px solid #30363d;
        }
        .modal-header h2 {
            font-size: 16px;
            font-weight: 600;
            color: #f0f6fc;
        }
        .modal-close {
            background: none;
            border: none;
            color: #8b949e;
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }
        .modal-close:hover { color: #f85149; }
        .modal-body {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .modal-sidebar {
            width: 280px;
            padding: 16px;
            border-right: 1px solid #30363d;
            overflow-y: auto;
        }
        .modal-content {
            flex: 1;
            padding: 16px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .modal-chart {
            flex: 1;
            min-height: 400px;
        }
        .config-section {
            margin-bottom: 16px;
        }
        .config-section-title {
            font-size: 12px;
            font-weight: 600;
            color: #8b949e;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .config-row {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }
        .config-row label {
            width: 80px;
            font-size: 12px;
            color: #8b949e;
        }
        .config-row input, .config-row select {
            flex: 1;
            padding: 6px 8px;
            border: 1px solid #30363d;
            border-radius: 4px;
            background: #0d1117;
            color: #c9d1d9;
            font-size: 12px;
        }
        .config-row input[type="checkbox"] {
            width: auto;
            flex: none;
            margin-right: 8px;
        }
        .config-row input[type="color"] {
            width: 60px;
            height: 28px;
            padding: 2px;
            flex: none;
        }
        .chart-info {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 10px;
            margin-top: 12px;
            font-size: 11px;
            color: #8b949e;
        }
        .chart-info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        .chart-info-row:last-child { margin-bottom: 0; }
        .btn-chart {
            background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
            border: none;
            color: #fff;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            margin-top: 8px;
            width: 100%;
        }
        .btn-chart:hover {
            opacity: 0.9;
        }
        .btn-chart:disabled {
            background: #30363d;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Bloomberg 数据工具箱</h1>
        <div class="header-right">
            <div class="version-info">
                <div class="ver">v{{ version }}</div>
                <div>{{ update_time }}</div>
            </div>
            <div class="status">
                <span id="statusText">未连接</span>
                <div class="status-dot" id="statusDot"></div>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- 左侧控制面板 -->
        <div class="panel">
            <div class="panel-title">数据下载</div>
            
            <!-- 数据类型选择 -->
            <div class="data-type-tabs">
                <button class="active" onclick="selectDataType('bar')">K线</button>
                <button onclick="selectDataType('tick')">Tick</button>
                <button onclick="selectDataType('bidask')">Bid/Ask</button>
                <button onclick="selectDataType('ref')">参考</button>
            </div>
            
            <!-- 品种输入 -->
            <div class="form-group">
                <label>Bloomberg代码</label>
                <input type="text" id="symbol" value="USDCNH Curncy" placeholder="如: USDCNH Curncy">
                <div class="quick-symbols">
                    <button onclick="setSymbol('USDCNH Curncy')">USDCNH</button>
                    <button onclick="setSymbol('EURUSD Curncy')">EURUSD</button>
                    <button onclick="setSymbol('USDJPY Curncy')">USDJPY</button>
                    <button onclick="setSymbol('GBPUSD Curncy')">GBPUSD</button>
                    <button onclick="setSymbol('SPX Index')">SPX</button>
                    <button onclick="setSymbol('HSI Index')">HSI</button>
                </div>
            </div>
            
            <!-- 时区选择 -->
            <div class="form-group">
                <label>时区</label>
                <select id="timezone">
                    <option value="Asia/Shanghai" selected>北京时间 (UTC+8)</option>
                    <option value="America/New_York">纽约时间 (EST/EDT)</option>
                    <option value="Europe/London">伦敦时间 (GMT/BST)</option>
                    <option value="Asia/Tokyo">东京时间 (UTC+9)</option>
                    <option value="Asia/Hong_Kong">香港时间 (UTC+8)</option>
                    <option value="UTC">UTC</option>
                </select>
            </div>
            
            <!-- Bar数据参数 -->
            <div id="barParams">
                <div class="form-group">
                    <label>时间间隔</label>
                    <select id="interval">
                        <option value="1m">1分钟</option>
                        <option value="5m">5分钟</option>
                        <option value="15m">15分钟</option>
                        <option value="30m">30分钟</option>
                        <option value="1h">1小时</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>时间模式</label>
                    <select id="barTimeMode" onchange="toggleBarTimeMode()">
                        <option value="days">向前N天</option>
                        <option value="range">指定时间段</option>
                    </select>
                </div>
                <div id="barDaysMode">
                    <div class="form-group">
                        <label>天数</label>
                        <input type="number" id="daysBack" value="7" min="1" max="365">
                    </div>
                </div>
                <div id="barRangeMode" style="display:none;">
                    <div class="form-group">
                        <label>开始时间</label>
                        <input type="datetime-local" id="barStartTime">
                    </div>
                    <div class="form-group">
                        <label>结束时间</label>
                        <input type="datetime-local" id="barEndTime">
                    </div>
                    <div class="quick-symbols">
                        <button onclick="setBarLastWeek()">最近一周</button>
                        <button onclick="setBarLastMonth()">最近一月</button>
                        <button onclick="setBarLastFriday()">上周五</button>
                    </div>
                </div>
            </div>
            
            <!-- Tick数据参数 -->
            <div id="tickParams" style="display:none;">
                <div class="form-group">
                    <label>时间模式</label>
                    <select id="tickTimeMode" onchange="toggleTickTimeMode()">
                        <option value="hours">向前N小时</option>
                        <option value="range">指定时间段</option>
                    </select>
                </div>
                <div id="tickHoursMode">
                    <div class="form-group">
                        <label>小时数</label>
                        <input type="number" id="hoursBack" value="2" min="0.5" max="24" step="0.5">
                    </div>
                </div>
                <div id="tickRangeMode" style="display:none;">
                    <div class="form-group">
                        <label>开始时间</label>
                        <input type="datetime-local" id="tickStartTime">
                    </div>
                    <div class="form-group">
                        <label>结束时间</label>
                        <input type="datetime-local" id="tickEndTime">
                    </div>
                    <div class="quick-symbols">
                        <button onclick="setTickLastTradeDay()">上个交易日</button>
                        <button onclick="setTickLastHour()">最近1小时</button>
                    </div>
                </div>
            </div>
            
            <!-- Bid/Ask数据参数 -->
            <div id="bidaskParams" style="display:none;">
                <div class="form-group">
                    <label>时间模式</label>
                    <select id="bidaskTimeMode" onchange="toggleBidaskTimeMode()">
                        <option value="hours">向前N小时</option>
                        <option value="range">指定时间段</option>
                    </select>
                </div>
                <div id="bidaskHoursMode">
                    <div class="form-group">
                        <label>小时数</label>
                        <input type="number" id="bidaskHoursBack" value="2" min="0.5" max="24" step="0.5">
                    </div>
                </div>
                <div id="bidaskRangeMode" style="display:none;">
                    <div class="form-group">
                        <label>开始日期时间</label>
                        <input type="datetime-local" id="bidaskStartTime">
                    </div>
                    <div class="form-group">
                        <label>结束日期时间</label>
                        <input type="datetime-local" id="bidaskEndTime">
                    </div>
                    <div class="quick-symbols">
                        <button onclick="setBidaskLastTradeDay()">上个交易日</button>
                        <button onclick="setBidaskLastFriday()">上周五晚</button>
                    </div>
                    
                    <!-- 每日时段过滤 -->
                    <div class="form-group" style="margin-top:10px; padding-top:10px; border-top:1px dashed #ddd;">
                        <label>
                            <input type="checkbox" id="bidaskDailyFilter" onchange="toggleDailyFilter()"> 
                            每日时段过滤
                        </label>
                        <small style="color:#888; display:block; margin-top:3px;">仅保留每天指定时间段的数据</small>
                    </div>
                    <div id="bidaskDailyFilterOptions" style="display:none; background:#f9f9f9; padding:8px; border-radius:4px;">
                        <div style="display:flex; gap:10px;">
                            <div class="form-group" style="flex:1; margin:0;">
                                <label style="font-size:12px;">每日开始</label>
                                <input type="time" id="bidaskDailyStart" value="09:00">
                            </div>
                            <div class="form-group" style="flex:1; margin:0;">
                                <label style="font-size:12px;">每日结束</label>
                                <input type="time" id="bidaskDailyEnd" value="10:00">
                            </div>
                        </div>
                        <div class="quick-symbols" style="margin-top:8px;">
                            <button onclick="setDailyTime('09:00','10:00')">9-10点</button>
                            <button onclick="setDailyTime('09:00','12:00')">上午盘</button>
                            <button onclick="setDailyTime('14:00','17:00')">下午盘</button>
                            <button onclick="setDailyTime('20:00','23:00')">晚盘</button>
                        </div>
                    </div>
                </div>
                <div class="form-group">
                    <label>重采样</label>
                    <select id="bidaskResample">
                        <option value="">原始Tick</option>
                        <option value="1s">1秒</option>
                        <option value="5s">5秒</option>
                        <option value="10s">10秒</option>
                        <option value="30s">30秒</option>
                        <option value="1min" selected>1分钟</option>
                        <option value="2min">2分钟</option>
                        <option value="5min">5分钟</option>
                        <option value="10min">10分钟</option>
                        <option value="15min">15分钟</option>
                        <option value="30min">30分钟</option>
                        <option value="1h">1小时</option>
                    </select>
                    <small style="color:#888; font-size:11px;">优先尝试 Bar 请求, 间隔不对时自动回退到 tick 重采样</small>
                </div>
            </div>
            
            <!-- 参考数据参数 -->
            <div id="refParams" style="display:none;">
                <div class="form-group">
                    <label>字段（逗号分隔）</label>
                    <input type="text" id="refFields" value="PX_LAST,NAME,CRNCY">
                </div>
            </div>
            
            <!-- 操作按钮组 - 按顺序排列 -->
            <button class="btn btn-primary" onclick="downloadData()">1. 下载数据</button>
            
            <div id="chartBtnContainer">
                <button class="btn-chart" onclick="openChartModal(currentDataType)" id="customChartBtn" disabled>2. 📈 自定义画图</button>
            </div>
            
            <div class="btn-group">
                <button class="btn" onclick="exportCSV()">3. 导出CSV</button>
                <button class="btn" onclick="exportExcel()">导出Excel</button>
            </div>
            
            <button class="btn" onclick="connectBBG()">重新连接</button>
            
            <!-- 日志 -->
            <div class="log-panel" id="logPanel">
                <div class="log-entry info">[系统] 准备就绪</div>
            </div>
        </div>
        
        <!-- 右侧数据展示 -->
        <div class="right-panel">
            <!-- 统计卡片 -->
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <div class="value" id="statRows">-</div>
                    <div class="label">数据行数</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="statLast">-</div>
                    <div class="label">最新价</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="statHigh">-</div>
                    <div class="label">最高</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="statLow">-</div>
                    <div class="label">最低</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="statReturn">-</div>
                    <div class="label">区间收益</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="statSpread">-</div>
                    <div class="label">平均Spread</div>
                </div>
            </div>
            
            <!-- 图表区域 -->
            <div class="chart-section" id="chartSection">
                <div class="chart-header">
                    <div class="chart-title" id="chartTitle">K线图</div>
                    <div class="chart-type-btns">
                        <button class="active" onclick="setChartType('candle')">K线</button>
                        <button onclick="setChartType('line')">折线</button>
                        <button onclick="setChartType('area')">面积</button>
                    </div>
                </div>
                <div class="chart-container" id="mainChart"></div>
            </div>
            
            <!-- 可拖拽调节高度的分隔条 -->
            <div class="resize-handle" id="resizeHandle" title="拖拽调整图表和表格高度"></div>
            
            <!-- 数据表格 -->
            <div class="table-section" id="tableSection">
                <div class="panel-title">数据明细 <span id="tableInfo" style="font-weight:normal;color:#8b949e;"></span></div>
                
                <!-- 时间筛选器 -->
                <div class="table-filter" id="tableFilter">
                    <label>时间筛选:</label>
                    <select id="filterMode" onchange="toggleFilterMode()">
                        <option value="all">全部</option>
                        <option value="date">日期</option>
                        <option value="daterange">日期范围</option>
                        <option value="exact">精确时间</option>
                        <option value="range">时间范围</option>
                        <option value="contains">包含</option>
                    </select>
                    <input type="date" id="filterDate" style="width:130px;display:none;">
                    <input type="date" id="filterDateStart" style="width:120px;display:none;">
                    <input type="date" id="filterDateEnd" style="width:120px;display:none;">
                    <input type="text" id="filterExact" placeholder="如: 21:00" style="width:80px;display:none;">
                    <input type="text" id="filterStart" placeholder="开始 如:20:00" style="width:90px;display:none;">
                    <input type="text" id="filterEnd" placeholder="结束 如:22:00" style="width:90px;display:none;">
                    <input type="text" id="filterContains" placeholder="包含文字" style="width:80px;display:none;">
                    <button class="filter-btn" onclick="applyFilter()">筛选</button>
                    <button class="filter-btn" onclick="clearFilter()">清除</button>
                    <span style="margin-left:auto;font-size:11px;color:#8b949e;">
                        <button class="filter-btn" onclick="jumpToTime('first')">首条</button>
                        <button class="filter-btn" onclick="jumpToTime('last')">末条</button>
                    </span>
                </div>
                
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead>
                            <tr id="tableHeader">
                                <th>时间</th>
                                <th>开盘</th>
                                <th>最高</th>
                                <th>最低</th>
                                <th>收盘</th>
                                <th>成交量</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody">
                            <tr><td colspan="6" style="text-align:center;color:#8b949e;">暂无数据</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 画图配置模态框 -->
    <div class="modal-overlay" id="chartModal">
        <div class="modal">
            <div class="modal-header">
                <h2 id="modalTitle">📈 自定义画图配置</h2>
                <button class="modal-close" onclick="closeChartModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-sidebar">
                    <div class="config-section">
                        <div class="config-section-title">数据信息</div>
                        <div class="chart-info" id="dataInfo">
                            <div class="chart-info-row"><span>品种:</span><span id="infoSymbol">-</span></div>
                            <div class="chart-info-row"><span>数据类型:</span><span id="infoType">-</span></div>
                            <div class="chart-info-row"><span>数据量:</span><span id="infoRows">-</span></div>
                            <div class="chart-info-row"><span>时间范围:</span><span id="infoTimeRange">-</span></div>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <div class="config-section-title">时间范围</div>
                        <div class="config-row">
                            <label>开始</label>
                            <input type="datetime-local" id="chartStartTime">
                        </div>
                        <div class="config-row">
                            <label>结束</label>
                            <input type="datetime-local" id="chartEndTime">
                        </div>
                        <div class="quick-symbols" style="margin-top:8px;">
                            <button onclick="setChartTimeRange('all')">全部</button>
                            <button onclick="setChartTimeRange('last1h')">最近1h</button>
                            <button onclick="setChartTimeRange('last4h')">最近4h</button>
                            <button onclick="setChartTimeRange('last1d')">最近1天</button>
                        </div>
                    </div>
                    
                    <div class="config-section">
                        <div class="config-section-title">图表类型</div>
                        <div class="config-row">
                            <label>类型</label>
                            <select id="modalChartType" onchange="updateModalChart()">
                                <option value="candlestick">K线图</option>
                                <option value="line">折线图</option>
                                <option value="area">面积图</option>
                                <option value="scatter">散点图</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="config-section" id="columnConfig">
                        <div class="config-section-title">数据列选择 (左Y轴)</div>
                        <div id="columnCheckboxes"></div>
                    </div>
                    
                    <div class="config-section" id="rightAxisConfig">
                        <div class="config-section-title">右Y轴数据列</div>
                        <div id="rightAxisCheckboxes"></div>
                    </div>
                    
                    <div class="config-section">
                        <div class="config-section-title">样式设置</div>
                        <div class="config-row">
                            <label>涨色</label>
                            <input type="color" id="colorUp" value="#3fb950" onchange="updateModalChart()">
                        </div>
                        <div class="config-row">
                            <label>跌色</label>
                            <input type="color" id="colorDown" value="#f85149" onchange="updateModalChart()">
                        </div>
                        <div class="config-row">
                            <label>线宽</label>
                            <select id="lineWidth" onchange="updateModalChart()">
                                <option value="1">1px</option>
                                <option value="2" selected>2px</option>
                                <option value="3">3px</option>
                            </select>
                        </div>
                        <div class="config-row">
                            <input type="checkbox" id="showMA" onchange="updateModalChart()">
                            <label style="width:auto;">显示均线</label>
                        </div>
                    </div>
                    
                    <button class="btn btn-primary" onclick="updateModalChart()" style="margin-top:12px;">预览图表</button>
                    <button class="btn btn-primary" onclick="applyToMainChart()" style="margin-top:8px;background:#238636;">✓ 应用到主图</button>
                </div>
                <div class="modal-content">
                    <div class="modal-chart" id="modalChartContainer"></div>
                    <div class="chart-info" style="margin-top:12px;">
                        <div class="chart-info-row"><span>显示数据点:</span><span id="chartDataPoints">-</span></div>
                        <div class="chart-info-row"><span>最高价:</span><span id="chartHigh">-</span></div>
                        <div class="chart-info-row"><span>最低价:</span><span id="chartLow">-</span></div>
                        <div class="chart-info-row"><span>区间涨跌:</span><span id="chartChange">-</span></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentDataType = 'bar';
        let currentCacheKey = null;
        let currentChartType = 'candle';
        let mainChart = null;
        let modalChart = null;
        let cachedData = null;
        let fullData = null;  // 完整数据用于模态框
        let dataTimeRange = { start: null, end: null };
        
        // 颜色配置
        const colors = {
            up: '#3fb950',
            down: '#f85149',
            bid: '#3fb950',
            ask: '#f85149',
            line: '#58a6ff',
            volume: '#30363d',
            grid: '#21262d'
        };
        
        // 初始化图表
        function initChart() {
            mainChart = echarts.init(document.getElementById('mainChart'));
            window.addEventListener('resize', () => {
                mainChart.resize();
                if (modalChart) modalChart.resize();
            });
        }
        
        // 选择数据类型
        function selectDataType(type) {
            currentDataType = type;
            document.querySelectorAll('.data-type-tabs button').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            document.getElementById('barParams').style.display = type === 'bar' ? 'block' : 'none';
            document.getElementById('tickParams').style.display = type === 'tick' ? 'block' : 'none';
            document.getElementById('bidaskParams').style.display = type === 'bidask' ? 'block' : 'none';
            document.getElementById('refParams').style.display = type === 'ref' ? 'block' : 'none';
        }
        
        // 设置品种
        function setSymbol(symbol) {
            document.getElementById('symbol').value = symbol;
        }
        
        // 格式化为datetime-local格式
        function formatDateTimeLocal(date) {
            const pad = n => n.toString().padStart(2, '0');
            return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
        }
        
        // ========== Bar时间模式 ==========
        function toggleBarTimeMode() {
            const mode = document.getElementById('barTimeMode').value;
            document.getElementById('barDaysMode').style.display = mode === 'days' ? 'block' : 'none';
            document.getElementById('barRangeMode').style.display = mode === 'range' ? 'block' : 'none';
        }
        
        function setBarLastWeek() {
            const now = new Date();
            const end = new Date(now);
            const start = new Date(now);
            start.setDate(start.getDate() - 7);
            document.getElementById('barStartTime').value = formatDateTimeLocal(start);
            document.getElementById('barEndTime').value = formatDateTimeLocal(end);
        }
        
        function setBarLastMonth() {
            const now = new Date();
            const end = new Date(now);
            const start = new Date(now);
            start.setMonth(start.getMonth() - 1);
            document.getElementById('barStartTime').value = formatDateTimeLocal(start);
            document.getElementById('barEndTime').value = formatDateTimeLocal(end);
        }
        
        function setBarLastFriday() {
            const now = new Date();
            const dayOfWeek = now.getDay();
            let lastFriday = new Date(now);
            const diff = dayOfWeek === 5 ? 7 : (dayOfWeek === 6 ? 1 : dayOfWeek + 2);
            lastFriday.setDate(now.getDate() - diff);
            
            const start = new Date(lastFriday);
            start.setHours(0, 0, 0, 0);
            const end = new Date(lastFriday);
            end.setHours(23, 59, 0, 0);
            
            document.getElementById('barStartTime').value = formatDateTimeLocal(start);
            document.getElementById('barEndTime').value = formatDateTimeLocal(end);
        }
        
        // ========== Tick时间模式 ==========
        function toggleTickTimeMode() {
            const mode = document.getElementById('tickTimeMode').value;
            document.getElementById('tickHoursMode').style.display = mode === 'hours' ? 'block' : 'none';
            document.getElementById('tickRangeMode').style.display = mode === 'range' ? 'block' : 'none';
        }
        
        function setTickLastTradeDay() {
            const now = new Date();
            let lastTradeEnd = new Date(now);
            while (lastTradeEnd.getDay() === 0 || lastTradeEnd.getDay() === 6) {
                lastTradeEnd.setDate(lastTradeEnd.getDate() - 1);
            }
            lastTradeEnd.setHours(22, 0, 0, 0);
            const lastTradeStart = new Date(lastTradeEnd);
            lastTradeStart.setHours(20, 0, 0, 0);
            document.getElementById('tickStartTime').value = formatDateTimeLocal(lastTradeStart);
            document.getElementById('tickEndTime').value = formatDateTimeLocal(lastTradeEnd);
        }
        
        function setTickLastHour() {
            const now = new Date();
            const end = new Date(now);
            const start = new Date(now);
            start.setHours(start.getHours() - 1);
            document.getElementById('tickStartTime').value = formatDateTimeLocal(start);
            document.getElementById('tickEndTime').value = formatDateTimeLocal(end);
        }
        
        // ========== Bid/Ask时间模式 ==========
        function toggleBidaskTimeMode() {
            const mode = document.getElementById('bidaskTimeMode').value;
            document.getElementById('bidaskHoursMode').style.display = mode === 'hours' ? 'block' : 'none';
            document.getElementById('bidaskRangeMode').style.display = mode === 'range' ? 'block' : 'none';
        }
        
        function setBidaskLastTradeDay() {
            const now = new Date();
            let lastTradeEnd = new Date(now);
            while (lastTradeEnd.getDay() === 0 || lastTradeEnd.getDay() === 6) {
                lastTradeEnd.setDate(lastTradeEnd.getDate() - 1);
            }
            lastTradeEnd.setHours(22, 0, 0, 0);
            const lastTradeStart = new Date(lastTradeEnd);
            lastTradeStart.setHours(20, 0, 0, 0);
            document.getElementById('bidaskStartTime').value = formatDateTimeLocal(lastTradeStart);
            document.getElementById('bidaskEndTime').value = formatDateTimeLocal(lastTradeEnd);
        }
        
        function setBidaskLastFriday() {
            const now = new Date();
            const dayOfWeek = now.getDay();
            let lastFriday = new Date(now);
            const diff = dayOfWeek === 5 ? 7 : (dayOfWeek === 6 ? 1 : dayOfWeek + 2);
            lastFriday.setDate(now.getDate() - diff);
            
            const start = new Date(lastFriday);
            start.setHours(20, 0, 0, 0);
            const end = new Date(lastFriday);
            end.setHours(22, 0, 0, 0);
            
            document.getElementById('bidaskStartTime').value = formatDateTimeLocal(start);
            document.getElementById('bidaskEndTime').value = formatDateTimeLocal(end);
        }
        
        // 每日时段过滤
        function toggleDailyFilter() {
            const checked = document.getElementById('bidaskDailyFilter').checked;
            document.getElementById('bidaskDailyFilterOptions').style.display = checked ? 'block' : 'none';
        }
        
        function setDailyTime(start, end) {
            document.getElementById('bidaskDailyStart').value = start;
            document.getElementById('bidaskDailyEnd').value = end;
        }
        
        // 设置图表类型
        function setChartType(type) {
            currentChartType = type;
            document.querySelectorAll('.chart-type-btns button').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            if (cachedData) {
                renderChart(cachedData, currentDataType);
            }
        }
        
        // ========== 模态框画图功能 ==========
        function openChartModal(dataType) {
            if (!fullData || fullData.length === 0) {
                addLog('请先下载数据', 'error');
                return;
            }
            
            const modal = document.getElementById('chartModal');
            modal.classList.add('show');
            
            // 初始化模态框图表
            if (!modalChart) {
                modalChart = echarts.init(document.getElementById('modalChartContainer'));
            }
            
            // 设置数据信息
            document.getElementById('infoSymbol').textContent = document.getElementById('symbol').value;
            document.getElementById('infoType').textContent = {bar:'K线',tick:'Tick',bidask:'Bid/Ask'}[dataType] || dataType;
            document.getElementById('infoRows').textContent = fullData.length + ' 条';
            
            // 设置时间范围
            if (fullData.length > 0) {
                const firstTime = fullData[0].timestamp;
                const lastTime = fullData[fullData.length - 1].timestamp;
                document.getElementById('infoTimeRange').textContent = `${firstTime?.substring(5,16) || '-'} ~ ${lastTime?.substring(11,16) || '-'}`;
                
                dataTimeRange.start = firstTime;
                dataTimeRange.end = lastTime;
                
                // 设置时间选择器默认值
                if (firstTime) document.getElementById('chartStartTime').value = firstTime.replace(' ', 'T').substring(0, 16);
                if (lastTime) document.getElementById('chartEndTime').value = lastTime.replace(' ', 'T').substring(0, 16);
            }
            
            // 设置图表类型选项
            const chartTypeSelect = document.getElementById('modalChartType');
            chartTypeSelect.innerHTML = '';
            if (dataType === 'bar') {
                chartTypeSelect.innerHTML = `
                    <option value="candlestick">K线图</option>
                    <option value="line">折线图</option>
                    <option value="area">面积图</option>
                `;
            } else if (dataType === 'tick') {
                chartTypeSelect.innerHTML = `
                    <option value="scatter">散点图</option>
                    <option value="line">折线图</option>
                    <option value="area">面积图</option>
                `;
            } else if (dataType === 'bidask') {
                chartTypeSelect.innerHTML = `
                    <option value="line">折线图</option>
                    <option value="area">面积图</option>
                `;
            }
            
            // 设置列选择
            setupColumnCheckboxes(dataType);
            
            // 渲染图表
            setTimeout(() => {
                modalChart.resize();
                updateModalChart();
            }, 100);
        }
        
        function closeChartModal() {
            document.getElementById('chartModal').classList.remove('show');
        }
        
        function setupColumnCheckboxes(dataType) {
            const container = document.getElementById('columnCheckboxes');
            const rightContainer = document.getElementById('rightAxisCheckboxes');
            let columns = [];
            let rightColumns = [];
            
            if (dataType === 'bar') {
                columns = [
                    { id: 'open', name: '开盘价', checked: false },
                    { id: 'high', name: '最高价', checked: false },
                    { id: 'low', name: '最低价', checked: false },
                    { id: 'close', name: '收盘价', checked: true }
                ];
                rightColumns = [
                    { id: 'volume', name: '成交量', checked: true }
                ];
            } else if (dataType === 'tick') {
                columns = [
                    { id: 'price', name: '价格', checked: true }
                ];
                rightColumns = [
                    { id: 'size', name: '数量', checked: false }
                ];
            } else if (dataType === 'bidask') {
                columns = [
                    { id: 'bid', name: 'Bid', checked: true },
                    { id: 'ask', name: 'Ask', checked: true },
                    { id: 'mid', name: 'Mid', checked: false }
                ];
                rightColumns = [
                    { id: 'spread', name: 'Spread(pips)', checked: false }
                ];
            }
            
            container.innerHTML = columns.map(col => `
                <div class="config-row">
                    <input type="checkbox" id="col_${col.id}" ${col.checked ? 'checked' : ''} onchange="updateModalChart()">
                    <label style="width:auto;">${col.name}</label>
                </div>
            `).join('');
            
            rightContainer.innerHTML = rightColumns.map(col => `
                <div class="config-row">
                    <input type="checkbox" id="col_right_${col.id}" ${col.checked ? 'checked' : ''} onchange="updateModalChart()">
                    <label style="width:auto;">${col.name}</label>
                </div>
            `).join('');
        }
        
        // 智能格式化X轴时间 - 始终包含年月日+时间
        function getSmartTimeFormat(data) {
            if (!data || data.length < 2) return { format: 'YYYY-MM-DD HH:mm', interval: 0 };
            
            const firstTime = new Date(data[0].timestamp.replace(' ', 'T'));
            const lastTime = new Date(data[data.length - 1].timestamp.replace(' ', 'T'));
            const spanMs = lastTime - firstTime;
            const spanHours = spanMs / (1000 * 60 * 60);
            const spanDays = spanMs / (1000 * 60 * 60 * 24);
            
            let format, interval;
            
            if (spanDays > 30) {
                // 超过30天：显示 YYYY-MM-DD HH:mm
                format = 'YYYY-MM-DD HH:mm';
                interval = Math.ceil(data.length / 10);
            } else if (spanDays > 7) {
                // 7-30天：显示 YYYY-MM-DD HH:mm
                format = 'YYYY-MM-DD HH:mm';
                interval = Math.ceil(data.length / 10);
            } else if (spanDays > 1) {
                // 1-7天：显示 MM-DD HH:mm
                format = 'MM-DD HH:mm';
                interval = Math.ceil(data.length / 10);
            } else if (spanHours > 4) {
                // 4小时-1天：显示 MM-DD HH:mm
                format = 'MM-DD HH:mm';
                interval = Math.ceil(data.length / 12);
            } else {
                // 4小时内：显示 MM-DD HH:mm:ss
                format = 'MM-DD HH:mm:ss';
                interval = Math.ceil(data.length / 12);
            }
            
            return { format, interval, spanDays, spanHours };
        }
        
        // 格式化时间戳
        function formatTimestamp(timestamp, format) {
            if (!timestamp) return '';
            const parts = timestamp.split(' ');
            const datePart = parts[0] || '';
            const timePart = parts[1] || '';
            
            const [year, month, day] = datePart.split('-');
            const [hour, minute, second] = (timePart.split(':').concat(['00', '00', '00']));
            
            return format
                .replace('YYYY', year || '')
                .replace('MM', month || '')
                .replace('DD', day || '')
                .replace('HH', hour || '')
                .replace('mm', minute || '')
                .replace('ss', second?.substring(0,2) || '');
        }
        
        function setChartTimeRange(range) {
            if (!fullData || fullData.length === 0) return;
            
            const lastTime = new Date(fullData[fullData.length - 1].timestamp.replace(' ', 'T'));
            let startTime;
            
            if (range === 'all') {
                startTime = new Date(fullData[0].timestamp.replace(' ', 'T'));
            } else if (range === 'last1h') {
                startTime = new Date(lastTime.getTime() - 60 * 60 * 1000);
            } else if (range === 'last4h') {
                startTime = new Date(lastTime.getTime() - 4 * 60 * 60 * 1000);
            } else if (range === 'last1d') {
                startTime = new Date(lastTime.getTime() - 24 * 60 * 60 * 1000);
            }
            
            document.getElementById('chartStartTime').value = formatDateTimeLocal(startTime);
            document.getElementById('chartEndTime').value = formatDateTimeLocal(lastTime);
            updateModalChart();
        }
        
        function updateModalChart() {
            if (!modalChart || !fullData || fullData.length === 0) return;
            
            const startTime = document.getElementById('chartStartTime').value.replace('T', ' ');
            const endTime = document.getElementById('chartEndTime').value.replace('T', ' ');
            const chartType = document.getElementById('modalChartType').value;
            const colorUp = document.getElementById('colorUp').value;
            const colorDown = document.getElementById('colorDown').value;
            const lineWidth = parseInt(document.getElementById('lineWidth').value);
            const showMA = document.getElementById('showMA')?.checked;
            
            // 筛选时间范围内的数据
            let filteredData = fullData.filter(d => {
                const t = d.timestamp;
                return (!startTime || t >= startTime) && (!endTime || t <= endTime);
            });
            
            if (filteredData.length === 0) {
                addLog('所选时间范围内无数据', 'error');
                return;
            }
            
            // 更新统计信息
            document.getElementById('chartDataPoints').textContent = filteredData.length;
            
            // 获取选中的列
            const { leftCols, rightCols } = getSelectedColumns(currentDataType);
            
            let option = {};
            
            if (currentDataType === 'bar') {
                const high = Math.max(...filteredData.map(d => d.high));
                const low = Math.min(...filteredData.map(d => d.low));
                const firstClose = filteredData[0].close;
                const lastClose = filteredData[filteredData.length - 1].close;
                const change = ((lastClose - firstClose) / firstClose * 100).toFixed(3);
                
                document.getElementById('chartHigh').textContent = high.toFixed(4);
                document.getElementById('chartLow').textContent = low.toFixed(4);
                document.getElementById('chartChange').innerHTML = `<span style="color:${change >= 0 ? colorUp : colorDown}">${change >= 0 ? '+' : ''}${change}%</span>`;
                
                option = buildModalBarChartOption(filteredData, chartType, colorUp, colorDown, lineWidth, showMA, leftCols, rightCols);
            } else if (currentDataType === 'tick') {
                const prices = filteredData.map(d => d.price);
                const high = Math.max(...prices);
                const low = Math.min(...prices);
                
                document.getElementById('chartHigh').textContent = high.toFixed(5);
                document.getElementById('chartLow').textContent = low.toFixed(5);
                document.getElementById('chartChange').textContent = '-';
                
                option = buildModalTickChartOption(filteredData, chartType, colorUp, lineWidth, leftCols, rightCols);
            } else if (currentDataType === 'bidask') {
                const bids = filteredData.map(d => d.bid).filter(b => b);
                const asks = filteredData.map(d => d.ask).filter(a => a);
                
                document.getElementById('chartHigh').textContent = asks.length ? Math.max(...asks).toFixed(5) : '-';
                document.getElementById('chartLow').textContent = bids.length ? Math.min(...bids).toFixed(5) : '-';
                document.getElementById('chartChange').textContent = '-';
                
                option = buildModalBidAskChartOption(filteredData, chartType, colorUp, colorDown, lineWidth, leftCols, rightCols);
            }
            
            modalChart.setOption(option, true);
        }
        
        // 模态框 Bar 图表配置（响应列选择）
        function buildModalBarChartOption(data, chartType, colorUp, colorDown, lineWidth, showMA, leftCols, rightCols) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const ohlc = data.map(d => [d.open, d.close, d.low, d.high]);
            const closes = data.map(d => d.close);
            const volumes = data.map(d => d.volume || 0);
            
            let series = [];
            let legend = [];
            const hasRightAxis = rightCols.length > 0;
            
            const hasOHLC = leftCols.includes('open') && leftCols.includes('high') && 
                           leftCols.includes('low') && leftCols.includes('close');
            
            if (chartType === 'candlestick' && hasOHLC) {
                series.push({
                    name: 'K线',
                    type: 'candlestick',
                    data: ohlc,
                    yAxisIndex: 0,
                    itemStyle: { color: colorUp, color0: colorDown, borderColor: colorUp, borderColor0: colorDown }
                });
                legend.push('K线');
            } else {
                const colColors = { close: colorUp, open: '#58a6ff', high: '#f0883e', low: '#a371f7' };
                const colNames = { close: '收盘价', open: '开盘价', high: '最高价', low: '最低价' };
                
                leftCols.forEach(col => {
                    if (['open', 'high', 'low', 'close'].includes(col)) {
                        series.push({
                            name: colNames[col],
                            type: 'line',
                            data: data.map(d => d[col]),
                            yAxisIndex: 0,
                            smooth: chartType === 'area',
                            lineStyle: { color: colColors[col], width: lineWidth },
                            areaStyle: chartType === 'area' ? { color: colColors[col] + '33' } : null,
                            symbol: 'none'
                        });
                        legend.push(colNames[col]);
                    }
                });
            }
            
            if (showMA && closes.length >= 5) {
                const ma5 = calculateMA(closes, 5);
                const ma10 = calculateMA(closes, 10);
                series.push({ name: 'MA5', type: 'line', data: ma5, yAxisIndex: 0, symbol: 'none', lineStyle: { color: '#f0883e', width: 1 } });
                series.push({ name: 'MA10', type: 'line', data: ma10, yAxisIndex: 0, symbol: 'none', lineStyle: { color: '#a371f7', width: 1 } });
                legend.push('MA5', 'MA10');
            }
            
            if (rightCols.includes('volume')) {
                series.push({
                    name: '成交量',
                    type: 'bar',
                    yAxisIndex: 1,
                    data: volumes.map((v, i) => ({
                        value: v,
                        itemStyle: { color: data[i].close >= data[i].open ? colorUp + '66' : colorDown + '66' }
                    }))
                });
                legend.push('成交量');
            }
            
            let yAxes = [
                { type: 'value', position: 'left', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { lineStyle: { color: '#21262d' } } }
            ];
            
            if (hasRightAxis) {
                yAxes.push({ type: 'value', position: 'right', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { show: false } });
            }
            
            return {
                backgroundColor: 'transparent',
                legend: { data: legend, top: 5, textStyle: { color: '#8b949e' } },
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
                grid: { left: 60, right: hasRightAxis ? 60 : 20, top: 45, bottom: 70 },
                xAxis: { type: 'category', data: times, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                yAxis: yAxes,
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 16, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        // 模态框 Tick 图表配置
        function buildModalTickChartOption(data, chartType, colorUp, lineWidth, leftCols, rightCols) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const prices = data.map(d => d.price);
            const sizes = data.map(d => d.size || 0);
            
            let series = [];
            let legend = [];
            const hasRightAxis = rightCols.length > 0;
            
            if (leftCols.includes('price')) {
                series.push({
                    name: '价格',
                    type: chartType === 'scatter' ? 'scatter' : 'line',
                    data: prices,
                    yAxisIndex: 0,
                    symbolSize: chartType === 'scatter' ? 4 : 0,
                    lineStyle: chartType !== 'scatter' ? { color: colorUp, width: lineWidth } : null,
                    itemStyle: { color: colorUp },
                    areaStyle: chartType === 'area' ? { color: colorUp + '33' } : null
                });
                legend.push('价格');
            }
            
            if (rightCols.includes('size')) {
                series.push({
                    name: '数量',
                    type: 'bar',
                    yAxisIndex: 1,
                    data: sizes,
                    itemStyle: { color: '#58a6ff66' }
                });
                legend.push('数量');
            }
            
            let yAxes = [{ type: 'value', position: 'left', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { lineStyle: { color: '#21262d' } } }];
            if (hasRightAxis) {
                yAxes.push({ type: 'value', position: 'right', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { show: false } });
            }
            
            return {
                backgroundColor: 'transparent',
                legend: { data: legend, top: 5, textStyle: { color: '#8b949e' } },
                tooltip: { trigger: 'axis' },
                grid: { left: 60, right: hasRightAxis ? 60 : 20, top: 45, bottom: 70 },
                xAxis: { type: 'category', data: times, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                yAxis: yAxes,
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 16, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        // 模态框 BidAsk 图表配置
        function buildModalBidAskChartOption(data, chartType, colorUp, colorDown, lineWidth, leftCols, rightCols) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            
            let series = [];
            let legend = [];
            const hasRightAxis = rightCols.length > 0;
            
            if (leftCols.includes('bid')) {
                series.push({
                    name: 'Bid',
                    type: 'line',
                    data: data.map(d => d.bid),
                    yAxisIndex: 0,
                    lineStyle: { color: colorUp, width: lineWidth },
                    areaStyle: chartType === 'area' ? { color: colorUp + '33' } : null,
                    symbol: 'none'
                });
                legend.push('Bid');
            }
            
            if (leftCols.includes('ask')) {
                series.push({
                    name: 'Ask',
                    type: 'line',
                    data: data.map(d => d.ask),
                    yAxisIndex: 0,
                    lineStyle: { color: colorDown, width: lineWidth },
                    areaStyle: chartType === 'area' ? { color: colorDown + '33' } : null,
                    symbol: 'none'
                });
                legend.push('Ask');
            }
            
            if (leftCols.includes('mid')) {
                const mids = data.map(d => (d.bid && d.ask) ? ((d.bid + d.ask) / 2) : null);
                series.push({
                    name: 'Mid',
                    type: 'line',
                    data: mids,
                    yAxisIndex: 0,
                    lineStyle: { color: '#f0883e', width: lineWidth },
                    symbol: 'none'
                });
                legend.push('Mid');
            }
            
            if (rightCols.includes('spread')) {
                const spreads = data.map(d => (d.ask && d.bid) ? ((d.ask - d.bid) * 10000) : 0);
                series.push({
                    name: 'Spread(pips)',
                    type: 'line',
                    yAxisIndex: 1,
                    data: spreads,
                    lineStyle: { color: '#a371f7', width: lineWidth },
                    symbol: 'none'
                });
                legend.push('Spread(pips)');
            }
            
            let yAxes = [{ type: 'value', position: 'left', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { lineStyle: { color: '#21262d' } } }];
            if (hasRightAxis) {
                yAxes.push({ type: 'value', position: 'right', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { show: false } });
            }
            
            return {
                backgroundColor: 'transparent',
                legend: { data: legend, top: 5, textStyle: { color: '#8b949e' } },
                tooltip: { trigger: 'axis' },
                grid: { left: 60, right: hasRightAxis ? 60 : 20, top: 45, bottom: 70 },
                xAxis: { type: 'category', data: times, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                yAxis: yAxes,
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 16, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        // 获取选中的左Y轴和右Y轴列
        function getSelectedColumns(dataType) {
            let leftCols = [];
            let rightCols = [];
            
            if (dataType === 'bar') {
                ['open', 'high', 'low', 'close'].forEach(col => {
                    if (document.getElementById('col_' + col)?.checked) leftCols.push(col);
                });
                if (document.getElementById('col_right_volume')?.checked) rightCols.push('volume');
            } else if (dataType === 'tick') {
                if (document.getElementById('col_price')?.checked) leftCols.push('price');
                if (document.getElementById('col_right_size')?.checked) rightCols.push('size');
            } else if (dataType === 'bidask') {
                ['bid', 'ask', 'mid'].forEach(col => {
                    if (document.getElementById('col_' + col)?.checked) leftCols.push(col);
                });
                if (document.getElementById('col_right_spread')?.checked) rightCols.push('spread');
            }
            
            return { leftCols, rightCols };
        }
        
        // 应用配置到主图
        function applyToMainChart() {
            if (!fullData || fullData.length === 0) {
                addLog('没有数据可应用', 'error');
                return;
            }
            
            const startTime = document.getElementById('chartStartTime').value.replace('T', ' ');
            const endTime = document.getElementById('chartEndTime').value.replace('T', ' ');
            const chartType = document.getElementById('modalChartType').value;
            const colorUp = document.getElementById('colorUp').value;
            const colorDown = document.getElementById('colorDown').value;
            const lineWidth = parseInt(document.getElementById('lineWidth').value);
            const showMA = document.getElementById('showMA')?.checked;
            
            // 筛选时间范围内的数据
            let filteredData = fullData.filter(d => {
                const t = d.timestamp;
                return (!startTime || t >= startTime) && (!endTime || t <= endTime);
            });
            
            if (filteredData.length === 0) {
                addLog('所选时间范围内无数据', 'error');
                return;
            }
            
            // 获取选中的列
            const { leftCols, rightCols } = getSelectedColumns(currentDataType);
            
            // 构建主图的配置
            let option = {};
            
            if (currentDataType === 'bar') {
                option = buildMainBarChartOption(filteredData, chartType, colorUp, colorDown, lineWidth, showMA, leftCols, rightCols);
            } else if (currentDataType === 'tick') {
                option = buildMainTickChartOption(filteredData, chartType, colorUp, lineWidth, leftCols, rightCols);
            } else if (currentDataType === 'bidask') {
                option = buildMainBidAskChartOption(filteredData, chartType, colorUp, colorDown, lineWidth, leftCols, rightCols);
            }
            
            // 应用到主图
            mainChart.setOption(option, true);
            
            // 更新缓存数据为筛选后的数据
            cachedData = filteredData;
            
            // 更新表格
            renderTable(filteredData, currentDataType);
            
            // 关闭模态框
            closeChartModal();
            
            addLog(`已应用自定义配置到主图 (${filteredData.length}条数据)`, 'success');
        }
        
        // 主图 Bar 配置（带智能X轴和双Y轴）
        function buildMainBarChartOption(data, chartType, colorUp, colorDown, lineWidth, showMA, leftCols, rightCols) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const ohlc = data.map(d => [d.open, d.close, d.low, d.high]);
            const closes = data.map(d => d.close);
            const volumes = data.map(d => d.volume || 0);
            
            let series = [];
            let legend = [];
            const hasRightAxis = rightCols.length > 0;
            
            const hasOHLC = leftCols.includes('open') && leftCols.includes('high') && 
                           leftCols.includes('low') && leftCols.includes('close');
            
            if (chartType === 'candlestick' && hasOHLC) {
                series.push({
                    name: 'K线',
                    type: 'candlestick',
                    data: ohlc,
                    yAxisIndex: 0,
                    itemStyle: { color: colorUp, color0: colorDown, borderColor: colorUp, borderColor0: colorDown }
                });
                legend.push('K线');
            } else {
                // 折线图模式
                const colColors = { close: colorUp, open: '#58a6ff', high: '#f0883e', low: '#a371f7' };
                const colNames = { close: '收盘价', open: '开盘价', high: '最高价', low: '最低价' };
                
                leftCols.forEach(col => {
                    if (['open', 'high', 'low', 'close'].includes(col)) {
                        series.push({
                            name: colNames[col],
                            type: 'line',
                            data: data.map(d => d[col]),
                            yAxisIndex: 0,
                            smooth: chartType === 'area',
                            lineStyle: { color: colColors[col], width: lineWidth },
                            areaStyle: chartType === 'area' ? { color: colColors[col] + '33' } : null,
                            symbol: 'none'
                        });
                        legend.push(colNames[col]);
                    }
                });
            }
            
            if (showMA && closes.length >= 5) {
                const ma5 = calculateMA(closes, 5);
                const ma10 = calculateMA(closes, 10);
                series.push({ name: 'MA5', type: 'line', data: ma5, yAxisIndex: 0, symbol: 'none', lineStyle: { color: '#f0883e', width: 1 } });
                series.push({ name: 'MA10', type: 'line', data: ma10, yAxisIndex: 0, symbol: 'none', lineStyle: { color: '#a371f7', width: 1 } });
                legend.push('MA5', 'MA10');
            }
            
            // 右Y轴数据
            if (rightCols.includes('volume')) {
                series.push({
                    name: '成交量',
                    type: 'bar',
                    yAxisIndex: 1,
                    data: volumes.map((v, i) => ({
                        value: v,
                        itemStyle: { color: data[i].close >= data[i].open ? colorUp + '66' : colorDown + '66' }
                    }))
                });
                legend.push('成交量');
            }
            
            let yAxes = [
                { 
                    type: 'value', 
                    position: 'left',
                    scale: true, 
                    axisLabel: { color: '#8b949e' }, 
                    splitLine: { lineStyle: { color: '#21262d' } },
                    name: '价格',
                    nameTextStyle: { color: '#8b949e' }
                }
            ];
            
            if (hasRightAxis) {
                yAxes.push({
                    type: 'value',
                    position: 'right',
                    scale: true,
                    axisLabel: { color: '#8b949e' },
                    splitLine: { show: false },
                    name: rightCols.includes('volume') ? '成交量' : '',
                    nameTextStyle: { color: '#8b949e' }
                });
            }
            
            return {
                backgroundColor: 'transparent',
                legend: { data: legend, top: 5, textStyle: { color: '#8b949e' } },
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
                grid: { left: 70, right: hasRightAxis ? 70 : 20, top: 50, bottom: 80 },
                xAxis: { 
                    type: 'category', 
                    data: times, 
                    axisLabel: { 
                        color: '#8b949e', 
                        fontSize: 10,
                        interval: timeInfo.interval,
                        rotate: 45
                    }
                },
                yAxis: yAxes,
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 18, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        // 主图 Tick 配置（带智能X轴和双Y轴）
        function buildMainTickChartOption(data, chartType, colorUp, lineWidth, leftCols, rightCols) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const prices = data.map(d => d.price);
            const sizes = data.map(d => d.size || 0);
            
            let series = [];
            let legend = [];
            const hasRightAxis = rightCols.length > 0;
            
            if (leftCols.includes('price')) {
                series.push({
                    name: '价格',
                    type: chartType === 'scatter' ? 'scatter' : 'line',
                    data: prices,
                    yAxisIndex: 0,
                    symbolSize: chartType === 'scatter' ? 4 : 0,
                    lineStyle: chartType !== 'scatter' ? { color: colorUp, width: lineWidth } : null,
                    itemStyle: { color: colorUp },
                    areaStyle: chartType === 'area' ? { color: colorUp + '33' } : null
                });
                legend.push('价格');
            }
            
            if (rightCols.includes('size')) {
                series.push({
                    name: '数量',
                    type: 'bar',
                    yAxisIndex: 1,
                    data: sizes,
                    itemStyle: { color: '#58a6ff66' }
                });
                legend.push('数量');
            }
            
            let yAxes = [
                { type: 'value', position: 'left', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { lineStyle: { color: '#21262d' } }, name: '价格', nameTextStyle: { color: '#8b949e' } }
            ];
            
            if (hasRightAxis) {
                yAxes.push({ type: 'value', position: 'right', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { show: false }, name: '数量', nameTextStyle: { color: '#8b949e' } });
            }
            
            return {
                backgroundColor: 'transparent',
                legend: { data: legend, top: 5, textStyle: { color: '#8b949e' } },
                tooltip: { trigger: 'axis' },
                grid: { left: 70, right: hasRightAxis ? 70 : 20, top: 50, bottom: 80 },
                xAxis: { type: 'category', data: times, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                yAxis: yAxes,
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 18, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        // 主图 BidAsk 配置（带智能X轴和双Y轴）
        function buildMainBidAskChartOption(data, chartType, colorUp, colorDown, lineWidth, leftCols, rightCols) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            
            let series = [];
            let legend = [];
            const hasRightAxis = rightCols.length > 0;
            
            if (leftCols.includes('bid')) {
                series.push({
                    name: 'Bid',
                    type: 'line',
                    data: data.map(d => d.bid),
                    yAxisIndex: 0,
                    lineStyle: { color: colorUp, width: lineWidth },
                    areaStyle: chartType === 'area' ? { color: colorUp + '33' } : null,
                    symbol: 'none'
                });
                legend.push('Bid');
            }
            
            if (leftCols.includes('ask')) {
                series.push({
                    name: 'Ask',
                    type: 'line',
                    data: data.map(d => d.ask),
                    yAxisIndex: 0,
                    lineStyle: { color: colorDown, width: lineWidth },
                    areaStyle: chartType === 'area' ? { color: colorDown + '33' } : null,
                    symbol: 'none'
                });
                legend.push('Ask');
            }
            
            if (leftCols.includes('mid')) {
                const mids = data.map(d => (d.bid && d.ask) ? ((d.bid + d.ask) / 2) : null);
                series.push({
                    name: 'Mid',
                    type: 'line',
                    data: mids,
                    yAxisIndex: 0,
                    lineStyle: { color: '#f0883e', width: lineWidth },
                    symbol: 'none'
                });
                legend.push('Mid');
            }
            
            if (rightCols.includes('spread')) {
                const spreads = data.map(d => (d.ask && d.bid) ? ((d.ask - d.bid) * 10000) : 0);
                series.push({
                    name: 'Spread(pips)',
                    type: 'line',
                    yAxisIndex: 1,
                    data: spreads,
                    lineStyle: { color: '#a371f7', width: lineWidth },
                    symbol: 'none'
                });
                legend.push('Spread(pips)');
            }
            
            let yAxes = [
                { type: 'value', position: 'left', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { lineStyle: { color: '#21262d' } }, name: '价格', nameTextStyle: { color: '#8b949e' } }
            ];
            
            if (hasRightAxis) {
                yAxes.push({ type: 'value', position: 'right', scale: true, axisLabel: { color: '#8b949e' }, splitLine: { show: false }, name: 'Spread(pips)', nameTextStyle: { color: '#8b949e' } });
            }
            
            return {
                backgroundColor: 'transparent',
                legend: { data: legend, top: 5, textStyle: { color: '#8b949e' } },
                tooltip: { trigger: 'axis' },
                grid: { left: 70, right: hasRightAxis ? 70 : 20, top: 50, bottom: 80 },
                xAxis: { type: 'category', data: times, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                yAxis: yAxes,
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 18, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        function buildBarChartOption(data, chartType, colorUp, colorDown, lineWidth, showVolume, showMA) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const ohlc = data.map(d => [d.open, d.close, d.low, d.high]);
            const closes = data.map(d => d.close);
            const volumes = data.map(d => d.volume || 0);
            
            let series = [];
            let grids = showVolume ? [
                { left: 70, right: 30, top: 40, height: '50%' },
                { left: 70, right: 30, top: '68%', height: '15%' }
            ] : [{ left: 70, right: 30, top: 40, bottom: 80 }];
            
            if (chartType === 'candlestick') {
                series.push({
                    name: 'K线',
                    type: 'candlestick',
                    data: ohlc,
                    itemStyle: { color: colorUp, color0: colorDown, borderColor: colorUp, borderColor0: colorDown }
                });
            } else {
                series.push({
                    name: '收盘价',
                    type: 'line',
                    data: closes,
                    smooth: chartType === 'area',
                    lineStyle: { color: colorUp, width: lineWidth },
                    areaStyle: chartType === 'area' ? { color: colorUp + '33' } : null,
                    symbol: 'none'
                });
            }
            
            if (showMA && closes.length >= 5) {
                const ma5 = calculateMA(closes, 5);
                const ma10 = calculateMA(closes, 10);
                series.push({ name: 'MA5', type: 'line', data: ma5, symbol: 'none', lineStyle: { color: '#f0883e', width: 1 } });
                series.push({ name: 'MA10', type: 'line', data: ma10, symbol: 'none', lineStyle: { color: '#a371f7', width: 1 } });
            }
            
            if (showVolume) {
                series.push({
                    name: '成交量',
                    type: 'bar',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: volumes,
                    itemStyle: { color: (params) => data[params.dataIndex].close >= data[params.dataIndex].open ? colorUp : colorDown }
                });
            }
            
            return {
                backgroundColor: 'transparent',
                animation: false,
                legend: { data: series.map(s => s.name), textStyle: { color: '#8b949e', fontSize: 11 }, top: 5 },
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: '#161b22', borderColor: '#30363d', textStyle: { color: '#c9d1d9', fontSize: 12 } },
                grid: grids,
                xAxis: showVolume ? [
                    { type: 'category', data: times, axisLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                    { type: 'category', data: times, gridIndex: 1, axisLine: { lineStyle: { color: '#21262d' } }, axisLabel: { show: false } }
                ] : [{ type: 'category', data: times, axisLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } }],
                yAxis: showVolume ? [
                    { scale: true, axisLine: { lineStyle: { color: '#21262d' } }, splitLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10 } },
                    { scale: true, gridIndex: 1, axisLine: { lineStyle: { color: '#21262d' } }, splitLine: { show: false }, axisLabel: { show: false } }
                ] : [{ scale: true, axisLine: { lineStyle: { color: '#21262d' } }, splitLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10 } }],
                dataZoom: [
                    { type: 'inside', xAxisIndex: showVolume ? [0, 1] : [0], start: 0, end: 100 },
                    { type: 'slider', xAxisIndex: showVolume ? [0, 1] : [0], bottom: 5, height: 18, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        function buildTickChartOption(data, chartType, color, lineWidth) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const prices = data.map(d => d.price);
            
            return {
                backgroundColor: 'transparent',
                animation: false,
                tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#30363d', textStyle: { color: '#c9d1d9', fontSize: 12 } },
                grid: { left: 70, right: 30, top: 40, bottom: 80 },
                xAxis: { type: 'category', data: times, axisLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                yAxis: { scale: true, axisLine: { lineStyle: { color: '#21262d' } }, splitLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10 } },
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 18, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: [{
                    type: chartType === 'scatter' ? 'scatter' : 'line',
                    data: prices,
                    symbolSize: chartType === 'scatter' ? 3 : 0,
                    itemStyle: { color: color },
                    lineStyle: { color: color, width: lineWidth },
                    areaStyle: chartType === 'area' ? { color: color + '33' } : null
                }]
            };
        }
        
        function buildBidAskChartOption(data, chartType, colorBid, colorAsk, lineWidth) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const bids = data.map(d => d.bid);
            const asks = data.map(d => d.ask);
            
            let series = [
                { name: 'Bid', type: 'line', data: bids, symbol: 'none', lineStyle: { color: colorBid, width: lineWidth }, areaStyle: chartType === 'area' ? { color: colorBid + '22' } : null },
                { name: 'Ask', type: 'line', data: asks, symbol: 'none', lineStyle: { color: colorAsk, width: lineWidth }, areaStyle: chartType === 'area' ? { color: colorAsk + '22' } : null }
            ];
            
            return {
                backgroundColor: 'transparent',
                animation: false,
                legend: { data: ['Bid', 'Ask'], textStyle: { color: '#8b949e', fontSize: 11 }, top: 5 },
                tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#30363d', textStyle: { color: '#c9d1d9', fontSize: 12 } },
                grid: { left: 70, right: 30, top: 40, bottom: 80 },
                xAxis: { type: 'category', data: times, axisLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                yAxis: { scale: true, axisLine: { lineStyle: { color: '#21262d' } }, splitLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', fontSize: 10 } },
                dataZoom: [
                    { type: 'inside', start: 0, end: 100 },
                    { type: 'slider', bottom: 5, height: 18, start: 0, end: 100, textStyle: { color: '#8b949e' } }
                ],
                series: series
            };
        }
        
        function calculateMA(data, period) {
            const result = [];
            for (let i = 0; i < data.length; i++) {
                if (i < period - 1) {
                    result.push(null);
                } else {
                    let sum = 0;
                    for (let j = 0; j < period; j++) {
                        sum += data[i - j];
                    }
                    result.push((sum / period).toFixed(5));
                }
            }
            return result;
        }
        
        // 添加日志
        function addLog(msg, type = 'info') {
            const panel = document.getElementById('logPanel');
            const time = new Date().toLocaleTimeString();
            panel.innerHTML += `<div class="log-entry ${type}">[${time}] ${msg}</div>`;
            panel.scrollTop = panel.scrollHeight;
        }
        
        // Bloomberg连接状态
        let bbgConnected = false;
        
        function updateConnectionUI(connected) {
            bbgConnected = connected;
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusText');
            const downloadBtn = document.getElementById('downloadBtn');
            
            if (connected) {
                dot.classList.add('connected');
                text.textContent = '已连接';
                if (downloadBtn) {
                    downloadBtn.disabled = false;
                    downloadBtn.style.opacity = '1';
                    downloadBtn.title = '';
                }
            } else {
                dot.classList.remove('connected');
                text.textContent = '未连接';
                if (downloadBtn) {
                    downloadBtn.disabled = true;
                    downloadBtn.style.opacity = '0.5';
                    downloadBtn.title = '请先连接Bloomberg Terminal';
                }
            }
        }
        
        // 连接Bloomberg
        async function connectBBG() {
            addLog('正在连接Bloomberg...', 'info');
            try {
                const res = await fetch('/api/connect', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    updateConnectionUI(true);
                    addLog('Bloomberg连接成功', 'success');
                } else {
                    updateConnectionUI(false);
                    addLog('连接失败: ' + data.message, 'error');
                    addLog('请确认: 1) Bloomberg Terminal已启动 2) 已登录BBG账号 3) API服务正在运行', 'warn');
                }
            } catch (e) {
                updateConnectionUI(false);
                addLog('连接错误: ' + e.message, 'error');
            }
        }
        
        // 定时检查连接状态（每30秒）
        setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (bbgConnected && !data.connected) {
                    updateConnectionUI(false);
                    addLog('Bloomberg连接已断开，请检查Terminal是否仍在运行', 'error');
                } else if (!bbgConnected && data.connected) {
                    updateConnectionUI(true);
                    addLog('Bloomberg连接已恢复', 'success');
                }
            } catch (e) { /* 静默处理 */ }
        }, 30000);
        
        // 下载数据
        async function downloadData() {
            // 前置检查: Bloomberg是否连接
            if (!bbgConnected) {
                addLog('无法下载: Bloomberg未连接。请先启动并登录Bloomberg Terminal，然后点击重新连接。', 'error');
                return;
            }
            
            const symbol = document.getElementById('symbol').value;
            if (!symbol) {
                addLog('请输入Bloomberg代码', 'error');
                return;
            }
            
            const timezone = document.getElementById('timezone').value;
            const typeNames = {bar: 'K线', tick: 'Tick', bidask: 'Bid/Ask', ref: '参考'};
            addLog(`正在下载 ${symbol} ${typeNames[currentDataType]}数据 (${timezone})...`, 'info');
            
            let endpoint = '';
            let params = { symbol, timezone };
            
            if (currentDataType === 'bar') {
                endpoint = '/api/download/bars';
                params.interval = document.getElementById('interval').value;
                const timeMode = document.getElementById('barTimeMode').value;
                if (timeMode === 'range') {
                    params.start_time = document.getElementById('barStartTime').value;
                    params.end_time = document.getElementById('barEndTime').value;
                    if (!params.start_time || !params.end_time) {
                        addLog('请选择开始和结束时间', 'error');
                        return;
                    }
                } else {
                    params.days_back = parseInt(document.getElementById('daysBack').value);
                }
            } else if (currentDataType === 'tick') {
                endpoint = '/api/download/ticks';
                const timeMode = document.getElementById('tickTimeMode').value;
                if (timeMode === 'range') {
                    params.start_time = document.getElementById('tickStartTime').value;
                    params.end_time = document.getElementById('tickEndTime').value;
                    if (!params.start_time || !params.end_time) {
                        addLog('请选择开始和结束时间', 'error');
                        return;
                    }
                } else {
                    params.hours_back = parseFloat(document.getElementById('hoursBack').value);
                }
            } else if (currentDataType === 'bidask') {
                endpoint = '/api/download/bidask';
                const timeMode = document.getElementById('bidaskTimeMode').value;
                if (timeMode === 'range') {
                    params.start_time = document.getElementById('bidaskStartTime').value;
                    params.end_time = document.getElementById('bidaskEndTime').value;
                    if (!params.start_time || !params.end_time) {
                        addLog('请选择开始和结束时间', 'error');
                        return;
                    }
                    // 每日时段过滤
                    if (document.getElementById('bidaskDailyFilter').checked) {
                        params.daily_start = document.getElementById('bidaskDailyStart').value;
                        params.daily_end = document.getElementById('bidaskDailyEnd').value;
                    }
                } else {
                    params.hours_back = parseFloat(document.getElementById('bidaskHoursBack').value);
                }
                params.resample = document.getElementById('bidaskResample').value || null;
            } else if (currentDataType === 'ref') {
                endpoint = '/api/download/reference';
                params.fields = document.getElementById('refFields').value;
            }
            
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });
                const data = await res.json();
                
                if (data.success) {
                    addLog(data.message, 'success');
                    currentCacheKey = data.cache_key;
                    cachedData = data.data?.preview;
                    updateStats(data.stats, data.data);
                    updateTable(data.data, currentDataType);
                    renderChart(data.data?.preview, currentDataType);
                    
                    // 获取完整数据用于自定义画图
                    await fetchFullData(data.cache_key);
                    
                    // 启用画图按钮
                    enableChartButtons();
                } else {
                    addLog(data.message, 'error');
                    // 如果是连接问题，更新连接状态
                    if (data.message && data.message.includes('未连接')) {
                        updateConnectionUI(false);
                    }
                }
            } catch (e) {
                addLog('下载错误: ' + e.message, 'error');
            }
        }
        
        // 获取完整数据
        async function fetchFullData(cacheKey) {
            try {
                const res = await fetch('/api/fulldata', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cache_key: cacheKey })
                });
                const result = await res.json();
                
                if (result.success) {
                    fullData = result.data;
                    addLog(`已加载完整数据 (${fullData.length}条) 用于自定义画图`, 'info');
                } else {
                    fullData = cachedData;  // 回退到预览数据
                }
            } catch (e) {
                fullData = cachedData;
                console.error('获取完整数据失败:', e);
            }
        }
        
        function enableChartButtons() {
            // 启用统一的自定义画图按钮
            const customChartBtn = document.getElementById('customChartBtn');
            if (customChartBtn && currentDataType !== 'ref') {
                customChartBtn.disabled = false;
            }
        }
        
        // 更新统计
        function updateStats(stats, data) {
            document.getElementById('statRows').textContent = data?.rows?.toLocaleString() || '-';
            
            if (stats) {
                // K线统计
                if (stats.last_price !== undefined) {
                    document.getElementById('statLast').textContent = stats.last_price?.toFixed(4) || '-';
                    document.getElementById('statHigh').textContent = stats.high?.toFixed(4) || '-';
                    document.getElementById('statLow').textContent = stats.low?.toFixed(4) || '-';
                    
                    const retEl = document.getElementById('statReturn');
                    if (stats.total_return !== undefined) {
                        const ret = stats.total_return;
                        retEl.textContent = (ret >= 0 ? '+' : '') + ret.toFixed(3) + '%';
                        retEl.className = 'value ' + (ret >= 0 ? 'positive' : 'negative');
                    } else {
                        retEl.textContent = '-';
                        retEl.className = 'value';
                    }
                }
                
                // Bid/Ask统计
                if (stats.avg_spread !== undefined) {
                    document.getElementById('statSpread').textContent = stats.avg_spread?.toFixed(5) || '-';
                    document.getElementById('statLast').textContent = stats.last_mid?.toFixed(4) || stats.last_bid?.toFixed(4) || '-';
                } else {
                    document.getElementById('statSpread').textContent = '-';
                }
                
                // Tick统计
                if (stats.avg_price !== undefined) {
                    document.getElementById('statLast').textContent = stats.avg_price?.toFixed(4) || '-';
                    document.getElementById('statHigh').textContent = stats.max_price?.toFixed(4) || '-';
                    document.getElementById('statLow').textContent = stats.min_price?.toFixed(4) || '-';
                }
            }
        }
        
        // 更新表格
        let allTableData = [];  // 存储完整数据用于筛选
        
        function updateTable(data, dataType) {
            const thead = document.getElementById('tableHeader');
            const tbody = document.getElementById('tableBody');
            const info = document.getElementById('tableInfo');
            
            if (!data?.preview || data.preview.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#8b949e;">暂无数据</td></tr>';
                allTableData = [];
                return;
            }
            
            // 存储完整数据（不再限制50条）
            allTableData = data.preview.slice().reverse();
            
            info.textContent = `(共 ${allTableData.length} 条)`;
            
            // 根据数据类型设置表头
            if (dataType === 'bar') {
                thead.innerHTML = '<th>时间</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>成交量</th>';
            } else if (dataType === 'tick') {
                thead.innerHTML = '<th>时间</th><th>价格</th><th>数量</th><th></th><th></th><th></th>';
            } else if (dataType === 'bidask') {
                if (data.preview[0]?.bid !== undefined) {
                    thead.innerHTML = '<th>时间</th><th>Bid</th><th>Ask</th><th>Spread</th><th>Mid</th><th></th>';
                } else {
                    thead.innerHTML = '<th>时间</th><th>类型</th><th>价格</th><th>数量</th><th></th><th></th>';
                }
            }
            
            renderTableRows(allTableData, dataType);
        }
        
        function renderTableRows(rows, dataType) {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            if (rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#8b949e;">无匹配数据</td></tr>';
                return;
            }
            
            // 限制显示最多200条以保持性能
            const displayRows = rows.slice(0, 200);
            
            displayRows.forEach((row, idx) => {
                const tr = document.createElement('tr');
                const fullTime = row.timestamp || '-';
                // 显示完整的年月日+时间
                const displayTime = fullTime;
                tr.setAttribute('data-index', idx);
                tr.setAttribute('data-time', fullTime);
                tr.onclick = () => highlightRow(tr, idx);
                
                if (dataType === 'bar' || currentDataType === 'bar') {
                    tr.innerHTML = `
                        <td title="${fullTime}">${displayTime}</td>
                        <td>${row.open?.toFixed(4) || '-'}</td>
                        <td>${row.high?.toFixed(4) || '-'}</td>
                        <td>${row.low?.toFixed(4) || '-'}</td>
                        <td>${row.close?.toFixed(4) || '-'}</td>
                        <td>${row.volume?.toLocaleString() || '-'}</td>
                    `;
                } else if (dataType === 'tick' || currentDataType === 'tick') {
                    tr.innerHTML = `
                        <td title="${fullTime}">${displayTime}</td>
                        <td>${row.price?.toFixed(5) || '-'}</td>
                        <td>${row.size?.toLocaleString() || '-'}</td>
                        <td></td><td></td><td></td>
                    `;
                } else if (dataType === 'bidask' || currentDataType === 'bidask') {
                    if (row.bid !== undefined) {
                        tr.innerHTML = `
                            <td title="${fullTime}">${displayTime}</td>
                            <td style="color:${colors.bid}">${row.bid?.toFixed(5) || '-'}</td>
                            <td style="color:${colors.ask}">${row.ask?.toFixed(5) || '-'}</td>
                            <td>${row.spread?.toFixed(6) || '-'}</td>
                            <td>${row.mid?.toFixed(5) || '-'}</td>
                            <td></td>
                        `;
                    } else {
                        const typeColor = row.type === 'BID' ? colors.bid : colors.ask;
                        tr.innerHTML = `
                            <td title="${fullTime}">${displayTime}</td>
                            <td style="color:${typeColor}">${row.type || '-'}</td>
                            <td>${row.price?.toFixed(5) || '-'}</td>
                            <td>${row.size?.toLocaleString() || '-'}</td>
                            <td></td><td></td>
                        `;
                    }
                }
                tbody.appendChild(tr);
            });
            
            if (rows.length > 200) {
                document.getElementById('tableInfo').textContent = `(显示前200条，共 ${rows.length} 条匹配)`;
            } else {
                document.getElementById('tableInfo').textContent = `(共 ${rows.length} 条匹配)`;
            }
        }
        
        // 高亮选中行并在图表上标记
        function highlightRow(tr, idx) {
            document.querySelectorAll('.data-table tbody tr').forEach(r => r.classList.remove('highlighted'));
            tr.classList.add('highlighted');
            
            // 在图表上高亮对应点
            if (mainChart && cachedData) {
                const dataIdx = cachedData.length - 1 - idx;
                mainChart.dispatchAction({
                    type: 'showTip',
                    seriesIndex: 0,
                    dataIndex: dataIdx
                });
            }
        }
        
        // ========== 时间筛选功能 ==========
        function toggleFilterMode() {
            const mode = document.getElementById('filterMode').value;
            document.getElementById('filterDate').style.display = mode === 'date' ? 'inline-block' : 'none';
            document.getElementById('filterDateStart').style.display = mode === 'daterange' ? 'inline-block' : 'none';
            document.getElementById('filterDateEnd').style.display = mode === 'daterange' ? 'inline-block' : 'none';
            document.getElementById('filterExact').style.display = mode === 'exact' ? 'inline-block' : 'none';
            document.getElementById('filterStart').style.display = mode === 'range' ? 'inline-block' : 'none';
            document.getElementById('filterEnd').style.display = mode === 'range' ? 'inline-block' : 'none';
            document.getElementById('filterContains').style.display = mode === 'contains' ? 'inline-block' : 'none';
        }
        
        function applyFilter() {
            const mode = document.getElementById('filterMode').value;
            
            if (mode === 'all' || allTableData.length === 0) {
                renderTableRows(allTableData, currentDataType);
                return;
            }
            
            let filtered = [];
            
            if (mode === 'date') {
                const dateVal = document.getElementById('filterDate').value;
                if (!dateVal) {
                    addLog('请选择日期', 'error');
                    return;
                }
                filtered = allTableData.filter(row => {
                    const time = row.timestamp || '';
                    const datePart = time.includes(' ') ? time.split(' ')[0] : time;
                    return datePart === dateVal;
                });
            } else if (mode === 'daterange') {
                const startDate = document.getElementById('filterDateStart').value;
                const endDate = document.getElementById('filterDateEnd').value;
                if (!startDate && !endDate) {
                    addLog('请选择日期范围', 'error');
                    return;
                }
                filtered = allTableData.filter(row => {
                    const time = row.timestamp || '';
                    const datePart = time.includes(' ') ? time.split(' ')[0] : time;
                    let pass = true;
                    if (startDate) pass = pass && datePart >= startDate;
                    if (endDate) pass = pass && datePart <= endDate;
                    return pass;
                });
            } else if (mode === 'exact') {
                const exact = document.getElementById('filterExact').value.trim();
                if (!exact) {
                    addLog('请输入精确时间', 'error');
                    return;
                }
                filtered = allTableData.filter(row => {
                    const time = row.timestamp || '';
                    return time.includes(exact);
                });
            } else if (mode === 'range') {
                const start = document.getElementById('filterStart').value.trim();
                const end = document.getElementById('filterEnd').value.trim();
                if (!start && !end) {
                    addLog('请输入时间范围', 'error');
                    return;
                }
                filtered = allTableData.filter(row => {
                    const time = row.timestamp || '';
                    const timeOnly = time.includes(' ') ? time.split(' ')[1] : time;
                    let pass = true;
                    if (start) pass = pass && timeOnly >= start;
                    if (end) pass = pass && timeOnly <= end;
                    return pass;
                });
            } else if (mode === 'contains') {
                const contains = document.getElementById('filterContains').value.trim();
                if (!contains) {
                    addLog('请输入包含文字', 'error');
                    return;
                }
                filtered = allTableData.filter(row => {
                    const time = row.timestamp || '';
                    return time.toLowerCase().includes(contains.toLowerCase());
                });
            }
            
            renderTableRows(filtered, currentDataType);
            addLog(`筛选完成，匹配 ${filtered.length} 条`, 'success');
        }
        
        function clearFilter() {
            document.getElementById('filterMode').value = 'all';
            document.getElementById('filterDate').value = '';
            document.getElementById('filterDateStart').value = '';
            document.getElementById('filterDateEnd').value = '';
            document.getElementById('filterExact').value = '';
            document.getElementById('filterStart').value = '';
            document.getElementById('filterEnd').value = '';
            document.getElementById('filterContains').value = '';
            toggleFilterMode();
            renderTableRows(allTableData, currentDataType);
        }
        
        function jumpToTime(position) {
            const tbody = document.getElementById('tableBody');
            const rows = tbody.querySelectorAll('tr');
            if (rows.length === 0) return;
            
            const wrapper = document.querySelector('.table-wrapper');
            if (position === 'first') {
                wrapper.scrollTop = 0;
                if (rows[0]) highlightRow(rows[0], 0);
            } else if (position === 'last') {
                wrapper.scrollTop = wrapper.scrollHeight;
                if (rows[rows.length - 1]) highlightRow(rows[rows.length - 1], rows.length - 1);
            }
        }
        
        // 渲染图表
        function renderChart(data, dataType) {
            if (!data || !mainChart) return;
            
            const chartTitle = document.getElementById('chartTitle');
            
            if (dataType === 'bar') {
                chartTitle.textContent = 'K线图';
                renderCandlestickChart(data);
            } else if (dataType === 'tick') {
                chartTitle.textContent = 'Tick价格';
                renderTickChart(data);
            } else if (dataType === 'bidask') {
                chartTitle.textContent = 'Bid/Ask报价';
                renderBidAskChart(data);
            }
        }
        
        // K线图
        function renderCandlestickChart(data) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            
            const ohlc = data.map(d => [d.open, d.close, d.low, d.high]);
            const volumes = data.map(d => d.volume || 0);
            const volColors = data.map(d => d.close >= d.open ? colors.up : colors.down);
            
            let series = [];
            
            if (currentChartType === 'candle') {
                series = [
                    {
                        name: 'K线',
                        type: 'candlestick',
                        data: ohlc,
                        itemStyle: {
                            color: colors.up,
                            color0: colors.down,
                            borderColor: colors.up,
                            borderColor0: colors.down
                        }
                    },
                    {
                        name: '成交量',
                        type: 'bar',
                        xAxisIndex: 1,
                        yAxisIndex: 1,
                        data: volumes,
                        itemStyle: {
                            color: (params) => volColors[params.dataIndex]
                        }
                    }
                ];
            } else {
                const closes = data.map(d => d.close);
                series = [{
                    name: '收盘价',
                    type: 'line',
                    data: closes,
                    smooth: currentChartType === 'area',
                    lineStyle: { color: colors.line, width: 2 },
                    areaStyle: currentChartType === 'area' ? { 
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(88,166,255,0.3)' },
                            { offset: 1, color: 'rgba(88,166,255,0.05)' }
                        ])
                    } : null,
                    symbol: 'none'
                }];
            }
            
            const option = {
                backgroundColor: 'transparent',
                animation: false,
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'cross' },
                    backgroundColor: '#161b22',
                    borderColor: '#30363d',
                    textStyle: { color: '#c9d1d9', fontSize: 12 }
                },
                grid: currentChartType === 'candle' ? [
                    { left: 60, right: 20, top: 30, height: '50%' },
                    { left: 60, right: 20, top: '70%', height: '18%' }
                ] : [
                    { left: 60, right: 20, top: 30, bottom: 60 }
                ],
                xAxis: currentChartType === 'candle' ? [
                    { type: 'category', data: times, axisLine: { lineStyle: { color: colors.grid } }, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 }, boundaryGap: true },
                    { type: 'category', data: times, gridIndex: 1, axisLine: { lineStyle: { color: colors.grid } }, axisLabel: { show: false }, boundaryGap: true }
                ] : [
                    { type: 'category', data: times, axisLine: { lineStyle: { color: colors.grid } }, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } }
                ],
                yAxis: currentChartType === 'candle' ? [
                    { scale: true, axisLine: { lineStyle: { color: colors.grid } }, splitLine: { lineStyle: { color: colors.grid } }, axisLabel: { color: '#8b949e', fontSize: 10 } },
                    { scale: true, gridIndex: 1, axisLine: { lineStyle: { color: colors.grid } }, splitLine: { show: false }, axisLabel: { show: false } }
                ] : [
                    { scale: true, axisLine: { lineStyle: { color: colors.grid } }, splitLine: { lineStyle: { color: colors.grid } }, axisLabel: { color: '#8b949e', fontSize: 10 } }
                ],
                dataZoom: [
                    { type: 'inside', xAxisIndex: currentChartType === 'candle' ? [0, 1] : [0], start: 0, end: 100 }
                ],
                series: series
            };
            
            mainChart.setOption(option, true);
        }
        
        // Tick图
        function renderTickChart(data) {
            const timeInfo = getSmartTimeFormat(data);
            const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
            const prices = data.map(d => d.price);
            
            const option = {
                backgroundColor: 'transparent',
                animation: false,
                tooltip: {
                    trigger: 'axis',
                    backgroundColor: '#161b22',
                    borderColor: '#30363d',
                    textStyle: { color: '#c9d1d9', fontSize: 12 }
                },
                grid: { left: 60, right: 20, top: 30, bottom: 60 },
                xAxis: {
                    type: 'category',
                    data: times,
                    axisLine: { lineStyle: { color: colors.grid } },
                    axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 }
                },
                yAxis: {
                    scale: true,
                    axisLine: { lineStyle: { color: colors.grid } },
                    splitLine: { lineStyle: { color: colors.grid } },
                    axisLabel: { color: '#8b949e', fontSize: 10 }
                },
                dataZoom: [{ type: 'inside', start: 0, end: 100 }],
                series: [{
                    type: currentChartType === 'area' ? 'line' : 'scatter',
                    data: prices,
                    symbolSize: currentChartType === 'area' ? 0 : 3,
                    itemStyle: { color: colors.line },
                    lineStyle: { color: colors.line, width: 1 },
                    areaStyle: currentChartType === 'area' ? {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(88,166,255,0.3)' },
                            { offset: 1, color: 'rgba(88,166,255,0.05)' }
                        ])
                    } : null
                }]
            };
            
            mainChart.setOption(option, true);
        }
        
        // Bid/Ask图
        function renderBidAskChart(data) {
            const hasBidAsk = data[0]?.bid !== undefined;
            
            if (hasBidAsk) {
                // 重采样后的bid/ask/spread数据
                const timeInfo = getSmartTimeFormat(data);
                const times = data.map(d => formatTimestamp(d.timestamp, timeInfo.format));
                const bids = data.map(d => d.bid);
                const asks = data.map(d => d.ask);
                const spreads = data.map(d => d.spread * 10000); // 转为pips
                
                const option = {
                    backgroundColor: 'transparent',
                    animation: false,
                    legend: {
                        data: ['Bid', 'Ask', 'Spread'],
                        textStyle: { color: '#8b949e', fontSize: 11 },
                        top: 0,
                        right: 0
                    },
                    tooltip: {
                        trigger: 'axis',
                        backgroundColor: '#161b22',
                        borderColor: '#30363d',
                        textStyle: { color: '#c9d1d9', fontSize: 12 },
                        formatter: function(params) {
                            let html = params[0].axisValue + '<br/>';
                            params.forEach(p => {
                                const val = p.seriesName === 'Spread' ? p.value.toFixed(2) + ' pips' : p.value?.toFixed(5);
                                html += `<span style="color:${p.color}">${p.seriesName}: ${val}</span><br/>`;
                            });
                            return html;
                        }
                    },
                    grid: [
                        { left: 60, right: 60, top: 40, height: '45%' },
                        { left: 60, right: 60, top: '68%', height: '22%' }
                    ],
                    xAxis: [
                        { type: 'category', data: times, axisLine: { lineStyle: { color: colors.grid } }, axisLabel: { color: '#8b949e', fontSize: 10, interval: timeInfo.interval, rotate: 45 } },
                        { type: 'category', data: times, gridIndex: 1, axisLine: { lineStyle: { color: colors.grid } }, axisLabel: { show: false } }
                    ],
                    yAxis: [
                        { scale: true, axisLine: { lineStyle: { color: colors.grid } }, splitLine: { lineStyle: { color: colors.grid } }, axisLabel: { color: '#8b949e', fontSize: 10 } },
                        { scale: true, gridIndex: 1, axisLine: { lineStyle: { color: colors.grid } }, splitLine: { show: false }, axisLabel: { color: '#8b949e', fontSize: 10, formatter: '{value}' }, name: 'Spread(pips)', nameTextStyle: { color: '#8b949e', fontSize: 10 } }
                    ],
                    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 }],
                    series: [
                        {
                            name: 'Bid',
                            type: 'line',
                            data: bids,
                            symbol: 'none',
                            lineStyle: { color: colors.bid, width: 1.5 }
                        },
                        {
                            name: 'Ask',
                            type: 'line',
                            data: asks,
                            symbol: 'none',
                            lineStyle: { color: colors.ask, width: 1.5 }
                        },
                        {
                            name: 'Spread',
                            type: 'line',
                            xAxisIndex: 1,
                            yAxisIndex: 1,
                            data: spreads,
                            symbol: 'none',
                            lineStyle: { color: '#f0883e', width: 1 },
                            areaStyle: { color: 'rgba(240,136,62,0.2)' }
                        }
                    ]
                };
                
                mainChart.setOption(option, true);
            } else {
                // 原始tick格式
                const bids = data.filter(d => d.type === 'BID');
                const asks = data.filter(d => d.type === 'ASK');
                const timeInfo = getSmartTimeFormat(data);
                
                const option = {
                    backgroundColor: 'transparent',
                    animation: false,
                    legend: {
                        data: ['Bid', 'Ask'],
                        textStyle: { color: '#8b949e', fontSize: 11 },
                        top: 0
                    },
                    tooltip: {
                        trigger: 'axis',
                        backgroundColor: '#161b22',
                        borderColor: '#30363d',
                        textStyle: { color: '#c9d1d9', fontSize: 12 }
                    },
                    grid: { left: 60, right: 20, top: 40, bottom: 60 },
                    xAxis: {
                        type: 'time',
                        axisLine: { lineStyle: { color: colors.grid } },
                        axisLabel: { 
                            color: '#8b949e', 
                            fontSize: 10,
                            rotate: 45,
                            formatter: function(value) {
                                const d = new Date(value);
                                const pad = n => n.toString().padStart(2, '0');
                                return `${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
                            }
                        }
                    },
                    yAxis: {
                        scale: true,
                        axisLine: { lineStyle: { color: colors.grid } },
                        splitLine: { lineStyle: { color: colors.grid } },
                        axisLabel: { color: '#8b949e', fontSize: 10 }
                    },
                    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
                    series: [
                        {
                            name: 'Bid',
                            type: 'scatter',
                            data: bids.map(d => [d.timestamp, d.price]),
                            symbolSize: 2,
                            itemStyle: { color: colors.bid }
                        },
                        {
                            name: 'Ask',
                            type: 'scatter',
                            data: asks.map(d => [d.timestamp, d.price]),
                            symbolSize: 2,
                            itemStyle: { color: colors.ask }
                        }
                    ]
                };
                
                mainChart.setOption(option, true);
            }
        }
        
        // 导出CSV
        async function exportCSV() {
            if (!currentCacheKey) {
                addLog('请先下载数据', 'error');
                return;
            }
            
            try {
                const res = await fetch('/api/export/csv', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cache_key: currentCacheKey })
                });
                const data = await res.json();
                addLog(data.message, data.success ? 'success' : 'error');
            } catch (e) {
                addLog('导出错误: ' + e.message, 'error');
            }
        }
        
        // 导出Excel
        async function exportExcel() {
            if (!currentCacheKey) {
                addLog('请先下载数据', 'error');
                return;
            }
            
            try {
                const res = await fetch('/api/export/excel', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cache_key: currentCacheKey })
                });
                const data = await res.json();
                addLog(data.message, data.success ? 'success' : 'error');
            } catch (e) {
                addLog('导出错误: ' + e.message, 'error');
            }
        }
        
        // 拖拽调节高度功能
        function initResizeHandle() {
            const resizeHandle = document.getElementById('resizeHandle');
            const chartSection = document.getElementById('chartSection');
            const tableSection = document.getElementById('tableSection');
            
            let isResizing = false;
            let startY = 0;
            let startChartHeight = 0;
            let startTableHeight = 0;
            
            resizeHandle.addEventListener('mousedown', function(e) {
                isResizing = true;
                startY = e.clientY;
                startChartHeight = chartSection.offsetHeight;
                startTableHeight = tableSection.offsetHeight;
                document.body.style.cursor = 'ns-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', function(e) {
                if (!isResizing) return;
                
                const deltaY = e.clientY - startY;
                const newChartHeight = Math.max(200, startChartHeight + deltaY);
                const newTableHeight = Math.max(200, startTableHeight - deltaY);
                
                chartSection.style.height = newChartHeight + 'px';
                tableSection.style.height = newTableHeight + 'px';
                
                // 调整图表大小
                if (mainChart) mainChart.resize();
            });
            
            document.addEventListener('mouseup', function() {
                if (isResizing) {
                    isResizing = false;
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';
                }
            });
        }
        
        // 页面加载
        window.onload = function() {
            initChart();
            initResizeHandle();
            updateConnectionUI(false);  // 初始状态: 未连接，禁用下载
            connectBBG();  // 尝试自动连接
        };
    </script>
</body>
</html>
'''


def create_app(host: str = "localhost", port: int = 8194) -> Flask:
    """创建Flask应用"""
    
    app = Flask(__name__)
    explorer = DataExplorer(host, port)
    
    # 全局错误处理 - 确保返回JSON
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500
    
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({
            'success': False,
            'message': '接口不存在'
        }), 404
    
    @app.route('/')
    def index():
        return render_template_string(
            HTML_TEMPLATE, 
            version=APP_VERSION, 
            update_time=APP_UPDATE_TIME
        )
    
    @app.route('/api/connect', methods=['POST'])
    def connect():
        success = explorer.connect()
        return jsonify({
            'success': success,
            'message': '连接成功' if success else '连接失败，请确认Bloomberg Terminal已启动并登录'
        })
    
    @app.route('/api/status', methods=['GET'])
    def status():
        """检查Bloomberg连接状态（活性检查）"""
        is_alive = explorer.is_connected and explorer.check_alive()
        return jsonify({
            'success': True,
            'connected': is_alive,
            'message': '已连接' if is_alive else '未连接'
        })
    
    def _require_bbg_connection(func_name: str):
        """前置检查: Bloomberg是否连接，返回错误响应或None"""
        if not explorer.is_connected:
            return jsonify({
                'success': False,
                'message': f'Bloomberg未连接，请先连接Bloomberg Terminal后再{func_name}'
            })
        return None
    
    @app.route('/api/download/bars', methods=['POST'])
    def download_bars():
        err = _require_bbg_connection('下载K线数据')
        if err:
            return err
        data = request.json
        result = explorer.download_bars(
            symbol=data.get('symbol'),
            interval=data.get('interval', '1m'),
            days_back=data.get('days_back', 30),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            timezone=data.get('timezone', 'Asia/Shanghai')
        )
        return jsonify(result)
    
    @app.route('/api/download/ticks', methods=['POST'])
    def download_ticks():
        err = _require_bbg_connection('下载Tick数据')
        if err:
            return err
        data = request.json
        result = explorer.download_ticks(
            symbol=data.get('symbol'),
            hours_back=data.get('hours_back', 1),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            timezone=data.get('timezone', 'Asia/Shanghai')
        )
        return jsonify(result)
    
    @app.route('/api/download/bidask', methods=['POST'])
    def download_bidask():
        err = _require_bbg_connection('下载Bid/Ask数据')
        if err:
            return err
        data = request.json
        result = explorer.download_bid_ask(
            symbol=data.get('symbol'),
            hours_back=data.get('hours_back', 1),
            resample=data.get('resample'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            timezone=data.get('timezone', 'Asia/Shanghai'),
            daily_start=data.get('daily_start'),
            daily_end=data.get('daily_end')
        )
        return jsonify(result)
    
    @app.route('/api/download/reference', methods=['POST'])
    def download_reference():
        err = _require_bbg_connection('下载参考数据')
        if err:
            return err
        data = request.json
        fields = data.get('fields', 'PX_LAST,NAME').split(',')
        symbols = data.get('symbol', '').split(',')
        result = explorer.download_reference(
            symbols=[s.strip() for s in symbols],
            fields=[f.strip() for f in fields]
        )
        return jsonify(result)
    
    @app.route('/api/export/csv', methods=['POST'])
    def export_csv():
        data = request.json
        cache_key = data.get('cache_key')
        result = explorer.export_csv(cache_key)
        return jsonify(result)
    
    @app.route('/api/export/excel', methods=['POST'])
    def export_excel():
        data = request.json
        cache_key = data.get('cache_key')
        result = explorer.export_excel(cache_key)
        return jsonify(result)
    
    @app.route('/api/chart', methods=['POST'])
    def get_chart():
        data = request.json
        result = explorer.get_chart_data(
            cache_key=data.get('cache_key'),
            chart_type=data.get('chart_type', 'candlestick')
        )
        return jsonify(result)
    
    @app.route('/api/fulldata', methods=['POST'])
    def get_full_data():
        """获取缓存中的完整数据"""
        data = request.json
        cache_key = data.get('cache_key')
        
        if not cache_key or cache_key not in explorer._cache:
            return jsonify({
                'success': False,
                'message': '缓存不存在',
                'data': None
            })
        
        df = explorer._cache[cache_key]
        # 转换为JSON格式
        full_data = explorer._df_to_preview(df, len(df))  # 获取全部数据
        
        return jsonify({
            'success': True,
            'message': f'获取 {len(full_data)} 条完整数据',
            'data': full_data
        })
    
    return app


def run_server(host: str = "127.0.0.1", port: int = 5001, bbg_host: str = "localhost", bbg_port: int = 8194):
    """启动Web服务"""
    app = create_app(bbg_host, bbg_port)
    
    print("=" * 60)
    print("Bloomberg Data Toolbox")
    print("=" * 60)
    print(f"Web UI: http://{host}:{port}")
    print(f"Bloomberg: {bbg_host}:{bbg_port}")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=False)
