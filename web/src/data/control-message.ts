import type { CameraCapabilitiesMessage } from "./camera-capabilities";
import type { ControlMessage } from "./contract";
import { availableFormats, isVideoFormat, type VideoFormat } from "./video-format";

const SESSION_STATE_TYPE = "session_state";
const VIDEO_FORMAT_TYPE = "video_format";
const SET_VIDEO_FORMAT_TYPE = "set_video_format";
const SNAPSHOT_REQUEST_TYPE = "snapshot_request";

export function parseControlMessage(data: unknown): ControlMessage | null {
  if (typeof data !== "string") {
    return null;
  }
  const message = parseJson(data);
  if (typeof message !== "object" || message === null || !("type" in message)) {
    return null;
  }
  if (message.type === VIDEO_FORMAT_TYPE) {
    return parseVideoFormat(message as Record<string, unknown>);
  }
  if (message.type === SESSION_STATE_TYPE) {
    return parseSessionState(message);
  }
  if (message.type === SNAPSHOT_REQUEST_TYPE) {
    return parseSnapshotRequest(message);
  }
  return null;
}

export function setVideoFormatMessage(format: VideoFormat): string {
  return JSON.stringify({ type: SET_VIDEO_FORMAT_TYPE, format });
}

export function cameraCapabilitiesData(message: CameraCapabilitiesMessage): string {
  return JSON.stringify(message);
}

function parseVideoFormat(message: Record<string, unknown>): ControlMessage | null {
  const { format, width, height, fps, maxBitrate, available } = message;
  if (!isVideoFormat(format) || !Array.isArray(available) || !isNumber(width, height, fps, maxBitrate)) {
    return null;
  }
  return {
    type: VIDEO_FORMAT_TYPE,
    format,
    width: Number(width),
    height: Number(height),
    fps: Number(fps),
    maxBitrate: Number(maxBitrate),
    available: availableFormats(available),
  };
}

function isNumber(...values: unknown[]): boolean {
  return values.every((value) => typeof value === "number" && Number.isFinite(value));
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
