import { t } from "../data/language";
import styles from "./capture-controls.module.scss";
import { ControlButton } from "./control-button";
import { PreviewOffIcon } from "./preview-off-icon";
import { SwitchCameraIcon } from "./switch-camera-icon";

interface CaptureControlsProps {
  dimmed: boolean;
  onPreviewOff: () => void;
  onSwitchCamera: () => void;
}

export function CaptureControls({ dimmed, onPreviewOff, onSwitchCamera }: CaptureControlsProps) {
  return (
    <div className={styles.rail} data-dimmed={dimmed} inert={dimmed}>
      <ControlButton label={t("cam.preview_off")} onClick={onPreviewOff}>
        <PreviewOffIcon />
      </ControlButton>
      <ControlButton label={t("cam.switch_camera")} onClick={onSwitchCamera}>
        <SwitchCameraIcon />
      </ControlButton>
    </div>
  );
}
