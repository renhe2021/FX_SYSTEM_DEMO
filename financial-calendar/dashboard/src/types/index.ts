export type ImpactLevel = 'high' | 'medium' | 'low';
export type SpreadStatus = 'normal' | 'widening' | 'peak' | 'recovering';
export type RomsAction = 'flatten' | 'reduce' | 'monitor';
export type SignalStatus = 'pending' | 'executing' | 'completed';

export interface EconomicEvent {
  eventId: string;
  name: string;
  datetime: string;
  currency: string;
  impact: ImpactLevel;
  forecast?: string;
  previous?: string;
  actual?: string;
  category: string;
  countryCode: string;
  relevance?: number;
  ticker?: string;
}

export interface EventCalendarConfig {
  eventType: string;
  affectedPairs: string[];
  preEventMinutes: number;
  postEventMinutes: number;
  spreadMultiplier: Record<ImpactLevel, number>;
  romsAction: RomsAction;
  flattenPercentage: number;
}

export interface SpreadSnapshot {
  timestamp: number;
  pair: string;
  normalSpread: number;
  currentSpread: number;
  status: SpreadStatus;
  triggerEvent?: string;
  multiplier: number;
}

export interface RomsSignal {
  signalId: string;
  eventId: string;
  pair: string;
  action: RomsAction;
  targetReduction: number;
  status: SignalStatus;
  exposureBefore: number;
  exposureAfter: number;
  executionProgress: number;
}

export interface CurrencyPair {
  pair: string;
  baseCurrency: string;
  quoteCurrency: string;
  normalSpread: number;
  pipPrecision: number;
  region: string;
  currentExposure: number;
}

export interface TimelineState {
  isPlaying: boolean;
  currentTime: number;
  startTime: number;
  endTime: number;
  speed: number;
  selectedEvent: EconomicEvent | null;
}

export interface PamasStage {
  id: string;
  name: string;
  label: string;
  isActive: boolean;
  multiplier?: number;
}
