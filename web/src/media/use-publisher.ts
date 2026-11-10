import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { ApiError, createSession } from "../data/api-client";
import type { CamEvent } from "../data/cam-state";
import { confirmationCode, sdpFingerprint } from "../data/confirmation-code";
import { cameraCapabilitiesData, parseControlMessage, setQualityPresetMessage } from "../data/control-message";
import { DEFAULT_QUALITY_PRESET, maxBitrate, type QualityPreset } from "../data/quality-preset";
import { readCameraCapabilities } from "./camera-capabilities";

interface PublisherOptions {
  track: MediaStreamTrack | null;
  shouldStart: boolean;
  keepAlive: boolean;
  takeToken: () => string | null;
  onEvent: (event: CamEvent) => void;
  videoRef: RefObject<HTMLVideoElement | null>;
}

export interface Publisher {
  qualityPreset: QualityPreset | null;
  snapshotRequest: SnapshotRequest | null;
  chooseQualityPreset: (preset: QualityPreset) => void;
  sendPaced: (messages: readonly string[]) => Promise<void>;
}

export interface SnapshotRequest {
  id: string;
  receivedAt: number;
}

interface PublisherSession {
  replaceTrack: (track: MediaStreamTrack) => void;
  chooseQualityPreset: (preset: QualityPreset) => void;
  sendPaced: (messages: readonly string[]) => Promise<void>;
  close: () => void;
}

interface SessionCallbacks {
  onEvent: (event: CamEvent) => void;
  onQualityPreset: (preset: QualityPreset) => void;
  onSnapshotRequest: (request: SnapshotRequest) => void;
  readVideo: () => HTMLVideoElement | null;
}

type SendParameters = RTCRtpSendParameters & { degradationPreference?: string };

const CONTROL_CHANNEL = "control";
const CONTENT_HINT = "detail";
const DEGRADATION_PREFERENCE = "maintain-resolution";
const CONNECTION_FAILED_REASON = "connection_failed";
const UNKNOWN_ERROR_CODE = "unknown";
const BUFFERED_HIGH_BYTES = 1_000_000;
const BUFFERED_LOW_BYTES = 256_000;
const FAILED_CONNECTION_STATES: ReadonlySet<RTCPeerConnectionState> = new Set(["failed", "closed"]);

export function usePublisher({
  track,
  shouldStart,
  keepAlive,
  takeToken,
  onEvent,
  videoRef,
}: PublisherOptions): Publisher {
  const sessionRef = useRef<PublisherSession | null>(null);
  const [qualityPreset, setQualityPreset] = useState<QualityPreset | null>(null);
  const [snapshotRequest, setSnapshotRequest] = useState<SnapshotRequest | null>(null);
  const sendPaced = useCallback((messages: readonly string[]) => {
    return sessionRef.current?.sendPaced(messages) ?? Promise.resolve();
  }, []);

  useEffect(() => {
    if (!shouldStart || !track || sessionRef.current) {
      return;
    }
    const token = takeToken();
    if (token === null) {
      return;
    }
    onEvent({ type: "session_started" });
    sessionRef.current = startSession(track, token, {
      onEvent,
      onQualityPreset: setQualityPreset,
      onSnapshotRequest: setSnapshotRequest,
      readVideo: () => videoRef.current,
    });
  }, [shouldStart, track, takeToken, onEvent, videoRef]);

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

  return {
    qualityPreset,
    snapshotRequest,
    chooseQualityPreset: (preset) => {
      sessionRef.current?.chooseQualityPreset(preset);
    },
    sendPaced,
  };
}

function startSession(
  track: MediaStreamTrack,
  token: string,
  { onEvent, onQualityPreset, onSnapshotRequest, readVideo }: SessionCallbacks,
): PublisherSession {
  const connection = new RTCPeerConnection({ iceServers: [] });
  const channel = connection.createDataChannel(CONTROL_CHANNEL);
  track.contentHint = CONTENT_HINT;
  const { sender } = connection.addTransceiver(track, {
    direction: "sendonly",
    sendEncodings: [{ maxBitrate: maxBitrate(DEFAULT_QUALITY_PRESET) }],
  });
  let currentTrack = track;
  let closed = false;
  let finished = false;
  let events = Promise.resolve();
  let parameterChanges = Promise.resolve();
  const isActive = () => !closed && !finished;
  const emit = (event: CamEvent) => {
    if (isActive()) {
      onEvent(event);
    }
  };
  const changeParameters = (change: (parameters: SendParameters) => void) => {
    parameterChanges = parameterChanges.then(() => applyParameters(sender, change));
  };
  const sendControl = (data: string) => {
    if (channel.readyState === "open") {
      channel.send(data);
    }
  };
  const sendCapabilities = () => {
    const track = currentTrack;
    void readCameraCapabilities(track, readVideo()).then((capabilities) => {
      if (track === currentTrack) {
        sendControl(cameraCapabilitiesData(capabilities));
      }
    });
  };
  const finish = (event: CamEvent) => {
    emit(event);
    finished = true;
  };
  const connectionLost = () => {
    finish({ type: "session_ended", reason: CONNECTION_FAILED_REASON });
  };

  const code = negotiate(connection, token).then((result) => {
    changeParameters(preferResolution);
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
    if (message.type === "quality_preset") {
      changeParameters(limitBitrate(maxBitrate(message.preset)));
      if (isActive()) {
        onQualityPreset(message.preset);
      }
      return;
    }
    if (message.type === "snapshot_request") {
      if (isActive()) {
        onSnapshotRequest({ id: message.id, receivedAt: performance.now() });
      }
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
  channel.bufferedAmountLowThreshold = BUFFERED_LOW_BYTES;
  channel.addEventListener("open", sendCapabilities);
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
      if (nextTrack !== currentTrack) {
        currentTrack = nextTrack;
        sendCapabilities();
      }
    },
    chooseQualityPreset: (preset) => {
      sendControl(setQualityPresetMessage(preset));
    },
    sendPaced: async (messages) => {
      for (const message of messages) {
        if (channel.bufferedAmount > BUFFERED_HIGH_BYTES) {
          await bufferedAmountLow(channel);
        }
        if (!isActive() || channel.readyState !== "open") {
          return;
        }
        channel.send(message);
      }
    },
    close: () => {
      closed = true;
      channel.close();
      connection.close();
    },
  };
}

function bufferedAmountLow(channel: RTCDataChannel): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      channel.removeEventListener("bufferedamountlow", done);
      channel.removeEventListener("close", done);
      resolve();
    };
    channel.addEventListener("bufferedamountlow", done);
    channel.addEventListener("close", done);
  });
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

async function applyParameters(sender: RTCRtpSender, change: (parameters: SendParameters) => void): Promise<void> {
  const parameters: SendParameters = sender.getParameters();
  change(parameters);
  await sender.setParameters(parameters).catch(() => undefined);
}

function preferResolution(parameters: SendParameters): void {
  parameters.degradationPreference = DEGRADATION_PREFERENCE;
}

function limitBitrate(bitrate: number): (parameters: SendParameters) => void {
  return (parameters) => {
    parameters.encodings.forEach((encoding) => {
      encoding.maxBitrate = bitrate;
    });
  };
}
