export type PreviewState = "connecting" | "showing" | "waiting" | "stopped";

export type PreviewEvent = "start" | "frame" | "connection_ended" | "no_frame";

export const FIRST_FRAME_TIMEOUT_MS = 5000;

export function nextPreviewState(state: PreviewState, event: PreviewEvent): PreviewState {
  if (event === "start") {
    return "connecting";
  }
  if (state === "stopped") {
    return "stopped";
  }
  if (event === "frame") {
    return "showing";
  }
  if (event === "connection_ended") {
    return "stopped";
  }
  return state === "connecting" ? "stopped" : state;
}
