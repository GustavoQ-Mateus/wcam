import { createColorCanvas, encodePng } from "./color-canvas";

export interface CameraFrame {
  png: Blob;
  width: number;
  height: number;
}

export interface WcamCamera {
  capture: () => Promise<CameraFrame>;
  close: () => void;
}

export type WcamCameraProblem = "camera_denied" | "camera_missing" | "camera_busy" | "camera_failed";

export class WcamCameraError extends Error {
  readonly problem: WcamCameraProblem;

  constructor(problem: WcamCameraProblem, message: string) {
    super(message);
    this.name = "WcamCameraError";
    this.problem = problem;
  }
}

const WCAM_LABEL = "WCam";
const VIDEO_INPUT = "videoinput";
const PREFERRED_WIDTH = 1920;
const PREFERRED_HEIGHT = 1080;
const PROBLEM_BY_ERROR_NAME: Readonly<Record<string, WcamCameraProblem>> = {
  NotAllowedError: "camera_denied",
  SecurityError: "camera_denied",
  NotFoundError: "camera_missing",
  OverconstrainedError: "camera_missing",
  NotReadableError: "camera_busy",
  AbortError: "camera_busy",
};

export async function openWcamCamera(): Promise<WcamCamera> {
  const stream = await openWcamStream().catch((error: unknown) => {
    throw cameraError(error);
  });
  const video = await playStream(stream).catch((error: unknown) => {
    stopStream(stream);
    throw cameraError(error);
  });
  return {
    capture: () => captureFrame(video),
    close: () => {
      video.srcObject = null;
      stopStream(stream);
    },
  };
}

async function openWcamStream(): Promise<MediaStream> {
  if (!navigator.mediaDevices) {
    throw new WcamCameraError("camera_denied", "Camera access needs a secure page");
  }
  const permission = await navigator.mediaDevices.getUserMedia({ video: true });
  if (isWcam(permission.getVideoTracks()[0]?.label)) {
    return permission;
  }
  stopStream(permission);
  const devices = await navigator.mediaDevices.enumerateDevices();
  const wcam = devices.find((device) => device.kind === VIDEO_INPUT && isWcam(device.label));
  if (!wcam) {
    throw new WcamCameraError("camera_missing", "WCam camera not found on this computer");
  }
  return navigator.mediaDevices.getUserMedia({
    video: {
      deviceId: { exact: wcam.deviceId },
      width: { ideal: PREFERRED_WIDTH },
      height: { ideal: PREFERRED_HEIGHT },
    },
  });
}

async function playStream(stream: MediaStream): Promise<HTMLVideoElement> {
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.srcObject = stream;
  await video.play();
  await nextFrame(video);
  return video;
}

async function captureFrame(video: HTMLVideoElement): Promise<CameraFrame> {
  const { videoWidth: width, videoHeight: height } = video;
  const frame = createColorCanvas(width, height, "srgb");
  if (!frame) {
    throw new WcamCameraError("camera_failed", "Canvas 2D is not available");
  }
  frame.context.drawImage(video, 0, 0, width, height);
  return { png: await encodePng(frame.canvas), width, height };
}

function nextFrame(video: HTMLVideoElement): Promise<void> {
  return new Promise((resolve) => {
    video.requestVideoFrameCallback(() => {
      resolve();
    });
  });
}

function cameraError(error: unknown): WcamCameraError {
  if (error instanceof WcamCameraError) {
    return error;
  }
  const name = error instanceof DOMException ? error.name : "";
  return new WcamCameraError(PROBLEM_BY_ERROR_NAME[name] ?? "camera_failed", String(error));
}

function isWcam(label: string | undefined): boolean {
  return label?.includes(WCAM_LABEL) ?? false;
}

function stopStream(stream: MediaStream): void {
  stream.getTracks().forEach((track) => {
    track.stop();
  });
}
