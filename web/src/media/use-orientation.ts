import { useEffect, type RefObject } from "react";
import type { CamEvent } from "../data/cam-state";

export function useOrientation(videoRef: RefObject<HTMLVideoElement | null>, onEvent: (event: CamEvent) => void): void {
  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    const reportFrame = () => {
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        onEvent({ type: "frame_changed", frame: { width: video.videoWidth, height: video.videoHeight } });
      }
    };
    video.addEventListener("resize", reportFrame);
    return () => {
      video.removeEventListener("resize", reportFrame);
    };
  }, [videoRef, onEvent]);
}
