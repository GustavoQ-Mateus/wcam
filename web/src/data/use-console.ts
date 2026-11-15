import { useEffect, useState } from "react";
import {
  ApiError,
  changeControls,
  changeVideoFormat,
  confirmSession,
  disconnectSession,
  openPairing,
  rejectSession,
} from "./api-client";
import type { ControlsPatch, PairingWindow, Status } from "./contract";
import type { VideoFormat } from "./video-format";

export interface ConsoleData {
  status: Status | null;
  receivedAt: number;
  qrSvg: string | null;
  errorCode: string | null;
  newPairing: () => void;
  confirm: () => void;
  reject: () => void;
  disconnect: () => void;
  chooseVideoFormat: (format: VideoFormat) => void;
  changeControls: (patch: ControlsPatch) => void;
}

const EVENTS_PATH = "/api/events";
const STATUS_EVENT = "status";
const NETWORK_ERROR_CODE = "network_error";
const UNKNOWN_ERROR_CODE = "unknown";

export function useConsole(): ConsoleData {
  const [status, setStatus] = useState<Status | null>(null);
  const [receivedAt, setReceivedAt] = useState(0);
  const [pairing, setPairing] = useState<PairingWindow | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  useEffect(() => {
    const events = new EventSource(EVENTS_PATH);
    events.addEventListener(STATUS_EVENT, (event) => {
      setStatus(JSON.parse(event.data as string) as Status);
      setReceivedAt(Date.now());
      setErrorCode((current) => (current === NETWORK_ERROR_CODE ? null : current));
    });
    events.addEventListener("error", () => {
      setErrorCode(NETWORK_ERROR_CODE);
    });
    return () => {
      events.close();
    };
  }, []);

  const run = (action: () => Promise<unknown>) => {
    setErrorCode(null);
    action().catch((error: unknown) => {
      setErrorCode(errorCodeOf(error));
    });
  };

  const qrSvg = pairing && status?.pairing ? pairing.qrSvg : null;

  return {
    status,
    receivedAt,
    qrSvg,
    errorCode,
    newPairing: () => {
      run(async () => {
        const opened = await openPairing();
        setPairing(opened);
        setStatus((current) => current && { ...current, pairing: { expiresAt: opened.expiresAt } });
      });
    },
    confirm: () => {
      run(confirmSession);
    },
    reject: () => {
      run(rejectSession);
    },
    disconnect: () => {
      run(disconnectSession);
    },
    chooseVideoFormat: (format) => {
      run(() => changeVideoFormat({ format }));
    },
    changeControls: (patch) => {
      run(() => changeControls(patch));
    },
  };
}

function errorCodeOf(error: unknown): string {
  return error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE;
}
