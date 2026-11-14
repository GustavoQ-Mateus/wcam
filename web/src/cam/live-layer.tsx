import type { ReactNode } from "react";
import type { LiveCamState } from "../data/cam-state";
import type { Controls } from "../data/contract";
import { t } from "../data/language";
import type { VideoFormat } from "../data/video-format";
import type { VideoFormatMessage } from "../media/use-publisher";
import { CameraOffCover } from "./camera-off-cover";
import { CaptureControls } from "./capture-controls";
import { CaptureReadout } from "./capture-readout";
import { ConfirmationPrompt } from "./confirmation-prompt";
import { ConnectingPrompt } from "./connecting-prompt";
import { FrozenNotice } from "./frozen-notice";
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
  controls: Controls | null;
  onDismissNotice: () => void;
  onSwitchCamera: () => void;
  onTogglePreview: () => void;
  onToggleFreeze: () => void;
  onToggleCamera: () => void;
  onToggleMirror: () => void;
  onChooseFormat: (format: VideoFormat) => void;
  onAnswerCode: (same: boolean) => void;
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
  controls,
  onDismissNotice,
  onSwitchCamera,
  onTogglePreview,
  onToggleFreeze,
  onToggleCamera,
  onToggleMirror,
  onChooseFormat,
  onAnswerCode,
  onSendScreenshot,
}: LiveLayerProps) {
  const prompt = promptFor(state, onAnswerCode);
  const previewOff = state.kind === "preview_off" || (state.kind === "live" && state.previewOff);
  const cameraOff = controls?.cameraOff ?? false;
  return (
    <>
      <ScrimLayer visible={prompt !== null} contentKey={prompt?.key ?? "none"}>
        {prompt?.content ?? (state.kind === "live" && <p className="visually-hidden">{t("cam.live")}</p>)}
      </ScrimLayer>
      {prompt === null && (
        <>
          <h1 className="visually-hidden">{t("app.name")}</h1>
          <PreviewCover visible={previewOff && !cameraOff} onShow={onTogglePreview} />
          {cameraOff && <CameraOffCover onCameraOn={onToggleCamera} />}
          <CaptureReadout capture={state.capture} dimmed={previewOff} />
          {state.kind === "live" && !cameraOff && <Tally />}
          {controls?.frozen && !cameraOff && <FrozenNotice />}
          {state.portrait && !previewOff && <PortraitHint />}
          <CaptureControls
            dimmed={previewOff}
            videoFormat={state.kind === "live" ? videoFormat : null}
            controls={controls}
            onPreviewOff={onTogglePreview}
            onToggleFreeze={onToggleFreeze}
            onToggleCamera={onToggleCamera}
            onToggleMirror={onToggleMirror}
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

function promptFor(state: LiveCamState, onAnswerCode: (same: boolean) => void): Prompt | null {
  if (state.kind === "connecting") {
    return { key: "connecting", content: <ConnectingPrompt /> };
  }
  if (state.kind === "awaiting_confirmation") {
    return {
      key: "awaiting_confirmation",
      content: (
        <ConfirmationPrompt
          code={state.code}
          answer={state.answer}
          onSame={() => {
            onAnswerCode(true);
          }}
          onDifferent={() => {
            onAnswerCode(false);
          }}
        />
      ),
    };
  }
  return null;
}
