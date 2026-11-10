import type { FormatOption } from "../data/format-view";
import { t } from "../data/language";
import { resolutionKey, type Resolution, type VideoFormat } from "../data/video-format";
import styles from "./resolution-option.module.scss";

interface ResolutionOptionProps {
  group: string;
  option: FormatOption<Resolution>;
  onChoose: (format: VideoFormat) => void;
}

export function ResolutionOption({ group, option, onChoose }: ResolutionOptionProps) {
  return (
    <label className={styles.pill} data-checked={option.checked}>
      <input
        type="radio"
        className="visually-hidden"
        name={group}
        checked={option.checked}
        onChange={() => {
          onChoose(option.format);
        }}
      />
      {option.pending && <span className={styles.pending} aria-hidden="true" />}
      {t(resolutionKey(option.value))}
    </label>
  );
}
