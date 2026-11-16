import { useCallback, useEffect, useRef, useState } from "react";

export function useElementWidth<T extends HTMLElement>(): [(element: T | null) => void, number] {
  const [width, setWidth] = useState(0);
  const observerRef = useRef<ResizeObserver | null>(null);

  useEffect(
    () => () => {
      observerRef.current?.disconnect();
    },
    [],
  );

  const attach = useCallback((element: T | null) => {
    observerRef.current?.disconnect();
    observerRef.current = null;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver(([entry]) => {
      setWidth(entry?.contentRect.width ?? 0);
    });
    observer.observe(element);
    observerRef.current = observer;
  }, []);

  return [attach, width];
}
