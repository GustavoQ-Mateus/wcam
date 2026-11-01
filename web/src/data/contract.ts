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
}

export interface Session {
  id: string;
  state: SessionState;
  deviceName: string | null;
  remoteIp: string;
  startedAt: string;
  confirmationCode: string | null;
  video: Video | null;
}

export interface Status {
  pairing: { expiresAt: string } | null;
  session: Session | null;
  lastEnded: { reason: EndReason; at: string } | null;
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
  | { type: "session_state"; state: "awaiting_confirmation" | "live" }
  | { type: "session_state"; state: "ended"; reason: string };
