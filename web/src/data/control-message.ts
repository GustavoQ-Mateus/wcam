import type { ControlMessage } from "./contract";

const SESSION_STATE_TYPE = "session_state";

export function parseControlMessage(data: unknown): ControlMessage | null {
  if (typeof data !== "string") {
    return null;
  }
  const message = parseJson(data);
  if (typeof message !== "object" || message === null || !("type" in message) || !("state" in message)) {
    return null;
  }
  if (message.type !== SESSION_STATE_TYPE) {
    return null;
  }
  if (message.state === "awaiting_confirmation" || message.state === "live") {
    return { type: SESSION_STATE_TYPE, state: message.state };
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
