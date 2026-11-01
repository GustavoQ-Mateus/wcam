import type { ErrorBody, Health } from "./contract";

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
  return requestJson<Health>("/api/health", signal);
}

export async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await send(path, signal);
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw toApiError(body, response.status);
  }
  return body as T;
}

async function send(path: string, signal?: AbortSignal): Promise<Response> {
  try {
    return await fetch(path, signal ? { signal } : {});
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }
    throw new ApiError(NETWORK_ERROR_CODE, NETWORK_ERROR_STATUS, String(error));
  }
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
