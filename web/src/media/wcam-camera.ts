import { createColorCanvas, encodePng } from "./color-canvas";

export interface CameraFrame {
  png: Blob;
  width: number;
  height: number;
}

const WCAM_LABEL = "WCam";
const VIDEO_INPUT = "videoinput";
const PREFERRED_WIDTH = 1920;
const PREFERRED_HEIGHT = 1080;

export async function captureWcamFrame(): Promise<CameraFrame> {
  const stream = await openWcamStream();
  try {
    return await captureFrame(stream);
  } finally {
    stopStream(stream);
  }
}

async function openWcamStream(): Promise<MediaStream> {
  const permission = await navigator.mediaDevices.getUserMedia({ video: true });
  if (isWcam(permission.getVideoTracks()[0]?.label)) {
    return permission;
  }
  stopStream(permission);
  const devices = await navigator.mediaDevices.enumerateDevices();
  const wcam = devices.find((device) => device.kind === VIDEO_INPUT && isWcam(device.label));
  if (!wcam) {
    throw new Error("WCam camera not found on this computer");
  }
  return navigator.mediaDevices.getUserMedia({
    video: {
      deviceId: { exact: wcam.deviceId },
      width: { ideal: PREFERRED_WIDTH },
      height: { ideal: PREFERRED_HEIGHT },
    },
  });
}

async function captureFrame(stream: MediaStream): Promise<CameraFrame> {
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.srcObject = stream;
  await video.play();
  await nextFrame(video);
  const { videoWidth: width, videoHeight: height } = video;
  const frame = createColorCanvas(width, height, "srgb");
  if (!frame) {
    throw new Error("Canvas 2D is not available");
  }
  frame.context.drawImage(video, 0, 0, width, height);
  video.srcObject = null;
  return { png: await encodePng(frame.canvas), width, height };
}

function nextFrame(video: HTMLVideoElement): Promise<void> {
  return new Promise((resolve) => {
    video.requestVideoFrameCallback(() => {
      resolve();
    });
  });
}

function isWcam(label: string | undefined): boolean {
  return label?.includes(WCAM_LABEL) ?? false;
}

function stopStream(stream: MediaStream): void {
  stream.getTracks().forEach((track) => {
    track.stop();
  });
}
