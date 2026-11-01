import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { cameraFailureFromError, type CamEvent, type Facing, type FrameSize } from "../data/cam-state";
import { captureConstraints, captureFormat, oppositeFacing } from "./capture";

export interface CameraStream {
  facing: Facing;
  opening: boolean;
  track: MediaStreamTrack | null;
  open: () => void;
  switchCamera: () => void;
  stop: () => void;
}

const INITIAL_FACING: Facing = "user";

export function useCameraStream(
  videoRef: RefObject<HTMLVideoElement | null>,
  onEvent: (event: CamEvent) => void,
): CameraStream {
  const [facing, setFacing] = useState<Facing>(INITIAL_FACING);
  const [opening, setOpening] = useState(false);
  const [track, setTrack] = useState<MediaStreamTrack | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const facingRef = useRef<Facing>(INITIAL_FACING);
  const requestRef = useRef(0);
  const reopenRef = useRef<() => void>(() => undefined);

  const openCamera = useCallback(
    async (nextFacing: Facing) => {
      const request = ++requestRef.current;
      const isCurrent = () => request === requestRef.current;
      stopStream(streamRef.current);
      streamRef.current = null;
      setOpening(true);
      try {
        const stream = await requestStream(nextFacing);
        if (!isCurrent()) {
          stopStream(stream);
          return;
        }
        streamRef.current = stream;
        const frame = await attachStream(videoRef.current, stream);
        if (!isCurrent()) {
          return;
        }
        facingRef.current = nextFacing;
        setFacing(nextFacing);
        setOpening(false);
        setTrack(videoTrack(stream) ?? null);
        onEvent({ type: "granted", capture: captureFormat(videoTrack(stream)?.getSettings() ?? {}, frame), frame });
        videoTrack(stream)?.addEventListener("ended", () => {
          reopenRef.current();
        });
      } catch (error) {
        if (isCurrent()) {
          setOpening(false);
          onEvent({ type: "failed", failure: cameraFailureFromError(error) });
        }
      }
    },
    [videoRef, onEvent],
  );

  const reopenWhenVisible = useCallback(() => {
    if (document.visibilityState === "visible" && videoTrack(streamRef.current)?.readyState === "ended") {
      void openCamera(facingRef.current);
    }
  }, [openCamera]);

  useEffect(() => {
    reopenRef.current = reopenWhenVisible;
    document.addEventListener("visibilitychange", reopenWhenVisible);
    return () => {
      document.removeEventListener("visibilitychange", reopenWhenVisible);
    };
  }, [reopenWhenVisible]);

  const stop = useCallback(() => {
    requestRef.current++;
    stopStream(streamRef.current);
    streamRef.current = null;
    setTrack(null);
    setOpening(false);
  }, []);

  useEffect(
    () => () => {
      requestRef.current++;
      stopStream(streamRef.current);
    },
    [],
  );

  return {
    facing,
    opening,
    track,
    open: () => void openCamera(facingRef.current),
    switchCamera: () => void openCamera(oppositeFacing(facingRef.current)),
    stop,
  };
}

function requestStream(facing: Facing): Promise<MediaStream> {
  if (typeof navigator.mediaDevices?.getUserMedia !== "function") {
    return Promise.reject(new TypeError("getUserMedia is not available"));
  }
  return navigator.mediaDevices.getUserMedia(captureConstraints(facing));
}

async function attachStream(video: HTMLVideoElement | null, stream: MediaStream): Promise<FrameSize> {
  if (!video) {
    throw new TypeError("Viewfinder video is not mounted");
  }
  video.srcObject = stream;
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    await new Promise((resolve) => video.addEventListener("loadeddata", resolve, { once: true }));
  }
  await video.play().catch(() => undefined);
  return { width: video.videoWidth, height: video.videoHeight };
}

function videoTrack(stream: MediaStream | null): MediaStreamTrack | undefined {
  return stream?.getVideoTracks()[0];
}

function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => {
    track.stop();
  });
}
