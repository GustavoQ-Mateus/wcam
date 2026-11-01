import { useEffect, useRef } from "react";
import { ApiError, createSession } from "../data/api-client";
import type { CamEvent } from "../data/cam-state";
import { confirmationCode, sdpFingerprint } from "../data/confirmation-code";
import { parseControlMessage } from "../data/control-message";

interface PublisherOptions {
  track: MediaStreamTrack | null;
  shouldStart: boolean;
  keepAlive: boolean;
  takeToken: () => string | null;
  onEvent: (event: CamEvent) => void;
}

interface PublisherSession {
  replaceTrack: (track: MediaStreamTrack) => void;
  close: () => void;
}

type SendParameters = RTCRtpSendParameters & { degradationPreference?: string };

const CONTROL_CHANNEL = "control";
const CONTENT_HINT = "detail";
const MAX_BITRATE = 10_000_000;
const DEGRADATION_PREFERENCE = "maintain-resolution";
const CONNECTION_FAILED_REASON = "connection_failed";
const UNKNOWN_ERROR_CODE = "unknown";
const FAILED_CONNECTION_STATES: ReadonlySet<RTCPeerConnectionState> = new Set(["failed", "closed"]);

export function usePublisher({ track, shouldStart, keepAlive, takeToken, onEvent }: PublisherOptions): void {
  const sessionRef = useRef<PublisherSession | null>(null);

  useEffect(() => {
    if (!shouldStart || !track || sessionRef.current) {
      return;
    }
    const token = takeToken();
    if (token === null) {
      return;
    }
    onEvent({ type: "session_started" });
    sessionRef.current = startSession(track, token, onEvent);
  }, [shouldStart, track, takeToken, onEvent]);

  useEffect(() => {
    if (track) {
      sessionRef.current?.replaceTrack(track);
    }
  }, [track]);

  useEffect(() => {
    if (keepAlive || shouldStart) {
      return;
    }
    sessionRef.current?.close();
    sessionRef.current = null;
  }, [keepAlive, shouldStart]);

  useEffect(
    () => () => {
      sessionRef.current?.close();
    },
    [],
  );
}

function startSession(track: MediaStreamTrack, token: string, onEvent: (event: CamEvent) => void): PublisherSession {
  const connection = new RTCPeerConnection({ iceServers: [] });
  const channel = connection.createDataChannel(CONTROL_CHANNEL);
  track.contentHint = CONTENT_HINT;
  const { sender } = connection.addTransceiver(track, {
    direction: "sendonly",
    sendEncodings: [{ maxBitrate: MAX_BITRATE }],
  });
  let closed = false;
  let finished = false;
  let events = Promise.resolve();
  const emit = (event: CamEvent) => {
    if (!closed && !finished) {
      onEvent(event);
    }
  };
  const finish = (event: CamEvent) => {
    emit(event);
    finished = true;
  };
  const connectionLost = () => {
    finish({ type: "session_ended", reason: CONNECTION_FAILED_REASON });
  };

  const code = negotiate(connection, token).then(async (result) => {
    await preferResolution(sender);
    return result;
  });
  code.catch((error: unknown) => {
    finish({ type: "session_failed", code: error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE });
  });

  channel.addEventListener("message", (event: MessageEvent<unknown>) => {
    const message = parseControlMessage(event.data);
    if (!message) {
      return;
    }
    events = events.then(async () => {
      if (message.state === "awaiting_confirmation") {
        emit({ type: "session_awaiting_confirmation", code: await code });
      } else if (message.state === "live") {
        emit({ type: "session_live" });
      } else {
        finish({ type: "session_ended", reason: message.reason });
      }
    });
  });
  channel.addEventListener("close", connectionLost);
  connection.addEventListener("connectionstatechange", () => {
    if (FAILED_CONNECTION_STATES.has(connection.connectionState)) {
      connectionLost();
    }
  });

  return {
    replaceTrack: (nextTrack) => {
      nextTrack.contentHint = CONTENT_HINT;
      void sender.replaceTrack(nextTrack);
    },
    close: () => {
      closed = true;
      channel.close();
      connection.close();
    },
  };
}

async function negotiate(connection: RTCPeerConnection, token: string): Promise<string> {
  await connection.setLocalDescription(await connection.createOffer());
  await iceGatheringComplete(connection);
  const offer = connection.localDescription?.sdp ?? "";
  const answer = await createSession({ token, sdp: offer });
  await connection.setRemoteDescription({ type: "answer", sdp: answer.sdp });
  const phoneFingerprint = sdpFingerprint(offer);
  const agentFingerprint = sdpFingerprint(answer.sdp);
  if (!phoneFingerprint || !agentFingerprint) {
    throw new TypeError("Session description without a sha-256 fingerprint");
  }
  return confirmationCode(answer.confirmationNonce, phoneFingerprint, agentFingerprint);
}

function iceGatheringComplete(connection: RTCPeerConnection): Promise<void> {
  if (connection.iceGatheringState === "complete") {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const check = () => {
      if (connection.iceGatheringState === "complete") {
        connection.removeEventListener("icegatheringstatechange", check);
        resolve();
      }
    };
    connection.addEventListener("icegatheringstatechange", check);
  });
}

async function preferResolution(sender: RTCRtpSender): Promise<void> {
  const parameters: SendParameters = sender.getParameters();
  parameters.degradationPreference = DEGRADATION_PREFERENCE;
  await sender.setParameters(parameters).catch(() => undefined);
}
