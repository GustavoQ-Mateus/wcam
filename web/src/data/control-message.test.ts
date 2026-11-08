import { describe, expect, it } from "vitest";
import type { CameraCapabilitiesMessage } from "./camera-capabilities";
import { cameraCapabilitiesData, parseControlMessage, setQualityPresetMessage } from "./control-message";

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

  it("unknown or malformed messages are ignored", () => {
    const messages = ["not json", '{"type":"other","state":"live"}', '{"type":"session_state","state":"paused"}', 42];

    expect(messages.map(parseControlMessage)).toEqual([null, null, null, null]);
  });

  it("quality preset message from the agent is parsed", () => {
    expect(parseControlMessage('{"type":"quality_preset","preset":"light"}')).toEqual({
      type: "quality_preset",
      preset: "light",
    });
  });

  it("quality preset message with unknown or missing preset is ignored", () => {
    const messages = ['{"type":"quality_preset","preset":"high"}', '{"type":"quality_preset"}'];

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

  it("chosen preset is sent as set_quality_preset", () => {
    expect(JSON.parse(setQualityPresetMessage("maximum"))).toEqual({ type: "set_quality_preset", preset: "maximum" });
  });

  it("camera capabilities are sent with the contract fields", () => {
    const message: CameraCapabilitiesMessage = {
      type: "camera_capabilities",
      width: 1920,
      height: 1080,
      frameRate: 30,
      facingMode: null,
      codecs: ["video/H264"],
    };

    expect(JSON.parse(cameraCapabilitiesData(message))).toEqual(message);
  });
});
