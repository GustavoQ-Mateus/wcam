import type { Facing } from "../data/cam-state";
import type { Controls, ControlsPatch } from "../data/contract";
import { otherFacing } from "../data/console-view";
import { t } from "../data/language";
import styles from "./control-bar.module.scss";

interface ControlBarProps {
  controls: Controls;
  facing: Facing | null;
  previewOn: boolean;
  onChange: (patch: ControlsPatch) => void;
  onTogglePreview: () => void;
  onDisconnect: () => void;
  onCompare?: (() => void) | undefined;
}

export function ControlBar({
  controls,
  facing,
  previewOn,
  onChange,
  onTogglePreview,
  onDisconnect,
  onCompare,
}: ControlBarProps) {
  const other = otherFacing(facing);
  return (
    <div className={styles.bar}>
      <button
        type="button"
        className={styles.control}
        aria-pressed={controls.frozen}
        disabled={controls.cameraOff}
        onClick={() => {
          onChange({ frozen: !controls.frozen });
        }}
      >
        {t(controls.frozen ? "controls.unfreeze" : "controls.freeze")}
      </button>
      <button
        type="button"
        className={styles.control}
        aria-pressed={controls.cameraOff}
        onClick={() => {
          onChange({ cameraOff: !controls.cameraOff });
        }}
      >
        {t(controls.cameraOff ? "controls.camera_on" : "controls.camera_off")}
      </button>
      <button
        type="button"
        className={styles.control}
        onClick={() => {
          onChange({ facing: other });
        }}
      >
        {t(other === "user" ? "controls.use_front" : "controls.use_back")}
      </button>
      <button
        type="button"
        className={styles.control}
        aria-pressed={controls.mirror}
        onClick={() => {
          onChange({ mirror: !controls.mirror });
        }}
      >
        {t("controls.mirror")}
      </button>
      <button type="button" className={styles.control} onClick={onTogglePreview}>
        {t(previewOn ? "controls.preview_off" : "controls.preview_on")}
      </button>
      {onCompare && (
        <button type="button" className={styles.control} onClick={onCompare}>
          {t("console.dev_compare")}
        </button>
      )}
      <button type="button" className={styles.disconnect} onClick={onDisconnect}>
        {t("controls.disconnect")}
      </button>
    </div>
  );
}
