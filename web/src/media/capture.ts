import type { CaptureFormat, Facing, FrameSize } from "../data/cam-state";

export const CAPTURE_WIDTH = 1920;
export const CAPTURE_HEIGHT = 1080;
export const CAPTURE_FRAME_RATE = 30;

export function captureConstraints(facing: Facing): MediaStreamConstraints {
  return {
    audio: false,
    video: {
      facingMode: facing,
      width: { ideal: CAPTURE_WIDTH },
      height: { ideal: CAPTURE_HEIGHT },
      frameRate: { ideal: CAPTURE_FRAME_RATE },
    },
  };
}

export function isMirrored(facing: Facing): boolean {
  return facing === "user";
}

export function oppositeFacing(facing: Facing): Facing {
  return facing === "user" ? "environment" : "user";
}

export function captureFormat(settings: MediaTrackSettings, frame: FrameSize): CaptureFormat {
  return {
    width: settings.width ?? frame.width,
    height: settings.height ?? frame.height,
    frameRate: Math.round(settings.frameRate ?? 0),
  };
}
