import { TimelineState, EconomicEvent } from '../types';
import { getConfigForEvent } from '../data/eventConfigs';

export class TimelineController {
  private state: TimelineState;
  private intervalId: number | null = null;
  private onTick: (state: TimelineState) => void;
  private tickIntervalMs: number = 50; // 50ms tick = 20fps

  constructor(onTick: (state: TimelineState) => void) {
    this.onTick = onTick;
    this.state = {
      isPlaying: false,
      currentTime: 0,
      startTime: 0,
      endTime: 0,
      speed: 1,
      selectedEvent: null,
    };
  }

  /**
   * Initialize the timeline for a specific event.
   * Sets up the time range from T-pre-5min to T+post+5min.
   */
  selectEvent(event: EconomicEvent): void {
    const config = getConfigForEvent(event.category);
    const eventTime = new Date(event.datetime).getTime();
    const preMs = config.preEventMinutes * 60 * 1000;
    const postMs = config.postEventMinutes * 60 * 1000;

    this.stop();

    this.state = {
      isPlaying: false,
      currentTime: eventTime - preMs - 5 * 60 * 1000,
      startTime: eventTime - preMs - 5 * 60 * 1000,
      endTime: eventTime + postMs + 5 * 60 * 1000,
      speed: 60, // 1 second real time = 1 minute sim time
      selectedEvent: event,
    };

    this.onTick(this.state);
  }

  /**
   * Start/resume playback.
   */
  play(): void {
    if (this.state.isPlaying) return;
    this.state.isPlaying = true;

    this.intervalId = window.setInterval(() => {
      const timeStep = (this.tickIntervalMs / 1000) * this.state.speed * 1000;
      this.state.currentTime = Math.min(
        this.state.currentTime + timeStep,
        this.state.endTime
      );

      if (this.state.currentTime >= this.state.endTime) {
        this.pause();
      }

      this.onTick({ ...this.state });
    }, this.tickIntervalMs);

    this.onTick({ ...this.state });
  }

  /**
   * Pause playback.
   */
  pause(): void {
    this.state.isPlaying = false;
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.onTick({ ...this.state });
  }

  /**
   * Toggle play/pause.
   */
  toggle(): void {
    if (this.state.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  /**
   * Stop playback and reset to start.
   */
  stop(): void {
    this.pause();
    this.state.currentTime = this.state.startTime;
    this.onTick({ ...this.state });
  }

  /**
   * Seek to a specific time position.
   */
  seek(time: number): void {
    this.state.currentTime = Math.max(
      this.state.startTime,
      Math.min(time, this.state.endTime)
    );
    this.onTick({ ...this.state });
  }

  /**
   * Set playback speed multiplier.
   */
  setSpeed(speed: number): void {
    this.state.speed = speed;
    this.onTick({ ...this.state });
  }

  /**
   * Get the current progress as a percentage (0-100).
   */
  getProgress(): number {
    const range = this.state.endTime - this.state.startTime;
    if (range <= 0) return 0;
    return ((this.state.currentTime - this.state.startTime) / range) * 100;
  }

  /**
   * Get current state.
   */
  getState(): TimelineState {
    return { ...this.state };
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    this.stop();
  }
}
