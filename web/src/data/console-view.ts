import type { Facing } from "./cam-state";
import type { Status, VirtualCameraUnavailableReason } from "./contract";
import type { MessageKey } from "./i18n";

export type ConsoleMode = "waiting" | "connecting" | "confirming" | "live" | "frozen" | "camera_off" | "lost";
export type BadgeTone = "neutral" | "live" | "still" | "warning" | "negative";
export type BadgeShape = "ring" | "dot" | "square" | "bars" | "triangle";
export type PathState = "ok" | "waiting" | "problem";

export interface Badge {
  key: MessageKey;
  tone: BadgeTone;
  shape: BadgeShape;
}

export interface PathStep {
  nameKey: MessageKey;
  state: PathState;
  noteKey: MessageKey;
  count?: number;
}

const BADGES: Readonly<Record<ConsoleMode, Badge>> = {
  waiting: { key: "state.waiting", tone: "neutral", shape: "ring" },
  connecting: { key: "console.state_connecting", tone: "neutral", shape: "ring" },
  confirming: { key: "state.confirming", tone: "warning", shape: "triangle" },
  live: { key: "state.live", tone: "live", shape: "dot" },
  frozen: { key: "state.frozen", tone: "still", shape: "square" },
  camera_off: { key: "state.camera_off", tone: "warning", shape: "bars" },
  lost: { key: "state.lost", tone: "negative", shape: "triangle" },
};
const PROBLEM_BADGE: Badge = { key: "state.problem", tone: "negative", shape: "triangle" };
const NOTE_KEYS: Readonly<Record<PathState, MessageKey>> = {
  ok: "console.path_ok",
  waiting: "console.path_waiting",
  problem: "console.path_problem",
};
const UNAVAILABLE_KEYS: Readonly<Record<VirtualCameraUnavailableReason, MessageKey>> = {
  driver_missing: "console.virtual_camera_driver_missing",
  device_in_use: "console.virtual_camera_device_in_use",
  error: "console.virtual_camera_error",
};
const LIVE_MODES: ReadonlySet<ConsoleMode> = new Set(["live", "frozen", "camera_off", "lost"]);

export function consoleMode(status: Status): ConsoleMode {
  const { session, controls, virtualCamera } = status;
  if (session === null) {
    return "waiting";
  }
  if (session.state === "connecting") {
    return "connecting";
  }
  if (session.state === "awaiting_confirmation") {
    return "confirming";
  }
  if (controls.cameraOff) {
    return "camera_off";
  }
  if (controls.frozen) {
    return "frozen";
  }
  return virtualCamera.source === "frozen" ? "lost" : "live";
}

export function isLiveMode(mode: ConsoleMode): boolean {
  return LIVE_MODES.has(mode);
}

export function hasProblem(status: Status): boolean {
  return status.virtualCamera.state === "unavailable";
}

export function stateBadge(status: Status): Badge {
  return hasProblem(status) ? PROBLEM_BADGE : BADGES[consoleMode(status)];
}

export function problemKey(status: Status): MessageKey | null {
  const { reason } = status.virtualCamera;
  return hasProblem(status) && reason !== null ? UNAVAILABLE_KEYS[reason] : null;
}

export function signalPath(status: Status): PathStep[] {
  const mode = consoleMode(status);
  return [
    step("console.path_phone", phoneState(mode)),
    step("console.path_wifi", networkState(mode)),
    step("console.path_computer", "ok"),
    appsStep(status),
  ];
}

export function currentFacing(status: Status): Facing | null {
  const facing = status.session?.cameraCapabilities?.facingMode;
  return facing === "user" || facing === "environment" ? facing : status.controls.facing;
}

export function otherFacing(facing: Facing | null): Facing {
  return facing === "user" ? "environment" : "user";
}

function phoneState(mode: ConsoleMode): PathState {
  if (mode === "lost") {
    return "problem";
  }
  return mode === "live" || mode === "frozen" ? "ok" : "waiting";
}

function networkState(mode: ConsoleMode): PathState {
  if (mode === "lost") {
    return "problem";
  }
  return isLiveMode(mode) ? "ok" : "waiting";
}

function appsStep(status: Status): PathStep {
  if (hasProblem(status)) {
    return step("console.path_apps", "problem");
  }
  const count = status.virtualCamera.streamingApps;
  if (count === null) {
    return step("console.path_apps", "ok");
  }
  if (count === 0) {
    return { nameKey: "console.path_apps", state: "waiting", noteKey: "console.apps_none" };
  }
  if (count === 1) {
    return { nameKey: "console.path_apps", state: "ok", noteKey: "console.apps_one" };
  }
  return { nameKey: "console.path_apps", state: "ok", noteKey: "console.apps_count", count };
}

function step(nameKey: MessageKey, state: PathState): PathStep {
  return { nameKey, state, noteKey: NOTE_KEYS[state] };
}
