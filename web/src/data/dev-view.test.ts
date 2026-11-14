import { describe, expect, it } from "vitest";
import type { DevMetrics } from "./dev-metrics";
import { devCharts, liveDuration, stageMedians } from "./dev-view";

function sample(second: number, packetsLost = 0): DevMetrics {
  return {
    at: new Date(Date.UTC(2026, 10, 12, 18, 0, second)).toISOString(),
    session: null,
    received: { fps: 30, bitrateKbps: 5000, packetsLost, jitterMs: 1 },
    delivered: { fps: 29, frames: 1, dropped: 0 },
    stages: {
      decode: { median: 3, p95: 4 },
      color: { median: 2, p95: 3 },
      deliver: { median: 1, p95: 1.5 },
      total: { median: 6, p95: 8 },
    },
    frameTimesMs: [],
    budgetMs: 33.3,
    ceilingKbps: 10000,
    virtualCamera: { format: "1080p30", pendingFormat: null, streamingApps: null, source: "phone" },
    process: { cpuPercent: 5 },
    phone: null,
  };
}

describe("dev view", () => {
  it("charts take one point per second from the samples", () => {
    const charts = devCharts([sample(0), sample(1)], [], 2);

    expect([charts.deliveredFps, charts.bitrate, charts.phoneFps, charts.decode]).toEqual([
      [29, 29],
      [5, 5],
      [null, null],
      [4, 4],
    ]);
  });

  it("events inside the window become marks at their place in time", () => {
    const events = [
      { at: sample(1).at, kind: "controls", data: {} },
      { at: sample(9).at, kind: "controls", data: {} },
    ];

    expect(devCharts([sample(0), sample(2)], events, 3).eventMarks).toEqual([{ share: 0.5, kind: "event" }]);
  });

  it("seconds with lost packets become loss marks", () => {
    expect(devCharts([sample(0), sample(1, 2), sample(2)], [], 3).lossMarks).toEqual([{ share: 0.5, kind: "loss" }]);
  });

  it("the frame path takes each stage median and half the round trip for the wifi", () => {
    const latest = {
      ...sample(0),
      phone: { at: 0, outbound: null, remoteInbound: { roundTripTime: 0.02, jitter: 0, packetsLost: 0 } },
    };

    expect(stageMedians(latest).map((stage) => stage.milliseconds)).toEqual([null, 10, 3, 2, 1, null]);
  });

  it("live duration shows minutes and two-digit seconds", () => {
    expect(liveDuration("2026-11-12T17:58:00Z", "2026-11-12T18:00:05.400Z")).toBe("2:05");
  });

  it("a stage without frames in the window is left empty instead of breaking the charts", () => {
    const early: DevMetrics = {
      ...sample(0),
      stages: { decode: null, color: { median: 2, p95: 3 }, deliver: null, total: null },
    };

    const charts = devCharts([early], [], 1);

    expect([charts.decode, charts.color, stageMedians(early).map((stage) => stage.milliseconds)]).toEqual([
      [0],
      [3],
      [null, null, null, 2, null, null],
    ]);
  });

  it("a window longer than the samples keeps the samples at the right, in time", () => {
    const charts = devCharts([sample(0), sample(1, 1)], [{ at: sample(1).at, kind: "controls", data: {} }], 5);

    expect(charts.deliveredFps).toEqual([null, null, null, 29, 29]);
    expect(charts.decode).toEqual([0, 0, 0, 4, 4]);
    expect(charts.eventMarks).toEqual([{ share: 1, kind: "event" }]);
    expect(charts.lossMarks).toEqual([{ share: 1, kind: "loss" }]);
  });
});
