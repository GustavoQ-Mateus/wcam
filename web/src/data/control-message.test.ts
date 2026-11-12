import { describe, expect, it } from "vitest";
import type { CameraCapabilitiesMessage } from "./camera-capabilities";
import { cameraCapabilitiesData, parseControlMessage, setVideoFormatMessage } from "./control-message";

describe("control message", () => {
  it("session state messages from the contract are parsed", () => {
    const messages = [
      '{"type":"session_state","state":"awaiting_confirmation"}',
      '{"type":"session_state","state":"live"}',
      '{"type":"session_state","state":"ended","reason":"rejected"}',
    ].map(parseControlMessage);

    expect(messages).toEqual([
      { type: "session_state", state: "awaiting_confirmation" },
      { type: "session_state", state: "live" },
      { type: "session_state", state: "ended", reason: "rejected" },
    ]);
  });

  it("confirmation message from the agent is parsed with both sides", () => {
    expect(parseControlMessage('{"type":"confirmation","pc":true,"phone":false}')).toEqual({
      type: "confirmation",
      pc: true,
      phone: false,
    });
  });

  it("confirmation message without both sides as booleans is ignored", () => {
    const messages = ['{"type":"confirmation","pc":true}', '{"type":"confirmation","pc":1,"phone":0}'];

    expect(messages.map(parseControlMessage)).toEqual([null, null]);
  });

  it("unknown or malformed messages are ignored", () => {
    const messages = ["not json", '{"type":"other","state":"live"}', '{"type":"session_state","state":"paused"}', 42];

    expect(messages.map(parseControlMessage)).toEqual([null, null, null, null]);
  });

  it("video format message from the agent is parsed with the size, rate and available formats", () => {
    const data = JSON.stringify({
      type: "video_format",
      format: "720p60",
      width: 1280,
      height: 720,
      fps: 60,
      maxBitrate: 8000000,
      available: ["720p30", "720p60", "1080p30", "1080p60"],
    });

    expect(parseControlMessage(data)).toEqual({
      type: "video_format",
      format: "720p60",
      width: 1280,
      height: 720,
      fps: 60,
      maxBitrate: 8000000,
      available: ["720p30", "720p60", "1080p30"],
    });
  });

  it("video format message with an unknown format or missing fields is ignored", () => {
    const messages = [
      '{"type":"video_format","format":"1080p60","width":1920,"height":1080,"fps":60,"maxBitrate":1,"available":[]}',
      '{"type":"video_format","format":"1080p30","available":[]}',
    ];

    expect(messages.map(parseControlMessage)).toEqual([null, null]);
  });

  it("snapshot request from the agent is parsed with its id", () => {
    expect(parseControlMessage('{"type":"snapshot_request","id":"c1"}')).toEqual({
      type: "snapshot_request",
      id: "c1",
    });
  });

  it("snapshot request without a text id is ignored", () => {
    const messages = [
      '{"type":"snapshot_request"}',
      '{"type":"snapshot_request","id":7}',
      '{"type":"snapshot_request","id":""}',
    ];

    expect(messages.map(parseControlMessage)).toEqual([null, null, null]);
  });

  it("chosen format is sent as set_video_format", () => {
    expect(JSON.parse(setVideoFormatMessage("2160p30"))).toEqual({ type: "set_video_format", format: "2160p30" });
  });

  it("camera capabilities are sent with the contract fields", () => {
    const message: CameraCapabilitiesMessage = {
      type: "camera_capabilities",
      width: 1920,
      height: 1080,
      frameRate: 30,
      facingMode: null,
      codecs: ["video/H264"],
      colorSpace: { primaries: "bt709", transfer: "bt709", matrix: "bt709", fullRange: true },
      modes: { exposureMode: "continuous", whiteBalanceMode: "continuous", focusMode: "continuous" },
    };

    expect(JSON.parse(cameraCapabilitiesData(message))).toEqual(message);
  });
});
