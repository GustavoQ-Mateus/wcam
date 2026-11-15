import type { Controls } from "../data/contract";
import { t } from "../data/language";
import type { VideoFormat } from "../data/video-format";
import type { VideoFormatMessage } from "../media/use-publisher";
import styles from "./capture-controls.module.scss";
import { CameraOffIcon } from "./camera-off-icon";
import { ControlButton } from "./control-button";
import { FreezeIcon } from "./freeze-icon";
import { PreviewOffIcon } from "./preview-off-icon";
import { FormatPicker } from "./format-picker";
import { SwitchCameraIcon } from "./switch-camera-icon";

interface CaptureControlsProps {
  dimmed: boolean;
  videoFormat: VideoFormatMessage | null;
  controls: Controls | null;
  onPreviewOff: () => void;
  onToggleFreeze: () => void;
  onToggleCamera: () => void;
  onToggleMirror: () => void;
  onSwitchCamera: () => void;
  onChooseFormat: (format: VideoFormat) => void;
}

export function CaptureControls({
  dimmed,
  videoFormat,
  controls,
  onPreviewOff,
  onToggleFreeze,
  onToggleCamera,
  onToggleMirror,
  onSwitchCamera,
  onChooseFormat,
}: CaptureControlsProps) {
  return (
    <div className={styles.rail} data-dimmed={dimmed} inert={dimmed}>
      {controls && !controls.cameraOff && (
        <ControlButton
          label={t(controls.frozen ? "controls.unfreeze" : "controls.freeze")}
          pressed={controls.frozen}
          onClick={onToggleFreeze}
        >
          <FreezeIcon />
        </ControlButton>
      )}
      {controls && (
        <ControlButton label={t("controls.camera_off")} pressed={controls.cameraOff} onClick={onToggleCamera}>
          <CameraOffIcon />
        </ControlButton>
      )}
      <ControlButton label={t("controls.preview_off")} onClick={onPreviewOff}>
        <PreviewOffIcon />
      </ControlButton>
      <ControlButton label={t("controls.switch_camera")} onClick={onSwitchCamera}>
        <SwitchCameraIcon />
      </ControlButton>
      {videoFormat && (
        <FormatPicker
          format={videoFormat.format}
          available={videoFormat.available}
          dimmed={dimmed}
          mirror={controls?.mirror ?? null}
          onChoose={onChooseFormat}
          onToggleMirror={onToggleMirror}
        />
      )}
    </div>
  );
}
