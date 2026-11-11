import { useEffect, type RefObject } from "react";
import type { CamEvent } from "../data/cam-state";
import type { VideoFormat } from "../data/video-format";
import { applyVideoFormat } from "./apply-video-format";
import { captureFormat } from "./capture";

export function useVideoFormat(
  track: MediaStreamTrack | null,
  videoRef: RefObject<HTMLVideoElement | null>,
  format: VideoFormat | null,
  portrait: boolean,
  onEvent: (event: CamEvent) => void,
): void {
  useEffect(() => {
    const video = videoRef.current;
    if (!track || !video || !format) {
      return;
    }
    const controller = new AbortController();
    void applyVideoFormat(track, video, format, portrait, controller.signal).then(() => {
      const settings = track.getSettings();
      const { width, height } = settings;
      if (!controller.signal.aborted && width && height) {
        onEvent({ type: "capture_changed", capture: captureFormat(settings, { width, height }) });
      }
    });
    return () => {
      controller.abort();
    };
  }, [track, videoRef, format, portrait, onEvent]);
}
