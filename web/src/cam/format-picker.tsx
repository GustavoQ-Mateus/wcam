import { useCallback, useId, useRef, useState } from "react";
import { formatName } from "../data/format-name";
import { formatView } from "../data/format-view";
import { t } from "../data/language";
import { useFormatChoice } from "../data/use-format-choice";
import type { VideoFormat } from "../data/video-format";
import { ControlButton } from "./control-button";
import { FormatIcon } from "./format-icon";
import styles from "./format-picker.module.scss";
import { FrameRateOption } from "./frame-rate-option";
import { ResolutionOption } from "./resolution-option";
import { useDismiss } from "./use-dismiss";

interface FormatPickerProps {
  format: VideoFormat;
  available: readonly VideoFormat[];
  dimmed: boolean;
  mirror: boolean | null;
  onChoose: (format: VideoFormat) => void;
  onToggleMirror: () => void;
}

export function FormatPicker({ format, available, dimmed, mirror, onChoose, onToggleMirror }: FormatPickerProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();
  const currentId = useId();
  const resolutionId = useId();
  const frameRateId = useId();
  const close = useCallback(() => {
    setOpen(false);
  }, []);
  const choice = useFormatChoice(format, onChoose, close);
  const view = formatView(format, available, choice.pending);
  const expanded = open && !dimmed;
  useDismiss(rootRef, expanded, close);

  return (
    <div ref={rootRef} className={styles.picker}>
      <div id={panelId} className={styles.panel} data-open={expanded} inert={!expanded}>
        <p className={styles.current}>{formatName(format)}</p>
        {view.resolutions.length > 0 && (
          <div className={styles.group}>
            <p id={resolutionId} className={styles.label}>
              {t("format.resolution_label")}
            </p>
            <div className={styles.pills} role="radiogroup" aria-labelledby={resolutionId}>
              {view.resolutions.map((option) => (
                <ResolutionOption key={option.value} group={resolutionId} option={option} onChoose={choice.choose} />
              ))}
            </div>
          </div>
        )}
        {view.frameRates.length > 0 && (
          <div className={styles.group}>
            <p id={frameRateId} className={styles.label}>
              {t("format.frame_rate_label")}
            </p>
            <div role="radiogroup" aria-labelledby={frameRateId}>
              {view.frameRates.map((option) => (
                <FrameRateOption key={option.value} group={frameRateId} option={option} onChoose={choice.choose} />
              ))}
            </div>
          </div>
        )}
        {mirror !== null && (
          <button type="button" className={styles.switch} role="switch" aria-checked={mirror} onClick={onToggleMirror}>
            {t("cam.mirror_apps")}
            <span className={styles.switchTrack} aria-hidden="true" />
          </button>
        )}
      </div>
      <ControlButton
        label={t("format.label")}
        describedBy={currentId}
        expanded={expanded}
        controls={panelId}
        onClick={() => {
          setOpen(!open);
        }}
      >
        <FormatIcon />
      </ControlButton>
      <span id={currentId} className="visually-hidden">
        {formatName(format)}
      </span>
    </div>
  );
}
