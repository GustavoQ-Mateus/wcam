import type { ColorCalibration, Video } from "./contract";
import type { MessageKey } from "./i18n";

const MILLISECONDS_PER_SECOND = 1000;
const KILOBITS_PER_MEGABIT = 1000;
const FPS_DECIMALS = 1;
const BITRATE_DECIMALS = 1;
const CPU_DECIMALS = 0;

export function secondsUntil(expiresAt: string, now: number): number {
  return Math.max(0, Math.ceil((Date.parse(expiresAt) - now) / MILLISECONDS_PER_SECOND));
}

export function videoFormatValues(video: Video): Readonly<Record<string, string>> {
  return {
    width: String(video.width),
    height: String(video.height),
    fps: video.fps.toFixed(FPS_DECIMALS),
    bitrate: (video.bitrateKbps / KILOBITS_PER_MEGABIT).toFixed(BITRATE_DECIMALS),
  };
}

export function colorCalibrationKey(calibration: ColorCalibration): MessageKey {
  return calibration.state === "applied" ? "console.color_matched" : "console.color_default";
}

export function cpuPercentValue(cpuPercent: number): string {
  return cpuPercent.toFixed(CPU_DECIMALS);
}

export function svgDataUrl(svg: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
