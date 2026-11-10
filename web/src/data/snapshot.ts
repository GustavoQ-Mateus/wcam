import { toBase64 } from "./base64";

export type CanvasColorSpace = "display-p3" | "srgb";

export interface SnapshotFrame {
  id: string;
  capturedAt: number;
  captureDelayMs: number;
  colorSpace: CanvasColorSpace;
  width: number;
  height: number;
  png: Uint8Array;
}

export const SNAPSHOT_CHUNK_BYTES = 45_000;

const PNG_SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10];

export function snapshotMessages({
  id,
  capturedAt,
  captureDelayMs,
  colorSpace,
  width,
  height,
  png,
}: SnapshotFrame): string[] {
  const begin = { type: "snapshot_begin", id, capturedAt, captureDelayMs, colorSpace, width, height };
  return chunkedMessages(begin, "snapshot_chunk", id, png);
}

export function screenshotMessages(id: string, png: Uint8Array): string[] {
  return chunkedMessages({ type: "screenshot_begin", id }, "screenshot_chunk", id, png);
}

export function isPng(bytes: Uint8Array): boolean {
  return PNG_SIGNATURE.every((value, index) => bytes[index] === value);
}

function chunkedMessages(begin: object, chunkType: string, id: string, png: Uint8Array): string[] {
  const chunks = Math.ceil(png.length / SNAPSHOT_CHUNK_BYTES);
  const parts = Array.from({ length: chunks }, (_, index) =>
    JSON.stringify({
      type: chunkType,
      id,
      index,
      data: toBase64(png.subarray(index * SNAPSHOT_CHUNK_BYTES, (index + 1) * SNAPSHOT_CHUNK_BYTES)),
    }),
  );
  return [JSON.stringify({ ...begin, size: png.length, chunks }), ...parts];
}
