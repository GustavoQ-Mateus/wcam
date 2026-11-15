import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { closePreview, openPreview } from "../data/api-client";
import { FIRST_FRAME_TIMEOUT_MS, nextPreviewState, type PreviewEvent, type PreviewState } from "../data/preview-state";
import { iceGatheringComplete } from "./ice-gathering";

export interface Preview {
  attach: (video: HTMLVideoElement | null) => void;
  state: PreviewState;
  showAgain: () => void;
}

const PREVIEW_CONFIGURATION: RTCConfiguration = { iceServers: [] };
const CLOSED_STATES: ReadonlySet<RTCPeerConnectionState> = new Set(["failed", "closed"]);
const FRAME_EVENTS = ["resize", "playing"] as const;

export function usePreview(enabled: boolean): Preview {
  const [state, dispatch] = useReducer(nextPreviewState, "connecting");
  const [attempt, setAttempt] = useState(0);
  const [startedFor, setStartedFor] = useState(enabled);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const frameRef = useRef<(() => void) | null>(null);

  if (startedFor !== enabled) {
    setStartedFor(enabled);
    dispatch("start");
  }

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const connection = new RTCPeerConnection(PREVIEW_CONFIGURATION);
    let running = true;
    let stopped = false;
    const show = (stream: MediaStream | null) => {
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    };
    const stop = (event: PreviewEvent) => {
      if (!running || stopped) {
        return;
      }
      stopped = true;
      window.clearTimeout(firstFrameTimer);
      connection.close();
      show(null);
      dispatch(event);
    };
    const firstFrameTimer = window.setTimeout(() => {
      stop("no_frame");
    }, FIRST_FRAME_TIMEOUT_MS);
    frameRef.current = () => {
      if (running && !stopped) {
        window.clearTimeout(firstFrameTimer);
        dispatch("frame");
      }
    };
    connection.addTransceiver("video", { direction: "recvonly" });
    connection.addEventListener("track", (event) => {
      if (running && !stopped) {
        show(event.streams[0] ?? new MediaStream([event.track]));
      }
    });
    connection.addEventListener("connectionstatechange", () => {
      if (CLOSED_STATES.has(connection.connectionState)) {
        stop("connection_ended");
      }
    });
    negotiate(connection).catch(() => {
      stop("connection_ended");
    });
    return () => {
      running = false;
      window.clearTimeout(firstFrameTimer);
      frameRef.current = null;
      connection.close();
      show(null);
      if (!stopped) {
        void closePreview().catch(() => undefined);
      }
    };
  }, [enabled, attempt]);

  const handleFrame = useCallback((event: Event) => {
    if (event.currentTarget instanceof HTMLVideoElement && event.currentTarget.videoWidth > 0) {
      frameRef.current?.();
    }
  }, []);
  const attach = useCallback(
    (video: HTMLVideoElement | null) => {
      FRAME_EVENTS.forEach((name) => videoRef.current?.removeEventListener(name, handleFrame));
      videoRef.current = video;
      if (video) {
        FRAME_EVENTS.forEach((name) => {
          video.addEventListener(name, handleFrame);
        });
        video.srcObject = streamRef.current;
      }
    },
    [handleFrame],
  );
  const showAgain = useCallback(() => {
    dispatch("start");
    setAttempt((count) => count + 1);
  }, []);
  return { attach, state, showAgain };
}

async function negotiate(connection: RTCPeerConnection): Promise<void> {
  await connection.setLocalDescription(await connection.createOffer());
  await iceGatheringComplete(connection);
  const answer = await openPreview(connection.localDescription?.sdp ?? "");
  if (connection.signalingState !== "closed") {
    await connection.setRemoteDescription({ type: "answer", sdp: answer.sdp });
  }
}
