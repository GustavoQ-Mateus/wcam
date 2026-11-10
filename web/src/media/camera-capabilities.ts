import {
  cameraCapabilitiesMessage,
  type CameraCapabilitiesMessage,
  type DeclaredColorSpace,
} from "../data/camera-capabilities";

const VIDEO_KIND = "video";
const FRAME_WAIT_MS = 2000;
const FRAME_CHECK_MS = 100;

type TrackProcessorConstructor = new (init: { track: MediaStreamTrack }) => {
  readable: ReadableStream<VideoFrame>;
};

export async function readCameraCapabilities(
  track: MediaStreamTrack,
  video: HTMLVideoElement | null,
): Promise<CameraCapabilitiesMessage> {
  const colorSpace = await readColorSpace(track, video).catch(() => null);
  return cameraCapabilitiesMessage(
    track.getCapabilities(),
    track.getSettings().facingMode,
    senderVideoCodecs(),
    colorSpace,
  );
}

async function readColorSpace(
  track: MediaStreamTrack,
  video: HTMLVideoElement | null,
): Promise<DeclaredColorSpace | null> {
  if (typeof VideoFrame === "undefined") {
    return null;
  }
  const frame = await trackFrame(track, video);
  if (!frame) {
    return null;
  }
  try {
    return frame.colorSpace.toJSON();
  } finally {
    frame.close();
  }
}

async function trackFrame(track: MediaStreamTrack, video: HTMLVideoElement | null): Promise<VideoFrame | null> {
  if (video && (await videoShowsTrack(video, track))) {
    try {
      return new VideoFrame(video);
    } catch {
      return processorFrame(track);
    }
  }
  return processorFrame(track);
}

async function videoShowsTrack(video: HTMLVideoElement, track: MediaStreamTrack): Promise<boolean> {
  const deadline = Date.now() + FRAME_WAIT_MS;
  while (Date.now() < deadline) {
    const stream = video.srcObject;
    if (
      stream instanceof MediaStream &&
      stream.getVideoTracks().includes(track) &&
      video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
    ) {
      return true;
    }
    await delay(FRAME_CHECK_MS);
  }
  return false;
}

async function processorFrame(track: MediaStreamTrack): Promise<VideoFrame | null> {
  const Processor = (globalThis as { MediaStreamTrackProcessor?: TrackProcessorConstructor }).MediaStreamTrackProcessor;
  if (!Processor) {
    return null;
  }
  const clone = track.clone();
  try {
    const reader = new Processor({ track: clone }).readable.getReader();
    const { value } = await reader.read();
    await reader.cancel();
    return value ?? null;
  } finally {
    clone.stop();
  }
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function senderVideoCodecs(): string[] {
  return RTCRtpSender.getCapabilities(VIDEO_KIND)?.codecs.map((codec) => codec.mimeType) ?? [];
}
