import { describe, expect, it } from "vitest";
import {
  clampedSeek,
  formatClock,
  formatPreciseClock,
  positionFraction,
  steppedSeek,
  videoPosition,
} from "./video-position";

const DURATION = 10;
const SAMPLE = { seconds: 4, receivedAt: 1_000 };

describe("video position", () => {
  it("running video advances by the local clock since the last agent value", () => {
    expect(videoPosition(SAMPLE, 2_500, true, DURATION)).toBeCloseTo(5.5);
  });

  it("new agent value replaces the clock estimate", () => {
    const estimate = videoPosition(SAMPLE, 2_500, true, DURATION);
    const corrected = videoPosition({ seconds: 5.2, receivedAt: 2_500 }, 2_500, true, DURATION);

    expect(estimate).toBeCloseTo(5.5);
    expect(corrected).toBeCloseTo(5.2);
  });

  it("frozen video keeps the agent position while the clock runs", () => {
    expect(videoPosition(SAMPLE, 9_000, false, DURATION)).toBe(4);
  });

  it("position past the end wraps to the start like the loop", () => {
    expect(videoPosition(SAMPLE, 8_000, true, DURATION)).toBeCloseTo(1);
  });

  it("clock earlier than the agent value does not move the position back", () => {
    expect(videoPosition(SAMPLE, 500, true, DURATION)).toBe(4);
  });

  it("position fraction stays between zero and one", () => {
    expect([positionFraction(5, DURATION), positionFraction(12, DURATION), positionFraction(-1, DURATION)]).toEqual([
      0.5, 1, 0,
    ]);
  });

  it("seek target stays inside the video before its end", () => {
    expect([clampedSeek(-3, DURATION), clampedSeek(4, DURATION), clampedSeek(10, DURATION)]).toEqual([0, 4, 9.999]);
  });

  it("arrow keys step five seconds and stop at the edges", () => {
    expect([steppedSeek(4, 1, DURATION), steppedSeek(4, -1, DURATION), steppedSeek(7, 1, DURATION)]).toEqual([
      9, 0, 9.999,
    ]);
  });

  it("clock shows minutes and seconds, and hours only for long videos", () => {
    expect([formatClock(0), formatClock(65.9), formatClock(3_725)]).toEqual(["0:00", "1:05", "1:02:05"]);
  });

  it("precise clock shows tenths of a second for trimming", () => {
    expect(formatPreciseClock(83.47)).toBe("1:23.4");
  });
});
