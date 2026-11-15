import { describe, expect, it } from "vitest";
import { ApiError } from "../data/api-client";
import { uploadVideo } from "./video-upload";

const CREATED_STATUS = 201;
const TOO_LARGE_STATUS = 413;
const UNPROCESSABLE_STATUS = 422;
const VIDEO_FILE = {
  name: "reunião.mov",
  durationSeconds: 6,
  width: 1280,
  height: 720,
  fps: 30,
  codec: "h264",
};

class FakeRequest extends EventTarget {
  readonly upload = new EventTarget();
  readonly headers: Record<string, string> = {};
  method = "";
  url = "";
  body: unknown = null;
  status = 0;
  responseText = "";
  aborted = false;

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }

  send(body: unknown) {
    this.body = body;
  }

  abort() {
    this.aborted = true;
    this.dispatchEvent(new Event("abort"));
  }

  progress(loaded: number, total: number) {
    this.upload.dispatchEvent(Object.assign(new Event("progress"), { loaded, total, lengthComputable: true }));
  }

  respond(status: number, body: unknown) {
    this.status = status;
    this.responseText = JSON.stringify(body);
    this.dispatchEvent(new Event("load"));
  }
}

function start(fractions: number[] = []) {
  const request = new FakeRequest();
  const file = new File([new Uint8Array([1, 2, 3])], "reunião.mov");
  const upload = uploadVideo(
    file,
    (fraction) => fractions.push(fraction),
    () => request as unknown as XMLHttpRequest,
  );
  return { request, file, upload };
}

describe("video upload", () => {
  it("video upload sends the raw file with its encoded name as a put", () => {
    const { request, file } = start();

    expect(request.method).toBe("PUT");
    expect(request.url).toBe("/api/video-source/file");
    expect(request.headers).toEqual({
      "Content-Type": "application/octet-stream",
      "X-File-Name": "reuni%C3%A3o.mov",
    });
    expect(request.body).toBe(file);
  });

  it("video upload reports progress as a fraction of the file", () => {
    const fractions: number[] = [];
    const { request } = start(fractions);

    request.progress(25, 100);
    request.progress(100, 100);

    expect(fractions).toEqual([0.25, 1]);
  });

  it("finished video upload resolves with the video details", async () => {
    const { request, upload } = start();

    request.respond(CREATED_STATUS, VIDEO_FILE);

    await expect(upload.done).resolves.toEqual(VIDEO_FILE);
  });

  it("video too large is rejected with its error code", async () => {
    const { request, upload } = start();

    request.respond(TOO_LARGE_STATUS, { error: { code: "video_too_large", message: "Too large" } });

    await expect(upload.done).rejects.toMatchObject({ code: "video_too_large", status: TOO_LARGE_STATUS });
  });

  it("file that is not a video is rejected with video_unsupported", async () => {
    const { request, upload } = start();

    request.respond(UNPROCESSABLE_STATUS, { error: { code: "video_unsupported", message: "Not a video" } });

    await expect(upload.done).rejects.toMatchObject({ code: "video_unsupported" });
  });

  it("network failure during video upload is rejected with network_error", async () => {
    const { request, upload } = start();

    request.dispatchEvent(new Event("error"));

    const error = await upload.done.catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "network_error" });
  });

  it("aborted video upload stops the request and is rejected with aborted", async () => {
    const { request, upload } = start();

    upload.abort();

    expect(request.aborted).toBe(true);
    await expect(upload.done).rejects.toMatchObject({ code: "aborted" });
  });
});
