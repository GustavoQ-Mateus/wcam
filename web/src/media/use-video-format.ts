import { useEffect } from "react";
import type { CamEvent } from "../data/cam-state";
import type { VideoFormat } from "../data/video-format";
import { applyVideoFormat } from "./apply-video-format";
import { captureFormat } from "./capture";

export function useVideoFormat(
  track: MediaStreamTrack | null,
  format: VideoFormat | null,
  portrait: boolean,
  onEvent: (event: CamEvent) => void,
): void {
  useEffect(() => {
    if (!track || !format) {
      return;
    }
    let current = true;
    void applyVideoFormat(track, format, portrait).then(() => {
      const settings = track.getSettings();
      const { width, height } = settings;
      if (current && width && height) {
        onEvent({ type: "capture_changed", capture: captureFormat(settings, { width, height }) });
      }
    });
    return () => {
      current = false;
    };
  }, [track, format, portrait, onEvent]);
}
