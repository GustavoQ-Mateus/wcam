import { describe, expect, it } from "vitest";
import { ApiError } from "../data/api-client";
import type { LibraryVideo } from "../data/contract";
import { createUploadQueue } from "./upload-queue";
import type { VideoUpload } from "./video-upload";

interface FakeUpload {
  file: File;
  progress: (fraction: number) => void;
  resolve: () => void;
  reject: (error: unknown) => void;
  aborted: boolean;
}

function fakeQueue() {
  const uploads: FakeUpload[] = [];
  let nextId = 0;
  const queue = createUploadQueue(
    (file, onProgress): VideoUpload => {
      let resolve = () => {};
      let reject: (error: unknown) => void = () => {};
      const done = new Promise<LibraryVideo>((resolveDone, rejectDone) => {
        resolve = () => {
          resolveDone({} as LibraryVideo);
        };
        reject = rejectDone;
      });
      const fake: FakeUpload = { file, progress: onProgress, resolve, reject, aborted: false };
      uploads.push(fake);
      return {
        done,
        abort: () => {
          fake.aborted = true;
          reject(new ApiError("aborted", 0, "aborted"));
        },
      };
    },
    () => String(++nextId),
  );
  return { queue, uploads };
}

function file(name: string): File {
  return new File([new Uint8Array([1])], name);
}

async function settle(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("upload queue", () => {
  it("added files are sent one at a time in order", () => {
    const { queue, uploads } = fakeQueue();

    queue.add([file("a.mov"), file("b.mov")]);

    expect(uploads.map((upload) => upload.file.name)).toEqual(["a.mov"]);
    expect(queue.items().map((item) => item.state)).toEqual(["sending", "queued"]);
  });

  it("finished upload leaves the queue and starts the next file", async () => {
    const { queue, uploads } = fakeQueue();
    queue.add([file("a.mov"), file("b.mov")]);

    uploads[0]?.resolve();
    await settle();

    expect(uploads.map((upload) => upload.file.name)).toEqual(["a.mov", "b.mov"]);
    expect(queue.items().map((item) => item.name)).toEqual(["b.mov"]);
  });

  it("progress is kept per file", () => {
    const { queue, uploads } = fakeQueue();
    queue.add([file("a.mov"), file("b.mov")]);

    uploads[0]?.progress(0.4);

    expect(queue.items().map((item) => item.fraction)).toEqual([0.4, 0]);
  });

  it("failed upload keeps its error code and the queue moves on", async () => {
    const { queue, uploads } = fakeQueue();
    queue.add([file("a.txt"), file("b.mov")]);

    uploads[0]?.reject(new ApiError("video_unsupported", 422, "Not a video"));
    await settle();

    expect(queue.items()[0]).toMatchObject({ name: "a.txt", state: "failed", errorCode: "video_unsupported" });
    expect(uploads[1]?.file.name).toBe("b.mov");
  });

  it("dismissing a failed upload removes it", async () => {
    const { queue, uploads } = fakeQueue();
    queue.add([file("a.txt")]);
    uploads[0]?.reject(new ApiError("video_too_large", 413, "Too large"));
    await settle();

    queue.dismiss("1");

    expect(queue.items()).toEqual([]);
  });

  it("stopping aborts the current upload and empties the queue", async () => {
    const { queue, uploads } = fakeQueue();
    queue.add([file("a.mov"), file("b.mov")]);

    queue.stop();
    await settle();

    expect(uploads[0]?.aborted).toBe(true);
    expect(uploads).toHaveLength(1);
    expect(queue.items()).toEqual([]);
  });

  it("subscribers hear every change", () => {
    const { queue } = fakeQueue();
    let changes = 0;
    queue.subscribe(() => {
      changes += 1;
    });

    queue.add([file("a.mov")]);

    expect(changes).toBeGreaterThan(0);
  });
});
