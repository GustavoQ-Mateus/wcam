import type { ReactNode } from "react";
import type { LiveCamState } from "../data/cam-state";
import { t } from "../data/language";
import type { VideoFormat } from "../data/video-format";
import type { VideoFormatMessage } from "../media/use-publisher";
import { CaptureControls } from "./capture-controls";
import { CaptureReadout } from "./capture-readout";
import { ConfirmationPrompt } from "./confirmation-prompt";
import { ConnectingPrompt } from "./connecting-prompt";
import { PortraitHint } from "./portrait-hint";
import { PreviewCover } from "./preview-cover";
import { ScreenNotice } from "./screen-notice";
import { ScreenshotButton } from "./screenshot-button";
import { ScrimLayer } from "./scrim-layer";
import { Tally } from "./tally";

interface LiveLayerProps {
  state: LiveCamState;
  showNotice: boolean;
  videoFormat: VideoFormatMessage | null;
  onDismissNotice: () => void;
  onSwitchCamera: () => void;
  onTogglePreview: () => void;
  onChooseFormat: (format: VideoFormat) => void;
  onSendScreenshot?: ((file: File) => Promise<boolean>) | undefined;
}

interface Prompt {
  key: string;
  content: ReactNode;
}

export function LiveLayer({
  state,
  showNotice,
  videoFormat,
  onDismissNotice,
  onSwitchCamera,
  onTogglePreview,
  onChooseFormat,
  onSendScreenshot,
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
          {state.portrait && !previewOff && <PortraitHint />}
          <CaptureControls
            dimmed={previewOff}
            videoFormat={state.kind === "live" ? videoFormat : null}
            onPreviewOff={onTogglePreview}
            onSwitchCamera={onSwitchCamera}
            onChooseFormat={onChooseFormat}
          />
          {showNotice && !previewOff && <ScreenNotice onDismiss={onDismissNotice} />}
          {onSendScreenshot && <ScreenshotButton onSend={onSendScreenshot} />}
        </>
      )}
    </>
  );
}

function promptFor(state: LiveCamState): Prompt | null {
  if (state.kind === "connecting") {
    return { key: "connecting", content: <ConnectingPrompt /> };
  }
  if (state.kind === "awaiting_confirmation") {
    return { key: "awaiting_confirmation", content: <ConfirmationPrompt code={state.code} /> };
  }
  return null;
}
