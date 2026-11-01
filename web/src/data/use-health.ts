import { useEffect, useState } from "react";
import { ApiError, fetchHealth } from "./api-client";

export type HealthState =
  { kind: "checking" } | { kind: "running"; version: string } | { kind: "failed"; code: string };

const UNKNOWN_ERROR_CODE = "unknown";

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ kind: "checking" });

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal).then(
      (health) => {
        setState({ kind: "running", version: health.version });
      },
      (error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setState({ kind: "failed", code: error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE });
      },
    );
    return () => {
      controller.abort();
    };
  }, []);

  return state;
}
