import { describe, expect, it } from "vitest";
import { formatView } from "./format-view";
import type { VideoFormat } from "./video-format";

const ALL: VideoFormat[] = ["720p30", "720p60", "1080p30", "1440p30", "2160p30"];

describe("format view", () => {
  it("marks the confirmed resolution and frame rate and gives the format each choice sends", () => {
    const view = formatView("720p60", ALL, null);

    expect(view.resolutions.map(({ value, checked, format }) => [value, checked, format])).toEqual([
      ["720p", true, "720p60"],
      ["1080p", false, "1080p30"],
      ["1440p", false, "1440p30"],
      ["2160p", false, "2160p30"],
    ]);
    expect(view.frameRates.map(({ value, checked, format }) => [value, checked, format])).toEqual([
      [30, false, "720p30"],
      [60, true, "720p60"],
    ]);
  });

  it("hides the frame rate group when the resolution has only one frame rate", () => {
    expect(formatView("1080p30", ALL, null).frameRates).toEqual([]);
  });

  it("hides the resolution group when only one resolution is available", () => {
    const view = formatView("1080p30", ["1080p30"], null);

    expect([view.resolutions, view.frameRates, view.resolution, view.frameRate]).toEqual([[], [], "1080p", 30]);
  });

  it("marks as pending only the option that differs in the format waiting for confirmation", () => {
    const resolutionChange = formatView("720p30", ALL, "1440p30");
    const frameRateChange = formatView("720p30", ALL, "720p60");

    expect(resolutionChange.resolutions.filter((option) => option.pending).map((option) => option.value)).toEqual([
      "1440p",
    ]);
    expect(resolutionChange.frameRates.some((option) => option.pending)).toBe(false);
    expect(frameRateChange.frameRates.filter((option) => option.pending).map((option) => option.value)).toEqual([60]);
  });
});
