import { describe, expect, it } from "vitest";
import { statsMessage } from "./phone-stats";

const AT = 1_794_528_000_000;
const OUTBOUND = {
  type: "outbound-rtp",
  kind: "video",
  framesPerSecond: 30,
  framesSent: 900,
  framesEncoded: 901,
  keyFramesEncoded: 3,
  bytesSent: 12_000_000,
  qualityLimitationReason: "none",
  nackCount: 1,
  pliCount: 0,
  frameWidth: 1920,
  frameHeight: 1080,
  ssrc: 42,
};
const REMOTE_INBOUND = {
  type: "remote-inbound-rtp",
  kind: "video",
  roundTripTime: 0.012,
  jitter: 0.002,
  packetsLost: 0,
};

describe("phone stats", () => {
  it("stats message carries the video sender and the agent report fields from the contract", () => {
    expect(JSON.parse(statsMessage([OUTBOUND, REMOTE_INBOUND], AT))).toEqual({
      type: "stats",
      at: AT,
      outbound: {
        framesPerSecond: 30,
        framesSent: 900,
        framesEncoded: 901,
        keyFramesEncoded: 3,
        bytesSent: 12_000_000,
        qualityLimitationReason: "none",
        nackCount: 1,
        pliCount: 0,
        frameWidth: 1920,
        frameHeight: 1080,
      },
      remoteInbound: { roundTripTime: 0.012, jitter: 0.002, packetsLost: 0 },
    });
  });

  it("a field the browser does not report goes as null", () => {
    const withoutFps = { ...OUTBOUND, framesPerSecond: undefined };

    const message = JSON.parse(statsMessage([withoutFps], AT)) as { outbound: Record<string, unknown> };

    expect(message.outbound.framesPerSecond).toBeNull();
  });

  it("a missing report goes as a null block", () => {
    const message = JSON.parse(statsMessage([OUTBOUND], AT)) as { remoteInbound: unknown };

    expect(message.remoteInbound).toBeNull();
  });

  it("audio and other reports are ignored", () => {
    const audio = { ...OUTBOUND, kind: "audio" };

    const message = JSON.parse(statsMessage([audio, { type: "candidate-pair" }], AT)) as { outbound: unknown };

    expect(message.outbound).toBeNull();
  });
});
