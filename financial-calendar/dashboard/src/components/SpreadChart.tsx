import React, { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceArea,
} from 'recharts';
import { SpreadSnapshot, EconomicEvent } from '../types';
import { TrendingUp } from 'lucide-react';

interface SpreadChartProps {
  snapshots: SpreadSnapshot[];
  selectedEvent: EconomicEvent | null;
  currentTime: number;
  selectedPairs: string[];
}

const pairColors: Record<string, string> = {
  EURUSD: '#3B82F6',
  GBPUSD: '#8B5CF6',
  USDJPY: '#F59E0B',
  USDCHF: '#22C55E',
  AUDUSD: '#EC4899',
  USDCAD: '#06B6D4',
  EURGBP: '#F97316',
  EURJPY: '#A855F7',
  GBPJPY: '#14B8A6',
  USDCNH: '#EF4444',
};

const SpreadChart: React.FC<SpreadChartProps> = ({
  snapshots, selectedEvent, currentTime, selectedPairs,
}) => {
  const chartData = useMemo(() => {
    if (!snapshots.length) return [];

    const timeGroups = new Map<number, Record<string, number>>();

    for (const snap of snapshots) {
      if (!selectedPairs.includes(snap.pair)) continue;
      if (!timeGroups.has(snap.timestamp)) {
        timeGroups.set(snap.timestamp, { timestamp: snap.timestamp });
      }
      const group = timeGroups.get(snap.timestamp)!;
      group[snap.pair] = snap.currentSpread;
      group[`${snap.pair}_normal`] = snap.normalSpread;
    }

    return Array.from(timeGroups.values()).sort(
      (a, b) => (a.timestamp as number) - (b.timestamp as number)
    );
  }, [snapshots, selectedPairs]);

  const eventTime = selectedEvent
    ? new Date(selectedEvent.datetime).getTime()
    : 0;

  const formatXTick = (ts: number) => {
    if (!eventTime) return '';
    const diff = ts - eventTime;
    const mins = Math.round(diff / 60000);
    if (mins === 0) return 'T-0';
    return mins > 0 ? `T+${mins}` : `T${mins}`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="glass-panel p-2.5 border border-white/10 text-xs">
        <p className="text-slate-400 mb-1.5 font-mono">{formatXTick(label)}</p>
        {payload.map((entry: any) => (
          <div key={entry.dataKey} className="flex items-center gap-2 mb-0.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-slate-300">{entry.dataKey}:</span>
            <span className="text-white font-semibold">{entry.value?.toFixed(1)} pips</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary-400" />
          <h2 className="text-sm font-semibold text-slate-200">Spread Timeline</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {selectedPairs.map(pair => (
            <span
              key={pair}
              className="px-2 py-0.5 rounded text-[10px] font-semibold"
              style={{
                backgroundColor: `${pairColors[pair]}20`,
                color: pairColors[pair],
                border: `1px solid ${pairColors[pair]}40`,
              }}
            >
              {pair}
            </span>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXTick}
              tick={{ fill: '#64748B', fontSize: 10 }}
              axisLine={{ stroke: '#334155' }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#64748B', fontSize: 10 }}
              axisLine={{ stroke: '#334155' }}
              label={{ value: 'Spread (pips)', angle: -90, position: 'insideLeft', fill: '#64748B', fontSize: 10 }}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Event marker */}
            {eventTime > 0 && (
              <ReferenceLine
                x={eventTime}
                stroke="#EF4444"
                strokeDasharray="4 4"
                label={{ value: 'EVENT', fill: '#EF4444', fontSize: 10, position: 'top' }}
              />
            )}

            {/* Current time marker */}
            {currentTime > 0 && (
              <ReferenceLine
                x={currentTime}
                stroke="#FFFFFF"
                strokeWidth={2}
                strokeOpacity={0.6}
              />
            )}

            {/* Spread lines for each pair */}
            {selectedPairs.map(pair => (
              <Line
                key={pair}
                type="monotone"
                dataKey={pair}
                stroke={pairColors[pair] || '#94A3B8'}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: pairColors[pair] }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SpreadChart;
