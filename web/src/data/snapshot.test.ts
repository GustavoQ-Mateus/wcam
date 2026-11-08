import { describe, expect, it } from "vitest";
import { isPng, screenshotMessages, SNAPSHOT_CHUNK_BYTES, snapshotMessages, type SnapshotFrame } from "./snapshot";

const FRAME: Omit<SnapshotFrame, "png"> = {
  id: "c1",
  capturedAt: 1793991387130,
  colorSpace: "display-p3",
  width: 1920,
  height: 1080,
};

function decode(data: string): number[] {
  return [...atob(data)].map((character) => character.charCodeAt(0));
}

describe("snapshotMessages", () => {
  it("begins with the frame data, the png size and the chunk count", () => {
    const png = new Uint8Array(SNAPSHOT_CHUNK_BYTES * 2 + 1);

    expect(JSON.parse(snapshotMessages({ ...FRAME, png })[0] ?? "")).toEqual({
      type: "snapshot_begin",
      ...FRAME,
      size: SNAPSHOT_CHUNK_BYTES * 2 + 1,
      chunks: 3,
    });
  });

  it("splits the png in numbered chunks of at most 45000 bytes that rebuild it", () => {
    const png = Uint8Array.from({ length: SNAPSHOT_CHUNK_BYTES + 3 }, (_, index) => index % 251);

    const chunks = snapshotMessages({ ...FRAME, png })
      .slice(1)
      .map((message) => JSON.parse(message) as { type: string; id: string; index: number; data: string });

    expect(chunks.map(({ type, id, index }) => ({ type, id, index }))).toEqual([
      { type: "snapshot_chunk", id: "c1", index: 0 },
      { type: "snapshot_chunk", id: "c1", index: 1 },
    ]);
    expect(decode(chunks[0]?.data ?? "")).toHaveLength(SNAPSHOT_CHUNK_BYTES);
    expect(chunks.flatMap((chunk) => decode(chunk.data))).toEqual([...png]);
  });

  it("every message fits the data channel limit of 65536 bytes", () => {
    const png = new Uint8Array(SNAPSHOT_CHUNK_BYTES * 3);

    expect(Math.max(...snapshotMessages({ ...FRAME, png }).map((message) => message.length))).toBeLessThan(65_536);
  });
});

describe("screenshotMessages", () => {
  it("begins with the comparison id, size and chunk count and then sends numbered chunks", () => {
    const png = new Uint8Array(SNAPSHOT_CHUNK_BYTES + 1);

    const messages = screenshotMessages("c2", png).map((message) => JSON.parse(message) as Record<string, unknown>);

    expect(messages[0]).toEqual({ type: "screenshot_begin", id: "c2", size: SNAPSHOT_CHUNK_BYTES + 1, chunks: 2 });
    expect(messages.slice(1).map(({ type, id, index }) => ({ type, id, index }))).toEqual([
      { type: "screenshot_chunk", id: "c2", index: 0 },
      { type: "screenshot_chunk", id: "c2", index: 1 },
    ]);
  });
});

describe("isPng", () => {
  it("accepts bytes that start with the png signature", () => {
    expect(isPng(new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0]))).toBe(true);
  });

  it("refuses a jpeg and a file too short to be a png", () => {
    expect([isPng(new Uint8Array([255, 216, 255, 224])), isPng(new Uint8Array([137, 80]))]).toEqual([false, false]);
  });
});
