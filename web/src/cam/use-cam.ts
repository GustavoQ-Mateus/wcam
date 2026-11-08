import { useEffect, useReducer, useRef, type RefObject } from "react";
import { camReducer, initialCamState, isFinal, isSession, type CamState, type Facing } from "../data/cam-state";
import { consumePairingToken } from "../data/pairing";
import { screenshotMessages } from "../data/snapshot";
import type { QualityPreset } from "../data/quality-preset";
import { useCameraStream } from "../media/use-camera-stream";
import { useColorSample } from "../media/use-color-sample";
import { readPngFile } from "../media/screenshot-file";
import { useOrientation } from "../media/use-orientation";
import { usePublisher } from "../media/use-publisher";
import { useSnapshotResponder } from "../media/use-snapshot-responder";
import { useWakeLock } from "../media/use-wake-lock";

export interface Cam {
  state: CamState;
  videoRef: RefObject<HTMLVideoElement | null>;
  facing: Facing;
  switching: boolean;
  wakeLockUnavailable: boolean;
  qualityPreset: QualityPreset | null;
  start: () => void;
  switchCamera: () => void;
  togglePreview: () => void;
  chooseQualityPreset: (preset: QualityPreset) => void;
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
  });
  const sampling = state.kind === "live" && !state.portrait && !camera.opening;
  useColorSample(videoRef, camera.track, sampling, publisher.sendControl);
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
    qualityPreset: publisher.qualityPreset,
    start: () => {
      dispatch({ type: "start" });
      camera.open();
    },
    switchCamera: camera.switchCamera,
    togglePreview: () => {
      dispatch({ type: "preview_toggled" });
    },
    chooseQualityPreset: publisher.chooseQualityPreset,
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
