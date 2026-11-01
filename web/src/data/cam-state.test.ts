import { describe, expect, it } from "vitest";
import { cameraFailureFromError, camReducer, initialCamState, type CamEvent, type CamState } from "./cam-state";

const CAPTURE = { width: 1920, height: 1080, frameRate: 30 };
const LANDSCAPE = { width: 1920, height: 1080 };
const PORTRAIT = { width: 1080, height: 1920 };

function run(state: CamState, ...events: CamEvent[]): CamState {
  return events.reduce(camReducer, state);
}

describe("cam state", () => {
  it("cam state goes from intro to requesting to ready when permission is granted", () => {
    const intro = initialCamState(true);
    const requesting = camReducer(intro, { type: "start" });
    const ready = camReducer(requesting, { type: "granted", capture: CAPTURE, frame: LANDSCAPE });

    expect([intro.kind, requesting.kind, ready]).toEqual(["intro", "requesting", { kind: "ready", capture: CAPTURE }]);
  });

  it("cam state goes to denied when permission is refused", () => {
    const state = run(initialCamState(true), { type: "start" }, { type: "failed", failure: "denied" });

    expect(state).toEqual({ kind: "denied" });
  });

  it("cam state goes to rotate when the frame is portrait", () => {
    const state = run(initialCamState(true), { type: "start" }, { type: "granted", capture: CAPTURE, frame: PORTRAIT });

    expect(state).toEqual({ kind: "rotate", capture: CAPTURE });
  });

  it("cam state returns to ready when the frame turns landscape", () => {
    const state = run(
      initialCamState(true),
      { type: "start" },
      { type: "granted", capture: CAPTURE, frame: PORTRAIT },
      { type: "frame_changed", frame: LANDSCAPE },
    );

    expect(state).toEqual({ kind: "ready", capture: CAPTURE });
  });

  it("cam state maps each getUserMedia error to its unavailable reason", () => {
    const failures = [
      "NotAllowedError",
      "NotFoundError",
      "OverconstrainedError",
      "NotReadableError",
      "AbortError",
      "SecurityError",
      "NotSupportedError",
    ].map((name) => cameraFailureFromError(new DOMException("", name)));

    expect(failures).toEqual(["denied", "no_camera", "no_camera", "in_use", "in_use", "unsupported", "unsupported"]);
    expect(cameraFailureFromError(new TypeError("getUserMedia is not a function"))).toBe("unsupported");
    expect(camReducer({ kind: "requesting" }, { type: "failed", failure: "in_use" })).toEqual({
      kind: "unavailable",
      reason: "in_use",
    });
  });

  it("cam state toggles the preview off and back on keeping the capture", () => {
    const ready: CamState = { kind: "ready", capture: CAPTURE };
    const off = camReducer(ready, { type: "preview_toggled" });

    expect([off, camReducer(off, { type: "preview_toggled" })]).toEqual([
      { kind: "preview_off", capture: CAPTURE },
      ready,
    ]);
  });

  it("cam state without pairing ignores every event", () => {
    const state = run(
      initialCamState(false),
      { type: "start" },
      { type: "granted", capture: CAPTURE, frame: LANDSCAPE },
    );

    expect(state).toEqual({ kind: "missing_pairing" });
  });
});
