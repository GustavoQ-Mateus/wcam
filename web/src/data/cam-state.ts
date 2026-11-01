export type Facing = "user" | "environment";
export type UnavailableReason = "unsupported" | "no_camera" | "in_use";
export type CameraFailure = "denied" | UnavailableReason;

export interface FrameSize {
  width: number;
  height: number;
}

export interface CaptureFormat extends FrameSize {
  frameRate: number;
}

export type CamState =
  | { kind: "missing_pairing" }
  | { kind: "intro" }
  | { kind: "requesting" }
  | { kind: "denied" }
  | { kind: "unavailable"; reason: UnavailableReason }
  | { kind: "rotate"; capture: CaptureFormat }
  | { kind: "ready"; capture: CaptureFormat }
  | { kind: "preview_off"; capture: CaptureFormat };

export type LiveCamState = Extract<CamState, { capture: CaptureFormat }>;

export type CamEvent =
  | { type: "start" }
  | { type: "granted"; capture: CaptureFormat; frame: FrameSize }
  | { type: "failed"; failure: CameraFailure }
  | { type: "frame_changed"; frame: FrameSize }
  | { type: "preview_toggled" };

const STARTABLE_KINDS: ReadonlySet<CamState["kind"]> = new Set(["intro", "denied", "unavailable"]);
const FAILURE_BY_ERROR_NAME: Readonly<Partial<Record<string, CameraFailure>>> = {
  NotAllowedError: "denied",
  NotFoundError: "no_camera",
  OverconstrainedError: "no_camera",
  NotReadableError: "in_use",
  AbortError: "in_use",
  SecurityError: "unsupported",
  NotSupportedError: "unsupported",
  TypeError: "unsupported",
};
const DEFAULT_FAILURE: CameraFailure = "in_use";

export function initialCamState(hasPairing: boolean): CamState {
  return hasPairing ? { kind: "intro" } : { kind: "missing_pairing" };
}

export function isLive(state: CamState): state is LiveCamState {
  return "capture" in state;
}

export function camReducer(state: CamState, event: CamEvent): CamState {
  if (state.kind === "missing_pairing") {
    return state;
  }
  switch (event.type) {
    case "start":
      return STARTABLE_KINDS.has(state.kind) ? { kind: "requesting" } : state;
    case "granted":
      return framedState(event.capture, event.frame, state.kind === "preview_off");
    case "failed":
      return failedState(event.failure);
    case "frame_changed":
      return isLive(state) ? framedState(state.capture, event.frame, state.kind === "preview_off") : state;
    case "preview_toggled":
      return togglePreview(state);
  }
}

export function cameraFailureFromError(error: unknown): CameraFailure {
  if (typeof error !== "object" || error === null || !("name" in error) || typeof error.name !== "string") {
    return DEFAULT_FAILURE;
  }
  return FAILURE_BY_ERROR_NAME[error.name] ?? DEFAULT_FAILURE;
}

function framedState(capture: CaptureFormat, frame: FrameSize, previewOff: boolean): LiveCamState {
  if (frame.width <= frame.height) {
    return { kind: "rotate", capture };
  }
  return { kind: previewOff ? "preview_off" : "ready", capture };
}

function failedState(failure: CameraFailure): CamState {
  return failure === "denied" ? { kind: "denied" } : { kind: "unavailable", reason: failure };
}

function togglePreview(state: CamState): CamState {
  if (state.kind === "ready") {
    return { kind: "preview_off", capture: state.capture };
  }
  if (state.kind === "preview_off") {
    return { kind: "ready", capture: state.capture };
  }
  return state;
}
