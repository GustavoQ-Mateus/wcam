import { bitrateMbps, phoneJitterMs, roundTripMs, type DevEvent, type DevMetrics } from "./dev-metrics";

export interface ChartMark {
  share: number;
  kind: "event" | "loss";
}

export interface DevCharts {
  phoneFps: (number | null)[];
  deliveredFps: (number | null)[];
  bitrate: (number | null)[];
  roundTrip: (number | null)[];
  jitter: (number | null)[];
  decode: number[];
  color: number[];
  deliver: number[];
  eventMarks: ChartMark[];
  lossMarks: ChartMark[];
}

export interface StageMedian {
  stage: "phone" | "wifi" | "decode" | "color" | "deliver" | "apps";
  milliseconds: number | null;
}

const HALF = 2;
const SECONDS_PER_MINUTE = 60;
const MILLISECONDS_PER_SECOND = 1000;
const TWO_DIGITS = 2;

export function devCharts(samples: readonly DevMetrics[], events: readonly DevEvent[]): DevCharts {
  return {
    phoneFps: samples.map((sample) => sample.phone?.outbound?.framesPerSecond ?? null),
    deliveredFps: samples.map((sample) => sample.delivered?.fps ?? null),
    bitrate: samples.map(bitrateMbps),
    roundTrip: samples.map(roundTripMs),
    jitter: samples.map(phoneJitterMs),
    decode: samples.map((sample) => sample.stages?.decode.p95 ?? 0),
    color: samples.map((sample) => sample.stages?.color.p95 ?? 0),
    deliver: samples.map((sample) => sample.stages?.deliver.p95 ?? 0),
    eventMarks: eventMarks(samples, events),
    lossMarks: lossMarks(samples),
  };
}

export function stageMedians(latest: DevMetrics | undefined): StageMedian[] {
  const roundTrip = latest ? roundTripMs(latest) : null;
  const stages = latest?.stages ?? null;
  return [
    { stage: "phone", milliseconds: null },
    { stage: "wifi", milliseconds: roundTrip === null ? null : roundTrip / HALF },
    { stage: "decode", milliseconds: stages?.decode.median ?? null },
    { stage: "color", milliseconds: stages?.color.median ?? null },
    { stage: "deliver", milliseconds: stages?.deliver.median ?? null },
    { stage: "apps", milliseconds: null },
  ];
}

export function liveDuration(since: string, at: string): string {
  const seconds = Math.max(0, Math.floor((Date.parse(at) - Date.parse(since)) / MILLISECONDS_PER_SECOND));
  const minutes = Math.floor(seconds / SECONDS_PER_MINUTE);
  return `${String(minutes)}:${String(seconds % SECONDS_PER_MINUTE).padStart(TWO_DIGITS, "0")}`;
}

function eventMarks(samples: readonly DevMetrics[], events: readonly DevEvent[]): ChartMark[] {
  const first = Date.parse(samples[0]?.at ?? "");
  const last = Date.parse(samples[samples.length - 1]?.at ?? "");
  if (!(last > first)) {
    return [];
  }
  return events
    .map((event) => (Date.parse(event.at) - first) / (last - first))
    .filter((share) => share >= 0 && share <= 1)
    .map((share) => ({ share, kind: "event" }));
}

function lossMarks(samples: readonly DevMetrics[]): ChartMark[] {
  if (samples.length < HALF) {
    return [];
  }
  return samples.flatMap((sample, index) =>
    (sample.received?.packetsLost ?? 0) > 0 ? [{ share: index / (samples.length - 1), kind: "loss" as const }] : [],
  );
}
