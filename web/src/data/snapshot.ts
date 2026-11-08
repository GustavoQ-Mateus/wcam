import type { SampleColorSpace } from "./color-sample";
import { toBase64 } from "./color-sample";

export interface SnapshotFrame {
  id: string;
  capturedAt: number;
  colorSpace: SampleColorSpace;
  width: number;
  height: number;
  png: Uint8Array;
}

export const SNAPSHOT_CHUNK_BYTES = 45_000;

export function snapshotMessages({ id, capturedAt, colorSpace, width, height, png }: SnapshotFrame): string[] {
  const chunks = Math.ceil(png.length / SNAPSHOT_CHUNK_BYTES);
  const begin = { type: "snapshot_begin", id, capturedAt, colorSpace, width, height, size: png.length, chunks };
  const parts = Array.from({ length: chunks }, (_, index) =>
    JSON.stringify({
      type: "snapshot_chunk",
      id,
      index,
      data: toBase64(png.subarray(index * SNAPSHOT_CHUNK_BYTES, (index + 1) * SNAPSHOT_CHUNK_BYTES)),
    }),
  );
  return [JSON.stringify(begin), ...parts];
}
