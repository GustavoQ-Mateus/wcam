import { describe, expect, it } from "vitest";
import { colorSampleMessage, dropAlpha } from "./color-sample";

describe("dropAlpha", () => {
  it("keeps red, green and blue of each pixel and drops alpha", () => {
    const rgba = new Uint8ClampedArray([1, 2, 3, 255, 4, 5, 6, 128]);

    expect([...dropAlpha(rgba)]).toEqual([1, 2, 3, 4, 5, 6]);
  });
});

describe("colorSampleMessage", () => {
  it("encodes the rgb bytes in base64 with the sample size and color space", () => {
    const rgba = new Uint8ClampedArray([255, 0, 128, 255]);

    expect(colorSampleMessage(rgba, 1, 1, "display-p3", 42)).toEqual({
      type: "color_sample",
      colorSpace: "display-p3",
      width: 1,
      height: 1,
      rgb: btoa(String.fromCharCode(255, 0, 128)),
      capturedAt: 42,
    });
  });
});
