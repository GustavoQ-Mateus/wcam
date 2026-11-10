export type Facing = "user" | "environment";
export type UnavailableReason = "unsupported" | "no_camera" | "in_use";
export type CameraFailure = "denied" | UnavailableReason;
export type BlockedReason = "network" | "attempts";
export type EndedReason = "rejected" | "disconnected" | "lost" | "timeout";

export interface FrameSize {
  width: number;
  height: number;
}

export interface CaptureFormat extends FrameSize {
  frameRate: number;
}

interface FramedFields {
  capture: CaptureFormat;
  portrait: boolean;
}

export type CamState =
  | { kind: "missing_pairing" }
  | { kind: "intro" }
  | { kind: "requesting" }
  | { kind: "denied" }
  | { kind: "unavailable"; reason: UnavailableReason }
  | ({ kind: "ready" } & FramedFields)
  | ({ kind: "preview_off" } & FramedFields)
  | ({ kind: "connecting" } & FramedFields)
  | ({ kind: "awaiting_confirmation"; code: string } & FramedFields)
  | ({ kind: "live"; previewOff: boolean } & FramedFields)
  | { kind: "pairing_failed" }
  | { kind: "blocked"; reason: BlockedReason }
  | { kind: "busy" }
  | { kind: "ended"; reason: EndedReason };

export type LiveCamState = Extract<CamState, { capture: CaptureFormat }>;
export type SessionCamState = Extract<CamState, { kind: "connecting" | "awaiting_confirmation" | "live" }>;

export type CamEvent =
  | { type: "start" }
  | { type: "granted"; capture: CaptureFormat; frame: FrameSize }
  | { type: "failed"; failure: CameraFailure }
  | { type: "frame_changed"; frame: FrameSize }
  | { type: "preview_toggled" }
  | { type: "session_started" }
  | { type: "session_awaiting_confirmation"; code: string }
  | { type: "session_live" }
  | { type: "session_failed"; code: string }
  | { type: "session_ended"; reason: string };

const SESSION_KINDS: ReadonlySet<CamState["kind"]> = new Set(["connecting", "awaiting_confirmation", "live"]);
const STARTABLE_KINDS: ReadonlySet<CamState["kind"]> = new Set(["intro", "denied", "unavailable"]);
const FINAL_KINDS: ReadonlySet<CamState["kind"]> = new Set([
  "missing_pairing",
  "pairing_failed",
  "blocked",
  "busy",
  "ended",
]);
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
const SESSION_FAILURE_BY_CODE: Readonly<Partial<Record<string, CamState>>> = {
  pairing_token_invalid: { kind: "pairing_failed" },
  pairing_token_expired: { kind: "pairing_failed" },
  pairing_window_closed: { kind: "pairing_failed" },
  not_same_network: { kind: "blocked", reason: "network" },
  too_many_attempts: { kind: "blocked", reason: "attempts" },
  session_already_active: { kind: "busy" },
};
const ENDED_REASON_BY_AGENT_REASON: Readonly<Partial<Record<string, EndedReason>>> = {
  rejected: "rejected",
  disconnected_by_pc: "disconnected",
  confirmation_timeout: "timeout",
};
const CONNECTION_LOST: CamState = { kind: "ended", reason: "lost" };

export function initialCamState(hasPairing: boolean): CamState {
  return hasPairing ? { kind: "intro" } : { kind: "missing_pairing" };
}

export function isLive(state: CamState): state is LiveCamState {
  return "capture" in state;
}

export function isSession(state: CamState): state is SessionCamState {
  return SESSION_KINDS.has(state.kind);
}

export function isFinal(state: CamState): boolean {
  return FINAL_KINDS.has(state.kind);
}

export function camReducer(state: CamState, event: CamEvent): CamState {
  if (isFinal(state)) {
    return state;
  }
  if (isSession(state)) {
    return sessionReducer(state, event);
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
    case "session_started":
      return state.kind === "ready" || state.kind === "preview_off"
        ? { kind: "connecting", capture: state.capture, portrait: state.portrait }
        : state;
    default:
      return state;
  }
}

export function cameraFailureFromError(error: unknown): CameraFailure {
  if (typeof error !== "object" || error === null || !("name" in error) || typeof error.name !== "string") {
    return DEFAULT_FAILURE;
  }
  return FAILURE_BY_ERROR_NAME[error.name] ?? DEFAULT_FAILURE;
}

function sessionReducer(state: SessionCamState, event: CamEvent): CamState {
  switch (event.type) {
    case "granted":
      return { ...state, capture: event.capture, portrait: isPortrait(event.frame) };
    case "frame_changed":
      return { ...state, portrait: isPortrait(event.frame) };
    case "failed":
      return failedState(event.failure);
    case "preview_toggled":
      return state.kind === "live" ? { ...state, previewOff: !state.previewOff } : state;
    case "session_awaiting_confirmation":
      return state.kind === "connecting"
        ? { kind: "awaiting_confirmation", capture: state.capture, portrait: state.portrait, code: event.code }
        : state;
    case "session_live":
      return state.kind === "awaiting_confirmation"
        ? { kind: "live", capture: state.capture, portrait: state.portrait, previewOff: false }
        : state;
    case "session_failed":
      return state.kind === "connecting" ? (SESSION_FAILURE_BY_CODE[event.code] ?? CONNECTION_LOST) : state;
    case "session_ended":
      return { kind: "ended", reason: ENDED_REASON_BY_AGENT_REASON[event.reason] ?? "lost" };
    case "start":
    case "session_started":
      return state;
  }
}

function isPortrait(frame: FrameSize): boolean {
  return frame.width <= frame.height;
}

function framedState(capture: CaptureFormat, frame: FrameSize, previewOff: boolean): LiveCamState {
  return { kind: previewOff ? "preview_off" : "ready", capture, portrait: isPortrait(frame) };
}

function failedState(failure: CameraFailure): CamState {
  return failure === "denied" ? { kind: "denied" } : { kind: "unavailable", reason: failure };
}

function togglePreview(state: CamState): CamState {
  if (state.kind === "ready") {
    return { ...state, kind: "preview_off" };
  }
  if (state.kind === "preview_off") {
    return { ...state, kind: "ready" };
  }
  return state;
}
