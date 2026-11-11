import { describe, expect, it, vi } from "vitest";
import { applyVideoFormat } from "./apply-video-format";

interface FakeCamera {
  track: MediaStreamTrack;
  requests: string[];
}

function rotatingCamera(devicePortrait: boolean): FakeCamera {
  let size = { width: 1920, height: 1080 };
  const requests: string[] = [];
  const track = {
    applyConstraints: vi.fn((constraints: { width?: { exact: number }; height?: { exact: number } }) => {
      const width = constraints.width?.exact ?? size.width;
      const height = constraints.height?.exact ?? size.height;
      requests.push(`${String(width)}x${String(height)}`);
      const longSide = Math.max(width, height);
      const shortSide = Math.min(width, height);
      size = devicePortrait ? { width: shortSide, height: longSide } : { width: longSide, height: shortSide };
      return Promise.resolve();
    }),
    getSettings: () => size,
    getCapabilities: () => ({}),
  } as unknown as MediaStreamTrack;
  return { track, requests };
}

function plainCamera(): FakeCamera {
  let size = { width: 1920, height: 1080 };
  const requests: string[] = [];
  const track = {
    applyConstraints: vi.fn((constraints: { width: { exact: number }; height: { exact: number } }) => {
      size = { width: constraints.width.exact, height: constraints.height.exact };
      requests.push(`${String(size.width)}x${String(size.height)}`);
      return Promise.resolve();
    }),
    getSettings: () => size,
    getCapabilities: () => ({}),
  } as unknown as MediaStreamTrack;
  return { track, requests };
}

describe("applyVideoFormat", () => {
  it("a camera that rotates by itself gets the landscape size once and is upright on an upright screen", async () => {
    const camera = rotatingCamera(true);

    await applyVideoFormat(camera.track, "1080p30", true);
    await applyVideoFormat(camera.track, "1080p30", true);

    expect(camera.requests).toEqual(["1920x1080", "1920x1080"]);
    expect(camera.track.getSettings()).toEqual({ width: 1080, height: 1920 });
  });

  it("a camera that does not rotate gets the swapped size on an upright screen", async () => {
    const camera = plainCamera();

    await applyVideoFormat(camera.track, "1080p30", true);

    expect(camera.requests).toEqual(["1920x1080", "1080x1920"]);
    expect(camera.track.getSettings()).toEqual({ width: 1080, height: 1920 });
  });

  it("lying down, the landscape size is enough for both kinds of camera", async () => {
    const rotating = rotatingCamera(false);
    const plain = plainCamera();

    await applyVideoFormat(rotating.track, "720p30", false);
    await applyVideoFormat(plain.track, "720p30", false);

    expect([rotating.requests, plain.requests]).toEqual([["1280x720"], ["1280x720"]]);
  });
});
