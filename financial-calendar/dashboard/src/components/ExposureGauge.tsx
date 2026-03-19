import React from 'react';

interface ExposureGaugeProps {
  pair: string;
  currentExposure: number;
  maxExposure: number;
  targetExposure?: number;
  isReducing: boolean;
}

const ExposureGauge: React.FC<ExposureGaugeProps> = ({
  pair, currentExposure, maxExposure, targetExposure, isReducing,
}) => {
  const percentage = Math.min((currentExposure / maxExposure) * 100, 100);
  const targetPct = targetExposure !== undefined
    ? Math.min((targetExposure / maxExposure) * 100, 100)
    : percentage;

  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - percentage / 100);
  const targetOffset = circumference * (1 - targetPct / 100);

  const getColor = () => {
    if (isReducing) return '#F59E0B';
    if (percentage > 75) return '#EF4444';
    if (percentage > 50) return '#F59E0B';
    return '#22C55E';
  };

  const formatExposure = (val: number) => {
    if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
    if (val >= 1e3) return `${(val / 1e3).toFixed(0)}K`;
    return val.toFixed(0);
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 96 96">
          {/* Background circle */}
          <circle
            cx="48" cy="48" r={radius}
            fill="none"
            stroke="#1E293B"
            strokeWidth="6"
          />
          {/* Target indicator (if reducing) */}
          {isReducing && targetExposure !== undefined && (
            <circle
              cx="48" cy="48" r={radius}
              fill="none"
              stroke="#22C55E"
              strokeWidth="6"
              strokeDasharray={circumference}
              strokeDashoffset={targetOffset}
              strokeLinecap="round"
              opacity={0.3}
            />
          )}
          {/* Current value */}
          <circle
            cx="48" cy="48" r={radius}
            fill="none"
            stroke={getColor()}
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700"
            style={{
              filter: `drop-shadow(0 0 6px ${getColor()}50)`,
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[10px] text-slate-400 font-semibold">{pair}</span>
          <span className="text-sm font-bold font-mono text-white">
            {formatExposure(currentExposure)}
          </span>
        </div>
      </div>
      {isReducing && targetExposure !== undefined && (
        <div className="mt-1 text-[9px] text-accent-amber animate-pulse">
          → {formatExposure(targetExposure)}
        </div>
      )}
    </div>
  );
};

export default ExposureGauge;
