import { useSyncExternalStore } from "react";

export function useDocumentVisible(): boolean {
  return useSyncExternalStore(subscribe, () => document.visibilityState === "visible");
}

function subscribe(onChange: () => void): () => void {
  document.addEventListener("visibilitychange", onChange);
  return () => {
    document.removeEventListener("visibilitychange", onChange);
  };
}
