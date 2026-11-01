import { describe, expect, it } from "vitest";
import { secondsUntil, svgDataUrl, videoFormatValues } from "./console-format";

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
    expect(videoFormatValues({ width: 1920, height: 1080, fps: 29.94, bitrateKbps: 9800 })).toEqual({
      width: "1920",
      height: "1080",
      fps: "29.9",
      bitrate: "9.8",
    });
  });

  it("qr svg becomes an image data url", () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>';

    expect(decodeURIComponent(svgDataUrl(svg))).toBe(`data:image/svg+xml;charset=utf-8,${svg}`);
  });
});
