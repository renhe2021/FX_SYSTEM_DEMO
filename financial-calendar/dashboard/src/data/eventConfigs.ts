import { EventCalendarConfig } from '../types';

export const eventConfigs: Record<string, EventCalendarConfig> = {
  'Employment': {
    eventType: 'Employment',
    affectedPairs: ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD'],
    preEventMinutes: 30,
    postEventMinutes: 15,
    spreadMultiplier: { high: 3.0, medium: 2.0, low: 1.5 },
    romsAction: 'flatten',
    flattenPercentage: 100,
  },
  'Interest Rate': {
    eventType: 'Interest Rate',
    affectedPairs: ['EURUSD', 'GBPUSD', 'USDJPY', 'EURGBP', 'EURJPY'],
    preEventMinutes: 30,
    postEventMinutes: 15,
    spreadMultiplier: { high: 3.0, medium: 2.0, low: 1.5 },
    romsAction: 'flatten',
    flattenPercentage: 100,
  },
  'Inflation': {
    eventType: 'Inflation',
    affectedPairs: ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF'],
    preEventMinutes: 15,
    postEventMinutes: 10,
    spreadMultiplier: { high: 2.5, medium: 2.0, low: 1.5 },
    romsAction: 'reduce',
    flattenPercentage: 50,
  },
  'GDP': {
    eventType: 'GDP',
    affectedPairs: ['GBPUSD', 'EURGBP', 'GBPJPY'],
    preEventMinutes: 15,
    postEventMinutes: 10,
    spreadMultiplier: { high: 2.5, medium: 2.0, low: 1.5 },
    romsAction: 'reduce',
    flattenPercentage: 50,
  },
  'PMI': {
    eventType: 'PMI',
    affectedPairs: ['EURUSD', 'EURGBP', 'EURJPY', 'EURCHF'],
    preEventMinutes: 10,
    postEventMinutes: 10,
    spreadMultiplier: { high: 2.0, medium: 1.8, low: 1.3 },
    romsAction: 'reduce',
    flattenPercentage: 30,
  },
  'Consumer': {
    eventType: 'Consumer',
    affectedPairs: ['EURUSD', 'USDJPY'],
    preEventMinutes: 5,
    postEventMinutes: 5,
    spreadMultiplier: { high: 1.8, medium: 1.5, low: 1.2 },
    romsAction: 'monitor',
    flattenPercentage: 0,
  },
};

export function getConfigForEvent(category: string): EventCalendarConfig {
  return eventConfigs[category] || eventConfigs['Consumer'];
}
