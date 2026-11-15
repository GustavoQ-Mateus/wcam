import type { BadgeShape, BadgeTone } from "../data/console-view";
import styles from "./status-mark.module.scss";

interface StatusMarkProps {
  shape: BadgeShape;
  tone: BadgeTone;
}

export function StatusMark({ shape, tone }: StatusMarkProps) {
  return <span className={styles.mark} data-shape={shape} data-tone={tone} aria-hidden="true" />;
}
