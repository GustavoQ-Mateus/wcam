import { useEffect, useReducer, useRef, type RefObject } from "react";
import { camReducer, initialCamState, isFinal, isLive, isSession, type CamState, type Facing } from "../data/cam-state";
import { consumePairingToken } from "../data/pairing";
import { screenshotMessages } from "../data/snapshot";
import type { VideoFormat } from "../data/video-format";
import { useVideoFormat } from "../media/use-video-format";
import { useCameraStream } from "../media/use-camera-stream";
import { readPngFile } from "../media/screenshot-file";
import { useOrientation } from "../media/use-orientation";
import { usePublisher, type VideoFormatMessage } from "../media/use-publisher";
import { useSnapshotResponder } from "../media/use-snapshot-responder";
import { useWakeLock } from "../media/use-wake-lock";

export interface Cam {
  state: CamState;
  videoRef: RefObject<HTMLVideoElement | null>;
  facing: Facing;
  switching: boolean;
  wakeLockUnavailable: boolean;
  videoFormat: VideoFormatMessage | null;
  start: () => void;
  switchCamera: () => void;
  togglePreview: () => void;
  chooseVideoFormat: (format: VideoFormat) => void;
  screenshotRequested: boolean;
  sendScreenshot: (file: File) => Promise<boolean>;
}

export function useCam(hasPairing: boolean): Cam {
  const [state, dispatch] = useReducer(camReducer, hasPairing, initialCamState);
  const videoRef = useRef<HTMLVideoElement>(null);
  const camera = useCameraStream(videoRef, dispatch);
  const capturing = state.kind === "ready" || state.kind === "preview_off";
  const final = isFinal(state);
  const wakeLock = useWakeLock(capturing || isSession(state));
  useOrientation(videoRef, dispatch);
  const publisher = usePublisher({
    track: camera.track,
    shouldStart: capturing,
    keepAlive: isSession(state),
    takeToken: consumePairingToken,
    onEvent: dispatch,
    videoRef,
  });
  useVideoFormat(camera.track, publisher.videoFormat?.format ?? null, isLive(state) && state.portrait);
  useSnapshotResponder(videoRef, publisher.snapshotRequest, state.kind === "live", publisher.sendPaced);

  const { stop } = camera;
  useEffect(() => {
    if (final) {
      stop();
    }
  }, [final, stop]);

  return {
    state,
    videoRef,
    facing: camera.facing,
    switching: camera.opening,
    wakeLockUnavailable: wakeLock.unavailable,
    videoFormat: publisher.videoFormat,
    start: () => {
      dispatch({ type: "start" });
      camera.open();
    },
    switchCamera: camera.switchCamera,
    togglePreview: () => {
      dispatch({ type: "preview_toggled" });
    },
    chooseVideoFormat: publisher.chooseVideoFormat,
    screenshotRequested: state.kind === "live" && publisher.snapshotRequest !== null,
    sendScreenshot: async (file) => {
      const request = publisher.snapshotRequest;
      const png = await readPngFile(file);
      if (!request || !png) {
        return false;
      }
      await publisher.sendPaced(screenshotMessages(request.id, png));
      return true;
    },
  };
}
