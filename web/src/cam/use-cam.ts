import { useReducer, useRef, type RefObject } from "react";
import { camReducer, initialCamState, type CamState, type Facing } from "../data/cam-state";
import { useCameraStream } from "../media/use-camera-stream";
import { useOrientation } from "../media/use-orientation";
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
  const wakeLock = useWakeLock(state.kind === "ready" || state.kind === "preview_off");
  useOrientation(videoRef, dispatch);

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
