import { describe, expect, it } from "vitest";
import { cameraCapabilitiesMessage } from "./camera-capabilities";

describe("camera capabilities", () => {
  it("message carries the maximum of each capability", () => {
    const capabilities = { width: { min: 1, max: 3840 }, height: { min: 1, max: 2160 }, frameRate: { max: 60 } };

    expect(cameraCapabilitiesMessage(capabilities, "environment", ["video/H264"], null, {})).toEqual({
      type: "camera_capabilities",
      width: 3840,
      height: 2160,
      frameRate: 60,
      facingMode: "environment",
      codecs: ["video/H264"],
      colorSpace: null,
      modes: { exposureMode: null, whiteBalanceMode: null, focusMode: null },
    });
  });

  it("capabilities the browser does not report are null", () => {
    const message = cameraCapabilitiesMessage({ width: {} }, undefined, [], null, {});

    expect([message.width, message.height, message.frameRate, message.facingMode]).toEqual([null, null, null, null]);
  });

  it("facing mode outside the contract is null", () => {
    expect(cameraCapabilitiesMessage({}, "left", [], null, {}).facingMode).toBeNull();
  });

  it("codecs drop retransmission, redundancy and correction entries and repeats", () => {
    const mimeTypes = ["video/VP8", "video/rtx", "video/H264", "video/H264", "video/red", "video/ulpfec", "video/AV1"];

    expect(cameraCapabilitiesMessage({}, "user", mimeTypes, null, {}).codecs).toEqual([
      "video/VP8",
      "video/H264",
      "video/AV1",
    ]);
  });

  it("color space declared by the camera is sent with the webcodecs names", () => {
    const declared = { primaries: "bt709", transfer: "bt709", matrix: "bt709", fullRange: true };

    expect(cameraCapabilitiesMessage({}, "environment", [], declared, {}).colorSpace).toEqual(declared);
  });

  it("color space fields the browser leaves out are null", () => {
    expect(cameraCapabilitiesMessage({}, "user", [], { transfer: "smpte170m" }, {}).colorSpace).toEqual({
      primaries: null,
      transfer: "smpte170m",
      matrix: null,
      fullRange: null,
    });
  });

  it("camera modes come from the track settings, null when the browser does not report them", () => {
    const settings = { exposureMode: "continuous", whiteBalanceMode: "continuous", focusMode: 3 };

    expect(cameraCapabilitiesMessage({}, "environment", [], null, settings).modes).toEqual({
      exposureMode: "continuous",
      whiteBalanceMode: "continuous",
      focusMode: null,
    });
  });
});
