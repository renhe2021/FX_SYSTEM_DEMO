import React from 'react';
import { SpreadStatus } from '../types';
import { ArrowRight, Zap } from 'lucide-react';

interface PamasFlowDiagramProps {
  currentStatus: SpreadStatus;
  currentMultiplier: number;
}

const stages = [
  { id: 'lpa', name: 'LPA', label: 'Liquid Provider', desc: 'Price Source' },
  { id: 'calendar', name: 'Calendar IPA', label: 'Financial Calendar', desc: 'Event Widening' },
  { id: 'spread', name: 'Spread Adj', label: 'Spread Adjustment', desc: 'Min/Max Spread' },
  { id: 'markup', name: 'Markup IPA', label: 'Manual Markup', desc: 'Trader Override' },
  { id: 'epa', name: 'EPA', label: 'External Output', desc: 'Client Price' },
];

const PamasFlowDiagram: React.FC<PamasFlowDiagramProps> = ({ currentStatus, currentMultiplier }) => {
  const isCalendarActive = currentStatus !== 'normal';

  const getStageStyle = (stageId: string) => {
    if (stageId === 'calendar' && isCalendarActive) {
      return {
        bg: currentStatus === 'peak'
          ? 'bg-accent-red/20 border-accent-red/50'
          : currentStatus === 'widening'
          ? 'bg-accent-amber/20 border-accent-amber/50'
          : 'bg-accent-green/20 border-accent-green/50',
        text: currentStatus === 'peak'
          ? 'text-accent-red'
          : currentStatus === 'widening'
          ? 'text-accent-amber'
          : 'text-accent-green',
        glow: currentStatus === 'peak'
          ? 'shadow-accent-red/20'
          : currentStatus === 'widening'
          ? 'shadow-accent-amber/20'
          : 'shadow-accent-green/20',
      };
    }
    return {
      bg: 'bg-surface-800/80 border-white/10',
      text: 'text-slate-300',
      glow: '',
    };
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Zap className="w-4 h-4 text-primary-400" />
        <h2 className="text-sm font-semibold text-slate-200">PAMAS Pipeline</h2>
        {isCalendarActive && (
          <span className="px-2 py-0.5 rounded bg-accent-amber/20 text-accent-amber text-[10px] font-bold animate-pulse">
            ACTIVE
          </span>
        )}
      </div>

      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {stages.map((stage, index) => {
          const style = getStageStyle(stage.id);
          return (
            <React.Fragment key={stage.id}>
              <div
                className={`flex-shrink-0 rounded-lg border p-2.5 transition-all duration-500 ${style.bg} ${
                  style.glow ? `shadow-lg ${style.glow}` : ''
                }`}
                style={{ minWidth: '120px' }}
              >
                <div className={`text-xs font-bold ${style.text} mb-0.5`}>
                  {stage.name}
                </div>
                <div className="text-[10px] text-slate-500">{stage.desc}</div>
                {stage.id === 'calendar' && isCalendarActive && (
                  <div className={`mt-1.5 text-sm font-bold font-mono ${style.text}`}>
                    {currentMultiplier.toFixed(1)}x
                  </div>
                )}
              </div>
              {index < stages.length - 1 && (
                <ArrowRight className={`w-4 h-4 flex-shrink-0 ${
                  stage.id === 'calendar' && isCalendarActive
                    ? 'text-accent-amber animate-pulse'
                    : 'text-slate-600'
                }`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default PamasFlowDiagram;
