export interface PositionSample {
  seconds: number;
  receivedAt: number;
}

export const KEYBOARD_STEP_SECONDS = 5;

const MILLISECONDS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;
const END_MARGIN_SECONDS = 0.001;
const TENTHS_PER_SECOND = 10;

export function videoPosition(sample: PositionSample, now: number, running: boolean, duration: number): number {
  if (!running || duration <= 0) {
    return sample.seconds;
  }
  const elapsed = Math.max(0, now - sample.receivedAt) / MILLISECONDS_PER_SECOND;
  return (sample.seconds + elapsed) % duration;
}

export function positionFraction(position: number, duration: number): number {
  return duration > 0 ? Math.min(1, Math.max(0, position / duration)) : 0;
}

export function clampedSeek(seconds: number, duration: number): number {
  return Math.min(Math.max(0, seconds), Math.max(0, duration - END_MARGIN_SECONDS));
}

export function steppedSeek(position: number, direction: 1 | -1, duration: number): number {
  return clampedSeek(position + direction * KEYBOARD_STEP_SECONDS, duration);
}

export function formatClock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(whole / SECONDS_PER_HOUR);
  const minutes = Math.floor((whole % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
  const rest = whole % SECONDS_PER_MINUTE;
  const paddedSeconds = String(rest).padStart(2, "0");
  if (hours === 0) {
    return `${String(minutes)}:${paddedSeconds}`;
  }
  return `${String(hours)}:${String(minutes).padStart(2, "0")}:${paddedSeconds}`;
}

export function formatPreciseClock(seconds: number): string {
  const tenths = Math.floor(Math.max(0, seconds) * TENTHS_PER_SECOND);
  return `${formatClock(tenths / TENTHS_PER_SECOND)}.${String(tenths % TENTHS_PER_SECOND)}`;
}
