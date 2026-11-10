import { useEffect, useState } from "react";
import type { VideoFormat } from "./video-format";

export interface FormatChoice {
  pending: VideoFormat | null;
  choose: (format: VideoFormat) => void;
}

const PENDING_TIMEOUT_MS = 2000;

export function useFormatChoice(
  confirmed: VideoFormat | null,
  send: (format: VideoFormat) => void,
  onConfirmed?: () => void,
): FormatChoice {
  const [pending, setPending] = useState<VideoFormat | null>(null);
  const [lastConfirmed, setLastConfirmed] = useState(confirmed);
  if (confirmed !== lastConfirmed) {
    setLastConfirmed(confirmed);
    if (confirmed !== null && confirmed === pending) {
      setPending(null);
      onConfirmed?.();
    }
  }

  useEffect(() => {
    if (pending === null) {
      return;
    }
    const timer = window.setTimeout(() => {
      setPending(null);
    }, PENDING_TIMEOUT_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [pending]);

  return {
    pending,
    choose: (format) => {
      if (format === confirmed) {
        return;
      }
      setPending(format);
      send(format);
    },
  };
}
