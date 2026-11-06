import { describe, expect, it } from "vitest";
import { DEFAULT_QUALITY_PRESET, isQualityPreset, maxBitrate, maxBitrateMbps, QUALITY_PRESETS } from "./quality-preset";

describe("quality preset", () => {
  it("each preset has the contract bitrate", () => {
    expect(QUALITY_PRESETS.map(maxBitrate)).toEqual([20_000_000, 10_000_000, 5_000_000]);
  });

  it("default preset is balanced at 10 Mbit/s", () => {
    expect([DEFAULT_QUALITY_PRESET, maxBitrate(DEFAULT_QUALITY_PRESET)]).toEqual(["balanced", 10_000_000]);
  });

  it("bitrate in megabits per second is shown without decimals", () => {
    expect(QUALITY_PRESETS.map(maxBitrateMbps)).toEqual([20, 10, 5]);
  });

  it("only contract keys are presets", () => {
    expect(["maximum", "balanced", "light", "high", "", null, 10].map(isQualityPreset)).toEqual([
      true,
      true,
      true,
      false,
      false,
      false,
      false,
    ]);
  });
});
