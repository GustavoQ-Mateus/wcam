import type { CameraCapabilitiesMessage } from "./camera-capabilities";
import type { Facing } from "./cam-state";
import type { VideoFormat } from "./video-format";

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
  orientation: "landscape" | "portrait";
  colorRange: "full" | "limited" | "unspecified";
  colorMatrix: string;
  colorCorrection: ColorCorrection;
}

export interface ColorCorrection {
  state: "applied" | "default";
  transfer: string | null;
  display: "apple" | "standard";
}

export interface Session {
  id: string;
  state: SessionState;
  deviceName: string | null;
  remoteIp: string;
  startedAt: string;
  confirmationCode: string | null;
  confirmations: { pc: boolean; phone: boolean };
  rtpPacketsBeforeLive: number;
  video: Video | null;
  cameraCapabilities: Omit<CameraCapabilitiesMessage, "type"> | null;
}

export type VirtualCameraUnavailableReason = "driver_missing" | "device_in_use" | "error";

export interface VirtualCamera {
  state: "active" | "unavailable";
  backend: "media_foundation" | "obs" | "fake";
  reason: VirtualCameraUnavailableReason | null;
  output: { width: number; height: number; fps: number };
  source: "phone" | "frozen" | "held" | "camera_off" | "placeholder";
  streamingApps: number | null;
}

export interface Controls {
  frozen: boolean;
  cameraOff: boolean;
  mirror: boolean;
  facing: Facing | null;
}

export type ControlsPatch = Partial<Omit<Controls, "facing">> & { facing?: Facing };

export interface Quality {
  ssim: number | null;
  minimum: number | null;
  frames: number;
}

export interface Status {
  pairing: { expiresAt: string } | null;
  session: Session | null;
  lastEnded: { reason: EndReason; at: string; rtpPacketsBeforeLive: number } | null;
  virtualCamera: VirtualCamera;
  videoFormat: VideoFormatStatus;
  process: { cpuPercent: number };
  quality: Quality | null;
  devTools: boolean;
  controls: Controls;
}

export interface VideoFormatStatus {
  selected: VideoFormat;
  available: VideoFormat[];
  camera: VideoFormat;
  pending: boolean;
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
  correction: ColorCorrection & { tables: Record<"y" | "u" | "v", number[]> };
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
  | { type: "confirmation"; pc: boolean; phone: boolean }
  | ({ type: "controls" } & Controls)
  | { type: "stats_request"; enabled: boolean }
  | {
      type: "video_format";
      format: VideoFormat;
      width: number;
      height: number;
      fps: number;
      maxBitrate: number;
      available: VideoFormat[];
    }
  | { type: "snapshot_request"; id: string };

export interface VideoFormatRequest {
  format: VideoFormat;
}
