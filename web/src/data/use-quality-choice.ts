import { useEffect, useState } from "react";
import type { QualityPreset } from "./quality-preset";

export interface QualityChoice {
  pending: QualityPreset | null;
  choose: (preset: QualityPreset) => void;
}

const PENDING_TIMEOUT_MS = 2000;

export function useQualityChoice(
  confirmed: QualityPreset | null,
  send: (preset: QualityPreset) => void,
  onConfirmed?: () => void,
): QualityChoice {
  const [pending, setPending] = useState<QualityPreset | null>(null);
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
    choose: (preset) => {
      if (preset === confirmed) {
        return;
      }
      setPending(preset);
      send(preset);
    },
  };
}
