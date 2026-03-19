import React from 'react';
import { EconomicEvent } from '../types';
import { Calendar, Clock, TrendingUp } from 'lucide-react';

interface CalendarViewProps {
  events: EconomicEvent[];
  selectedEvent: EconomicEvent | null;
  onSelectEvent: (event: EconomicEvent) => void;
}

const flagEmoji: Record<string, string> = {
  US: '🇺🇸', EU: '🇪🇺', GB: '🇬🇧', JP: '🇯🇵', CN: '🇨🇳', AU: '🇦🇺', CA: '🇨🇦', CH: '🇨🇭',
};

const CalendarView: React.FC<CalendarViewProps> = ({ events, selectedEvent, onSelectEvent }) => {
  const sortedEvents = [...events].sort(
    (a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime()
  );

  const formatEventTime = (dt: string) => {
    const d = new Date(dt);
    return d.toLocaleString('en-US', {
      month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
      hour12: false,
    });
  };

  const getImpactClass = (impact: string) => {
    switch (impact) {
      case 'high': return 'impact-high';
      case 'medium': return 'impact-medium';
      case 'low': return 'impact-low';
      default: return 'impact-low';
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <Calendar className="w-4 h-4 text-primary-400" />
        <h2 className="text-sm font-semibold text-slate-200">Economic Calendar</h2>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {sortedEvents.map(event => {
          const isSelected = selectedEvent?.eventId === event.eventId;
          return (
            <button
              key={event.eventId}
              onClick={() => onSelectEvent(event)}
              className={`w-full text-left p-3 rounded-lg transition-all duration-200 cursor-pointer group ${
                isSelected
                  ? 'bg-primary-500/15 border border-primary-500/40 shadow-lg shadow-primary-500/10'
                  : 'bg-surface-800/60 border border-transparent hover:border-white/10 hover:bg-surface-700/50'
              }`}
            >
              <div className="flex items-start justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{flagEmoji[event.countryCode] || '🏳️'}</span>
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">
                    {event.name}
                  </span>
                </div>
                <span className={getImpactClass(event.impact)}>
                  {event.impact}
                </span>
              </div>

              <div className="flex items-center gap-3 text-[11px] text-slate-400">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatEventTime(event.datetime)}
                </div>
                <span className="text-slate-600">|</span>
                <span className="text-primary-400 font-medium">{event.currency}</span>
              </div>

              {(event.forecast || event.previous) && (
                <div className="flex gap-4 mt-2 text-[10px]">
                  {event.forecast && (
                    <span className="text-slate-500">
                      Fcst: <span className="text-slate-300">{event.forecast}</span>
                    </span>
                  )}
                  {event.previous && (
                    <span className="text-slate-500">
                      Prev: <span className="text-slate-300">{event.previous}</span>
                    </span>
                  )}
                  {event.actual && (
                    <span className="text-slate-500">
                      Act: <span className="text-accent-green font-medium">{event.actual}</span>
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default CalendarView;
