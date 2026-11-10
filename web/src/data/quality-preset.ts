import type { MessageKey } from "./i18n";

export type QualityPreset = "maximum" | "balanced" | "light";

export const QUALITY_PRESETS: readonly QualityPreset[] = ["maximum", "balanced", "light"];
export const DEFAULT_QUALITY_PRESET: QualityPreset = "balanced";

const MAX_BITRATE_BY_PRESET: Readonly<Record<QualityPreset, number>> = {
  maximum: 20_000_000,
  balanced: 10_000_000,
  light: 5_000_000,
};
const BITS_PER_MEGABIT = 1_000_000;
const NAME_KEYS: Readonly<Record<QualityPreset, MessageKey>> = {
  maximum: "quality.maximum",
  balanced: "quality.balanced",
  light: "quality.light",
};
const HINT_KEYS: Readonly<Record<QualityPreset, MessageKey>> = {
  maximum: "quality.maximum_hint",
  balanced: "quality.balanced_hint",
  light: "quality.light_hint",
};
const LEVELS: Readonly<Record<QualityPreset, number>> = { maximum: 3, balanced: 2, light: 1 };

export function isQualityPreset(value: unknown): value is QualityPreset {
  return typeof value === "string" && (QUALITY_PRESETS as readonly string[]).includes(value);
}

export function maxBitrate(preset: QualityPreset): number {
  return MAX_BITRATE_BY_PRESET[preset];
}

export function maxBitrateMbps(preset: QualityPreset): number {
  return maxBitrate(preset) / BITS_PER_MEGABIT;
}

export function qualityNameKey(preset: QualityPreset): MessageKey {
  return NAME_KEYS[preset];
}

export function qualityHintKey(preset: QualityPreset): MessageKey {
  return HINT_KEYS[preset];
}

export function qualityLevel(preset: QualityPreset): number {
  return LEVELS[preset];
}
