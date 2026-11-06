import { useEffect, useState } from "react";
import {
  ApiError,
  changeQualityPreset,
  confirmSession,
  disconnectSession,
  fetchStatus,
  openPairing,
  rejectSession,
} from "./api-client";
import type { PairingWindow, Status } from "./contract";
import type { QualityPreset } from "./quality-preset";

export interface ConsoleData {
  status: Status | null;
  receivedAt: number;
  qrSvg: string | null;
  errorCode: string | null;
  newPairing: () => void;
  confirm: () => void;
  reject: () => void;
  disconnect: () => void;
  chooseQualityPreset: (preset: QualityPreset) => void;
}

const POLL_INTERVAL_MS = 250;
const UNKNOWN_ERROR_CODE = "unknown";

export function useConsole(): ConsoleData {
  const [status, setStatus] = useState<Status | null>(null);
  const [receivedAt, setReceivedAt] = useState(0);
  const [pairing, setPairing] = useState<PairingWindow | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const load = () => {
      fetchStatus(controller.signal).then(
        (next) => {
          setStatus(next);
          setReceivedAt(Date.now());
        },
        (error: unknown) => {
          if (!controller.signal.aborted) {
            setErrorCode(errorCodeOf(error));
          }
        },
      );
    };
    load();
    const timer = window.setInterval(load, POLL_INTERVAL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
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
    chooseQualityPreset: (preset) => {
      run(() => changeQualityPreset({ preset }));
    },
  };
}

function errorCodeOf(error: unknown): string {
  return error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE;
}
