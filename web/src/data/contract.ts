import type { CameraCapabilitiesMessage } from "./camera-capabilities";
import type { QualityPreset } from "./quality-preset";

export type Surface = "console" | "phone";

export interface Health {
  status: "ok";
  version: string;
  surface: Surface;
}

export interface ErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export interface PairingWindow {
  url: string;
  qrSvg: string;
  expiresAt: string;
}

export type SessionState = "connecting" | "awaiting_confirmation" | "live";
export type EndReason =
  "rejected" | "disconnected_by_pc" | "disconnected_by_phone" | "connection_failed" | "confirmation_timeout";

export interface Video {
  width: number;
  height: number;
  fps: number;
  bitrateKbps: number;
  codec: string;
  framesScaled: number;
  colorRange: "full" | "limited" | "unspecified";
  colorMatrix: string;
}

export interface Session {
  id: string;
  state: SessionState;
  deviceName: string | null;
  remoteIp: string;
  startedAt: string;
  confirmationCode: string | null;
  video: Video | null;
  cameraCapabilities: Omit<CameraCapabilitiesMessage, "type"> | null;
}

export type VirtualCameraUnavailableReason = "driver_missing" | "device_in_use" | "error";

export interface VirtualCamera {
  state: "active" | "unavailable";
  backend: "media_foundation" | "obs" | "fake";
  reason: VirtualCameraUnavailableReason | null;
  output: { width: number; height: number; fps: number };
  source: "phone" | "frozen" | "placeholder";
}

export interface Quality {
  ssim: number | null;
  minimum: number | null;
  frames: number;
}

export interface Status {
  pairing: { expiresAt: string } | null;
  session: Session | null;
  lastEnded: { reason: EndReason; at: string } | null;
  virtualCamera: VirtualCamera;
  qualityPreset: QualityPreset;
  process: { cpuPercent: number };
  quality: Quality | null;
}

export interface CreateSessionRequest {
  token: string;
  sdp: string;
}

export interface CreateSessionResponse {
  sessionId: string;
  sdp: string;
  confirmationNonce: string;
}

export type ControlMessage =
  | { type: "session_state"; state: "awaiting_confirmation" }
  | { type: "session_state"; state: "live" }
  | { type: "session_state"; state: "ended"; reason: string }
  | { type: "quality_preset"; preset: QualityPreset };

export interface QualityPresetRequest {
  preset: QualityPreset;
}
