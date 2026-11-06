import type { ReactNode } from "react";
import { isSession, type LiveCamState } from "../data/cam-state";
import { t } from "../data/language";
import type { QualityPreset } from "../data/quality-preset";
import { CaptureControls } from "./capture-controls";
import { CaptureReadout } from "./capture-readout";
import { ConfirmationPrompt } from "./confirmation-prompt";
import { ConnectingPrompt } from "./connecting-prompt";
import { PreviewCover } from "./preview-cover";
import { RotatePrompt } from "./rotate-prompt";
import { ScreenNotice } from "./screen-notice";
import { ScrimLayer } from "./scrim-layer";
import { Tally } from "./tally";

interface LiveLayerProps {
  state: LiveCamState;
  showNotice: boolean;
  qualityPreset: QualityPreset | null;
  onDismissNotice: () => void;
  onSwitchCamera: () => void;
  onTogglePreview: () => void;
  onChooseQuality: (preset: QualityPreset) => void;
}

interface Prompt {
  key: string;
  content: ReactNode;
}

export function LiveLayer({
  state,
  showNotice,
  qualityPreset,
  onDismissNotice,
  onSwitchCamera,
  onTogglePreview,
  onChooseQuality,
}: LiveLayerProps) {
  const prompt = promptFor(state);
  const previewOff = state.kind === "preview_off" || (state.kind === "live" && state.previewOff);
  return (
    <>
      <ScrimLayer visible={prompt !== null} contentKey={prompt?.key ?? "none"}>
        {prompt?.content ?? (state.kind === "live" && <p className="visually-hidden">{t("cam.live")}</p>)}
      </ScrimLayer>
      {prompt === null && (
        <>
          <h1 className="visually-hidden">{t("app.name")}</h1>
          <PreviewCover visible={previewOff} onShow={onTogglePreview} />
          <CaptureReadout capture={state.capture} dimmed={previewOff} />
          {state.kind === "live" && <Tally />}
          <CaptureControls
            dimmed={previewOff}
            qualityPreset={state.kind === "live" ? qualityPreset : null}
            onPreviewOff={onTogglePreview}
            onSwitchCamera={onSwitchCamera}
            onChooseQuality={onChooseQuality}
          />
          {showNotice && !previewOff && <ScreenNotice onDismiss={onDismissNotice} />}
        </>
      )}
    </>
  );
}

function promptFor(state: LiveCamState): Prompt | null {
  if (state.kind === "rotate" || (isSession(state) && state.portrait)) {
    return { key: "rotate", content: <RotatePrompt /> };
  }
  if (state.kind === "connecting") {
    return { key: "connecting", content: <ConnectingPrompt /> };
  }
  if (state.kind === "awaiting_confirmation") {
    return { key: "awaiting_confirmation", content: <ConfirmationPrompt code={state.code} /> };
  }
  return null;
}
