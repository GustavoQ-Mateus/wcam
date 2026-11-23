import { describe, expect, it } from "vitest";
import { appPreviewState, isNewerFrame, nv12Size, parseAppPreviewMessage, previewSource } from "./app-preview";

describe("previewSource", () => {
  it("uses the app channel inside the app window", () => {
    expect(previewSource({ chrome: { webview: {} } })).toBe("app");
  });

  it("uses webrtc in a common browser", () => {
    expect(previewSource({ chrome: {} })).toBe("webrtc");
  });

  it("uses webrtc when the browser has no chrome object", () => {
    expect(previewSource({})).toBe("webrtc");
  });
});

describe("parseAppPreviewMessage", () => {
  it("reads a buffer announcement", () => {
    expect(parseAppPreviewMessage({ type: "preview.buffer", slot: 1, width: 1920, height: 1080 })).toEqual({
      type: "preview.buffer",
      slot: 1,
      width: 1920,
      height: 1080,
    });
  });

  it("reads a frame notice", () => {
    expect(parseAppPreviewMessage({ type: "preview.frame", slot: 0, sequence: 42 })).toEqual({
      type: "preview.frame",
      slot: 0,
      sequence: 42,
    });
  });

  it("reads an idle notice", () => {
    expect(parseAppPreviewMessage({ type: "preview.idle" })).toEqual({ type: "preview.idle" });
  });

  it("rejects a slot outside the two buffers", () => {
    expect(parseAppPreviewMessage({ type: "preview.frame", slot: 2, sequence: 1 })).toBeNull();
  });

  it("rejects a negative sequence", () => {
    expect(parseAppPreviewMessage({ type: "preview.frame", slot: 0, sequence: -1 })).toBeNull();
  });

  it("rejects an odd frame side that nv12 cannot hold", () => {
    expect(parseAppPreviewMessage({ type: "preview.buffer", slot: 0, width: 1921, height: 1080 })).toBeNull();
  });

  it("rejects an unknown type", () => {
    expect(parseAppPreviewMessage({ type: "preview.other", slot: 0 })).toBeNull();
  });

  it("rejects a message that is not an object", () => {
    expect(parseAppPreviewMessage("preview.idle")).toBeNull();
  });
});

describe("nv12Size", () => {
  it("holds the luma plane and the half size chroma plane", () => {
    expect(nv12Size(3840, 2160)).toBe(12_441_600);
  });
});

describe("isNewerFrame", () => {
  it("draws the first frame after new buffers", () => {
    expect(isNewerFrame(null, 0)).toBe(true);
  });

  it("draws a frame with a higher sequence", () => {
    expect(isNewerFrame(7, 8)).toBe(true);
  });

  it("skips a frame already drawn", () => {
    expect(isNewerFrame(8, 8)).toBe(false);
  });

  it("skips an older frame", () => {
    expect(isNewerFrame(8, 3)).toBe(false);
  });
});

describe("appPreviewState", () => {
  it("connects when the preview starts", () => {
    expect(appPreviewState("start")).toBe("connecting");
  });

  it("shows the preview when a frame arrives", () => {
    expect(appPreviewState("frame")).toBe("showing");
  });

  it("waits while the wcam camera delivers no new frame", () => {
    expect(appPreviewState("idle")).toBe("waiting");
  });
});
