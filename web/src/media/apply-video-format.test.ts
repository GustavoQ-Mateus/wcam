import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { applyVideoFormat, FRAME_WAIT_MS, type FrameSource } from "./apply-video-format";

type Delivery = (requested: Size, devicePortrait: boolean) => Size;

interface Size {
  width: number;
  height: number;
}

interface FakeCamera {
  track: MediaStreamTrack;
  frames: FrameSource;
  requests: string[];
  turn: (portrait: boolean) => void;
}

const ROTATION_DELAY_MS = 400;

const rotatesWithDevice: Delivery = (requested, devicePortrait) => {
  const longSide = Math.max(requested.width, requested.height);
  const shortSide = Math.min(requested.width, requested.height);
  return devicePortrait ? { width: shortSide, height: longSide } : { width: longSide, height: shortSide };
};

const readsSensorTerms: Delivery = (requested, devicePortrait) =>
  devicePortrait ? { width: requested.height, height: requested.width } : requested;

const neverRotates: Delivery = (requested) => requested;

function delayedCamera(delivery: Delivery, devicePortrait: boolean): FakeCamera {
  const listeners = new Set<() => void>();
  const requests: string[] = [];
  let portrait = devicePortrait;
  let lastRequest = "";
  let frame: Size = { width: 1920, height: 1080 };
  const frames: FrameSource = {
    get videoWidth() {
      return frame.width;
    },
    get videoHeight() {
      return frame.height;
    },
    addEventListener: (_type, listener) => listeners.add(listener),
    removeEventListener: (_type, listener) => listeners.delete(listener),
  };
  const track = {
    applyConstraints: (constraints: { width: { exact: number }; height: { exact: number } }) => {
      const requested = { width: constraints.width.exact, height: constraints.height.exact };
      const key = `${String(requested.width)}x${String(requested.height)}`;
      requests.push(key);
      if (key !== lastRequest) {
        lastRequest = key;
        const delivered = delivery(requested, portrait);
        setTimeout(() => {
          const changed = delivered.width !== frame.width || delivered.height !== frame.height;
          frame = delivered;
          if (changed) {
            listeners.forEach((listener) => {
              listener();
            });
          }
        }, ROTATION_DELAY_MS);
      }
      return Promise.resolve();
    },
    getSettings: () => frame,
    getCapabilities: () => ({}),
  } as unknown as MediaStreamTrack;
  return {
    track,
    frames,
    requests,
    turn: (next) => {
      portrait = next;
    },
  };
}

async function turnAndApply(camera: FakeCamera, portrait: boolean): Promise<string[]> {
  const before = camera.requests.length;
  camera.turn(portrait);
  const applied = applyVideoFormat(camera.track, camera.frames, "1080p30", portrait, new AbortController().signal);
  await vi.advanceTimersByTimeAsync(FRAME_WAIT_MS + ROTATION_DELAY_MS * 2);
  await applied;
  await vi.advanceTimersByTimeAsync(ROTATION_DELAY_MS * 2);
  return camera.requests.slice(before);
}

function shape(frames: FrameSource): "portrait" | "landscape" {
  return frames.videoHeight > frames.videoWidth ? "portrait" : "landscape";
}

describe("applyVideoFormat", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("a camera that rotates with the device follows upright, lying down and upright with one request each", async () => {
    const camera = delayedCamera(rotatesWithDevice, true);

    const steps = [
      { requests: await turnAndApply(camera, true), shape: shape(camera.frames) },
      { requests: await turnAndApply(camera, false), shape: shape(camera.frames) },
      { requests: await turnAndApply(camera, true), shape: shape(camera.frames) },
    ];

    expect(steps).toEqual([
      { requests: ["1080x1920"], shape: "portrait" },
      { requests: ["1920x1080"], shape: "landscape" },
      { requests: ["1080x1920"], shape: "portrait" },
    ]);
  });

  it("a camera that reads sizes in sensor terms and ignores a repeated size ends matching the screen at every turn", async () => {
    const camera = delayedCamera(readsSensorTerms, true);

    const steps = [
      { requests: await turnAndApply(camera, true), shape: shape(camera.frames) },
      { requests: await turnAndApply(camera, false), shape: shape(camera.frames) },
      { requests: await turnAndApply(camera, true), shape: shape(camera.frames) },
    ];

    expect(steps).toEqual([
      { requests: ["1080x1920", "1920x1080"], shape: "portrait" },
      { requests: ["1080x1920", "1920x1080"], shape: "landscape" },
      { requests: ["1080x1920", "1920x1080"], shape: "portrait" },
    ]);
  });

  it("a camera that never rotates gets the swapped size upright and the plain size lying down", async () => {
    const camera = delayedCamera(neverRotates, true);

    const steps = [
      { requests: await turnAndApply(camera, true), shape: shape(camera.frames) },
      { requests: await turnAndApply(camera, false), shape: shape(camera.frames) },
    ];

    expect(steps).toEqual([
      { requests: ["1080x1920"], shape: "portrait" },
      { requests: ["1920x1080"], shape: "landscape" },
    ]);
  });

  it("a repeated size waits for the frame of the forcing request before asking for the oriented size", async () => {
    const camera = delayedCamera(neverRotates, false);

    const first = await turnAndApply(camera, false);
    const repeated = await turnAndApply(camera, false);

    expect([first, repeated, shape(camera.frames)]).toEqual([["1920x1080"], ["1080x1920", "1920x1080"], "landscape"]);
  });

  it("a new turn before the frame arrives cancels the correction of the old one", async () => {
    const camera = delayedCamera(readsSensorTerms, true);
    const controller = new AbortController();

    const applied = applyVideoFormat(camera.track, camera.frames, "1080p30", true, controller.signal);
    controller.abort();
    await vi.advanceTimersByTimeAsync(FRAME_WAIT_MS + ROTATION_DELAY_MS);
    await applied;

    expect(camera.requests).toEqual(["1080x1920"]);
  });
});
