import { t } from "../data/language";
import type { VideoFormat } from "../data/video-format";
import type { VideoFormatMessage } from "../media/use-publisher";
import styles from "./capture-controls.module.scss";
import { ControlButton } from "./control-button";
import { PreviewOffIcon } from "./preview-off-icon";
import { FormatPicker } from "./format-picker";
import { SwitchCameraIcon } from "./switch-camera-icon";

interface CaptureControlsProps {
  dimmed: boolean;
  videoFormat: VideoFormatMessage | null;
  onPreviewOff: () => void;
  onSwitchCamera: () => void;
  onChooseFormat: (format: VideoFormat) => void;
}

export function CaptureControls({
  dimmed,
  videoFormat,
  onPreviewOff,
  onSwitchCamera,
  onChooseFormat,
}: CaptureControlsProps) {
  return (
    <div className={styles.rail} data-dimmed={dimmed} inert={dimmed}>
      <ControlButton label={t("cam.preview_off")} onClick={onPreviewOff}>
        <PreviewOffIcon />
      </ControlButton>
      <ControlButton label={t("cam.switch_camera")} onClick={onSwitchCamera}>
        <SwitchCameraIcon />
      </ControlButton>
      {videoFormat && (
        <FormatPicker
          format={videoFormat.format}
          available={videoFormat.available}
          dimmed={dimmed}
          onChoose={onChooseFormat}
        />
      )}
    </div>
  );
}
