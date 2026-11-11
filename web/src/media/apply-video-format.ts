import { constraintFailure } from "../data/constraint-failure";
import { formatConstraints, matchesScreen, type FormatConstraints, type VideoFormat } from "../data/video-format";
import { continuousModes } from "./camera-modes";

export interface FrameSource {
  readonly videoWidth: number;
  readonly videoHeight: number;
  addEventListener: (type: "resize", listener: () => void) => void;
  removeEventListener: (type: "resize", listener: () => void) => void;
}

export const FRAME_WAIT_MS = 1500;

const lastSizes = new WeakMap<MediaStreamTrack, string>();

export async function applyVideoFormat(
  track: MediaStreamTrack,
  frames: FrameSource,
  format: VideoFormat,
  screenPortrait: boolean,
  signal: AbortSignal,
): Promise<void> {
  const oriented = formatConstraints(format, screenPortrait);
  const other = formatConstraints(format, !screenPortrait);
  if (
    lastSizes.get(track) === sizeKey(oriented) &&
    !(await forceReconfiguration(track, frames, format, other, signal))
  ) {
    return;
  }
  const nextFrame = waitForFrame(frames, signal);
  if (!(await applySize(track, format, oriented))) {
    return;
  }
  await nextFrame;
  if (signal.aborted || frameMatchesScreen(frames, screenPortrait)) {
    return;
  }
  await applySize(track, format, other);
}

async function forceReconfiguration(
  track: MediaStreamTrack,
  frames: FrameSource,
  format: VideoFormat,
  other: FormatConstraints,
  signal: AbortSignal,
): Promise<boolean> {
  const otherFrame = waitForFrame(frames, signal);
  if (!(await applySize(track, format, other))) {
    return false;
  }
  await otherFrame;
  return !signal.aborted;
}

function frameMatchesScreen(frames: FrameSource, screenPortrait: boolean): boolean {
  const width = frames.videoWidth;
  const height = frames.videoHeight;
  return width === 0 || height === 0 || matchesScreen({ width, height }, screenPortrait);
}

async function applySize(track: MediaStreamTrack, format: VideoFormat, size: FormatConstraints): Promise<boolean> {
  try {
    await track.applyConstraints(size);
  } catch (error) {
    console.warn(constraintFailure(format, error));
    return false;
  }
  lastSizes.set(track, sizeKey(size));
  // Chromium keeps the old size when camera modes come in the same call.
  const advanced = continuousModes(track);
  if (advanced.length > 0) {
    await track.applyConstraints({ ...size, advanced }).catch((error: unknown) => {
      console.warn(constraintFailure(format, error));
    });
  }
  return true;
}

function sizeKey(size: FormatConstraints): string {
  return `${String(size.width.exact)}x${String(size.height.exact)}`;
}

function waitForFrame(frames: FrameSource, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      frames.removeEventListener("resize", done);
      signal.removeEventListener("abort", done);
      resolve();
    };
    const timer = setTimeout(done, FRAME_WAIT_MS);
    frames.addEventListener("resize", done);
    signal.addEventListener("abort", done);
  });
}
