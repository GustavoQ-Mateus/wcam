import type { LiveCamState } from "../data/cam-state";
import { CaptureControls } from "./capture-controls";
import { CaptureReadout } from "./capture-readout";
import { PreviewCover } from "./preview-cover";
import { RotatePrompt } from "./rotate-prompt";
import { ScreenNotice } from "./screen-notice";

interface LiveLayerProps {
  state: LiveCamState;
  showNotice: boolean;
  onDismissNotice: () => void;
  onSwitchCamera: () => void;
  onTogglePreview: () => void;
}

export function LiveLayer({ state, showNotice, onDismissNotice, onSwitchCamera, onTogglePreview }: LiveLayerProps) {
  if (state.kind === "rotate") {
    return <RotatePrompt />;
  }
  const previewOff = state.kind === "preview_off";
  return (
    <>
      <PreviewCover visible={previewOff} onShow={onTogglePreview} />
      <CaptureReadout capture={state.capture} dimmed={previewOff} />
      <CaptureControls dimmed={previewOff} onPreviewOff={onTogglePreview} onSwitchCamera={onSwitchCamera} />
      {showNotice && !previewOff && <ScreenNotice onDismiss={onDismissNotice} />}
    </>
  );
}
