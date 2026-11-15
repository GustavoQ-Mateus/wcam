import type { PointerEvent } from "react";
import { t } from "../data/language";
import { rulerStep } from "../data/timeline";
import { formatClock } from "../data/video-position";
import styles from "./timeline-ruler.module.scss";

const MINIMUM_LABEL_GAP_PIXELS = 72;
const MAX_TICKS = 400;

interface TimelineRulerProps {
  duration: number;
  pixelsPerSecond: number;
  position: number;
  onPointerDown: (event: PointerEvent<HTMLDivElement>) => void;
}

export function TimelineRuler({ duration, pixelsPerSecond, position, onPointerDown }: TimelineRulerProps) {
  const step = rulerStep(pixelsPerSecond, MINIMUM_LABEL_GAP_PIXELS);
  const count = Math.min(MAX_TICKS, Math.floor(duration / step) + 1);
  return (
    <div
      className={styles.ruler}
      role="slider"
      tabIndex={0}
      aria-label={t("console.timeline_playhead")}
      aria-valuemin={0}
      aria-valuemax={duration}
      aria-valuenow={Math.floor(position)}
      aria-valuetext={t("console.video_position", {
        position: formatClock(position),
        duration: formatClock(duration),
      })}
      onPointerDown={onPointerDown}
    >
      {Array.from({ length: count }, (_, index) => (
        <span key={index} className={styles.tick} style={{ left: index * step * pixelsPerSecond }}>
          {formatClock(index * step)}
        </span>
      ))}
    </div>
  );
}
