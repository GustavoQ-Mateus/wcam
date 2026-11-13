import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { ApiError, createSession } from "../data/api-client";
import type { CamEvent } from "../data/cam-state";
import { confirmationCode, sdpFingerprint } from "../data/confirmation-code";
import type { ControlMessage } from "../data/contract";
import { cameraCapabilitiesData, parseControlMessage, setVideoFormatMessage } from "../data/control-message";
import { createPublisherGate } from "../data/publisher-gate";
import { DEFAULT_VIDEO_FORMAT, formatSpec, type VideoFormat } from "../data/video-format";
import { readCameraCapabilities } from "./camera-capabilities";
import { iceGatheringComplete } from "./ice-gathering";

interface PublisherOptions {
  track: MediaStreamTrack | null;
  shouldStart: boolean;
  keepAlive: boolean;
  takeToken: () => string | null;
  onEvent: (event: CamEvent) => void;
  videoRef: RefObject<HTMLVideoElement | null>;
}

export interface Publisher {
  videoFormat: VideoFormatMessage | null;
  snapshotRequest: SnapshotRequest | null;
  chooseVideoFormat: (format: VideoFormat) => void;
  sendPaced: (messages: readonly string[]) => Promise<void>;
  confirmCode: () => void;
  rejectCode: () => void;
}

export type VideoFormatMessage = Extract<ControlMessage, { type: "video_format" }>;

export interface SnapshotRequest {
  id: string;
  receivedAt: number;
}

interface PublisherSession {
  replaceTrack: (track: MediaStreamTrack) => void;
  chooseVideoFormat: (format: VideoFormat) => void;
  sendPaced: (messages: readonly string[]) => Promise<void>;
  confirmCode: () => void;
  rejectCode: () => void;
  close: () => void;
}

interface SessionCallbacks {
  onEvent: (event: CamEvent) => void;
  onVideoFormat: (message: VideoFormatMessage) => void;
  onSnapshotRequest: (request: SnapshotRequest) => void;
  readVideo: () => HTMLVideoElement | null;
}

type SendParameters = RTCRtpSendParameters & { degradationPreference?: string };

const CONTROL_CHANNEL = "control";
const CONTENT_HINT = "detail";
const DEGRADATION_PREFERENCE = "maintain-resolution";
const CONNECTION_FAILED_REASON = "connection_failed";
const REJECTED_REASON = "rejected";
const REJECT_GRACE_MS = 3000;
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
  const [videoFormat, setVideoFormat] = useState<VideoFormatMessage | null>(null);
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
      onVideoFormat: setVideoFormat,
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
    videoFormat,
    snapshotRequest,
    chooseVideoFormat: (format) => {
      sessionRef.current?.chooseVideoFormat(format);
    },
    sendPaced,
    confirmCode: () => {
      sessionRef.current?.confirmCode();
    },
    rejectCode: () => {
      sessionRef.current?.rejectCode();
    },
  };
}

function startSession(
  track: MediaStreamTrack,
  token: string,
  { onEvent, onVideoFormat, onSnapshotRequest, readVideo }: SessionCallbacks,
): PublisherSession {
  const connection = new RTCPeerConnection({ iceServers: [] });
  const channel = connection.createDataChannel(CONTROL_CHANNEL);
  const { sender } = connection.addTransceiver("video", {
    direction: "sendonly",
    sendEncodings: [{ maxBitrate: formatSpec(DEFAULT_VIDEO_FORMAT).maxBitrate }],
  });
  const sendOnChannel = (data: string) => {
    if (channel.readyState === "open") {
      channel.send(data);
    }
  };
  const gate = createPublisherGate<MediaStreamTrack>({
    replaceTrack: (nextTrack) => void sender.replaceTrack(nextTrack),
    send: sendOnChannel,
  });
  let currentTrack = track;
  let rejectGrace: ReturnType<typeof setTimeout> | undefined;
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
  const sendCapabilities = () => {
    const track = currentTrack;
    if (!gate.live) {
      return;
    }
    void readCameraCapabilities(track, readVideo()).then((capabilities) => {
      if (track === currentTrack) {
        gate.send(cameraCapabilitiesData(capabilities));
      }
    });
  };
  const setCameraTrack = (nextTrack: MediaStreamTrack) => {
    nextTrack.contentHint = CONTENT_HINT;
    gate.setTrack(nextTrack);
  };
  const finish = (event: CamEvent) => {
    clearTimeout(rejectGrace);
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
    if (message.type === "video_format") {
      changeParameters(limitBitrate(message.maxBitrate));
      if (isActive()) {
        onVideoFormat(message);
      }
      return;
    }
    if (message.type === "snapshot_request") {
      if (isActive() && gate.live) {
        onSnapshotRequest({ id: message.id, receivedAt: performance.now() });
      }
      return;
    }
    if (message.type === "confirmation") {
      if (message.phone) {
        emit({ type: "code_answered", same: true });
      }
      return;
    }
    events = events.then(async () => {
      if (message.state === "awaiting_confirmation") {
        emit({ type: "session_awaiting_confirmation", code: await code });
      } else if (message.state === "live") {
        gate.goLive();
        sendCapabilities();
        emit({ type: "session_live" });
      } else {
        finish({ type: "session_ended", reason: message.reason });
      }
    });
  });
  channel.bufferedAmountLowThreshold = BUFFERED_LOW_BYTES;
  channel.addEventListener("close", connectionLost);
  connection.addEventListener("connectionstatechange", () => {
    if (FAILED_CONNECTION_STATES.has(connection.connectionState)) {
      connectionLost();
    }
  });

  setCameraTrack(track);

  return {
    replaceTrack: (nextTrack) => {
      setCameraTrack(nextTrack);
      if (nextTrack !== currentTrack) {
        currentTrack = nextTrack;
        sendCapabilities();
      }
    },
    chooseVideoFormat: (format) => {
      gate.send(setVideoFormatMessage(format));
    },
    sendPaced: async (messages) => {
      for (const message of messages) {
        if (channel.bufferedAmount > BUFFERED_HIGH_BYTES) {
          await bufferedAmountLow(channel);
        }
        if (!isActive() || !gate.live || channel.readyState !== "open") {
          return;
        }
        channel.send(message);
      }
    },
    confirmCode: () => {
      gate.confirmCode();
      emit({ type: "code_answered", same: true });
    },
    rejectCode: () => {
      gate.rejectCode();
      emit({ type: "code_answered", same: false });
      rejectGrace = setTimeout(() => {
        finish({ type: "session_ended", reason: REJECTED_REASON });
      }, REJECT_GRACE_MS);
    },
    close: () => {
      clearTimeout(rejectGrace);
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
