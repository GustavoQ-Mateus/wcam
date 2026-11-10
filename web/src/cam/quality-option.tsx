import { t } from "../data/language";
import { qualityHintKey, qualityNameKey, type QualityPreset } from "../data/quality-preset";
import styles from "./quality-option.module.scss";

interface QualityOptionProps {
  group: string;
  preset: QualityPreset;
  checked: boolean;
  pending: boolean;
  onChoose: (preset: QualityPreset) => void;
}

export function QualityOption({ group, preset, checked, pending, onChoose }: QualityOptionProps) {
  return (
    <label className={styles.option} data-checked={checked}>
      <input
        type="radio"
        className="visually-hidden"
        name={group}
        checked={checked}
        onChange={() => {
          onChoose(preset);
        }}
      />
      <span className={styles.mark} data-mark={markOf(checked, pending)} aria-hidden="true" />
      <span className={styles.name}>{t(qualityNameKey(preset))}</span>
      <span className={styles.hint}>{t(qualityHintKey(preset))}</span>
    </label>
  );
}

function markOf(checked: boolean, pending: boolean): string {
  if (pending) {
    return "pending";
  }
  return checked ? "checked" : "open";
}
