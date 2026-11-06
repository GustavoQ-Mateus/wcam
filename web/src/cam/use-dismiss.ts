import { useEffect, type RefObject } from "react";

const ESCAPE_KEY = "Escape";

export function useDismiss(ref: RefObject<HTMLElement | null>, active: boolean, onDismiss: () => void): void {
  useEffect(() => {
    if (!active) {
      return;
    }
    const dismissOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !ref.current?.contains(event.target)) {
        onDismiss();
      }
    };
    const dismissOnEscape = (event: KeyboardEvent) => {
      if (event.key === ESCAPE_KEY) {
        onDismiss();
      }
    };
    document.addEventListener("pointerdown", dismissOutside);
    document.addEventListener("keydown", dismissOnEscape);
    return () => {
      document.removeEventListener("pointerdown", dismissOutside);
      document.removeEventListener("keydown", dismissOnEscape);
    };
  }, [ref, active, onDismiss]);
}
