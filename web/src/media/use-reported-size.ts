import { useCallback } from "react";

export function useReportedSize(
  report: (width: number, height: number) => void,
): (element: HTMLElement | null) => void {
  return useCallback(
    (element: HTMLElement | null) => {
      if (!element) {
        return;
      }
      let last = "";
      const observer = new ResizeObserver(([entry]) => {
        const box = entry?.borderBoxSize[0];
        if (!box) {
          return;
        }
        const width = Math.ceil(box.inlineSize);
        const height = Math.ceil(box.blockSize);
        const size = `${String(width)}x${String(height)}`;
        if (size !== last) {
          last = size;
          report(width, height);
        }
      });
      observer.observe(element);
      return () => {
        observer.disconnect();
      };
    },
    [report],
  );
}
