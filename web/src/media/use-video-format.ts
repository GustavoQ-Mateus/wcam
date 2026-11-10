import { useEffect } from "react";
import type { VideoFormat } from "../data/video-format";
import { applyVideoFormat } from "./apply-video-format";

export function useVideoFormat(track: MediaStreamTrack | null, format: VideoFormat | null, portrait: boolean): void {
  useEffect(() => {
    if (track && format) {
      void applyVideoFormat(track, format, portrait);
    }
  }, [track, format, portrait]);
}
