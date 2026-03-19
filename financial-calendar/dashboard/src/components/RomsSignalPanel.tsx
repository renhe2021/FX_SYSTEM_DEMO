import React from 'react';
import { RomsSignal } from '../types';
import { SignalEngine } from '../engine/SignalEngine';
import { Shield, ArrowDownRight, Eye, CheckCircle2, Loader2 } from 'lucide-react';

interface RomsSignalPanelProps {
  signals: RomsSignal[];
}

const RomsSignalPanel: React.FC<RomsSignalPanelProps> = ({ signals }) => {
  const formatExposure = (val: number) => {
    if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
    if (val >= 1e3) return `${(val / 1e3).toFixed(0)}K`;
    return val.toFixed(0);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <div className="w-2 h-2 rounded-full bg-slate-500" />;
      case 'executing':
        return <Loader2 className="w-3.5 h-3.5 text-accent-amber animate-spin" />;
      case 'completed':
        return <CheckCircle2 className="w-3.5 h-3.5 text-accent-green" />;
      default:
        return null;
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'flatten':
        return <ArrowDownRight className="w-3.5 h-3.5" />;
      case 'reduce':
        return <ArrowDownRight className="w-3.5 h-3.5" />;
      case 'monitor':
        return <Eye className="w-3.5 h-3.5" />;
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <Shield className="w-4 h-4 text-accent-purple" />
        <h2 className="text-sm font-semibold text-slate-200">ROMS Signals</h2>
        {signals.length > 0 && (
          <span className="px-1.5 py-0.5 rounded bg-accent-purple/20 text-accent-purple text-[10px] font-bold">
            {signals.length}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {signals.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-500">
            <Shield className="w-8 h-8 mb-2 opacity-30" />
            <p className="text-xs">No active signals</p>
            <p className="text-[10px] text-slate-600">Select an event and play timeline</p>
          </div>
        ) : (
          signals.map(signal => {
            const { label, color } = SignalEngine.getActionDisplay(signal.action);
            return (
              <div
                key={signal.signalId}
                className="glass-panel p-2.5 animate-slide-up"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-200">{signal.pair}</span>
                    <span
                      className="px-1.5 py-0.5 rounded text-[9px] font-bold flex items-center gap-1"
                      style={{
                        backgroundColor: `${color}20`,
                        color: color,
                        border: `1px solid ${color}40`,
                      }}
                    >
                      {getActionIcon(signal.action)}
                      {label}
                    </span>
                  </div>
                  {getStatusIcon(signal.status)}
                </div>

                {/* Exposure change */}
                <div className="flex items-center gap-2 mb-2 text-[10px]">
                  <span className="text-slate-500">Exposure:</span>
                  <span className="text-slate-300 font-mono">{formatExposure(signal.exposureBefore)}</span>
                  <span className="text-slate-600">→</span>
                  <span className="text-accent-green font-mono font-semibold">
                    {formatExposure(signal.exposureAfter)}
                  </span>
                  <span className="text-accent-red text-[9px]">
                    (-{signal.targetReduction}%)
                  </span>
                </div>

                {/* Progress bar */}
                {signal.action !== 'monitor' && (
                  <div className="relative h-1.5 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="absolute top-0 left-0 h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${signal.executionProgress}%`,
                        backgroundColor: signal.status === 'completed' ? '#22C55E' : color,
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default RomsSignalPanel;
