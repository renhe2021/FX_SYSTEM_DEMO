import { CurrencyPair } from '../types';

export const currencyPairs: CurrencyPair[] = [
  {
    pair: 'EURUSD',
    baseCurrency: 'EUR',
    quoteCurrency: 'USD',
    normalSpread: 1.2,
    pipPrecision: 5,
    region: 'G10',
    currentExposure: 5200000,
  },
  {
    pair: 'GBPUSD',
    baseCurrency: 'GBP',
    quoteCurrency: 'USD',
    normalSpread: 1.5,
    pipPrecision: 5,
    region: 'G10',
    currentExposure: 3800000,
  },
  {
    pair: 'USDJPY',
    baseCurrency: 'USD',
    quoteCurrency: 'JPY',
    normalSpread: 1.0,
    pipPrecision: 3,
    region: 'G10',
    currentExposure: 4500000,
  },
  {
    pair: 'USDCHF',
    baseCurrency: 'USD',
    quoteCurrency: 'CHF',
    normalSpread: 1.8,
    pipPrecision: 5,
    region: 'G10',
    currentExposure: 2100000,
  },
  {
    pair: 'AUDUSD',
    baseCurrency: 'AUD',
    quoteCurrency: 'USD',
    normalSpread: 1.4,
    pipPrecision: 5,
    region: 'G10',
    currentExposure: 1800000,
  },
  {
    pair: 'USDCAD',
    baseCurrency: 'USD',
    quoteCurrency: 'CAD',
    normalSpread: 1.6,
    pipPrecision: 5,
    region: 'G10',
    currentExposure: 2500000,
  },
  {
    pair: 'EURGBP',
    baseCurrency: 'EUR',
    quoteCurrency: 'GBP',
    normalSpread: 1.3,
    pipPrecision: 5,
    region: 'G10',
    currentExposure: 1500000,
  },
  {
    pair: 'EURJPY',
    baseCurrency: 'EUR',
    quoteCurrency: 'JPY',
    normalSpread: 1.8,
    pipPrecision: 3,
    region: 'G10',
    currentExposure: 2800000,
  },
  {
    pair: 'GBPJPY',
    baseCurrency: 'GBP',
    quoteCurrency: 'JPY',
    normalSpread: 2.2,
    pipPrecision: 3,
    region: 'G10',
    currentExposure: 1200000,
  },
  {
    pair: 'USDCNH',
    baseCurrency: 'USD',
    quoteCurrency: 'CNH',
    normalSpread: 5.0,
    pipPrecision: 4,
    region: 'EM-Asia',
    currentExposure: 8500000,
  },
];

export function getPairsByRegion(region: string): CurrencyPair[] {
  return currencyPairs.filter(p => p.region === region);
}

export function getPairsByCurrency(currency: string): CurrencyPair[] {
  return currencyPairs.filter(
    p => p.baseCurrency === currency || p.quoteCurrency === currency
  );
}
