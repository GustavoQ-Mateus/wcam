import type { Facing } from "./cam-state";

export interface StageTimes {
  median: number;
  p95: number;
}

export interface PhoneStats {
  at: number;
  outbound: {
    framesPerSecond: number | null;
    framesSent: number | null;
    framesEncoded: number | null;
    keyFramesEncoded: number | null;
    bytesSent: number | null;
    qualityLimitationReason: string | null;
    nackCount: number | null;
    pliCount: number | null;
    frameWidth: number | null;
    frameHeight: number | null;
  } | null;
  remoteInbound: { roundTripTime: number | null; jitter: number | null; packetsLost: number | null } | null;
}

export interface DevMetrics {
  at: string;
  session: {
    state: string;
    liveSince: string | null;
    deviceName: string | null;
    facing: Facing | null;
    format: string;
    codec: string | null;
  } | null;
  received: { fps: number; bitrateKbps: number; packetsLost: number; jitterMs: number } | null;
  delivered: { fps: number; frames: number; dropped: number } | null;
  stages: { decode: StageTimes; color: StageTimes; deliver: StageTimes; total: StageTimes } | null;
  frameTimesMs: number[] | null;
  budgetMs: number;
  ceilingKbps: number;
  virtualCamera: { format: string; pendingFormat: string | null; streamingApps: number | null; source: string };
  process: { cpuPercent: number };
  phone: PhoneStats | null;
}

export interface DevEvent {
  at: string;
  kind: string;
  data: Record<string, unknown>;
}

export type Health = "ok" | "attention";

export interface HealthValue {
  value: number | null;
  health: Health;
}

export interface HealthStrip {
  fpsDelivered: HealthValue;
  bitrateMbps: HealthValue;
  processingP95: HealthValue;
  packetsLost: HealthValue;
  cpuPercent: HealthValue;
  roundTripMs: HealthValue;
}

export const MAX_SAMPLES = 600;
export const MAX_EVENTS = 50;
const KILOBITS_PER_MEGABIT = 1000;
const MILLISECONDS_PER_SECOND = 1000;
const FPS_HEALTHY_SHARE = 0.9;
const PROCESSING_HEALTHY_SHARE = 0.5;
const CPU_ATTENTION_PERCENT = 50;
const ROUND_TRIP_ATTENTION_MS = 100;
const NICE_STEPS = [1, 2, 2.5, 5, 10];
const COORDINATE_PRECISION = 10;
const CSV_COLUMNS = [
  "at",
  "received_fps",
  "received_kbps",
  "packets_lost",
  "jitter_ms",
  "delivered_fps",
  "delivered_frames",
  "dropped_frames",
  "decode_median_ms",
  "decode_p95_ms",
  "color_median_ms",
  "color_p95_ms",
  "deliver_median_ms",
  "deliver_p95_ms",
  "total_median_ms",
  "total_p95_ms",
  "cpu_percent",
  "phone_fps",
  "round_trip_ms",
  "phone_jitter_ms",
] as const;

export function appendSample<T>(samples: readonly T[], sample: T, limit: number): T[] {
  return [...samples, sample].slice(-limit);
}

export function lastSeconds<T>(samples: readonly T[], seconds: number): T[] {
  return samples.slice(-seconds);
}

export function roundTripMs(metrics: DevMetrics): number | null {
  const seconds = metrics.phone?.remoteInbound?.roundTripTime;
  return seconds === null || seconds === undefined ? null : seconds * MILLISECONDS_PER_SECOND;
}

export function phoneJitterMs(metrics: DevMetrics): number | null {
  const seconds = metrics.phone?.remoteInbound?.jitter;
  return seconds === null || seconds === undefined ? null : seconds * MILLISECONDS_PER_SECOND;
}

export function bitrateMbps(metrics: DevMetrics): number | null {
  return metrics.received ? metrics.received.bitrateKbps / KILOBITS_PER_MEGABIT : null;
}

export function healthStrip(metrics: DevMetrics, formatFps: number, packetsLostInWindow: number | null): HealthStrip {
  const fps = metrics.delivered?.fps ?? null;
  const p95 = metrics.stages?.total.p95 ?? null;
  const roundTrip = roundTripMs(metrics);
  return {
    fpsDelivered: measured(fps, (value) => value >= formatFps * FPS_HEALTHY_SHARE),
    bitrateMbps: measured(bitrateMbps(metrics), (value) => value > 0),
    processingP95: measured(p95, (value) => value <= metrics.budgetMs * PROCESSING_HEALTHY_SHARE),
    packetsLost: measured(packetsLostInWindow, (value) => value === 0),
    cpuPercent: measured(metrics.process.cpuPercent, (value) => value < CPU_ATTENTION_PERCENT),
    roundTripMs: measured(roundTrip, (value) => value < ROUND_TRIP_ATTENTION_MS),
  };
}

export function packetsLostIn(samples: readonly DevMetrics[]): number | null {
  const counted = samples.filter((sample) => sample.received !== null);
  if (counted.length === 0) {
    return null;
  }
  return counted.reduce((total, sample) => total + (sample.received?.packetsLost ?? 0), 0);
}

export function niceCeiling(value: number): number {
  if (!(value > 0)) {
    return 1;
  }
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = NICE_STEPS.find((candidate) => candidate * magnitude >= value) ?? NICE_STEPS[NICE_STEPS.length - 1];
  return (step ?? 1) * magnitude;
}

export function lineSegments(values: readonly (number | null)[], width: number, height: number, max: number): string[] {
  const segments: string[] = [];
  let current: string[] = [];
  const stepX = values.length > 1 ? width / (values.length - 1) : 0;
  values.forEach((value, index) => {
    if (value === null) {
      if (current.length > 0) {
        segments.push(current.join(" "));
      }
      current = [];
      return;
    }
    current.push(`${round(index * stepX)},${round(height - (Math.min(value, max) / max) * height)}`);
  });
  if (current.length > 0) {
    segments.push(current.join(" "));
  }
  return segments;
}

export function stackedBands(
  layers: readonly (readonly number[])[],
  width: number,
  height: number,
  max: number,
): string[] {
  const count = layers[0]?.length ?? 0;
  const stepX = count > 1 ? width / (count - 1) : 0;
  const totals = new Array<number>(count).fill(0);
  return layers.map((layer) => {
    const lower = [...totals];
    layer.forEach((value, index) => {
      totals[index] = (totals[index] ?? 0) + value;
    });
    const y = (value: number) => round(height - (Math.min(value, max) / max) * height);
    const top = totals.map((total, index) => `${round(index * stepX)},${y(total)}`);
    const bottom = lower.map((total, index) => `${round(index * stepX)},${y(total)}`).reverse();
    return [...top, ...bottom].join(" ");
  });
}

export function histogram(values: readonly number[], binMs: number, maxMs: number): number[] {
  const bins = new Array<number>(Math.ceil(maxMs / binMs)).fill(0);
  values.forEach((value) => {
    const index = Math.min(bins.length - 1, Math.max(0, Math.floor(value / binMs)));
    bins[index] = (bins[index] ?? 0) + 1;
  });
  return bins;
}

export function percentile(values: readonly number[], share: number): number | null {
  if (values.length === 0) {
    return null;
  }
  const sorted = [...values].sort((first, second) => first - second);
  return sorted[Math.min(sorted.length - 1, Math.ceil(share * sorted.length) - 1)] ?? null;
}

export function keyFrameIntervalSeconds(samples: readonly DevMetrics[]): number | null {
  const counts = samples
    .map((sample) => sample.phone?.outbound?.keyFramesEncoded)
    .filter((count): count is number => typeof count === "number");
  const first = counts[0];
  const last = counts[counts.length - 1];
  if (first === undefined || last === undefined || last <= first) {
    return null;
  }
  return (counts.length - 1) / (last - first);
}

export function metricsCsv(samples: readonly DevMetrics[]): string {
  const rows = samples.map((sample) => csvRow(sample).map(csvValue).join(","));
  return [CSV_COLUMNS.join(","), ...rows].join("\n");
}

function csvRow(sample: DevMetrics): (string | number | null)[] {
  const { received, delivered, stages } = sample;
  return [
    sample.at,
    received?.fps ?? null,
    received?.bitrateKbps ?? null,
    received?.packetsLost ?? null,
    received?.jitterMs ?? null,
    delivered?.fps ?? null,
    delivered?.frames ?? null,
    delivered?.dropped ?? null,
    stages?.decode.median ?? null,
    stages?.decode.p95 ?? null,
    stages?.color.median ?? null,
    stages?.color.p95 ?? null,
    stages?.deliver.median ?? null,
    stages?.deliver.p95 ?? null,
    stages?.total.median ?? null,
    stages?.total.p95 ?? null,
    sample.process.cpuPercent,
    sample.phone?.outbound?.framesPerSecond ?? null,
    roundTripMs(sample),
    phoneJitterMs(sample),
  ];
}

function csvValue(value: string | number | null): string {
  return value === null ? "" : String(value);
}

function measured(value: number | null, healthy: (value: number) => boolean): HealthValue {
  return { value, health: value === null || healthy(value) ? "ok" : "attention" };
}

function round(value: number): number {
  return Math.round(value * COORDINATE_PRECISION) / COORDINATE_PRECISION;
}
