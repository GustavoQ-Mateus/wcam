import type { Controls, ControlsPatch, Status } from "../data/contract";
import { currentFacing, otherFacing } from "../data/console-view";
import { t } from "../data/language";
import styles from "../console/control-bar.module.scss";

interface PreviewControlsProps {
  controls: Controls;
  status: Status;
  onChange: (patch: ControlsPatch) => void;
}

export function PreviewControls({ controls, status, onChange }: PreviewControlsProps) {
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
          onChange({ facing: otherFacing(currentFacing(status)) });
        }}
      >
        {t("controls.switch_camera")}
      </button>
    </div>
  );
}
