import type { MessageKey } from "./i18n";

export type Resolution = "720p" | "1080p" | "1440p" | "2160p";
export type FrameRate = 30 | 60;
export type VideoFormat = "720p30" | "720p60" | "1080p30" | "1440p30" | "2160p30";

export interface FormatSpec {
  resolution: Resolution;
  frameRate: FrameRate;
  width: number;
  height: number;
  maxBitrate: number;
}

export interface FormatConstraints {
  width: { exact: number };
  height: { exact: number };
  frameRate: { exact: number };
}

export const DEFAULT_VIDEO_FORMAT: VideoFormat = "1080p30";

const FORMATS: Readonly<Record<VideoFormat, FormatSpec>> = {
  "720p30": { resolution: "720p", frameRate: 30, width: 1280, height: 720, maxBitrate: 5_000_000 },
  "720p60": { resolution: "720p", frameRate: 60, width: 1280, height: 720, maxBitrate: 8_000_000 },
  "1080p30": { resolution: "1080p", frameRate: 30, width: 1920, height: 1080, maxBitrate: 10_000_000 },
  "1440p30": { resolution: "1440p", frameRate: 30, width: 2560, height: 1440, maxBitrate: 18_000_000 },
  "2160p30": { resolution: "2160p", frameRate: 30, width: 3840, height: 2160, maxBitrate: 35_000_000 },
};
const VIDEO_FORMATS = Object.keys(FORMATS) as VideoFormat[];
const RESOLUTIONS: readonly Resolution[] = ["720p", "1080p", "1440p", "2160p"];
const FRAME_RATES: readonly FrameRate[] = [30, 60];
const RESOLUTION_KEYS: Readonly<Record<Resolution, MessageKey>> = {
  "720p": "format.resolution_720p",
  "1080p": "format.resolution_1080p",
  "1440p": "format.resolution_1440p",
  "2160p": "format.resolution_2160p",
};
const FRAME_RATE_KEYS: Readonly<Record<FrameRate, MessageKey>> = {
  30: "format.frame_rate_30",
  60: "format.frame_rate_60",
};
const FRAME_RATE_HINT_KEYS: Readonly<Record<FrameRate, MessageKey>> = {
  30: "format.frame_rate_30_hint",
  60: "format.frame_rate_60_hint",
};
const BITS_PER_MEGABIT = 1_000_000;

export function isVideoFormat(value: unknown): value is VideoFormat {
  return typeof value === "string" && Object.hasOwn(FORMATS, value);
}

export function formatSpec(format: VideoFormat): FormatSpec {
  return FORMATS[format];
}

export function availableFormats(values: readonly unknown[]): VideoFormat[] {
  return VIDEO_FORMATS.filter((format) => values.includes(format));
}

export function resolutionsIn(available: readonly VideoFormat[]): Resolution[] {
  return RESOLUTIONS.filter((resolution) => available.some((format) => FORMATS[format].resolution === resolution));
}

export function frameRatesFor(resolution: Resolution, available: readonly VideoFormat[]): FrameRate[] {
  return FRAME_RATES.filter((frameRate) => findFormat(resolution, frameRate, available) !== null);
}

export function chooseResolution(
  current: VideoFormat,
  resolution: Resolution,
  available: readonly VideoFormat[],
): VideoFormat | null {
  const sameFrameRate = findFormat(resolution, FORMATS[current].frameRate, available);
  if (sameFrameRate) {
    return sameFrameRate;
  }
  return available.find((format) => FORMATS[format].resolution === resolution) ?? null;
}

export function chooseFrameRate(
  current: VideoFormat,
  frameRate: FrameRate,
  available: readonly VideoFormat[],
): VideoFormat | null {
  const sameResolution = findFormat(FORMATS[current].resolution, frameRate, available);
  if (sameResolution) {
    return sameResolution;
  }
  const withFrameRate = available.filter((format) => FORMATS[format].frameRate === frameRate);
  return withFrameRate.at(-1) ?? null;
}

export function formatConstraints(format: VideoFormat, portrait: boolean): FormatConstraints {
  const { width, height, frameRate } = FORMATS[format];
  return {
    width: { exact: portrait ? height : width },
    height: { exact: portrait ? width : height },
    frameRate: { exact: frameRate },
  };
}

export function maxBitrateMbps(format: VideoFormat): number {
  return FORMATS[format].maxBitrate / BITS_PER_MEGABIT;
}

export function resolutionKey(resolution: Resolution): MessageKey {
  return RESOLUTION_KEYS[resolution];
}

export function frameRateKey(frameRate: FrameRate): MessageKey {
  return FRAME_RATE_KEYS[frameRate];
}

export function frameRateHintKey(frameRate: FrameRate): MessageKey {
  return FRAME_RATE_HINT_KEYS[frameRate];
}

function findFormat(
  resolution: Resolution,
  frameRate: FrameRate,
  available: readonly VideoFormat[],
): VideoFormat | null {
  return (
    available.find((format) => FORMATS[format].resolution === resolution && FORMATS[format].frameRate === frameRate) ??
    null
  );
}
