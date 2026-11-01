import { describe, expect, it } from "vitest";
import { captureConstraints, captureFormat, isMirrored } from "./capture";

describe("capture", () => {
  it("capture constraints ask for 1920x1080 at 30 fps without audio", () => {
    expect(captureConstraints("user")).toEqual({
      audio: false,
      video: { facingMode: "user", width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } },
    });
  });

  it("front camera is mirrored and rear camera is not", () => {
    expect([isMirrored("user"), isMirrored("environment")]).toEqual([true, false]);
  });

  it("capture format rounds the configured frame rate", () => {
    expect(captureFormat({ width: 1920, height: 1080, frameRate: 29.97 }, { width: 1, height: 1 })).toEqual({
      width: 1920,
      height: 1080,
      frameRate: 30,
    });
  });
});
