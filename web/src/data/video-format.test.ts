import { describe, expect, it } from "vitest";
import {
  availableFormats,
  chooseFrameRate,
  chooseResolution,
  formatConstraints,
  frameRatesFor,
  isVideoFormat,
  matchesScreen,
  maxBitrateMbps,
  resolutionsIn,
  type VideoFormat,
} from "./video-format";

const ALL: VideoFormat[] = ["720p30", "720p60", "1080p30", "1440p30", "2160p30"];

describe("video format", () => {
  it("only the formats of the contract table are recognized, in table order", () => {
    expect([isVideoFormat("1080p30"), isVideoFormat("1080p60"), isVideoFormat(30)]).toEqual([true, false, false]);
    expect(availableFormats(["2160p30", "unknown", "720p30", "1080p60"])).toEqual(["720p30", "2160p30"]);
  });

  it("resolutions are the available ones from smallest to largest", () => {
    expect(resolutionsIn(["2160p30", "720p60", "1080p30"])).toEqual(["720p", "1080p", "2160p"]);
  });

  it("frame rates are only the ones the chosen resolution has", () => {
    expect([frameRatesFor("720p", ALL), frameRatesFor("1080p", ALL)]).toEqual([[30, 60], [30]]);
  });

  it("choosing a resolution keeps the frame rate when it exists there", () => {
    expect(chooseResolution("720p30", "1080p", ALL)).toBe("1080p30");
  });

  it("choosing a resolution without the current frame rate takes the one it has", () => {
    expect(chooseResolution("720p60", "2160p", ALL)).toBe("2160p30");
  });

  it("choosing a frame rate keeps the resolution when it has it", () => {
    expect(chooseFrameRate("720p30", 60, ALL)).toBe("720p60");
  });

  it("choosing a frame rate the resolution lacks takes the largest resolution that has it", () => {
    expect(chooseFrameRate("2160p30", 60, ALL)).toBe("720p60");
  });

  it("a choice outside the available formats gives nothing", () => {
    expect([chooseResolution("1080p30", "2160p", ["1080p30"]), chooseFrameRate("1080p30", 60, ["1080p30"])]).toEqual([
      null,
      null,
    ]);
  });

  it("constraints are exact and swap width and height when the phone is upright", () => {
    expect([formatConstraints("1080p30", false), formatConstraints("1080p30", true)]).toEqual([
      { width: { exact: 1920 }, height: { exact: 1080 }, frameRate: { exact: 30 } },
      { width: { exact: 1080 }, height: { exact: 1920 }, frameRate: { exact: 30 } },
    ]);
  });

  it("bitrate limit follows the contract table", () => {
    expect(ALL.map(maxBitrateMbps)).toEqual([5, 8, 10, 18, 35]);
  });

  it("a delivered frame matches the screen when both are upright or both are lying down", () => {
    expect([
      matchesScreen({ width: 1080, height: 1920 }, true),
      matchesScreen({ width: 1920, height: 1080 }, false),
      matchesScreen({ width: 1920, height: 1080 }, true),
      matchesScreen({ width: 1080, height: 1920 }, false),
    ]).toEqual([true, true, false, false]);
  });
});
