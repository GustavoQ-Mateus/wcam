export type QualityPreset = "maximum" | "balanced" | "light";

export const QUALITY_PRESETS: readonly QualityPreset[] = ["maximum", "balanced", "light"];
export const DEFAULT_QUALITY_PRESET: QualityPreset = "balanced";

const MAX_BITRATE_BY_PRESET: Readonly<Record<QualityPreset, number>> = {
  maximum: 20_000_000,
  balanced: 10_000_000,
  light: 5_000_000,
};
const BITS_PER_MEGABIT = 1_000_000;

export function isQualityPreset(value: unknown): value is QualityPreset {
  return typeof value === "string" && (QUALITY_PRESETS as readonly string[]).includes(value);
}

export function maxBitrate(preset: QualityPreset): number {
  return MAX_BITRATE_BY_PRESET[preset];
}

export function maxBitrateMbps(preset: QualityPreset): number {
  return maxBitrate(preset) / BITS_PER_MEGABIT;
}
