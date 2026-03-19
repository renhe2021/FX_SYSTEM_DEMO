import React from 'react';
import { EconomicEvent, EventCalendarConfig } from '../types';
import { getConfigForEvent } from '../data/eventConfigs';
import { Settings, Clock, Layers, Zap } from 'lucide-react';

interface EventConfigPanelProps {
  selectedEvent: EconomicEvent | null;
  overrideMultiplier: number | null;
  onOverrideMultiplier: (val: number | null) => void;
}

const EventConfigPanel: React.FC<EventConfigPanelProps> = ({
  selectedEvent, overrideMultiplier, onOverrideMultiplier,
}) => {
  if (!selectedEvent) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 py-8">
        <Settings className="w-8 h-8 mb-2 opacity-30" />
        <p className="text-xs">No event selected</p>
        <p className="text-[10px] text-slate-600">Select an event from the calendar</p>
      </div>
    );
  }

  const config = getConfigForEvent(selectedEvent.category);
  const currentMultiplier = overrideMultiplier ?? config.spreadMultiplier[selectedEvent.impact];

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Settings className="w-4 h-4 text-accent-amber" />
        <h2 className="text-sm font-semibold text-slate-200">Event Configuration</h2>
      </div>

      {/* Event info */}
      <div className="glass-panel p-3 mb-3">
        <h3 className="text-xs font-bold text-slate-200 mb-1">{selectedEvent.name}</h3>
        <div className="flex gap-2 text-[10px] text-slate-400">
          <span>{selectedEvent.currency}</span>
          <span>•</span>
          <span className={`font-semibold ${
            selectedEvent.impact === 'high' ? 'text-accent-red' :
            selectedEvent.impact === 'medium' ? 'text-accent-amber' : 'text-yellow-400'
          }`}>
            {selectedEvent.impact.toUpperCase()} IMPACT
          </span>
        </div>
      </div>

      {/* Affected pairs */}
      <div className="mb-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Layers className="w-3 h-3 text-slate-400" />
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Affected Pairs</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {config.affectedPairs.map(pair => (
            <span
              key={pair}
              className="px-2 py-0.5 rounded bg-primary-500/10 border border-primary-500/20 text-primary-300 text-[10px] font-medium"
            >
              {pair}
            </span>
          ))}
        </div>
      </div>

      {/* Spread multipliers */}
      <div className="mb-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Zap className="w-3 h-3 text-slate-400" />
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Spread Multiplier</span>
        </div>
        <div className="space-y-1.5">
          {(['high', 'medium', 'low'] as const).map(level => {
            const isActive = selectedEvent.impact === level;
            const val = config.spreadMultiplier[level];
            return (
              <div
                key={level}
                className={`flex items-center justify-between p-2 rounded-lg text-xs ${
                  isActive
                    ? 'bg-primary-500/15 border border-primary-500/30'
                    : 'bg-surface-800/50'
                }`}
              >
                <span className={`font-medium ${isActive ? 'text-white' : 'text-slate-500'}`}>
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </span>
                <span className={`font-bold font-mono ${isActive ? 'text-primary-300' : 'text-slate-500'}`}>
                  {val.toFixed(1)}x
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Time windows */}
      <div className="mb-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Clock className="w-3 h-3 text-slate-400" />
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Time Windows</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="glass-panel p-2 text-center">
            <p className="text-[10px] text-slate-500">Pre-Event</p>
            <p className="text-sm font-bold text-accent-amber font-mono">{config.preEventMinutes}m</p>
          </div>
          <div className="glass-panel p-2 text-center">
            <p className="text-[10px] text-slate-500">Post-Event</p>
            <p className="text-sm font-bold text-accent-green font-mono">{config.postEventMinutes}m</p>
          </div>
        </div>
      </div>

      {/* ROMS action */}
      <div className="mb-3">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">ROMS Action</span>
        <div className={`p-2 rounded-lg text-xs font-bold text-center ${
          config.romsAction === 'flatten' ? 'bg-accent-red/15 text-accent-red border border-accent-red/20' :
          config.romsAction === 'reduce' ? 'bg-accent-amber/15 text-accent-amber border border-accent-amber/20' :
          'bg-accent-green/15 text-accent-green border border-accent-green/20'
        }`}>
          {config.romsAction.toUpperCase()} {config.flattenPercentage > 0 ? `(${config.flattenPercentage}%)` : ''}
        </div>
      </div>

      {/* Manual override */}
      <div className="glass-panel p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Manual Override</span>
          {overrideMultiplier !== null && (
            <button
              onClick={() => onOverrideMultiplier(null)}
              className="text-[10px] text-accent-red hover:text-red-300 cursor-pointer"
            >
              Reset
            </button>
          )}
        </div>
        <input
          type="range"
          min="1"
          max="5"
          step="0.1"
          value={currentMultiplier}
          onChange={(e) => onOverrideMultiplier(parseFloat(e.target.value))}
          className="w-full h-1.5 rounded-full appearance-none bg-surface-700 accent-primary-500 cursor-pointer"
        />
        <div className="flex justify-between mt-1 text-[10px] text-slate-500">
          <span>1.0x</span>
          <span className="text-primary-300 font-bold">{currentMultiplier.toFixed(1)}x</span>
          <span>5.0x</span>
        </div>
      </div>
    </div>
  );
};

export default EventConfigPanel;
