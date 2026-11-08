import { describe, expect, it } from "vitest";
import {
  colorCalibrationKey,
  comparisonAvailable,
  cpuPercentValue,
  secondsUntil,
  svgDataUrl,
  videoFormatValues,
} from "./console-format";
import type { Session, Status, Video } from "./contract";

const NOW = Date.parse("2026-11-01T18:00:00Z");

describe("console format", () => {
  it("pairing countdown rounds up and stops at zero", () => {
    expect([
      secondsUntil("2026-11-01T18:02:00Z", NOW),
      secondsUntil("2026-11-01T18:00:00.200Z", NOW),
      secondsUntil("2026-11-01T17:59:00Z", NOW),
    ]).toEqual([120, 1, 0]);
  });

  it("video values show fps with one decimal and bitrate in megabits", () => {
    const video: Video = {
      width: 1920,
      height: 1080,
      fps: 29.94,
      bitrateKbps: 9800,
      codec: "H264",
      framesScaled: 0,
      colorRange: "full",
      colorMatrix: "unspecified",
      colorCalibration: { state: "measuring", deltaE: null },
    };

    expect(videoFormatValues(video)).toEqual({ width: "1920", height: "1080", fps: "29.9", bitrate: "9.8" });
  });

  it("agent cpu is shown as a whole percent", () => {
    expect([cpuPercentValue(12.5), cpuPercentValue(0), cpuPercentValue(99.4)]).toEqual(["13", "0", "99"]);
  });

  it("qr svg becomes an image data url", () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>';

    expect(decodeURIComponent(svgDataUrl(svg))).toBe(`data:image/svg+xml;charset=utf-8,${svg}`);
  });

  it("color calibration shows matched only when it was applied", () => {
    expect(colorCalibrationKey({ state: "applied", deltaE: 1.2 })).toBe("console.color_matched");
  });

  it("color calibration shows default while measuring or when not applied", () => {
    expect(colorCalibrationKey({ state: "measuring", deltaE: null })).toBe("console.color_default");
    expect(colorCalibrationKey({ state: "default", deltaE: 2.4 })).toBe("console.color_default");
  });

  it("comparison is offered only with dev tools on and a live session", () => {
    const live = { state: "live" } as Session;
    const status = (devTools: boolean, session: Session | null) => ({ devTools, session }) as Status;

    expect([
      comparisonAvailable(status(true, live)),
      comparisonAvailable(status(false, live)),
      comparisonAvailable(status(true, { state: "awaiting_confirmation" } as Session)),
      comparisonAvailable(status(true, null)),
      comparisonAvailable(null),
    ]).toEqual([true, false, false, false, false]);
  });
});
