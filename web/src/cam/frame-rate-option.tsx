import type { FormatOption } from "../data/format-view";
import { t } from "../data/language";
import { frameRateHintKey, frameRateKey, type FrameRate, type VideoFormat } from "../data/video-format";
import styles from "./frame-rate-option.module.scss";

interface FrameRateOptionProps {
  group: string;
  option: FormatOption<FrameRate>;
  onChoose: (format: VideoFormat) => void;
}

export function FrameRateOption({ group, option, onChoose }: FrameRateOptionProps) {
  return (
    <label className={styles.option} data-checked={option.checked}>
      <input
        type="radio"
        className="visually-hidden"
        name={group}
        checked={option.checked}
        onChange={() => {
          onChoose(option.format);
        }}
      />
      <span className={styles.mark} data-mark={markOf(option)} aria-hidden="true" />
      <span className={styles.name}>{t(frameRateKey(option.value))}</span>
      <span className={styles.hint}>{t(frameRateHintKey(option.value))}</span>
    </label>
  );
}

function markOf({ checked, pending }: FormatOption<FrameRate>): string {
  if (pending) {
    return "pending";
  }
  return checked ? "checked" : "open";
}
