import { useEffect, useRef } from "react";

export function useFrameLoop(onFrame: (now: number) => void): void {
  const callbackRef = useRef(onFrame);

  useEffect(() => {
    callbackRef.current = onFrame;
  });

  useEffect(() => {
    let frame = 0;
    const tick = () => {
      callbackRef.current(Date.now());
      frame = window.requestAnimationFrame(tick);
    };
    frame = window.requestAnimationFrame(tick);
    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, []);
}
