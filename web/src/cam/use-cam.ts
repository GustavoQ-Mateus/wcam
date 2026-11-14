import { useEffect, useReducer, useRef, type RefObject } from "react";
import type { Controls } from "../data/contract";
import { camReducer, initialCamState, isFinal, isLive, isSession, type CamState, type Facing } from "../data/cam-state";
import { consumePairingToken } from "../data/pairing";
import { screenshotMessages } from "../data/snapshot";
import type { VideoFormat } from "../data/video-format";
import { useVideoFormat } from "../media/use-video-format";
import { useCameraStream, type CameraStream } from "../media/use-camera-stream";
import { oppositeFacing } from "../media/capture";
import { readPngFile } from "../media/screenshot-file";
import { useScreenOrientation } from "../media/use-screen-orientation";
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
  controls: Controls | null;
  start: () => void;
  switchCamera: () => void;
  toggleFreeze: () => void;
  toggleCamera: () => void;
  toggleMirror: () => void;
  togglePreview: () => void;
  chooseVideoFormat: (format: VideoFormat) => void;
  answerCode: (same: boolean) => void;
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
  useScreenOrientation(dispatch);
  const publisher = usePublisher({
    track: camera.track,
    shouldStart: capturing,
    keepAlive: isSession(state),
    takeToken: consumePairingToken,
    onEvent: dispatch,
    videoRef,
  });
  useVideoFormat(
    camera.track,
    videoRef,
    publisher.videoFormat?.format ?? null,
    isLive(state) && state.portrait,
    dispatch,
  );
  useSnapshotResponder(videoRef, publisher.snapshotRequest, state.kind === "live", publisher.sendPaced);

  const { stop } = camera;
  useEffect(() => {
    if (final) {
      stop();
    }
  }, [final, stop]);
  const live = state.kind === "live";
  const controls = live ? publisher.controls : null;
  useControlledCamera(camera, controls);

  return {
    state,
    videoRef,
    facing: camera.facing,
    switching: camera.opening,
    wakeLockUnavailable: wakeLock.unavailable,
    videoFormat: publisher.videoFormat,
    controls,
    start: () => {
      dispatch({ type: "start" });
      camera.open();
    },
    switchCamera: () => {
      if (controls) {
        publisher.changeControls({ facing: oppositeFacing(camera.facing) });
      } else {
        camera.switchCamera();
      }
    },
    toggleFreeze: () => {
      if (controls) {
        publisher.changeControls({ frozen: !controls.frozen });
      }
    },
    toggleCamera: () => {
      if (controls) {
        publisher.changeControls({ cameraOff: !controls.cameraOff });
      }
    },
    toggleMirror: () => {
      if (controls) {
        publisher.changeControls({ mirror: !controls.mirror });
      }
    },
    togglePreview: () => {
      dispatch({ type: "preview_toggled" });
    },
    chooseVideoFormat: publisher.chooseVideoFormat,
    answerCode: (same) => {
      if (same) {
        publisher.confirmCode();
      } else {
        publisher.rejectCode();
      }
    },
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

function useControlledCamera(camera: CameraStream, controls: Controls | null): void {
  const cameraOff = controls?.cameraOff ?? false;
  const facing = controls?.facing ?? null;
  const previousRef = useRef<{ cameraOff: boolean; facing: Facing | null } | null>(null);
  const { stop, openFacing } = camera;
  const currentFacing = camera.facing;

  useEffect(() => {
    if (controls === null) {
      previousRef.current = null;
      return;
    }
    const previous = previousRef.current;
    previousRef.current = { cameraOff, facing };
    if (cameraOff) {
      if (!previous?.cameraOff) {
        stop();
      }
      return;
    }
    if (previous?.cameraOff) {
      openFacing(facing ?? currentFacing);
      return;
    }
    if (previous && facing !== null && facing !== previous.facing && facing !== currentFacing) {
      openFacing(facing);
    }
  }, [controls, cameraOff, facing, currentFacing, stop, openFacing]);
}
