import { RomsSignal, EconomicEvent, RomsAction, SignalStatus } from '../types';
import { getConfigForEvent } from '../data/eventConfigs';
import { currencyPairs } from '../data/currencyPairs';

let signalCounter = 0;

export class SignalEngine {
  /**
   * Generate ROMS signals for a given event at the trigger time.
   * Returns signals for each affected currency pair.
   */
  static generateSignals(event: EconomicEvent): RomsSignal[] {
    const config = getConfigForEvent(event.category);
    const signals: RomsSignal[] = [];

    const affectedPairs = currencyPairs.filter(cp =>
      config.affectedPairs.includes(cp.pair)
    );

    for (const cp of affectedPairs) {
      signalCounter++;
      const reductionPct = config.flattenPercentage / 100;

      signals.push({
        signalId: `SIG-${String(signalCounter).padStart(4, '0')}`,
        eventId: event.eventId,
        pair: cp.pair,
        action: config.romsAction,
        targetReduction: config.flattenPercentage,
        status: 'pending',
        exposureBefore: cp.currentExposure,
        exposureAfter: cp.currentExposure * (1 - reductionPct),
        executionProgress: 0,
      });
    }

    return signals;
  }

  /**
   * Simulate signal execution progress over time.
   * Returns updated signals with progress based on elapsed time since trigger.
   */
  static updateSignalProgress(
    signals: RomsSignal[],
    elapsedMs: number,
    executionDurationMs: number = 120000 // 2 minutes to fully execute
  ): RomsSignal[] {
    const progress = Math.min(elapsedMs / executionDurationMs, 1);

    return signals.map(signal => {
      if (signal.action === 'monitor') {
        return { ...signal, status: 'completed' as SignalStatus, executionProgress: 100 };
      }

      let status: SignalStatus = 'pending';
      let executionProgress = 0;

      if (progress <= 0) {
        status = 'pending';
        executionProgress = 0;
      } else if (progress < 1) {
        status = 'executing';
        executionProgress = Math.round(progress * 100);
      } else {
        status = 'completed';
        executionProgress = 100;
      }

      const currentReduction = (signal.targetReduction / 100) * (executionProgress / 100);
      const exposureAfter = signal.exposureBefore * (1 - currentReduction);

      return {
        ...signal,
        status,
        executionProgress,
        exposureAfter,
      };
    });
  }

  /**
   * Get action label and color for display.
   */
  static getActionDisplay(action: RomsAction): { label: string; color: string } {
    switch (action) {
      case 'flatten':
        return { label: '全量平仓', color: '#EF4444' };
      case 'reduce':
        return { label: '部分减仓', color: '#F59E0B' };
      case 'monitor':
        return { label: '仅监控', color: '#22C55E' };
    }
  }
}
