import { SpreadSnapshot, EconomicEvent, ImpactLevel, SpreadStatus } from '../types';
import { getConfigForEvent } from '../data/eventConfigs';
import { currencyPairs } from '../data/currencyPairs';

export class PriceSimulator {
  /**
   * Calculate spread snapshots for a given event over the simulation timeline.
   * Generates data points from T-pre to T+post for each affected currency pair.
   */
  static generateSpreadTimeline(
    event: EconomicEvent,
    intervalSeconds: number = 30
  ): SpreadSnapshot[] {
    const config = getConfigForEvent(event.category);
    const eventTime = new Date(event.datetime).getTime();
    const preMs = config.preEventMinutes * 60 * 1000;
    const postMs = config.postEventMinutes * 60 * 1000;
    const startTime = eventTime - preMs - 5 * 60 * 1000; // extra 5 min before
    const endTime = eventTime + postMs + 5 * 60 * 1000;   // extra 5 min after
    const step = intervalSeconds * 1000;
    const snapshots: SpreadSnapshot[] = [];

    const affectedPairs = currencyPairs.filter(cp =>
      config.affectedPairs.includes(cp.pair)
    );

    for (let t = startTime; t <= endTime; t += step) {
      for (const cp of affectedPairs) {
        const { multiplier, status } = PriceSimulator.calculateMultiplier(
          t, eventTime, preMs, postMs, config.spreadMultiplier[event.impact]
        );

        snapshots.push({
          timestamp: t,
          pair: cp.pair,
          normalSpread: cp.normalSpread,
          currentSpread: cp.normalSpread * multiplier,
          status,
          triggerEvent: event.eventId,
          multiplier,
        });
      }
    }

    return snapshots;
  }

  /**
   * Calculate the spread multiplier and status for a given point in time.
   */
  static calculateMultiplier(
    currentTime: number,
    eventTime: number,
    preMs: number,
    postMs: number,
    maxMultiplier: number
  ): { multiplier: number; status: SpreadStatus } {
    const preStart = eventTime - preMs;
    const postEnd = eventTime + postMs;

    if (currentTime < preStart) {
      return { multiplier: 1.0, status: 'normal' };
    }

    if (currentTime >= preStart && currentTime < eventTime) {
      // Pre-event widening: linear ramp up
      const progress = (currentTime - preStart) / preMs;
      const eased = easeInOut(progress);
      const multiplier = 1.0 + (maxMultiplier - 1.0) * eased;
      return { multiplier, status: 'widening' };
    }

    if (currentTime >= eventTime && currentTime < eventTime + 60000) {
      // Peak: 1 minute window at max
      return { multiplier: maxMultiplier, status: 'peak' };
    }

    if (currentTime >= eventTime + 60000 && currentTime <= postEnd) {
      // Post-event recovery: exponential decay
      const elapsed = currentTime - eventTime - 60000;
      const total = postMs - 60000;
      const progress = Math.min(elapsed / Math.max(total, 1), 1);
      const eased = easeOutExpo(progress);
      const multiplier = maxMultiplier - (maxMultiplier - 1.0) * eased;
      return { multiplier: Math.max(multiplier, 1.0), status: 'recovering' };
    }

    return { multiplier: 1.0, status: 'normal' };
  }

  /**
   * Get current spread for a specific pair at a specific time.
   */
  static getCurrentSpread(
    pair: string,
    currentTime: number,
    event: EconomicEvent
  ): SpreadSnapshot {
    const config = getConfigForEvent(event.category);
    const eventTime = new Date(event.datetime).getTime();
    const preMs = config.preEventMinutes * 60 * 1000;
    const postMs = config.postEventMinutes * 60 * 1000;
    const cp = currencyPairs.find(c => c.pair === pair);
    const normalSpread = cp?.normalSpread || 1.5;
    const maxMultiplier = config.spreadMultiplier[event.impact];

    const { multiplier, status } = PriceSimulator.calculateMultiplier(
      currentTime, eventTime, preMs, postMs, maxMultiplier
    );

    return {
      timestamp: currentTime,
      pair,
      normalSpread,
      currentSpread: normalSpread * multiplier,
      status,
      triggerEvent: event.eventId,
      multiplier,
    };
  }
}

// Easing functions for smooth transitions
function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

function easeOutExpo(t: number): number {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}
