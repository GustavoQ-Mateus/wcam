import { useEffect, type RefObject } from "react";

export function useCtrlWheel(target: RefObject<HTMLElement | null>, onWheel: (event: WheelEvent) => void): void {
  useEffect(() => {
    const element = target.current;
    if (!element) {
      return;
    }
    const listener = (event: WheelEvent) => {
      if (!event.ctrlKey) {
        return;
      }
      event.preventDefault();
      onWheel(event);
    };
    element.addEventListener("wheel", listener, { passive: false });
    return () => {
      element.removeEventListener("wheel", listener);
    };
  });
}
