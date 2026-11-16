import { useState } from "react";
import { clampedSeek, videoPosition, type PositionSample } from "./video-position";

interface PlaybackInput {
  active: boolean;
  running: boolean;
  positionSeconds: number | null;
  receivedAt: number;
  duration: number;
  onSeek: (seconds: number) => void;
}

export interface PlaybackPosition {
  positionAt: (now: number) => number;
  seek: (seconds: number) => void;
}

interface SeekOverride {
  sample: PositionSample;
  until: number;
}

export function usePlaybackPosition({
  active,
  running,
  positionSeconds,
  receivedAt,
  duration,
  onSeek,
}: PlaybackInput): PlaybackPosition {
  const [cursor, setCursor] = useState(0);
  const [override, setOverride] = useState<SeekOverride | null>(null);
  const serverSample = { seconds: positionSeconds ?? 0, receivedAt };
  const sample = override && receivedAt <= override.until ? override.sample : serverSample;
  return {
    positionAt: (now) => {
      if (!active) {
        return clampedSeek(cursor, duration);
      }
      return videoPosition(sample, now, running, duration);
    },
    seek: (seconds) => {
      const target = clampedSeek(seconds, duration);
      if (!active) {
        setCursor(target);
        return;
      }
      setOverride({ sample: { seconds: target, receivedAt: Date.now() }, until: receivedAt });
      onSeek(target);
    },
  };
}
