import { useCallback, useEffect, useRef, useState } from "react";
import { closePreview, openPreview } from "../data/api-client";
import { iceGatheringComplete } from "./ice-gathering";

export interface Preview {
  attach: (video: HTMLVideoElement | null) => void;
  showing: boolean;
}

const PREVIEW_CONFIGURATION: RTCConfiguration = { iceServers: [] };
const CLOSED_STATES: ReadonlySet<RTCPeerConnectionState> = new Set(["failed", "closed"]);

export function usePreview(enabled: boolean): Preview {
  const [showing, setShowing] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const connection = new RTCPeerConnection(PREVIEW_CONFIGURATION);
    let open = true;
    const show = (stream: MediaStream | null) => {
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setShowing(stream !== null);
    };
    connection.addTransceiver("video", { direction: "recvonly" });
    connection.addEventListener("track", (event) => {
      if (open) {
        show(event.streams[0] ?? new MediaStream([event.track]));
      }
    });
    connection.addEventListener("connectionstatechange", () => {
      if (CLOSED_STATES.has(connection.connectionState)) {
        show(null);
      }
    });
    negotiate(connection).catch(() => {
      show(null);
    });
    return () => {
      open = false;
      connection.close();
      show(null);
      void closePreview().catch(() => undefined);
    };
  }, [enabled]);

  const attach = useCallback((video: HTMLVideoElement | null) => {
    videoRef.current = video;
    if (video) {
      video.srcObject = streamRef.current;
    }
  }, []);
  return { attach, showing };
}

async function negotiate(connection: RTCPeerConnection): Promise<void> {
  await connection.setLocalDescription(await connection.createOffer());
  await iceGatheringComplete(connection);
  const answer = await openPreview(connection.localDescription?.sdp ?? "");
  if (connection.signalingState !== "closed") {
    await connection.setRemoteDescription({ type: "answer", sdp: answer.sdp });
  }
}
