import type { PreviewState } from "./preview-state";

export type PreviewSource = "app" | "webrtc";

export type PreviewSlot = 0 | 1;

export type AppPreviewEvent = "start" | "frame" | "idle";

export type AppPreviewMessage =
  | { type: "preview.buffer"; slot: PreviewSlot; width: number; height: number }
  | { type: "preview.frame"; slot: PreviewSlot; sequence: number }
  | { type: "preview.idle" };

export type PageMessage =
  { type: "preview.start" } | { type: "preview.stop" } | { type: "preview.release"; slot: PreviewSlot };

const NV12_BYTES_PER_PIXEL = 1.5;
const CHROMA_SUBSAMPLING = 2;

export function previewSource(host: { chrome?: { webview?: unknown } }): PreviewSource {
  return host.chrome?.webview ? "app" : "webrtc";
}

export function parseAppPreviewMessage(data: unknown): AppPreviewMessage | null {
  if (!isRecord(data)) {
    return null;
  }
  if (data.type === "preview.idle") {
    return { type: "preview.idle" };
  }
  if (!isSlot(data.slot)) {
    return null;
  }
  if (data.type === "preview.frame" && isCount(data.sequence)) {
    return { type: "preview.frame", slot: data.slot, sequence: data.sequence };
  }
  if (data.type === "preview.buffer" && isFrameSide(data.width) && isFrameSide(data.height)) {
    return { type: "preview.buffer", slot: data.slot, width: data.width, height: data.height };
  }
  return null;
}

export function nv12Size(width: number, height: number): number {
  return width * height * NV12_BYTES_PER_PIXEL;
}

export function isNewerFrame(lastSequence: number | null, sequence: number): boolean {
  return lastSequence === null || sequence > lastSequence;
}

export function appPreviewState(event: AppPreviewEvent): PreviewState {
  if (event === "start") {
    return "connecting";
  }
  return event === "frame" ? "showing" : "stopped";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSlot(value: unknown): value is PreviewSlot {
  return value === 0 || value === 1;
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function isFrameSide(value: unknown): value is number {
  return isCount(value) && value > 0 && value % CHROMA_SUBSAMPLING === 0;
}
