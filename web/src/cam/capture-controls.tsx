import { t } from "../data/language";
import type { QualityPreset } from "../data/quality-preset";
import styles from "./capture-controls.module.scss";
import { ControlButton } from "./control-button";
import { PreviewOffIcon } from "./preview-off-icon";
import { QualityPicker } from "./quality-picker";
import { SwitchCameraIcon } from "./switch-camera-icon";

interface CaptureControlsProps {
  dimmed: boolean;
  qualityPreset: QualityPreset | null;
  onPreviewOff: () => void;
  onSwitchCamera: () => void;
  onChooseQuality: (preset: QualityPreset) => void;
}

export function CaptureControls({
  dimmed,
  qualityPreset,
  onPreviewOff,
  onSwitchCamera,
  onChooseQuality,
}: CaptureControlsProps) {
  return (
    <div className={styles.rail} data-dimmed={dimmed} inert={dimmed}>
      <ControlButton label={t("cam.preview_off")} onClick={onPreviewOff}>
        <PreviewOffIcon />
      </ControlButton>
      <ControlButton label={t("cam.switch_camera")} onClick={onSwitchCamera}>
        <SwitchCameraIcon />
      </ControlButton>
      {qualityPreset && <QualityPicker preset={qualityPreset} dimmed={dimmed} onChoose={onChooseQuality} />}
    </div>
  );
}
