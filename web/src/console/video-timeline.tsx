import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { t } from "../data/language";
import {
  clampedSeek,
  formatClock,
  positionFraction,
  steppedSeek,
  videoPosition,
  type PositionSample,
} from "../data/video-position";
import { useFrameLoop } from "../media/use-frame-loop";
import styles from "./video-timeline.module.scss";

interface VideoTimelineProps {
  duration: number;
  sample: PositionSample;
  running: boolean;
  onSeek: (seconds: number) => void;
}

const FORWARD_KEYS: ReadonlySet<string> = new Set(["ArrowRight", "ArrowUp"]);
const BACKWARD_KEYS: ReadonlySet<string> = new Set(["ArrowLeft", "ArrowDown"]);
const START_KEY = "Home";
const PERCENT = 100;

export function VideoTimeline({ duration, sample, running, onSeek }: VideoTimelineProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const thumbRef = useRef<HTMLDivElement>(null);
  const [dragSeconds, setDragSeconds] = useState<number | null>(null);
  const [seekSample, setSeekSample] = useState<PositionSample | null>(null);
  const [shownSecond, setShownSecond] = useState(Math.floor(sample.seconds));
  const current = seekSample && seekSample.receivedAt > sample.receivedAt ? seekSample : sample;
  const positionAt = (now: number) => dragSeconds ?? videoPosition(current, now, running, duration);

  useFrameLoop((now) => {
    const position = positionAt(now);
    const fraction = positionFraction(position, duration);
    progressRef.current?.style.setProperty("transform", `scaleX(${String(fraction)})`);
    thumbRef.current?.style.setProperty("transform", `translateX(${String(fraction * PERCENT)}%)`);
    const second = Math.floor(position);
    if (second !== shownSecond) {
      setShownSecond(second);
    }
  });

  const seek = (seconds: number) => {
    setSeekSample({ seconds, receivedAt: Date.now() });
    onSeek(seconds);
  };
  const secondsAtPointer = (event: PointerEvent) => {
    const track = trackRef.current?.getBoundingClientRect();
    if (!track || track.width === 0) {
      return 0;
    }
    return clampedSeek(((event.clientX - track.left) / track.width) * duration, duration);
  };
  const handleKey = (event: KeyboardEvent) => {
    const position = positionAt(Date.now());
    if (FORWARD_KEYS.has(event.key)) {
      seek(steppedSeek(position, 1, duration));
    } else if (BACKWARD_KEYS.has(event.key)) {
      seek(steppedSeek(position, -1, duration));
    } else if (event.key === START_KEY) {
      seek(0);
    } else {
      return;
    }
    event.preventDefault();
  };
  const positionText = t("console.video_position", {
    position: formatClock(shownSecond),
    duration: formatClock(duration),
  });
  return (
    <div className={styles.timeline}>
      <p className={styles.time} aria-hidden="true">
        {positionText}
      </p>
      <div
        ref={trackRef}
        className={styles.slider}
        role="slider"
        tabIndex={0}
        aria-label={t("console.video_timeline")}
        aria-valuemin={0}
        aria-valuemax={Math.floor(duration)}
        aria-valuenow={shownSecond}
        aria-valuetext={positionText}
        data-dragging={dragSeconds !== null}
        onKeyDown={handleKey}
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          setDragSeconds(secondsAtPointer(event));
        }}
        onPointerMove={(event) => {
          if (dragSeconds !== null) {
            setDragSeconds(secondsAtPointer(event));
          }
        }}
        onPointerUp={(event) => {
          if (dragSeconds === null) {
            return;
          }
          setDragSeconds(null);
          seek(secondsAtPointer(event));
        }}
        onPointerCancel={() => {
          setDragSeconds(null);
        }}
      >
        <div className={styles.track}>
          <div ref={progressRef} className={styles.progress} />
        </div>
        <div ref={thumbRef} className={styles.thumbRail}>
          <span className={styles.thumb} />
        </div>
      </div>
    </div>
  );
}
