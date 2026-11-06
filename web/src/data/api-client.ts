import type {
  CreateSessionRequest,
  CreateSessionResponse,
  ErrorBody,
  Health,
  PairingWindow,
  QualityPresetRequest,
  Status,
} from "./contract";

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

const NETWORK_ERROR_CODE = "network_error";
const UNKNOWN_ERROR_CODE = "unknown";
const NETWORK_ERROR_STATUS = 0;

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export function fetchHealth(signal?: AbortSignal): Promise<Health> {
  return requestJson<Health>("/api/health", signal ? { signal } : {});
}

export function createSession(request: CreateSessionRequest): Promise<CreateSessionResponse> {
  return requestJson<CreateSessionResponse>("/api/sessions", { method: "POST", body: request });
}

export function fetchStatus(signal: AbortSignal): Promise<Status> {
  return requestJson<Status>("/api/status", { signal });
}

export function openPairing(): Promise<PairingWindow> {
  return requestJson<PairingWindow>("/api/pairing", { method: "POST" });
}

export function confirmSession(): Promise<null> {
  return requestJson<null>("/api/sessions/current/confirm", { method: "POST" });
}

export function rejectSession(): Promise<null> {
  return requestJson<null>("/api/sessions/current/reject", { method: "POST" });
}

export function disconnectSession(): Promise<null> {
  return requestJson<null>("/api/sessions/current", { method: "DELETE" });
}

export function changeQualityPreset(request: QualityPresetRequest): Promise<null> {
  return requestJson<null>("/api/quality-preset", { method: "PUT", body: request });
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options);
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw toApiError(body, response.status);
  }
  return body as T;
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  try {
    return await fetch(path, requestInit(options));
  } catch (error) {
    if (options.signal?.aborted) {
      throw error;
    }
    throw new ApiError(NETWORK_ERROR_CODE, NETWORK_ERROR_STATUS, String(error));
  }
}

function requestInit({ method = "GET", body, signal }: RequestOptions): RequestInit {
  const init: RequestInit = { method };
  if (signal) {
    init.signal = signal;
  }
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers = { "Content-Type": "application/json" };
  }
  return init;
}

function toApiError(body: unknown, status: number): ApiError {
  if (!isErrorBody(body)) {
    return new ApiError(UNKNOWN_ERROR_CODE, status, `HTTP ${String(status)}`);
  }
  return new ApiError(body.error.code, status, body.error.message);
}

function isErrorBody(body: unknown): body is ErrorBody {
  if (typeof body !== "object" || body === null || !("error" in body)) {
    return false;
  }
  const { error } = body;
  return typeof error === "object" && error !== null && "code" in error && typeof error.code === "string";
}
