import React from 'react';
import { Activity, Radio, Shield } from 'lucide-react';
import { SpreadStatus } from '../types';

interface HeaderProps {
  currentTime: number;
  calendarStatus: 'connected' | 'warning' | 'offline';
  pamasStatus: SpreadStatus;
  romsStatus: 'idle' | 'executing' | 'completed';
}

const Header: React.FC<HeaderProps> = ({ currentTime, calendarStatus, pamasStatus, romsStatus }) => {
  const formatTime = (ts: number) => {
    if (!ts) return '--:--:--';
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (ts: number) => {
    if (!ts) return '----/--/--';
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' });
  };

  const getStatusDot = (type: string, status: string) => {
    let className = 'status-dot';
    if (type === 'calendar') {
      className += status === 'connected' ? ' status-dot-active' : status === 'warning' ? ' status-dot-warning' : ' status-dot-danger';
    } else if (type === 'pamas') {
      className += (status === 'normal') ? ' status-dot-active' : (status === 'peak' || status === 'widening') ? ' status-dot-warning' : ' status-dot-active';
    } else {
      className += status === 'idle' ? ' status-dot-active' : status === 'executing' ? ' status-dot-warning' : ' status-dot-active';
    }
    return className;
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-gradient-to-r from-surface-900 via-surface-800 to-surface-900 border-b border-white/5 flex items-center px-6">
      {/* Left: Title */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-indigo flex items-center justify-center">
          <Activity className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-slate-100 tracking-wide">Financial Calendar System</h1>
          <p className="text-[10px] text-slate-500 -mt-0.5">PAMAS × ROMS Integration Demo</p>
        </div>
      </div>

      {/* Center: Clock */}
      <div className="flex-1 flex justify-center">
        <div className="text-center">
          <div className="text-2xl font-bold font-mono text-slate-100 neon-text tracking-wider">
            {formatTime(currentTime)}
          </div>
          <div className="text-[10px] text-slate-500 tracking-widest">
            {formatDate(currentTime)} UTC
          </div>
        </div>
      </div>

      {/* Right: Status indicators */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2">
          <div className={getStatusDot('calendar', calendarStatus)} />
          <span className="text-xs text-slate-400">Calendar</span>
        </div>
        <div className="flex items-center gap-2">
          <div className={getStatusDot('pamas', pamasStatus)} />
          <span className="text-xs text-slate-400">PAMAS</span>
        </div>
        <div className="flex items-center gap-2">
          <div className={getStatusDot('roms', romsStatus)} />
          <span className="text-xs text-slate-400">ROMS</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
