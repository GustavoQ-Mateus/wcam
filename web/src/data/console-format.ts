import type { Decoder, Status } from "./contract";
import type { MessageKey } from "./i18n";

const MILLISECONDS_PER_SECOND = 1000;
const PAIRING_WINDOW_SECONDS = 120;
const FULL_PERCENT = 100;
const CPU_DECIMALS = 0;
const DECODER_KEYS: Readonly<Record<Decoder, MessageKey>> = {
  hardware: "console.detail_decoder_hardware",
  software: "console.detail_decoder_software",
};

export function secondsUntil(expiresAt: string, now: number): number {
  return Math.max(0, Math.ceil((Date.parse(expiresAt) - now) / MILLISECONDS_PER_SECOND));
}

export function windowProgress(expiresAt: string, now: number): number {
  return Math.min(FULL_PERCENT, (secondsUntil(expiresAt, now) / PAIRING_WINDOW_SECONDS) * FULL_PERCENT);
}

export function comparisonAvailable(status: Status | null): boolean {
  return status?.devTools === true && status.session?.state === "live";
}

export function cpuPercentValue(cpuPercent: number): string {
  return cpuPercent.toFixed(CPU_DECIMALS);
}

export function svgDataUrl(svg: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function currentDecoder({ session, videoSource }: Status): Decoder | null {
  return videoSource.active ? videoSource.decoder : (session?.video?.decoder ?? null);
}

export function decoderKey(decoder: Decoder): MessageKey {
  return DECODER_KEYS[decoder];
}
