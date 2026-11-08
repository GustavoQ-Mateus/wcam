import { describe, expect, it } from "vitest";
import { captureTime, comparisonFailureKey, differenceLines, gridCells, reportDataUrl } from "./comparison-format";
import type { ImageDifference } from "./contract";

const DIFFERENCE: ImageDifference = {
  captureGapMs: 60.4,
  correlation: 0.97,
  mirrored: false,
  deltaE2000: { mean: 3.21, median: 2.94, p90: 6.08 },
  deltaL: -4.12,
  chromaRatio: 0.917,
  hueShiftDegrees: 2.34,
  grid: { columns: 2, rows: 1, deltaE2000: [1.96, 2.04] },
};

describe("differenceLines", () => {
  it("formats delta e, capture gap, tone, chroma and hue for the detail area", () => {
    expect(differenceLines(DIFFERENCE)).toEqual([
      { key: "console.dev_compare_delta_e", values: { mean: "3.2", median: "2.9", p90: "6.1" } },
      { key: "console.dev_compare_gap", values: { ms: "60" } },
      { key: "console.dev_compare_tone", values: { value: "-4.1" } },
      { key: "console.dev_compare_chroma", values: { ratio: "0.92" } },
      { key: "console.dev_compare_hue", values: { degrees: "+2.3" } },
    ]);
  });

  it("tone and hue that round to zero have no sign", () => {
    const lines = differenceLines({ ...DIFFERENCE, deltaL: -0.04, hueShiftDegrees: 0.02 });

    expect([lines[2]?.values, lines[4]?.values]).toEqual([{ value: "0.0" }, { degrees: "0.0" }]);
  });
});

describe("gridCells", () => {
  it("marks only the regions whose shown delta e is above 2", () => {
    const grid = { columns: 3, rows: 1, deltaE2000: [1.96, 2.04, 2.06] };

    expect(gridCells(grid)).toEqual([
      { text: "2.0", overLimit: false },
      { text: "2.0", overLimit: false },
      { text: "2.1", overLimit: true },
    ]);
  });
});

describe("captureTime", () => {
  it("shows local hours, minutes, seconds and milliseconds", () => {
    const time = new Date(2026, 10, 7, 9, 5, 3, 40);

    expect(captureTime(time.toISOString())).toBe("09:05:03.040");
  });
});

describe("reportDataUrl", () => {
  it("encodes the report as downloadable json", () => {
    const url = reportDataUrl({ id: "c1" });

    expect(JSON.parse(decodeURIComponent(url.slice(url.indexOf(",") + 1)))).toEqual({ id: "c1" });
  });
});

describe("comparisonFailureKey", () => {
  it("turns each failure reason of the contract into its own text", () => {
    const reasons = ["phone_timeout", "phone_invalid", "pc_missing", "session_ended", "no_live_session"];

    expect(reasons.map(comparisonFailureKey)).toEqual([
      "console.dev_compare_phone_timeout",
      "console.dev_compare_phone_invalid",
      "console.dev_compare_pc_missing",
      "console.dev_compare_session_ended",
      "console.dev_compare_not_live",
    ]);
  });

  it("turns each camera problem on the computer into its own text", () => {
    const problems = ["camera_denied", "camera_missing", "camera_busy", "camera_failed"];

    expect(problems.map(comparisonFailureKey)).toEqual([
      "console.dev_compare_camera_denied",
      "console.dev_compare_camera_missing",
      "console.dev_compare_camera_busy",
      "console.dev_compare_camera_failed",
    ]);
  });

  it("falls back to the shared error text and never shows the raw code", () => {
    expect([comparisonFailureKey("network_error"), comparisonFailureKey("something_new")]).toEqual([
      "errors.network_error",
      "errors.unknown",
    ]);
  });
});
