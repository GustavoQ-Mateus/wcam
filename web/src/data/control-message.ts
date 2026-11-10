import type { CameraCapabilitiesMessage } from "./camera-capabilities";
import type { ControlMessage } from "./contract";
import { isQualityPreset, type QualityPreset } from "./quality-preset";

const SESSION_STATE_TYPE = "session_state";
const QUALITY_PRESET_TYPE = "quality_preset";
const SET_QUALITY_PRESET_TYPE = "set_quality_preset";
const SNAPSHOT_REQUEST_TYPE = "snapshot_request";

export function parseControlMessage(data: unknown): ControlMessage | null {
  if (typeof data !== "string") {
    return null;
  }
  const message = parseJson(data);
  if (typeof message !== "object" || message === null || !("type" in message)) {
    return null;
  }
  if (message.type === QUALITY_PRESET_TYPE) {
    return parseQualityPreset(message);
  }
  if (message.type === SESSION_STATE_TYPE) {
    return parseSessionState(message);
  }
  if (message.type === SNAPSHOT_REQUEST_TYPE) {
    return parseSnapshotRequest(message);
  }
  return null;
}

export function setQualityPresetMessage(preset: QualityPreset): string {
  return JSON.stringify({ type: SET_QUALITY_PRESET_TYPE, preset });
}

export function cameraCapabilitiesData(message: CameraCapabilitiesMessage): string {
  return JSON.stringify(message);
}

function parseQualityPreset(message: object): ControlMessage | null {
  if (!("preset" in message) || !isQualityPreset(message.preset)) {
    return null;
  }
  return { type: QUALITY_PRESET_TYPE, preset: message.preset };
}

function parseSnapshotRequest(message: object): ControlMessage | null {
  if (!("id" in message) || typeof message.id !== "string" || message.id === "") {
    return null;
  }
  return { type: SNAPSHOT_REQUEST_TYPE, id: message.id };
}

function parseSessionState(message: object): ControlMessage | null {
  if (!("state" in message)) {
    return null;
  }
  if (message.state === "awaiting_confirmation") {
    return { type: SESSION_STATE_TYPE, state: "awaiting_confirmation" };
  }
  if (message.state === "live") {
    return { type: SESSION_STATE_TYPE, state: "live" };
  }
  if (message.state === "ended") {
    const reason = "reason" in message && typeof message.reason === "string" ? message.reason : "";
    return { type: SESSION_STATE_TYPE, state: "ended", reason };
  }
  return null;
}

function parseJson(data: string): unknown {
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}
