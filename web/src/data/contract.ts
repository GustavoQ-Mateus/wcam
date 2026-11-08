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
  colorCalibration: ColorCalibration;
}

export interface ColorCalibration {
  state: "measuring" | "applied" | "default";
  deltaE: number | null;
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
  devTools: boolean;
}

export type ComparisonState = "pending" | "ready" | "failed";

export interface ImageDifference {
  captureGapMs: number;
  correlation: number;
  mirrored: boolean;
  deltaE2000: { mean: number; median: number; p90: number };
  deltaL: number;
  chromaRatio: number;
  hueShiftDegrees: number;
  grid: { columns: number; rows: number; deltaE2000: number[] };
}

export interface Comparison {
  id: string;
  state: ComparisonState;
  reason: string | null;
  requestedAt: string;
  phone: { capturedAt: string; colorSpace: string; width: number; height: number } | null;
  pc: { receivedAt: string; width: number; height: number } | null;
  calibration: { state: ColorCalibration["state"]; deltaE: number | null; tables: Record<"y" | "u" | "v", number[]> };
  difference: ImageDifference | null;
  screen: { receivedAt: string; width: number; height: number; colorSpace: string } | null;
  screenDifference: { phone: ImageDifference; pc: ImageDifference } | null;
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
  | { type: "quality_preset"; preset: QualityPreset }
  | { type: "snapshot_request"; id: string };

export interface QualityPresetRequest {
  preset: QualityPreset;
}
