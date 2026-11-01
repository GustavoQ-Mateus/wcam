import { useEffect, useState } from "react";

const WAKE_LOCK_SUPPORTED = "wakeLock" in navigator;

export function useWakeLock(active: boolean): { unavailable: boolean } {
  const [requestFailed, setRequestFailed] = useState(false);

  useEffect(() => {
    if (!active || !WAKE_LOCK_SUPPORTED) {
      return;
    }
    let cancelled = false;
    let sentinel: WakeLockSentinel | null = null;
    const request = () => {
      if (document.visibilityState !== "visible") {
        return;
      }
      navigator.wakeLock.request("screen").then(
        (acquired) => {
          if (cancelled) {
            void acquired.release();
            return;
          }
          sentinel = acquired;
        },
        () => {
          if (!cancelled) {
            setRequestFailed(true);
          }
        },
      );
    };
    request();
    document.addEventListener("visibilitychange", request);
    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", request);
      void sentinel?.release();
    };
  }, [active]);

  return { unavailable: !WAKE_LOCK_SUPPORTED || requestFailed };
}
