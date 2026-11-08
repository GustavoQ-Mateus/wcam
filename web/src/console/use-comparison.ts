import { useEffect, useRef, useState } from "react";
import { ApiError, createComparison, fetchComparison, uploadComparisonImage } from "../data/api-client";
import type { Comparison } from "../data/contract";
import { captureWcamFrame } from "../media/wcam-camera";

export type ComparisonView =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "failed"; reason: string }
  | { kind: "ready"; comparison: Comparison; pcImageUrl: string | null; screen: ScreenUpload };

export type ScreenUpload = { kind: "none" } | { kind: "sending" } | { kind: "failed"; code: string };

export interface ComparisonControls {
  view: ComparisonView;
  capture: () => void;
  addScreen: (file: File) => void;
}

const POLL_INTERVAL_MS = 250;
const SCREEN_POLL_INTERVAL_MS = 1000;
const WAIT_LIMIT_MS = 15_000;
const TIMEOUT_REASON = "timeout";
const UNKNOWN_ERROR_CODE = "unknown";

export function useComparison(): ComparisonControls {
  const [view, setView] = useState<ComparisonView>({ kind: "idle" });
  const pcImageUrlRef = useRef<string | null>(null);
  const activeRef = useRef(0);

  useEffect(
    () => () => {
      activeRef.current += 1;
      revoke(pcImageUrlRef.current);
    },
    [],
  );

  const waitingScreenId = view.kind === "ready" && !view.comparison.screen ? view.comparison.id : null;
  useEffect(() => {
    if (!waitingScreenId) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setInterval(() => {
      fetchComparison(waitingScreenId, controller.signal).then(
        (comparison) => {
          if (comparison.screen && comparison.screenDifference) {
            setView((current) =>
              current.kind === "ready" && current.comparison.id === comparison.id
                ? { ...current, comparison, screen: { kind: "none" } }
                : current,
            );
          }
        },
        () => undefined,
      );
    }, SCREEN_POLL_INTERVAL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [waitingScreenId]);

  const capture = () => {
    if (view.kind === "pending") {
      return;
    }
    const run = activeRef.current + 1;
    activeRef.current = run;
    revoke(pcImageUrlRef.current);
    pcImageUrlRef.current = null;
    setView({ kind: "pending" });
    const isCurrent = () => activeRef.current === run;
    runComparison(isCurrent).then(
      ({ comparison, pcImageUrl }) => {
        if (!isCurrent()) {
          revoke(pcImageUrl);
          return;
        }
        pcImageUrlRef.current = pcImageUrl;
        setView(
          comparison.state === "ready"
            ? { kind: "ready", comparison, pcImageUrl, screen: { kind: "none" } }
            : { kind: "failed", reason: comparison.reason ?? TIMEOUT_REASON },
        );
      },
      (error: unknown) => {
        if (isCurrent()) {
          setView({ kind: "failed", reason: errorCodeOf(error) });
        }
      },
    );
  };

  const addScreen = (file: File) => {
    if (view.kind !== "ready" || view.screen.kind === "sending") {
      return;
    }
    const run = activeRef.current;
    const isCurrent = () => activeRef.current === run;
    const { id } = view.comparison;
    setView({ ...view, screen: { kind: "sending" } });
    sendScreen(id, file, isCurrent).then(
      (comparison) => {
        if (isCurrent()) {
          setView((current) =>
            current.kind === "ready" ? { ...current, comparison, screen: { kind: "none" } } : current,
          );
        }
      },
      (error: unknown) => {
        if (isCurrent()) {
          setView((current) =>
            current.kind === "ready" ? { ...current, screen: { kind: "failed", code: errorCodeOf(error) } } : current,
          );
        }
      },
    );
  };

  return { view, capture, addScreen };
}

async function runComparison(isCurrent: () => boolean): Promise<{ comparison: Comparison; pcImageUrl: string | null }> {
  const frame = captureWcamFrame().catch(() => null);
  const { id } = await createComparison();
  const pcFrame = await frame;
  if (pcFrame) {
    await uploadComparisonImage(id, "pc", pcFrame.png);
  }
  const comparison = await waitFor(id, isCurrent, (current) => current.state !== "pending");
  return { comparison, pcImageUrl: pcFrame ? URL.createObjectURL(pcFrame.png) : null };
}

async function sendScreen(id: string, file: File, isCurrent: () => boolean): Promise<Comparison> {
  await uploadComparisonImage(id, "screen", file);
  return waitFor(id, isCurrent, (current) => current.screen !== null && current.screenDifference !== null);
}

async function waitFor(
  id: string,
  isCurrent: () => boolean,
  isDone: (comparison: Comparison) => boolean,
): Promise<Comparison> {
  const deadline = Date.now() + WAIT_LIMIT_MS;
  let comparison = await fetchComparison(id);
  while (!isDone(comparison) && isCurrent() && Date.now() < deadline) {
    await delay(POLL_INTERVAL_MS);
    comparison = await fetchComparison(id);
  }
  if (!isDone(comparison) && isCurrent()) {
    throw new ApiError(TIMEOUT_REASON, 0, "The comparison did not finish in time");
  }
  return comparison;
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function revoke(url: string | null): void {
  if (url) {
    URL.revokeObjectURL(url);
  }
}

function errorCodeOf(error: unknown): string {
  return error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE;
}
