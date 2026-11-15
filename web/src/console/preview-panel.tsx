import type { ConsoleMode } from "../data/console-view";
import { t } from "../data/language";
import type { PreviewState } from "../data/preview-state";
import { ConsoleButton } from "./console-button";
import styles from "./preview-panel.module.scss";
import { StatusMark } from "./status-mark";

interface PreviewPanelProps {
  mode: ConsoleMode;
  previewOn: boolean;
  attachPreview: (video: HTMLVideoElement | null) => void;
  previewState: PreviewState;
  frozenSince: string | null;
  onUnfreeze: () => void;
  onCameraOn: () => void;
  onShowPreviewAgain: () => void;
}

export function PreviewPanel({
  mode,
  previewOn,
  attachPreview,
  previewState,
  frozenSince,
  onUnfreeze,
  onCameraOn,
  onShowPreviewAgain,
}: PreviewPanelProps) {
  const cameraOff = mode === "camera_off";
  const previewStopped = previewOn && previewState === "stopped";
  return (
    <div className={styles.frame} data-mode={mode}>
      {previewOn && !previewStopped && (
        <video ref={attachPreview} className={styles.video} hidden={cameraOff} autoPlay muted playsInline />
      )}
      {previewState === "showing" && previewOn && !cameraOff && (
        <span className={styles.label}>{t("console.preview_label")}</span>
      )}
      {!previewOn && !cameraOff && <p className={styles.center}>{t("console.preview_hidden")}</p>}
      {previewStopped && !cameraOff && (
        <div className={styles.center}>
          <p>{t("console.preview_stopped")}</p>
          <ConsoleButton variant="primary" onClick={onShowPreviewAgain}>
            {t("console.preview_show_again")}
          </ConsoleButton>
        </div>
      )}
      {cameraOff && (
        <div className={styles.center}>
          <p className={styles.centerTitle}>{t("state.camera_off")}</p>
          <ConsoleButton variant="primary" onClick={onCameraOn}>
            {t("controls.camera_on")}
          </ConsoleButton>
        </div>
      )}
      {mode === "frozen" && (
        <div className={styles.notice}>
          <p className={styles.noticeText}>
            <StatusMark shape="square" tone="still" />
            {frozenSince ? t("console.frozen_since", { time: frozenSince }) : t("state.frozen")}
          </p>
          <ConsoleButton variant="primary" onClick={onUnfreeze}>
            {t("controls.unfreeze")}
          </ConsoleButton>
        </div>
      )}
      {mode === "lost" && (
        <div className={styles.notice}>
          <p className={styles.noticeText}>
            <StatusMark shape="triangle" tone="negative" />
            {t("state.lost")}
          </p>
        </div>
      )}
    </div>
  );
}
