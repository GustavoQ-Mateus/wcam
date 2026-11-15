import type { KeyboardEvent, PointerEvent } from "react";
import type { LibraryVideo, TimelineClip } from "../data/contract";
import { t } from "../data/language";
import { clipLength } from "../data/timeline";
import { formatClock, formatPreciseClock } from "../data/video-position";
import { Filmstrip } from "./filmstrip";
import styles from "./timeline-clip.module.scss";

export type ClipEdge = "start" | "end";

interface TimelineClipViewProps {
  clip: TimelineClip;
  video: LibraryVideo;
  index: number;
  count: number;
  left: number;
  pixelsPerSecond: number;
  selected: boolean;
  offset: number;
  lifted: boolean;
  trimmingEdge: ClipEdge | null;
  onBodyPointerDown: (event: PointerEvent<HTMLDivElement>) => void;
  onEdgePointerDown: (edge: ClipEdge, event: PointerEvent<HTMLDivElement>) => void;
  onEdgeKey: (edge: ClipEdge, event: KeyboardEvent<HTMLDivElement>) => void;
  onSelect: () => void;
}

export function TimelineClipView({
  clip,
  video,
  index,
  count,
  left,
  pixelsPerSecond,
  selected,
  offset,
  lifted,
  trimmingEdge,
  onBodyPointerDown,
  onEdgePointerDown,
  onEdgeKey,
  onSelect,
}: TimelineClipViewProps) {
  const position = String(index + 1);
  const length = clipLength(clip);
  return (
    <div
      className={styles.clip}
      style={{ left, width: length * pixelsPerSecond, transform: `translateX(${String(offset)}px)` }}
      data-selected={selected}
      data-lifted={lifted}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      aria-label={t("console.timeline_clip", {
        index: position,
        count: String(count),
        name: video.name,
        duration: formatClock(length),
      })}
      onFocus={onSelect}
      onPointerDown={onBodyPointerDown}
    >
      <Filmstrip
        video={video}
        inSeconds={clip.inSeconds}
        outSeconds={clip.outSeconds}
        pixelsPerSecond={pixelsPerSecond}
      />
      <span className={styles.name}>{video.name}</span>
      {(["start", "end"] as const).map((edge) => (
        <div
          key={edge}
          className={styles.edge}
          data-edge={edge}
          role="slider"
          tabIndex={selected ? 0 : -1}
          aria-label={t(edge === "start" ? "console.timeline_trim_start" : "console.timeline_trim_end", {
            index: position,
          })}
          aria-valuemin={0}
          aria-valuemax={video.durationSeconds}
          aria-valuenow={edge === "start" ? clip.inSeconds : clip.outSeconds}
          aria-valuetext={formatPreciseClock(edge === "start" ? clip.inSeconds : clip.outSeconds)}
          onPointerDown={(event) => {
            onEdgePointerDown(edge, event);
          }}
          onKeyDown={(event) => {
            onEdgeKey(edge, event);
          }}
        >
          {trimmingEdge === edge && (
            <span className={styles.edgeTime}>
              {formatPreciseClock(edge === "start" ? clip.inSeconds : clip.outSeconds)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
