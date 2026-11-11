import { useEffect } from "react";
import type { CamEvent } from "../data/cam-state";

const PORTRAIT_QUERY = "(orientation: portrait)";

export function isScreenPortrait(): boolean {
  return window.matchMedia(PORTRAIT_QUERY).matches;
}

export function useScreenOrientation(onEvent: (event: CamEvent) => void): void {
  useEffect(() => {
    const query = window.matchMedia(PORTRAIT_QUERY);
    const report = () => {
      onEvent({ type: "orientation_changed", portrait: query.matches });
    };
    query.addEventListener("change", report);
    return () => {
      query.removeEventListener("change", report);
    };
  }, [onEvent]);
}
