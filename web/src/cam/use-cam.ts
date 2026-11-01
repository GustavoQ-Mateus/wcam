import { useEffect, useReducer, useRef, type RefObject } from "react";
import { camReducer, initialCamState, isFinal, isSession, type CamState, type Facing } from "../data/cam-state";
import { consumePairingToken } from "../data/pairing";
import { useCameraStream } from "../media/use-camera-stream";
import { useOrientation } from "../media/use-orientation";
import { usePublisher } from "../media/use-publisher";
import { useWakeLock } from "../media/use-wake-lock";

export interface Cam {
  state: CamState;
  videoRef: RefObject<HTMLVideoElement | null>;
  facing: Facing;
  switching: boolean;
  wakeLockUnavailable: boolean;
  start: () => void;
  switchCamera: () => void;
  togglePreview: () => void;
}

export function useCam(hasPairing: boolean): Cam {
  const [state, dispatch] = useReducer(camReducer, hasPairing, initialCamState);
  const videoRef = useRef<HTMLVideoElement>(null);
  const camera = useCameraStream(videoRef, dispatch);
  const capturing = state.kind === "ready" || state.kind === "preview_off";
  const final = isFinal(state);
  const wakeLock = useWakeLock(capturing || isSession(state));
  useOrientation(videoRef, dispatch);
  usePublisher({
    track: camera.track,
    shouldStart: capturing,
    keepAlive: isSession(state),
    takeToken: consumePairingToken,
    onEvent: dispatch,
  });

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
    start: () => {
      dispatch({ type: "start" });
      camera.open();
    },
    switchCamera: camera.switchCamera,
    togglePreview: () => {
      dispatch({ type: "preview_toggled" });
    },
  };
}
