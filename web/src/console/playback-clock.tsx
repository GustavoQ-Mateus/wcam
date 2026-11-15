import { useState } from "react";
import { t } from "../data/language";
import { formatClock } from "../data/video-position";
import { useFrameLoop } from "../media/use-frame-loop";
import styles from "./transport-bar.module.scss";

interface PlaybackClockProps {
  duration: number;
  positionAt: (now: number) => number;
}

export function PlaybackClock({ duration, positionAt }: PlaybackClockProps) {
  const [second, setSecond] = useState(0);
  useFrameLoop((now) => {
    const next = Math.floor(positionAt(now));
    setSecond((current) => (current === next ? current : next));
  });
  return (
    <p className={styles.clock}>
      {t("console.video_position", { position: formatClock(second), duration: formatClock(duration) })}
    </p>
  );
}
