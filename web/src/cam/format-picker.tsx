import { useCallback, useId, useRef, useState } from "react";
import { t } from "../data/language";
import { QUALITY_PRESETS, qualityLevel, qualityNameKey, type QualityPreset } from "../data/quality-preset";
import { useQualityChoice } from "../data/use-quality-choice";
import { ControlButton } from "./control-button";
import { QualityIcon } from "./quality-icon";
import { QualityOption } from "./quality-option";
import styles from "./quality-picker.module.scss";
import { useDismiss } from "./use-dismiss";

interface QualityPickerProps {
  preset: QualityPreset;
  dimmed: boolean;
  onChoose: (preset: QualityPreset) => void;
}

export function QualityPicker({ preset, dimmed, onChoose }: QualityPickerProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();
  const titleId = useId();
  const currentId = useId();
  const close = useCallback(() => {
    setOpen(false);
  }, []);
  const choice = useQualityChoice(preset, onChoose, close);
  const expanded = open && !dimmed;
  useDismiss(rootRef, expanded, close);

  return (
    <div ref={rootRef} className={styles.picker}>
      <div
        id={panelId}
        className={styles.panel}
        data-open={expanded}
        inert={!expanded}
        role="radiogroup"
        aria-labelledby={titleId}
      >
        <p id={titleId} className={styles.title}>
          {t("quality.label")}
        </p>
        {QUALITY_PRESETS.map((option) => (
          <QualityOption
            key={option}
            group={panelId}
            preset={option}
            checked={option === preset}
            pending={option === choice.pending}
            onChoose={choice.choose}
          />
        ))}
      </div>
      <ControlButton
        label={t("quality.label")}
        describedBy={currentId}
        expanded={expanded}
        controls={panelId}
        onClick={() => {
          setOpen(!open);
        }}
      >
        <QualityIcon level={qualityLevel(preset)} />
      </ControlButton>
      <span id={currentId} className="visually-hidden">
        {t(qualityNameKey(preset))}
      </span>
    </div>
  );
}
