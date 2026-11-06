import { useId } from "react";
import { t } from "../data/language";
import {
  maxBitrateMbps,
  QUALITY_PRESETS,
  qualityHintKey,
  qualityNameKey,
  type QualityPreset,
} from "../data/quality-preset";
import { useQualityChoice } from "../data/use-quality-choice";
import styles from "./quality-panel.module.scss";

interface QualityPanelProps {
  preset: QualityPreset;
  onChoose: (preset: QualityPreset) => void;
}

export function QualityPanel({ preset, onChoose }: QualityPanelProps) {
  const titleId = useId();
  const groupName = useId();
  const choice = useQualityChoice(preset, onChoose);
  return (
    <section className={styles.panel}>
      <h2 id={titleId} className={styles.title}>
        {t("quality.label")}
      </h2>
      <div className={styles.track} role="radiogroup" aria-labelledby={titleId}>
        {QUALITY_PRESETS.map((option) => (
          <label key={option} className={styles.segment} data-checked={option === preset}>
            <input
              type="radio"
              className="visually-hidden"
              name={groupName}
              checked={option === preset}
              onChange={() => {
                choice.choose(option);
              }}
            />
            {option === choice.pending && <span className={styles.pending} aria-hidden="true" />}
            {t(qualityNameKey(option))}
          </label>
        ))}
      </div>
      <p className={styles.hint}>{t(qualityHintKey(preset))}</p>
      <p className={styles.detail}>{t("quality.bitrate_limit", { mbps: String(maxBitrateMbps(preset)) })}</p>
    </section>
  );
}
