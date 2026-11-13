import { describe, expect, it } from "vitest";
import {
  appendSample,
  healthStrip,
  histogram,
  keyFrameIntervalSeconds,
  lineSegments,
  metricsCsv,
  niceCeiling,
  packetsLostIn,
  percentile,
  stackedBands,
  type DevMetrics,
} from "./dev-metrics";

const STAGES: NonNullable<DevMetrics["stages"]> = {
  decode: { median: 3.1, p95: 4.8 },
  color: { median: 2, p95: 2.9 },
  deliver: { median: 0.6, p95: 1.1 },
  total: { median: 5.9, p95: 8.2 },
};
const OUTBOUND: NonNullable<NonNullable<DevMetrics["phone"]>["outbound"]> = {
  framesPerSecond: 30,
  framesSent: 900,
  framesEncoded: 900,
  keyFramesEncoded: 3,
  bytesSent: 1,
  qualityLimitationReason: "none",
  nackCount: 0,
  pliCount: 0,
  frameWidth: 1920,
  frameHeight: 1080,
};
const RECEIVED: NonNullable<DevMetrics["received"]> = { fps: 30, bitrateKbps: 9400, packetsLost: 0, jitterMs: 2.1 };
const LIVE: DevMetrics = {
  at: "2026-11-12T18:00:01.000Z",
  session: {
    state: "live",
    liveSince: "2026-11-12T17:58:00Z",
    deviceName: "iPhone · Safari",
    facing: "environment",
    format: "1080p30",
    codec: "H264",
  },
  received: RECEIVED,
  delivered: { fps: 30, frames: 3540, dropped: 2 },
  stages: STAGES,
  frameTimesMs: [5.8, 6.1],
  budgetMs: 33.3,
  ceilingKbps: 10000,
  virtualCamera: { format: "1080p30", pendingFormat: null, streamingApps: 1, source: "phone" },
  process: { cpuPercent: 12.5 },
  phone: {
    at: 1,
    outbound: OUTBOUND,
    remoteInbound: { roundTripTime: 0.012, jitter: 0.002, packetsLost: 0 },
  },
};
const IDLE: DevMetrics = { ...LIVE, session: null, received: null, delivered: null, stages: null, phone: null };

describe("dev metrics", () => {
  it("samples keep only the most recent ones up to the limit", () => {
    expect(appendSample([1, 2, 3], 4, 3)).toEqual([2, 3, 4]);
  });

  it("a healthy live second is ok on every number", () => {
    const strip = healthStrip(LIVE, 30, 0);

    expect(Object.values(strip).map((value) => value.health)).toEqual(["ok", "ok", "ok", "ok", "ok", "ok"]);
    expect(strip.roundTripMs.value).toBe(12);
    expect(strip.bitrateMbps.value).toBe(9.4);
  });

  it("low fps, lost packets, slow frames, busy cpu and a long round trip ask for attention", () => {
    const slow: DevMetrics = {
      ...LIVE,
      delivered: { fps: 20, frames: 1, dropped: 0 },
      stages: { ...STAGES, total: { median: 20, p95: 25 } },
      process: { cpuPercent: 80 },
      phone: { at: 1, outbound: OUTBOUND, remoteInbound: { roundTripTime: 0.3, jitter: 0, packetsLost: 4 } },
    };

    const strip = healthStrip(slow, 30, 4);

    expect([
      strip.fpsDelivered.health,
      strip.processingP95.health,
      strip.packetsLost.health,
      strip.cpuPercent.health,
      strip.roundTripMs.health,
    ]).toEqual(["attention", "attention", "attention", "attention", "attention"]);
  });

  it("numbers that are not measured yet stay empty and ok", () => {
    const strip = healthStrip(IDLE, 30, null);

    expect([strip.fpsDelivered, strip.roundTripMs]).toEqual([
      { value: null, health: "ok" },
      { value: null, health: "ok" },
    ]);
  });

  it("packets lost add up over the seconds that were measured", () => {
    const lossy = { ...LIVE, received: { ...RECEIVED, packetsLost: 3 } };

    expect([packetsLostIn([LIVE, lossy, lossy]), packetsLostIn([IDLE])]).toEqual([6, null]);
  });

  it("chart ceilings round up to a readable step", () => {
    expect([9.4, 31, 0.7, 120, 0].map(niceCeiling)).toEqual([10, 50, 1, 200, 1]);
  });

  it("a line breaks where a second has no value", () => {
    expect(lineSegments([0, 10, null, 5, 10], 40, 10, 10)).toEqual(["0,10 10,0", "30,5 40,0"]);
  });

  it("stacked bands sit on top of each other", () => {
    expect(
      stackedBands(
        [
          [2, 2],
          [3, 3],
        ],
        10,
        10,
        10,
      ),
    ).toEqual(["0,8 10,8 10,10 0,10", "0,5 10,5 10,8 0,8"]);
  });

  it("frame times fall into their bins and the slowest ones into the last", () => {
    expect(histogram([0.5, 1.5, 1.9, 99], 1, 3)).toEqual([1, 2, 1]);
  });

  it("percentile picks the nearest rank", () => {
    expect([percentile([5, 1, 3, 2, 4], 0.5), percentile([5, 1, 3, 2, 4], 0.95), percentile([], 0.5)]).toEqual([
      3,
      5,
      null,
    ]);
  });

  it("key frame interval is the seconds between key frames over the window", () => {
    const withKeyFrames = (count: number): DevMetrics => ({
      ...LIVE,
      phone: { at: 1, outbound: { ...OUTBOUND, keyFramesEncoded: count }, remoteInbound: null },
    });

    expect(keyFrameIntervalSeconds([3, 3, 4, 4, 5].map(withKeyFrames))).toBe(2);
    expect(keyFrameIntervalSeconds([withKeyFrames(3)])).toBeNull();
  });

  it("csv has a header and one row per second with empty cells for missing values", () => {
    const [header, live, idle] = metricsCsv([LIVE, IDLE]).split("\n");

    expect(header?.startsWith("at,received_fps,received_kbps")).toBe(true);
    expect(live?.split(",").slice(0, 3)).toEqual(["2026-11-12T18:00:01.000Z", "30", "9400"]);
    expect(idle?.split(",")[1]).toBe("");
  });
});
