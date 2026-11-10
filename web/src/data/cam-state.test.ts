import { describe, expect, it } from "vitest";
import { cameraFailureFromError, camReducer, initialCamState, type CamEvent, type CamState } from "./cam-state";

const CAPTURE = { width: 1920, height: 1080, frameRate: 30 };
const LANDSCAPE = { width: 1920, height: 1080 };
const PORTRAIT = { width: 1080, height: 1920 };
const CONNECTING: CamState = { kind: "connecting", capture: CAPTURE, portrait: false };
const LIVE: CamState = { kind: "live", capture: CAPTURE, portrait: false, previewOff: false };

function run(state: CamState, ...events: CamEvent[]): CamState {
  return events.reduce(camReducer, state);
}

describe("cam state", () => {
  it("cam state goes from intro to requesting to ready when permission is granted", () => {
    const intro = initialCamState(true);
    const requesting = camReducer(intro, { type: "start" });
    const ready = camReducer(requesting, { type: "granted", capture: CAPTURE, frame: LANDSCAPE });

    expect([intro.kind, requesting.kind, ready]).toEqual([
      "intro",
      "requesting",
      { kind: "ready", capture: CAPTURE, portrait: false },
    ]);
  });

  it("cam state goes to denied when permission is refused", () => {
    const state = run(initialCamState(true), { type: "start" }, { type: "failed", failure: "denied" });

    expect(state).toEqual({ kind: "denied" });
  });

  it("a portrait frame is ready to stream and marked portrait", () => {
    const state = run(initialCamState(true), { type: "start" }, { type: "granted", capture: CAPTURE, frame: PORTRAIT });

    expect(state).toEqual({ kind: "ready", capture: CAPTURE, portrait: true });
  });

  it("cam state stays ready and drops the portrait mark when the frame turns landscape", () => {
    const state = run(
      initialCamState(true),
      { type: "start" },
      { type: "granted", capture: CAPTURE, frame: PORTRAIT },
      { type: "frame_changed", frame: LANDSCAPE },
    );

    expect(state).toEqual({ kind: "ready", capture: CAPTURE, portrait: false });
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
    const ready: CamState = { kind: "ready", capture: CAPTURE, portrait: false };
    const off = camReducer(ready, { type: "preview_toggled" });

    expect([off, camReducer(off, { type: "preview_toggled" })]).toEqual([
      { kind: "preview_off", capture: CAPTURE, portrait: false },
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

  it("a phone held upright starts the session marked portrait", () => {
    const state = camReducer({ kind: "ready", capture: CAPTURE, portrait: true }, { type: "session_started" });

    expect(state).toEqual({ kind: "connecting", capture: CAPTURE, portrait: true });
  });

  it("cam state goes from ready to connecting when the session starts", () => {
    const state = camReducer({ kind: "ready", capture: CAPTURE, portrait: false }, { type: "session_started" });

    expect(state).toEqual({ kind: "connecting", capture: CAPTURE, portrait: false });
  });

  it("cam state shows the confirmation code and then goes live after confirmation", () => {
    const awaiting = camReducer(CONNECTING, { type: "session_awaiting_confirmation", code: "92Q-M2H" });
    const live = camReducer(awaiting, { type: "session_live" });

    expect([awaiting, live]).toEqual([
      { kind: "awaiting_confirmation", capture: CAPTURE, portrait: false, code: "92Q-M2H" },
      { kind: "live", capture: CAPTURE, portrait: false, previewOff: false },
    ]);
  });

  it("cam state maps each session error to its final state", () => {
    const states = [
      "pairing_token_invalid",
      "pairing_token_expired",
      "pairing_window_closed",
      "not_same_network",
      "too_many_attempts",
      "session_already_active",
      "invalid_request",
    ].map((code) => camReducer(CONNECTING, { type: "session_failed", code }));

    expect(states).toEqual([
      { kind: "pairing_failed" },
      { kind: "pairing_failed" },
      { kind: "pairing_failed" },
      { kind: "blocked", reason: "network" },
      { kind: "blocked", reason: "attempts" },
      { kind: "busy" },
      { kind: "ended", reason: "lost" },
    ]);
  });

  it("cam state ends with the reason sent by the agent", () => {
    const states = [
      "rejected",
      "disconnected_by_pc",
      "confirmation_timeout",
      "connection_failed",
      "disconnected_by_phone",
    ].map((reason) => camReducer(LIVE, { type: "session_ended", reason }));

    expect(states).toEqual([
      { kind: "ended", reason: "rejected" },
      { kind: "ended", reason: "disconnected" },
      { kind: "ended", reason: "timeout" },
      { kind: "ended", reason: "lost" },
      { kind: "ended", reason: "lost" },
    ]);
  });

  it("portrait frame during the session keeps the session and marks it portrait", () => {
    const portrait = camReducer(LIVE, { type: "frame_changed", frame: PORTRAIT });
    const landscape = camReducer(portrait, { type: "frame_changed", frame: LANDSCAPE });

    expect([portrait, landscape]).toEqual([{ ...LIVE, portrait: true }, LIVE]);
  });

  it("live preview toggles without leaving the session", () => {
    expect(camReducer(LIVE, { type: "preview_toggled" })).toEqual({ ...LIVE, previewOff: true });
  });

  it("final states ignore every later event", () => {
    const ended: CamState = { kind: "ended", reason: "rejected" };
    const state = run(ended, { type: "start" }, { type: "granted", capture: CAPTURE, frame: LANDSCAPE });

    expect(state).toBe(ended);
  });
});
