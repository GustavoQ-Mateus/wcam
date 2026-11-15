import { MonitorOff, MonitorPause, SwitchCamera, VideoOff } from "lucide-react";
import type { Controls } from "../data/contract";
import { t } from "../data/language";
import type { VideoFormat } from "../data/video-format";
import type { VideoFormatMessage } from "../media/use-publisher";
import styles from "./capture-controls.module.scss";
import { ControlButton } from "./control-button";
import { FormatPicker } from "./format-picker";

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
          <MonitorPause />
        </ControlButton>
      )}
      {controls && (
        <ControlButton label={t("controls.camera_off")} pressed={controls.cameraOff} onClick={onToggleCamera}>
          <VideoOff />
        </ControlButton>
      )}
      <ControlButton label={t("controls.preview_off")} onClick={onPreviewOff}>
        <MonitorOff />
      </ControlButton>
      <ControlButton label={t("controls.switch_camera")} onClick={onSwitchCamera}>
        <SwitchCamera />
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
