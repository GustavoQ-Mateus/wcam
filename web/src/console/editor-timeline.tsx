import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent, type PointerEvent } from "react";
import type { LibraryVideo, TimelineClip } from "../data/contract";
import { t } from "../data/language";
import {
  clipLength,
  clipStarts,
  dropIndex,
  LIBRARY_VIDEO_TYPE,
  moveClip,
  reorderTarget,
  timelineLength,
  trimEnd,
  trimStart,
} from "../data/timeline";
import { clampedSeek } from "../data/video-position";
import { useElementWidth } from "../media/use-element-width";
import { useFrameLoop } from "../media/use-frame-loop";
import styles from "./editor-timeline.module.scss";
import { TimelineClipView, type ClipEdge } from "./timeline-clip";
import { TimelineRuler } from "./timeline-ruler";

type Gesture =
  | { kind: "move"; index: number; startX: number; offset: number; moved: boolean }
  | { kind: "trim"; index: number; edge: ClipEdge; startX: number; original: TimelineClip; clips: TimelineClip[] }
  | { kind: "seek"; seconds: number };

interface EditorTimelineProps {
  videos: readonly LibraryVideo[];
  clips: readonly TimelineClip[];
  zoom: number;
  selectedId: string | null;
  positionAt: (now: number) => number;
  onSelect: (id: string) => void;
  onSeek: (seconds: number) => void;
  onChange: (clips: TimelineClip[]) => void;
  onInsertVideo: (videoId: string, index: number) => void;
  onDropFiles: (files: File[]) => void;
  onKeyDown: (event: KeyboardEvent<HTMLDivElement>) => void;
}

const DRAG_THRESHOLD_PIXELS = 4;
const TRIM_STEP_SECONDS = 0.1;
const TRIM_LARGE_STEP_SECONDS = 1;

export function EditorTimeline({
  videos,
  clips,
  zoom,
  selectedId,
  positionAt,
  onSelect,
  onSeek,
  onChange,
  onInsertVideo,
  onDropFiles,
  onKeyDown,
}: EditorTimelineProps) {
  const [attachViewport, viewportWidth] = useElementWidth<HTMLDivElement>();
  const trackRef = useRef<HTMLDivElement>(null);
  const playheadRef = useRef<HTMLDivElement>(null);
  const [gesture, setGesture] = useState<Gesture | null>(null);
  const [dropAt, setDropAt] = useState<number | null>(null);
  const [instant, setInstant] = useState(false);
  const [shownSecond, setShownSecond] = useState(0);
  const duration = timelineLength(clips);
  const pixelsPerSecond = duration > 0 ? (viewportWidth * zoom) / duration : 0;
  const shown = gesture?.kind === "trim" ? gesture.clips : clips;
  const starts = clipStarts(shown);
  const trackWidth = Math.max(viewportWidth * zoom, timelineLength(shown) * pixelsPerSecond);
  const videoById = new Map(videos.map((video) => [video.id, video]));

  useEffect(() => {
    if (!instant) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      setInstant(false);
    });
    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [instant]);

  useFrameLoop((now) => {
    const playhead = playheadRef.current;
    if (!playhead) {
      return;
    }
    const seconds = gesture?.kind === "seek" ? gesture.seconds : positionAt(now);
    const second = Math.floor(seconds);
    setShownSecond((current) => (current === second ? current : second));
    playhead.style.transform = `translateX(${String(seconds * pixelsPerSecond)}px)`;
  });

  const secondsAt = (clientX: number) => {
    const left = trackRef.current?.getBoundingClientRect().left ?? 0;
    return pixelsPerSecond > 0 ? (clientX - left) / pixelsPerSecond : 0;
  };
  const capture = (event: PointerEvent<HTMLElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const busy = gesture !== null;

  const startMove = (index: number, event: PointerEvent<HTMLDivElement>) => {
    if (busy) {
      return;
    }
    capture(event);
    setGesture({ kind: "move", index, startX: event.clientX, offset: 0, moved: false });
  };
  const startTrim = (index: number, edge: ClipEdge, event: PointerEvent<HTMLDivElement>) => {
    const original = clips[index];
    event.stopPropagation();
    if (!original || busy) {
      return;
    }
    capture(event);
    onSelect(original.id);
    setGesture({ kind: "trim", index, edge, startX: event.clientX, original, clips: [...clips] });
  };
  const startSeek = (event: PointerEvent<HTMLDivElement>) => {
    if (busy) {
      return;
    }
    capture(event);
    setGesture({ kind: "seek", seconds: clampedSeek(secondsAt(event.clientX), duration) });
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!gesture) {
      return;
    }
    if (gesture.kind === "seek") {
      setGesture({ kind: "seek", seconds: clampedSeek(secondsAt(event.clientX), duration) });
      return;
    }
    const offset = event.clientX - gesture.startX;
    if (gesture.kind === "move") {
      setGesture({ ...gesture, offset, moved: gesture.moved || Math.abs(offset) > DRAG_THRESHOLD_PIXELS });
      return;
    }
    setGesture({ ...gesture, clips: trimmed(gesture.index, gesture.edge, gesture.original, offset / pixelsPerSecond) });
  };
  const handlePointerUp = () => {
    if (!gesture) {
      return;
    }
    setGesture(null);
    setInstant(true);
    if (gesture.kind === "seek") {
      onSeek(gesture.seconds);
      return;
    }
    if (gesture.kind === "trim") {
      onChange(gesture.clips);
      return;
    }
    const target = moveTarget(gesture);
    if (gesture.moved && target !== gesture.index) {
      onChange(moveClip(clips, gesture.index, target));
    }
  };

  const trimmed = (index: number, edge: ClipEdge, original: TimelineClip, deltaSeconds: number) => {
    const videoDuration = videoById.get(original.videoId)?.durationSeconds ?? original.outSeconds;
    return edge === "start"
      ? trimStart(clips, index, original.inSeconds + deltaSeconds)
      : trimEnd(clips, index, original.outSeconds + deltaSeconds, videoDuration);
  };
  const moveTarget = (move: Extract<Gesture, { kind: "move" }>) => {
    const clip = clips[move.index];
    if (!clip || pixelsPerSecond === 0) {
      return move.index;
    }
    const center = (starts[move.index] ?? 0) + clipLength(clip) / 2 + move.offset / pixelsPerSecond;
    return reorderTarget(clips, move.index, center);
  };
  const neighborOffset = (index: number) => {
    if (gesture?.kind !== "move" || !gesture.moved) {
      return 0;
    }
    if (index === gesture.index) {
      return gesture.offset;
    }
    const moved = clips[gesture.index];
    const width = moved ? clipLength(moved) * pixelsPerSecond : 0;
    const target = moveTarget(gesture);
    if (gesture.index < index && index <= target) {
      return -width;
    }
    return target <= index && index < gesture.index ? width : 0;
  };
  const trimByKey = (index: number, edge: ClipEdge, event: KeyboardEvent<HTMLDivElement>) => {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    const clip = clips[index];
    if (direction === 0 || !clip) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const step = direction * (event.shiftKey ? TRIM_LARGE_STEP_SECONDS : TRIM_STEP_SECONDS);
    onChange(trimmed(index, edge, clip, step));
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    const types = event.dataTransfer.types;
    if (!types.includes(LIBRARY_VIDEO_TYPE) && !types.includes("Files")) {
      return;
    }
    event.preventDefault();
    setDropAt(dropIndex(clips, secondsAt(event.clientX)));
  };
  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const index = dropIndex(clips, secondsAt(event.clientX));
    setDropAt(null);
    const videoId = event.dataTransfer.getData(LIBRARY_VIDEO_TYPE);
    if (videoId) {
      onInsertVideo(videoId, index);
      return;
    }
    const files = [...event.dataTransfer.files];
    if (files.length > 0) {
      onDropFiles(files);
    }
  };

  return (
    <div
      className={styles.viewport}
      ref={attachViewport}
      onKeyDown={onKeyDown}
      onDragOver={handleDragOver}
      onDragLeave={() => {
        setDropAt(null);
      }}
      onDrop={handleDrop}
    >
      {clips.length === 0 ? (
        <p className={styles.empty} data-dragging={dropAt !== null}>
          {t("console.timeline_empty")}
        </p>
      ) : (
        <div
          className={styles.content}
          ref={trackRef}
          style={{ width: trackWidth }}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={() => {
            setGesture(null);
          }}
        >
          <TimelineRuler
            duration={duration}
            pixelsPerSecond={pixelsPerSecond}
            position={shownSecond}
            onPointerDown={startSeek}
          />
          <div className={styles.track} data-instant={instant}>
            {shown.map((clip, index) => {
              const video = videoById.get(clip.videoId);
              return (
                video && (
                  <TimelineClipView
                    key={clip.id}
                    clip={clip}
                    video={video}
                    index={index}
                    count={shown.length}
                    left={(starts[index] ?? 0) * pixelsPerSecond}
                    pixelsPerSecond={pixelsPerSecond}
                    selected={clip.id === selectedId}
                    offset={neighborOffset(index)}
                    lifted={gesture?.kind === "move" && gesture.moved && gesture.index === index}
                    trimmingEdge={gesture?.kind === "trim" && gesture.index === index ? gesture.edge : null}
                    onBodyPointerDown={(event) => {
                      onSelect(clip.id);
                      startMove(index, event);
                    }}
                    onEdgePointerDown={(edge, event) => {
                      startTrim(index, edge, event);
                    }}
                    onEdgeKey={(edge, event) => {
                      trimByKey(index, edge, event);
                    }}
                    onSelect={() => {
                      onSelect(clip.id);
                    }}
                  />
                )
              );
            })}
            {dropAt !== null && (
              <span
                className={styles.dropMarker}
                style={{ transform: `translateX(${String(dropPosition(shown, starts, dropAt) * pixelsPerSecond)}px)` }}
              />
            )}
          </div>
          <div className={styles.playhead} ref={playheadRef} aria-hidden="true" />
        </div>
      )}
    </div>
  );
}

function dropPosition(clips: readonly TimelineClip[], starts: number[], index: number): number {
  return index < clips.length ? (starts[index] ?? 0) : timelineLength(clips);
}
