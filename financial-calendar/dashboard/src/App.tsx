import React, { useState, useMemo } from 'react';
import { economicEvents } from './data/economicEvents';
import { getConfigForEvent } from './data/eventConfigs';
import { PriceSimulator } from './engine/PriceSimulator';
import { SignalEngine } from './engine/SignalEngine';
import { EconomicEvent } from './types';
import {
  Activity, Calendar, Shield, Zap, ArrowRight, ArrowDown,
  X, ChevronDown, ChevronRight,
  BarChart3, Settings, Database, Radio, Play,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';

/* ─── Popup ─── */
const Popup: React.FC<{
  title: string; onClose: () => void; children: React.ReactNode;
  icon?: React.ReactNode; wide?: boolean;
}> = ({ title, onClose, children, icon, wide }) => (
  <div className="fixed inset-0 bg-black/25 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    onClick={onClose} style={{ animation: 'fadeIn 0.15s ease-out' }}>
    <div className={`bg-white rounded-2xl shadow-2xl border border-gray-100 p-6 ${wide ? 'max-w-4xl' : 'max-w-lg'} w-full max-h-[85vh] overflow-y-auto`}
      onClick={e => e.stopPropagation()} style={{ animation: 'popIn 0.2s ease-out' }}>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          {icon}
          <h2 className="text-lg font-bold text-gray-800">{title}</h2>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
          <X className="w-5 h-5 text-gray-400" />
        </button>
      </div>
      {children}
    </div>
  </div>
);

/* ─── Helpers ─── */
const flags: Record<string, string> = { US: '🇺🇸', EU: '🇪🇺', GB: '🇬🇧', JP: '🇯🇵', CN: '🇨🇳' };
const impactLabel: Record<string, string> = { high: '高', medium: '中', low: '低' };
const impactTag = { high: 'bg-red-50 text-red-600 border-red-200', medium: 'bg-amber-50 text-amber-600 border-amber-200', low: 'bg-emerald-50 text-emerald-600 border-emerald-200' };
const pairColors: Record<string, string> = { EURUSD: '#3B82F6', GBPUSD: '#8B5CF6', USDJPY: '#F59E0B', USDCHF: '#10B981', AUDUSD: '#EC4899', USDCAD: '#06B6D4', EURGBP: '#F97316', EURJPY: '#A855F7' };
const fmtExp = (v: number) => v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${(v / 1e3).toFixed(0)}K`;
const romsActionLabel: Record<string, string> = { flatten: '全量平仓', reduce: '部分减仓', monitor: '仅监控' };

/* ─── 阶段颜色 ─── */
const phaseColors = {
  normal: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', dot: 'bg-gray-400' },
  pre: { bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-700', dot: 'bg-amber-500' },
  peak: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700', dot: 'bg-red-500' },
  recovery: { bg: 'bg-blue-50', border: 'border-blue-300', text: 'text-blue-700', dot: 'bg-blue-500' },
  restored: { bg: 'bg-emerald-50', border: 'border-emerald-300', text: 'text-emerald-700', dot: 'bg-emerald-500' },
};

/* ═══ MAIN APP ═══ */
const App: React.FC = () => {
  const [selectedEvent, setSelectedEvent] = useState<EconomicEvent | null>(null);
  const [popup, setPopup] = useState<string | null>(null);
  const [activePhase, setActivePhase] = useState(0);
  const [expandedSection, setExpandedSection] = useState<string | null>('arch');

  const config = selectedEvent ? getConfigForEvent(selectedEvent.category) : null;
  const pairs = config ? config.affectedPairs.slice(0, 3) : [];

  const spreadData = useMemo(() => {
    if (!selectedEvent) return [];
    const snaps = PriceSimulator.generateSpreadTimeline(selectedEvent, 30);
    const groups = new Map<number, Record<string, number>>();
    for (const s of snaps) {
      if (!pairs.includes(s.pair)) continue;
      if (!groups.has(s.timestamp)) groups.set(s.timestamp, { timestamp: s.timestamp });
      groups.get(s.timestamp)![s.pair] = s.currentSpread;
    }
    return Array.from(groups.values()).sort((a, b) => (a.timestamp as number) - (b.timestamp as number));
  }, [selectedEvent]);

  const signals = useMemo(() => selectedEvent ? SignalEngine.generateSignals(selectedEvent) : [], [selectedEvent]);
  const eventTime = selectedEvent ? new Date(selectedEvent.datetime).getTime() : 0;
  const fmtTick = (ts: number) => { const m = Math.round((ts - eventTime) / 60000); return m === 0 ? 'T-0' : m > 0 ? `T+${m}` : `T${m}`; };
  const sortedEvents = [...economicEvents].sort((a, b) => (b.relevance || 0) - (a.relevance || 0));
  const toggleSection = (id: string) => setExpandedSection(expandedSection === id ? null : id);

  /* 场景阶段定义 — 修正后的逻辑 */
  const phases = config ? [
    {
      key: 'normal', label: '常态', time: `T-${config.preEventMinutes + 5}min`,
      pamas: '价宽正常（1.0x），Calendar IPA 未激活',
      roms: '按常规对冲规则运行',
      pamasState: '正常', romsState: '正常',
    },
    {
      key: 'pre', label: '事件预警', time: `T-${config.preEventMinutes}min`,
      pamas: `Calendar IPA 激活 → 价宽开始逐步放大，目标 ${config.spreadMultiplier[selectedEvent?.impact || 'high'].toFixed(1)}x`,
      roms: `收到日历信号 → 执行${romsActionLabel[config.romsAction]}，提前清理敞口`,
      pamasState: '加价中', romsState: '平仓中',
    },
    {
      key: 'peak', label: '事件发布', time: 'T-0',
      pamas: `价宽锁定峰值 ${config.spreadMultiplier[selectedEvent?.impact || 'high'].toFixed(1)}x`,
      roms: '已完成预减仓，此阶段冻结 — 不做新的平仓操作，等待数据消化',
      pamasState: '峰值锁定', romsState: '冻结等待',
    },
    {
      key: 'recovery', label: '恢复期', time: `T+1 ~ T+${config.postEventMinutes}min`,
      pamas: '价宽开始衰减回正常水平',
      roms: '数据已消化 → 开始处理剩余敞口，如偏差大（|actual-survey| > 20%）可延长窗口',
      pamasState: '衰减中', romsState: '平剩余敞口',
    },
    {
      key: 'restored', label: '恢复正常', time: `T+${config.postEventMinutes}min+`,
      pamas: 'Calendar IPA 退出，价宽回到 1.0x',
      roms: '恢复常规对冲规则',
      pamasState: '正常', romsState: '正常',
    },
  ] : [];

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-200">
              <Calendar className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">金融日历 — PAMAS / ROMS 集成方案</h1>
              <p className="text-[11px] text-gray-400">概念演示 · 仅供内部讨论</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">

        {/* ═══ Section 1: 整体架构 — 金融日历作为桥 ═══ */}
        <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <button onClick={() => toggleSection('arch')}
            className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors cursor-pointer">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-500" />
              <h2 className="text-base font-bold text-gray-800">整体架构</h2>
            </div>
            {expandedSection === 'arch' ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
          </button>
          {expandedSection === 'arch' && (
            <div className="px-5 pb-6">

              {/* 三列架构图 */}
              <div className="grid grid-cols-[1fr_auto_1fr] gap-0 items-start mt-2">

                {/* 左: PAMAS */}
                <div className="space-y-3">
                  <div className="text-center">
                    <div className="inline-flex items-center gap-1.5 bg-blue-50 text-blue-700 text-sm font-bold px-4 py-2 rounded-xl border border-blue-200">
                      <Zap className="w-4 h-4" /> PAMAS 定价管线
                    </div>
                  </div>
                  {/* Pipeline 竖排 */}
                  <div className="flex flex-col items-center gap-1">
                    {[
                      { id: 'lpa', name: 'LPA 模型定价', desc: '聚合LP报价 → 内部中间价', active: false },
                      { id: 'spread', name: 'Spread Adj', desc: '静态价宽约束 min/max/default', active: false },
                      { id: 'calendar', name: '📅 Calendar IPA', desc: '事件驱动 · 临时价宽放大', active: true },
                      { id: 'markup', name: 'Markup IPA', desc: '交易员手动加价层', active: false },
                      { id: 'epa', name: 'EPA 对客价格', desc: '最终报价 → FIX/API 输出', active: false },
                    ].map((node, i, arr) => (
                      <React.Fragment key={node.id}>
                        <div
                          onClick={() => setPopup(`p-${node.id}`)}
                          className={`w-full max-w-[260px] rounded-xl border-2 px-4 py-2.5 cursor-pointer transition-all hover:shadow-md ${
                            node.active
                              ? 'border-blue-400 bg-blue-50 shadow-md shadow-blue-100'
                              : 'border-gray-200 bg-white hover:border-gray-300'
                          }`}>
                          <div className={`text-sm font-bold ${node.active ? 'text-blue-700' : 'text-gray-700'}`}>{node.name}</div>
                          <div className="text-[10px] text-gray-400 mt-0.5 leading-snug">{node.desc}</div>
                          {node.active && <div className="text-[9px] text-blue-500 font-semibold mt-1">← 新增模块</div>}
                        </div>
                        {i < arr.length - 1 && <ArrowDown className="w-3.5 h-3.5 text-gray-300" />}
                      </React.Fragment>
                    ))}
                  </div>
                </div>

                {/* 中: 金融日历（桥） */}
                <div className="flex flex-col items-center justify-center px-6 pt-14">
                  {/* 左箭头 */}
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-16 h-px bg-blue-300 relative">
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-0 h-0 border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent border-l-[6px] border-l-blue-300" />
                    </div>
                    <div className="text-[9px] text-blue-400 whitespace-nowrap">事件信号</div>
                  </div>

                  {/* 日历核心 */}
                  <div className="bg-gradient-to-b from-amber-50 to-orange-50 border-2 border-amber-300 rounded-2xl p-5 shadow-lg shadow-amber-100 text-center relative">
                    <div className="text-3xl mb-2">📅</div>
                    <div className="text-sm font-bold text-amber-800">金融日历</div>
                    <div className="text-[10px] text-amber-600 mt-1 leading-snug max-w-[140px]">
                      Bloomberg 数据源<br />
                      事件分级引擎<br />
                      时间窗口管理
                    </div>
                    <div className="mt-3 space-y-1">
                      <div className="text-[9px] bg-white/70 rounded-lg px-2 py-0.5 text-amber-700 border border-amber-200">Relevance ≥ 85 → 高</div>
                      <div className="text-[9px] bg-white/70 rounded-lg px-2 py-0.5 text-amber-700 border border-amber-200">60~85 → 中</div>
                      <div className="text-[9px] bg-white/70 rounded-lg px-2 py-0.5 text-amber-700 border border-amber-200">{'< 60 → 低'}</div>
                    </div>
                  </div>

                  {/* 右箭头 */}
                  <div className="flex items-center gap-2 mt-3">
                    <div className="text-[9px] text-purple-400 whitespace-nowrap">对冲指令</div>
                    <div className="w-16 h-px bg-purple-300 relative">
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-0 h-0 border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent border-l-[6px] border-l-purple-300" />
                    </div>
                  </div>
                </div>

                {/* 右: ROMS */}
                <div className="space-y-3">
                  <div className="text-center">
                    <div className="inline-flex items-center gap-1.5 bg-purple-50 text-purple-700 text-sm font-bold px-4 py-2 rounded-xl border border-purple-200">
                      <Shield className="w-4 h-4" /> ROMS 风控对冲
                    </div>
                  </div>
                  <div className="flex flex-col items-center gap-1">
                    {[
                      { name: '敞口监控', desc: '实时计算各币种对 net exposure', color: 'text-gray-700' },
                      { name: '触发引擎', desc: '敞口触发 / 定时触发 / 日历触发(新增)', color: 'text-gray-700', isNew: true },
                      { name: '对冲决策', desc: '根据规则确定 action 和 reduction%', color: 'text-gray-700' },
                      { name: '执行策略', desc: 'SingleOrder 一次下单 / TWAP 分批', color: 'text-gray-700' },
                      { name: '订单管理 OMS', desc: '下单 → 确认 → 更新头寸', color: 'text-gray-700' },
                    ].map((node, i, arr) => (
                      <React.Fragment key={node.name}>
                        <div className={`w-full max-w-[260px] rounded-xl border-2 px-4 py-2.5 ${node.isNew ? 'border-purple-300 bg-purple-50' : 'border-gray-200 bg-white'}`}>
                          <div className={`text-sm font-bold ${node.color}`}>{node.name}</div>
                          <div className="text-[10px] text-gray-400 mt-0.5 leading-snug">{node.desc}</div>
                          {node.isNew && <div className="text-[9px] text-purple-500 font-semibold mt-1">← 新增触发类型</div>}
                        </div>
                        {i < arr.length - 1 && <ArrowDown className="w-3.5 h-3.5 text-gray-300" />}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </div>

              <p className="text-xs text-gray-400 mt-4 text-center">
                金融日历作为中间层，向左给 PAMAS 发「事件信号」控制价宽，向右给 ROMS 发「对冲指令」控制敞口。点击左侧节点查看说明。
              </p>
            </div>
          )}
        </section>

        {/* ═══ Section 2: 选择事件 ═══ */}
        <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <button onClick={() => toggleSection('events')}
            className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors cursor-pointer">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-amber-500" />
              <h2 className="text-base font-bold text-gray-800">选一个事件，看系统怎么响应</h2>
            </div>
            {expandedSection === 'events' ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
          </button>
          {expandedSection === 'events' && (
            <div className="px-5 pb-5">
              <p className="text-sm text-gray-500 mb-3">以下是 Bloomberg 经济日历里近期的真实事件，按 Relevance 排序。</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {sortedEvents.map(ev => {
                  const sel = selectedEvent?.eventId === ev.eventId;
                  return (
                    <div key={ev.eventId}
                      onClick={() => { setSelectedEvent(ev); setActivePhase(0); setExpandedSection('scenario'); }}
                      className={`p-3 rounded-xl border-2 cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-md ${
                        sel ? 'border-blue-400 bg-blue-50 shadow-md' : 'border-gray-100 bg-white hover:border-gray-300'
                      }`}>
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <span className="text-base">{flags[ev.countryCode] || '🏳️'}</span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${impactTag[ev.impact]}`}>{impactLabel[ev.impact]}</span>
                      </div>
                      <h3 className="text-xs font-semibold text-gray-800 leading-tight mb-1">{ev.name}</h3>
                      <div className="text-[10px] text-gray-400 font-mono">
                        {new Date(ev.datetime).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
                        {' '}
                        {new Date(ev.datetime).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })}
                      </div>
                      {ev.relevance && (
                        <div className="mt-1.5 flex items-center gap-1">
                          <div className="flex-1 h-1 rounded bg-gray-100 overflow-hidden">
                            <div className="h-full rounded bg-blue-400" style={{ width: `${ev.relevance}%` }} />
                          </div>
                          <span className="text-[9px] text-gray-400 font-mono">{ev.relevance.toFixed(0)}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        {/* ═══ Section 3: 场景走查 — 双轨时间线 ═══ */}
        {selectedEvent && config && (
          <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden" style={{ animation: 'slideUp 0.3s ease-out' }}>
            <button onClick={() => toggleSection('scenario')}
              className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors cursor-pointer">
              <div className="flex items-center gap-2">
                <Play className="w-5 h-5 text-emerald-500" />
                <h2 className="text-base font-bold text-gray-800">
                  场景走查 — {selectedEvent.name}
                </h2>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${impactTag[selectedEvent.impact]}`}>
                  {impactLabel[selectedEvent.impact]}影响 · Relevance {selectedEvent.relevance?.toFixed(0)}
                </span>
              </div>
              {expandedSection === 'scenario' ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
            </button>
            {expandedSection === 'scenario' && (
              <div className="px-5 pb-6">
                {/* 阶段切换 */}
                <div className="flex gap-1 mb-6">
                  {phases.map((p, i) => {
                    const c = phaseColors[p.key as keyof typeof phaseColors];
                    return (
                      <button key={p.key} onClick={() => setActivePhase(i)}
                        className={`flex-1 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer border ${
                          activePhase === i
                            ? `${c.bg} ${c.border} ${c.text} shadow-sm`
                            : 'bg-gray-50 border-gray-100 text-gray-400 hover:bg-gray-100'
                        }`}>{p.label}</button>
                    );
                  })}
                </div>

                {/* 双轨时间线 */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {/* PAMAS 轨 */}
                  <div>
                    <div className="flex items-center gap-1.5 mb-3">
                      <Zap className="w-4 h-4 text-blue-500" />
                      <span className="text-xs font-bold text-blue-700">PAMAS 定价侧</span>
                    </div>
                    <div className="space-y-2">
                      {phases.map((p, i) => {
                        const c = phaseColors[p.key as keyof typeof phaseColors];
                        const active = i <= activePhase;
                        return (
                          <div key={p.key} className={`rounded-xl border p-3 transition-all ${active ? `${c.bg} ${c.border}` : 'bg-gray-50 border-gray-100 opacity-40'}`}>
                            <div className="flex items-center gap-2 mb-1">
                              <div className={`w-2 h-2 rounded-full ${active ? c.dot : 'bg-gray-300'}`} />
                              <span className={`text-[10px] font-mono ${active ? c.text : 'text-gray-400'}`}>{p.time}</span>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${active ? `${c.bg} ${c.text}` : 'text-gray-400'}`}>{p.pamasState}</span>
                            </div>
                            <p className={`text-xs leading-relaxed ${active ? 'text-gray-600' : 'text-gray-400'}`}>{p.pamas}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* ROMS 轨 */}
                  <div>
                    <div className="flex items-center gap-1.5 mb-3">
                      <Shield className="w-4 h-4 text-purple-500" />
                      <span className="text-xs font-bold text-purple-700">ROMS 风控侧</span>
                    </div>
                    <div className="space-y-2">
                      {phases.map((p, i) => {
                        const c = phaseColors[p.key as keyof typeof phaseColors];
                        const active = i <= activePhase;
                        return (
                          <div key={p.key} className={`rounded-xl border p-3 transition-all ${active ? `${c.bg} ${c.border}` : 'bg-gray-50 border-gray-100 opacity-40'}`}>
                            <div className="flex items-center gap-2 mb-1">
                              <div className={`w-2 h-2 rounded-full ${active ? c.dot : 'bg-gray-300'}`} />
                              <span className={`text-[10px] font-mono ${active ? c.text : 'text-gray-400'}`}>{p.time}</span>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${active ? `${c.bg} ${c.text}` : 'text-gray-400'}`}>{p.romsState}</span>
                            </div>
                            <p className={`text-xs leading-relaxed ${active ? 'text-gray-600' : 'text-gray-400'}`}>{p.roms}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* 下方：图表 + 信号 + 配置 */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {/* 价宽曲线 */}
                  <div className="lg:col-span-2 rounded-xl border border-gray-200 p-4 cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => setPopup('spread-big')}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <BarChart3 className="w-4 h-4 text-blue-500" />
                        <span className="text-xs font-semibold text-gray-700">价宽变化曲线</span>
                      </div>
                      <span className="text-[10px] text-gray-400">点击放大</span>
                    </div>
                    <div className="h-44">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={spreadData} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                          <XAxis dataKey="timestamp" tickFormatter={fmtTick} tick={{ fill: '#9CA3AF', fontSize: 9 }} axisLine={false} interval="preserveStartEnd" />
                          <YAxis tick={{ fill: '#9CA3AF', fontSize: 9 }} axisLine={false} />
                          <ReferenceLine x={eventTime} stroke="#EF4444" strokeDasharray="4 4" />
                          {pairs.map(p => <Line key={p} type="monotone" dataKey={p} stroke={pairColors[p] || '#6B7280'} strokeWidth={2} dot={false} />)}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex gap-3 mt-1">
                      {pairs.map(p => (
                        <span key={p} className="flex items-center gap-1 text-[10px] text-gray-400">
                          <span className="inline-block w-3 h-1 rounded" style={{ backgroundColor: pairColors[p] }} /> {p}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* 右侧：配置 + 信号 */}
                  <div className="space-y-4">
                    {/* 配置概览 */}
                    <div className="rounded-xl border border-gray-200 p-4 cursor-pointer hover:shadow-md transition-shadow"
                      onClick={() => setPopup('config-detail')}>
                      <div className="flex items-center gap-1.5 mb-3">
                        <Settings className="w-4 h-4 text-amber-500" />
                        <span className="text-xs font-semibold text-gray-700">配置概览</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-center">
                        <div className="bg-gray-50 rounded-lg p-2">
                          <div className="text-base font-bold text-gray-900">{config.spreadMultiplier[selectedEvent.impact].toFixed(1)}x</div>
                          <div className="text-[10px] text-gray-400">价宽倍数</div>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-2">
                          <div className="text-base font-bold text-gray-900">{config.preEventMinutes}min</div>
                          <div className="text-[10px] text-gray-400">提前窗口</div>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-2">
                          <div className="text-base font-bold text-gray-900">{config.postEventMinutes}min</div>
                          <div className="text-[10px] text-gray-400">恢复窗口</div>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-2">
                          <div className="text-base font-bold text-gray-900">{romsActionLabel[config.romsAction]}</div>
                          <div className="text-[10px] text-gray-400">预警动作</div>
                        </div>
                      </div>
                    </div>

                    {/* ROMS 信号 */}
                    <div className="rounded-xl border border-gray-200 p-4">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Shield className="w-4 h-4 text-purple-500" />
                        <span className="text-xs font-semibold text-gray-700">对冲信号</span>
                      </div>
                      <div className="space-y-1.5">
                        {signals.slice(0, 3).map(sig => {
                          const { label, color } = SignalEngine.getActionDisplay(sig.action);
                          return (
                            <div key={sig.signalId}
                              className="flex items-center justify-between p-2 rounded-lg border border-gray-100 hover:border-purple-200 cursor-pointer transition-colors"
                              onClick={() => setPopup(`sig-${sig.signalId}`)}>
                              <div className="flex items-center gap-2">
                                <span className="text-[11px] font-bold text-gray-800">{sig.pair}</span>
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: `${color}12`, color }}>{label}</span>
                              </div>
                              <div className="text-[10px] text-gray-400">
                                {fmtExp(sig.exposureBefore)} → <span className="text-emerald-600 font-semibold">{fmtExp(sig.exposureAfter)}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* ═══ Section 4: 配置表设计（含现有 Schema 对比） ═══ */}
        <section className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <button onClick={() => toggleSection('schema')}
            className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors cursor-pointer">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-indigo-500" />
              <h2 className="text-base font-bold text-gray-800">配置表设计</h2>
              <span className="text-[10px] text-gray-400 font-normal ml-1">基于现有 Schema 扩展</span>
            </div>
            {expandedSection === 'schema' ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
          </button>
          {expandedSection === 'schema' && (
            <div className="px-5 pb-5 space-y-6">

              {/* ── 设计思路总览 ── */}
              <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-xl border border-indigo-200 p-4">
                <h3 className="text-sm font-bold text-indigo-800 mb-2">💡 设计思路：最大化复用现有表结构</h3>
                <p className="text-xs text-indigo-700 leading-relaxed mb-3">
                  经过调研现有 ROMS 数据库（<span className="font-mono bg-white/50 px-1 rounded">fx_romshedge_db</span>）和
                  PAMAS 数据库（<span className="font-mono bg-white/50 px-1 rounded">data_query_conf</span>），
                  金融日历的接入方案尽量<strong>复用已有框架</strong>，避免重建轮子：
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-white rounded-lg p-3 border border-indigo-100">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Shield className="w-3.5 h-3.5 text-purple-500" />
                      <span className="text-xs font-bold text-purple-700">ROMS 侧</span>
                    </div>
                    <p className="text-[11px] text-gray-600 leading-relaxed">
                      复用现有 <span className="font-mono text-purple-600">t_trigger_condition</span> + <span className="font-mono text-purple-600">t_rule</span> 框架，
                      新增触发变量类型 <span className="font-mono bg-purple-50 px-1 rounded text-purple-600">Ftrigger_var_type = 13</span>（金融日历事件），
                      规则表沿用 <span className="font-mono text-purple-600">t_rule</span> 的字段结构
                    </p>
                  </div>
                  <div className="bg-white rounded-lg p-3 border border-indigo-100">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Zap className="w-3.5 h-3.5 text-blue-500" />
                      <span className="text-xs font-bold text-blue-700">PAMAS 侧</span>
                    </div>
                    <p className="text-[11px] text-gray-600 leading-relaxed">
                      参照现有 <span className="font-mono text-blue-600">exrate_scenario_config</span> 的配置风格，
                      新增 <span className="font-mono text-blue-600">t_calendar_ipa_config</span> 表，
                      字段命名遵循 PAMAS 的 <span className="font-mono bg-blue-50 px-1 rounded text-blue-600">F前缀</span> 规范
                    </p>
                  </div>
                </div>
              </div>

              {/* ── Part A: ROMS 现有 Schema + 扩展 ── */}
              <div>
                <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-1.5">
                  <Shield className="w-4 h-4 text-purple-500" /> ROMS 侧 — 基于现有框架扩展
                </h3>

                {/* 现有触发条件表 */}
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-semibold text-gray-600">现有表：</span>
                    <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-700">fx_romshedge_db.t_trigger_condition</span>
                    <span className="text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full border border-emerald-200">已有</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs border-collapse">
                      <thead><tr className="bg-gray-50">
                        {['字段', '说明', '现有值枚举'].map(h => <th key={h} className="text-left p-2 border-b border-gray-200 font-semibold text-gray-600">{h}</th>)}
                      </tr></thead>
                      <tbody>
                        {[
                          ['Ftrigger_var_type', '触发变量类型', '1=各自敞口, 2=自身未实现盈亏, 3=时间, 4=头寸集敞口, 5=头寸集盈亏, 10=在离岸价差, 11=全期限敞口, 12=预平盘修正'],
                          ['Fcompare_operator', '比较运算符', '0=无, 1=大于, 2=小于, 3=等于'],
                          ['Ftrigger_value_type', '触发值类型', '0=无, 1=绝对值, 2=百分比'],
                          ['Flstate', '物理状态', '1=正常, 2=删除'],
                          ['Fmemo', '备注', '如"敞口触发"、"时间兜底触发"'],
                        ].map(([f, d, e]) => (
                          <tr key={f} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="p-2 font-mono text-gray-600">{f}</td>
                            <td className="p-2 text-gray-600">{d}</td>
                            <td className="p-2 text-gray-400 text-[11px]">{e}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* 新增 INSERT */}
                  <div className="mt-2 bg-purple-50 rounded-lg border border-purple-200 p-3">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <span className="text-[10px] font-bold text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded">新增</span>
                      <span className="text-xs text-purple-700 font-medium">追加触发变量类型 13 = 金融日历事件</span>
                    </div>
                    <pre className="text-[10px] font-mono text-purple-800 bg-white/60 rounded p-2 overflow-x-auto leading-relaxed">
{`INSERT INTO fx_romshedge_db.t_trigger_condition
  (Ftrigger_cond_id, Ftrigger_var_type, Fcompare_operator,
   Ftrigger_value_type, Flstate, Fmemo)
VALUES (20, 13, 0, 0, 1, '金融日历事件触发');`}
                    </pre>
                    <p className="text-[10px] text-purple-600 mt-1.5">
                      💬 沿用现有的递增模式：type 11（全期限敞口）→ 12（预平盘修正）→ <strong>13（金融日历事件）</strong>
                    </p>
                  </div>
                </div>

                {/* 现有规则表 */}
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-semibold text-gray-600">现有表：</span>
                    <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-700">fx_romshedge_db.t_rule</span>
                    <span className="text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full border border-emerald-200">已有</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs border-collapse">
                      <thead><tr className="bg-gray-50">
                        {['字段', '说明', '日历场景复用'].map(h => <th key={h} className="text-left p-2 border-b border-gray-200 font-semibold text-gray-600">{h}</th>)}
                      </tr></thead>
                      <tbody>
                        {[
                          ['Frule_id', '规则 ID（自增）', '✅ 复用'],
                          ['Frule_name', '规则名称', '✅ 如 "NFP_高影响_平仓"'],
                          ['Frule_group_id', '规则组 ID', '✅ 可创建"日历对冲"规则组'],
                          ['Ftrigger_cond_id', '关联触发条件', '✅ 指向 type=13 的条件'],
                          ['Ftrigger_threshold', '触发阈值', '📅 存事件等级 (1/2/3)'],
                          ['Fexecutable_time_begin', '可执行开始时间', '📅 事件前 N 分钟'],
                          ['Fexecutable_time_end', '可执行结束时间', '📅 事件后 N 分钟'],
                          ['Ftarget_var_type', '目标变量类型', '✅ 1=敞口归零, 5=按比例减仓'],
                          ['Fpriority', '优先级', '✅ 日历规则可设高优先级'],
                          ['Falgo_type', '执行算法', '✅ 1=SingleOrder, 2=TWAP'],
                          ['Fstate', '启停状态', '✅ 复用'],
                          ['Fforce_offshore_trade', '强制离岸交易', '✅ 复用'],
                          ['Funderlying_tenor', '标的 tenor', '✅ 如 SPOT/1W'],
                        ].map(([f, d, r]) => (
                          <tr key={f} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="p-2 font-mono text-gray-600">{f}</td>
                            <td className="p-2 text-gray-600">{d}</td>
                            <td className="p-2 text-gray-500">{r}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 现有子表 */}
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-semibold text-gray-600">相关子表（均已有）：</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { name: 't_rule_range', desc: '规则适用的币种对范围', usage: '可配 EURUSD, GBPUSD 等受影响对' },
                      { name: 't_rule_amount', desc: '规则金额阈值', usage: '可配不同金额级别的减仓策略' },
                      { name: 't_rule_banktype', desc: '规则渠道/对手方', usage: '指定通过哪些银行执行对冲' },
                    ].map(t => (
                      <div key={t.name} className="bg-gray-50 rounded-lg p-2.5 border border-gray-100">
                        <div className="font-mono text-[10px] text-gray-700 font-semibold">{t.name}</div>
                        <div className="text-[10px] text-gray-500 mt-0.5">{t.desc}</div>
                        <div className="text-[10px] text-purple-600 mt-1">📅 {t.usage}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 需要新增的字段 / 表 */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-semibold text-gray-600">需新增：</span>
                    <span className="font-mono text-xs bg-purple-50 px-2 py-0.5 rounded text-purple-700 border border-purple-200">t_rule 扩展字段 或 t_calendar_rule_ext</span>
                    <span className="text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full border border-amber-200">新增</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mb-2">
                    现有 <span className="font-mono">t_rule</span> 无法表达"事件等级""冻结期""恢复窗口"等日历特有概念，有两种方案：
                  </p>
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="rounded-lg border-2 border-purple-300 bg-purple-50 p-3">
                      <div className="text-xs font-bold text-purple-700 mb-1">方案 A：扩展 t_rule（推荐）</div>
                      <p className="text-[10px] text-purple-600 leading-relaxed">
                        在 <span className="font-mono">t_rule</span> 新增 3 个字段：<br />
                        <span className="font-mono bg-white/50 px-1 rounded">Fevent_level</span> — 事件等级<br />
                        <span className="font-mono bg-white/50 px-1 rounded">Ffreeze_during_event</span> — 是否冻结<br />
                        <span className="font-mono bg-white/50 px-1 rounded">Frestore_after_min</span> — 恢复时间<br />
                        <span className="mt-1 inline-block text-[9px] text-purple-500">✅ 不改变现有规则逻辑，type≠13 时新字段为空</span>
                      </p>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-white p-3">
                      <div className="text-xs font-bold text-gray-600 mb-1">方案 B：独立扩展表</div>
                      <p className="text-[10px] text-gray-500 leading-relaxed">
                        新建 <span className="font-mono">t_calendar_rule_ext</span>，<br />
                        通过 <span className="font-mono">Frule_id</span> 外键关联 <span className="font-mono">t_rule</span><br />
                        <span className="mt-1 inline-block text-[9px] text-gray-400">零侵入但增加了 JOIN 复杂度</span>
                      </p>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs border-collapse">
                      <thead><tr className="bg-purple-50">
                        {['新增字段', '类型', '说明', '示例'].map(h => <th key={h} className="text-left p-2 border-b border-purple-200 font-semibold text-purple-700">{h}</th>)}
                      </tr></thead>
                      <tbody>
                        {[
                          ['Fevent_level', 'TINYINT(4)', '事件等级: 1=High, 2=Medium, 3=Low', '1'],
                          ['Ffreeze_during_event', 'TINYINT(1)', '事件发布期间冻结对冲（默认 1）', '1'],
                          ['Frestore_after_min', 'INT(10)', '事件后恢复常规规则的分钟数', '15'],
                        ].map(([f, t, d, e]) => (
                          <tr key={f} className="border-b border-purple-100 hover:bg-purple-50/50">
                            <td className="p-2 font-mono text-purple-600 font-semibold">{f}</td>
                            <td className="p-2 text-gray-500">{t}</td>
                            <td className="p-2 text-gray-600">{d}</td>
                            <td className="p-2 text-gray-400 font-mono">{e}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 信号条件 signalConditions */}
                <div className="mt-3 bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <div className="text-xs font-semibold text-gray-600 mb-1">补充：现有 SignalCondition 类型枚举</div>
                  <p className="text-[10px] text-gray-500 leading-relaxed">
                    ROMS 的 <span className="font-mono">AutoHedgeRuleStructuredEntity</span> 包含 <span className="font-mono">signalConditions</span> 字段，
                    现有类型有 <span className="font-mono bg-white px-1 rounded">HOLIDAY</span>、
                    <span className="font-mono bg-white px-1 rounded">PRE_HEDGE_BUY</span>、
                    <span className="font-mono bg-white px-1 rounded">PRE_HEDGE_SELL</span>。
                    金融日历可新增 <span className="font-mono bg-purple-100 px-1 rounded text-purple-600">CALENDAR_EVENT</span> 类型作为规则的启用/禁用条件。
                  </p>
                </div>
              </div>

              {/* 分隔 */}
              <div className="border-t border-gray-100" />

              {/* ── Part B: PAMAS 侧 ── */}
              <div>
                <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-blue-500" /> PAMAS 侧 — Calendar IPA 配置表（新增）
                </h3>

                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-semibold text-gray-600">参考表：</span>
                    <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-700">data_query_conf.exrate_scenario_config</span>
                    <span className="text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full border border-emerald-200">已有</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mb-2">
                    现有场景配置表管理报价源、markup、base_ccy 等。Calendar IPA 配置表采用相似的命名风格和 F 前缀规范，
                    但独立存放（因为是事件驱动的临时性配置，生命周期不同）。
                  </p>
                </div>

                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-gray-600">新增表：</span>
                  <span className="font-mono text-xs bg-blue-50 px-2 py-0.5 rounded text-blue-700 border border-blue-200">fx_rate_db.t_calendar_ipa_config</span>
                  <span className="text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full border border-amber-200">新增</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead><tr className="bg-blue-50">
                      {['字段', '类型', '说明', '示例'].map(h => <th key={h} className="text-left p-2 border-b border-blue-200 font-semibold text-blue-700">{h}</th>)}
                    </tr></thead>
                    <tbody>
                      {[
                        ['Fpa_config_name', 'VARCHAR(32)', 'PA 配置名（复用已有概念）', 'prod_v1'],
                        ['Fcurrency_pair', 'VARCHAR(8)', '币种对，default = 全币种', 'USDCNH'],
                        ['Fevent_level', 'TINYINT(4)', '事件等级: 1=High, 2=Medium, 3=Low', '1'],
                        ['Fspread_multiplier', 'DECIMAL(4,2)', '价宽放大倍数', '3.00'],
                        ['Fpre_event_minutes', 'INT(10)', '事件前生效分钟数', '30'],
                        ['Fpost_event_minutes', 'INT(10)', '事件后恢复分钟数', '15'],
                        ['Fwidening_curve', 'VARCHAR(32)', '变化曲线: linear / ease_in_out / step', 'ease_in_out'],
                        ['Fmanual_override', 'TINYINT(1)', '是否允许交易员覆盖', '0'],
                        ['Flstate', 'SMALLINT(6)', '物理状态: 1=正常, 2=删除', '1'],
                        ['Fcreate_user', 'VARCHAR(64)', '创建人', 'tencentren'],
                        ['Fmodify_time', 'DATETIME', '最后修改时间', 'CURRENT_TIMESTAMP'],
                      ].map(([f, t, d, e]) => (
                        <tr key={f} className="border-b border-blue-100/50 hover:bg-blue-50/30">
                          <td className="p-2 font-mono text-blue-600 font-semibold">{f}</td>
                          <td className="p-2 text-gray-500">{t}</td>
                          <td className="p-2 text-gray-600">{d}</td>
                          <td className="p-2 text-gray-400 font-mono">{e}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-[10px] text-gray-400 mt-1.5">
                  主键：(Fpa_config_name, Fcurrency_pair, Fevent_level) · 字段命名遵循 PAMAS F 前缀规范 · Flstate 复用现有软删除模式
                </p>
              </div>

              {/* 分隔 */}
              <div className="border-t border-gray-100" />

              {/* ── Part C: Bloomberg 数据源字段 ── */}
              <div>
                <h3 className="text-sm font-bold text-gray-800 mb-2 flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-amber-500" /> Bloomberg 数据源字段映射
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead><tr className="bg-amber-50">
                      {['字段', '用途', '分级映射'].map(h => <th key={h} className="text-left p-2 border-b border-amber-200 font-semibold text-amber-700">{h}</th>)}
                    </tr></thead>
                    <tbody>
                      {[
                        ['Date Time', '触发时间锚点', '-'],
                        ['Country Code', '映射受影响币种对', 'US → USD 相关对'],
                        ['Event', '匹配事件分级规则', '-'],
                        ['Relevance', '重要性评分 0~100', '≥85 高 / 60~85 中 / <60 低'],
                        ['Survey / Actual', '偏差判断', '偏差超 20% → 延长恢复窗口'],
                        ['Ticker', '唯一标识', 'FDTR Index'],
                      ].map(([f, u, m]) => (
                        <tr key={f} className="border-b border-amber-100/50 hover:bg-amber-50/30">
                          <td className="p-2 font-mono text-amber-600">{f}</td>
                          <td className="p-2 text-gray-600">{u}</td>
                          <td className="p-2 text-gray-400">{m}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* ── 总结：变更清单 ── */}
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-4">
                <h3 className="text-sm font-bold text-gray-700 mb-3">📋 数据库变更清单</h3>
                <div className="space-y-2">
                  {[
                    { action: '新增', color: 'bg-amber-100 text-amber-700', target: 'fx_romshedge_db.t_trigger_condition', detail: 'INSERT 一条记录：Ftrigger_var_type = 13（金融日历事件触发）' },
                    { action: '扩展', color: 'bg-purple-100 text-purple-700', target: 'fx_romshedge_db.t_rule', detail: 'ALTER TABLE 新增 3 个字段：Fevent_level / Ffreeze_during_event / Frestore_after_min' },
                    { action: '复用', color: 'bg-emerald-100 text-emerald-700', target: 'fx_romshedge_db.t_rule_range', detail: '配置日历规则适用的币种对范围（无需改表结构）' },
                    { action: '复用', color: 'bg-emerald-100 text-emerald-700', target: 'fx_romshedge_db.t_rule_banktype', detail: '配置日历对冲走哪些银行渠道（无需改表结构）' },
                    { action: '新建', color: 'bg-blue-100 text-blue-700', target: 'fx_rate_db.t_calendar_ipa_config', detail: 'Calendar IPA 配置表，管理各等级/币种对的价宽放大规则' },
                    { action: '新建', color: 'bg-amber-100 text-amber-700', target: 'fx_calendar_db.t_calendar_event', detail: 'Bloomberg 事件数据存储表（ETL 落库）' },
                  ].map((item) => (
                    <div key={item.target} className="flex items-start gap-2">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${item.color} shrink-0 mt-0.5`}>{item.action}</span>
                      <div>
                        <span className="text-xs font-mono text-gray-700">{item.target}</span>
                        <span className="text-[10px] text-gray-400 ml-2">{item.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </main>

      <footer className="border-t border-gray-100 py-6 mt-8">
        <div className="max-w-6xl mx-auto px-6 text-xs text-gray-400 text-center">
          金融日历 × PAMAS × ROMS 集成方案 · 概念演示 · 仅供内部讨论
        </div>
      </footer>

      {/* ═══ 弹窗 ═══ */}

      {popup === 'p-lpa' && <Popup title="LPA — 模型定价" onClose={() => setPopup(null)} icon={<Zap className="w-5 h-5 text-gray-400" />}>
        <p className="text-sm text-gray-600">聚合多个 LP 报价，通过 tenor model / bidask model 等模型生成内部中间价。</p>
      </Popup>}
      {popup === 'p-spread' && <Popup title="Spread Adj — 静态价宽约束" onClose={() => setPopup(null)} icon={<Settings className="w-5 h-5 text-gray-400" />}>
        <p className="text-sm text-gray-600">按币种对粒度配 min/max/default spread，价差超范围时用 default 兜底。现有逻辑不动。</p>
      </Popup>}
      {popup === 'p-calendar' && <Popup title="📅 Calendar IPA — 事件价宽放大（新增）" onClose={() => setPopup(null)} icon={<Calendar className="w-5 h-5 text-blue-500" />}>
        <p className="text-sm text-gray-600 mb-3">基于金融日历事件<strong>动态</strong>调整价宽。跟 Spread Adj 的静态约束不同，这个是有时间窗口的临时性调整。</p>
        <div className="space-y-2">
          <div className="bg-blue-50 rounded-xl p-3 text-xs text-blue-700">
            <strong>流程：</strong>事件前 T-N 分钟逐步放大 → T-0 峰值锁定 → 事件后逐步衰减恢复
          </div>
          <div className="bg-amber-50 rounded-xl p-3 text-xs text-amber-700">
            <strong>多事件：</strong>窗口重叠时取最大倍数，时间取并集
          </div>
        </div>
      </Popup>}
      {popup === 'p-markup' && <Popup title="Markup IPA — 交易员手动加价" onClose={() => setPopup(null)} icon={<Settings className="w-5 h-5 text-gray-400" />}>
        <p className="text-sm text-gray-600">交易员手动加价/折扣层。现有逻辑不动。</p>
      </Popup>}
      {popup === 'p-epa' && <Popup title="EPA — 对客输出价格" onClose={() => setPopup(null)} icon={<Radio className="w-5 h-5 text-gray-400" />}>
        <p className="text-sm text-gray-600">经过所有环节调整后的最终报价，通过 FIX / API 分发给客户。</p>
      </Popup>}

      {popup === 'spread-big' && selectedEvent && config && (
        <Popup title="价宽变化曲线" onClose={() => setPopup(null)} icon={<BarChart3 className="w-5 h-5 text-blue-500" />} wide>
          <div className="h-80 -mx-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={spreadData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="timestamp" tickFormatter={fmtTick} tick={{ fill: '#9CA3AF', fontSize: 10 }} axisLine={{ stroke: '#E5E7EB' }} interval="preserveStartEnd" />
                <YAxis tick={{ fill: '#9CA3AF', fontSize: 10 }} axisLine={{ stroke: '#E5E7EB' }}
                  label={{ value: '价宽 (pips)', angle: -90, position: 'insideLeft', fill: '#9CA3AF', fontSize: 10 }} />
                <Tooltip content={({ active, payload, label }: any) => {
                  if (!active || !payload?.length) return null;
                  return (<div className="bg-white rounded-lg shadow-lg border border-gray-100 p-3 text-xs">
                    <p className="text-gray-500 font-mono mb-1">{fmtTick(label)}</p>
                    {payload.map((e: any) => (<div key={e.dataKey} className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: e.color }} />
                      <span className="text-gray-600">{e.dataKey}:</span>
                      <span className="font-semibold">{e.value?.toFixed(1)} pips</span>
                    </div>))}
                  </div>);
                }} />
                <ReferenceLine x={eventTime} stroke="#EF4444" strokeDasharray="4 4"
                  label={{ value: '事件发布', fill: '#EF4444', fontSize: 11, position: 'top' }} />
                {config.affectedPairs.slice(0, 4).map(p => <Line key={p} type="monotone" dataKey={p} stroke={pairColors[p] || '#6B7280'} strokeWidth={2.5} dot={false} />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Popup>
      )}

      {popup === 'config-detail' && selectedEvent && config && (
        <Popup title="Calendar IPA 完整配置" onClose={() => setPopup(null)} icon={<Settings className="w-5 h-5 text-amber-500" />}>
          <div className="space-y-3">
            <div><h4 className="text-xs font-semibold text-gray-500 mb-2">受影响币种对</h4>
              <div className="flex flex-wrap gap-1.5">
                {config.affectedPairs.map(p => <span key={p} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-200 font-medium">{p}</span>)}
              </div></div>
            <div><h4 className="text-xs font-semibold text-gray-500 mb-2">各等级价宽倍数</h4>
              <div className="grid grid-cols-3 gap-2">
                {(['high', 'medium', 'low'] as const).map(l => (
                  <div key={l} className={`rounded-xl p-3 text-center ${selectedEvent.impact === l ? 'bg-blue-50 border-2 border-blue-300' : 'bg-gray-50 border border-gray-100'}`}>
                    <div className="text-lg font-bold">{config.spreadMultiplier[l].toFixed(1)}x</div>
                    <div className="text-[10px] text-gray-400">{impactLabel[l]}影响</div>
                  </div>
                ))}
              </div></div>
          </div>
        </Popup>
      )}

      {signals.map(sig => popup === `sig-${sig.signalId}` && (
        <Popup key={sig.signalId} title={`ROMS 对冲信号 · ${sig.pair}`} onClose={() => setPopup(null)} icon={<Shield className="w-5 h-5 text-purple-500" />}>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-50 rounded-xl p-3"><div className="text-[10px] text-gray-400 mb-1">操作前敞口</div><div className="text-xl font-bold">{fmtExp(sig.exposureBefore)}</div></div>
            <div className="bg-emerald-50 rounded-xl p-3"><div className="text-[10px] text-emerald-600 mb-1">操作后敞口</div><div className="text-xl font-bold text-emerald-700">{fmtExp(sig.exposureAfter)}</div></div>
          </div>
          <div className="mt-3 bg-gray-50 rounded-xl p-3 text-sm">
            <strong>动作：</strong>{romsActionLabel[sig.action]} · 目标减仓 {sig.targetReduction}%
          </div>
        </Popup>
      ))}
    </div>
  );
};

export default App;
