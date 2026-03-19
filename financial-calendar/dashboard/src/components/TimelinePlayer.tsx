import React from 'react';
import { Play, Pause, RotateCcw, Zap } from 'lucide-react';
import { TimelineState, EconomicEvent } from '../types';
import { getConfigForEvent } from '../data/eventConfigs';

interface TimelinePlayerProps {
  state: TimelineState;
  onToggle: () => void;
  onReset: () => void;
  onSeek: (time: number) => void;
  onSpeedChange: (speed: number) => void;
}

const speeds = [30, 60, 120, 300];
const speedLabels = ['0.5x', '1x', '2x', '5x'];

const TimelinePlayer: React.FC<TimelinePlayerProps> = ({
  state, onToggle, onReset, onSeek, onSpeedChange,
}) => {
  const { isPlaying, currentTime, startTime, endTime, speed, selectedEvent } = state;

  const progress = endTime > startTime
    ? ((currentTime - startTime) / (endTime - startTime)) * 100
    : 0;

  const formatRelativeTime = (ts: number) => {
    if (!selectedEvent) return '';
    const eventTime = new Date(selectedEvent.datetime).getTime();
    const diff = ts - eventTime;
    const mins = Math.round(diff / 60000);
    if (mins === 0) return 'T-0';
    return mins > 0 ? `T+${mins}m` : `T${mins}m`;
  };

  const getEventMarkerPosition = () => {
    if (!selectedEvent) return 50;
    const eventTime = new Date(selectedEvent.datetime).getTime();
    return ((eventTime - startTime) / (endTime - startTime)) * 100;
  };

  const getPhaseGradient = () => {
    if (!selectedEvent) return 'bg-surface-700';
    const config = getConfigForEvent(selectedEvent.category);
    const eventTime = new Date(selectedEvent.datetime).getTime();
    const preStart = eventTime - config.preEventMinutes * 60000;
    const postEnd = eventTime + config.postEventMinutes * 60000;
    const range = endTime - startTime;

    const preStartPct = ((preStart - startTime) / range) * 100;
    const eventPct = ((eventTime - startTime) / range) * 100;
    const postEndPct = ((postEnd - startTime) / range) * 100;

    return `linear-gradient(to right, 
      #22C55E00 0%, #22C55E30 ${preStartPct}%, 
      #F59E0B40 ${preStartPct}%, #EF444460 ${eventPct}%, 
      #F59E0B40 ${eventPct}%, #22C55E30 ${postEndPct}%, 
      #22C55E00 100%)`;
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const time = startTime + pct * (endTime - startTime);
    onSeek(time);
  };

  return (
    <div className="glass-panel p-3 mx-4">
      <div className="flex items-center gap-4">
        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggle}
            className="w-9 h-9 rounded-full bg-primary-500 hover:bg-primary-400 flex items-center justify-center transition-all duration-200 hover:shadow-lg hover:shadow-primary-500/30 cursor-pointer"
          >
            {isPlaying
              ? <Pause className="w-4 h-4 text-white" />
              : <Play className="w-4 h-4 text-white ml-0.5" />
            }
          </button>
          <button
            onClick={onReset}
            className="w-7 h-7 rounded-full bg-surface-700 hover:bg-surface-600 flex items-center justify-center transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
          </button>
        </div>

        {/* Timeline */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-slate-500 font-mono">{formatRelativeTime(startTime)}</span>
            <span className="text-xs font-semibold text-primary-400 font-mono">
              {formatRelativeTime(currentTime)}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">{formatRelativeTime(endTime)}</span>
          </div>

          <div
            className="relative h-6 rounded-full bg-surface-700 overflow-hidden cursor-pointer group"
            onClick={handleProgressClick}
            style={{ background: getPhaseGradient() }}
          >
            {/* Progress bar */}
            <div
              className="absolute top-0 left-0 h-full bg-primary-500/30 transition-all duration-75"
              style={{ width: `${progress}%` }}
            />

            {/* Event marker */}
            <div
              className="absolute top-0 h-full w-0.5 bg-accent-red z-10"
              style={{ left: `${getEventMarkerPosition()}%` }}
            >
              <div className="absolute -top-0.5 left-1/2 -translate-x-1/2">
                <Zap className="w-3 h-3 text-accent-red" />
              </div>
            </div>

            {/* Playhead */}
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white shadow-lg shadow-white/30 z-20 transition-all duration-75"
              style={{ left: `calc(${progress}% - 6px)` }}
            />
          </div>

          {/* Phase labels */}
          <div className="flex justify-between mt-1">
            <span className="text-[9px] text-accent-green/70">NORMAL</span>
            <span className="text-[9px] text-accent-amber/70">PRE-EVENT</span>
            <span className="text-[9px] text-accent-red/70">PEAK</span>
            <span className="text-[9px] text-accent-amber/70">RECOVERY</span>
            <span className="text-[9px] text-accent-green/70">NORMAL</span>
          </div>
        </div>

        {/* Speed selector */}
        <div className="flex items-center gap-1">
          {speeds.map((s, i) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`px-2 py-1 rounded text-[10px] font-semibold transition-colors cursor-pointer ${
                speed === s
                  ? 'bg-primary-500/30 text-primary-300 border border-primary-500/30'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-surface-700'
              }`}
            >
              {speedLabels[i]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TimelinePlayer;
