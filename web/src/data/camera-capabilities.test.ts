import { describe, expect, it } from "vitest";
import { cameraCapabilitiesMessage } from "./camera-capabilities";

describe("camera capabilities", () => {
  it("message carries the maximum of each capability", () => {
    const capabilities = { width: { min: 1, max: 3840 }, height: { min: 1, max: 2160 }, frameRate: { max: 60 } };

    expect(cameraCapabilitiesMessage(capabilities, "environment", ["video/H264"])).toEqual({
      type: "camera_capabilities",
      width: 3840,
      height: 2160,
      frameRate: 60,
      facingMode: "environment",
      codecs: ["video/H264"],
    });
  });

  it("capabilities the browser does not report are null", () => {
    const message = cameraCapabilitiesMessage({ width: {} }, undefined, []);

    expect([message.width, message.height, message.frameRate, message.facingMode]).toEqual([null, null, null, null]);
  });

  it("facing mode outside the contract is null", () => {
    expect(cameraCapabilitiesMessage({}, "left", []).facingMode).toBeNull();
  });

  it("codecs drop retransmission, redundancy and correction entries and repeats", () => {
    const mimeTypes = ["video/VP8", "video/rtx", "video/H264", "video/H264", "video/red", "video/ulpfec", "video/AV1"];

    expect(cameraCapabilitiesMessage({}, "user", mimeTypes).codecs).toEqual(["video/VP8", "video/H264", "video/AV1"]);
  });
});
