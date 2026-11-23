import type { ConsoleMode } from "../data/console-view";
import { t } from "../data/language";
import type { PreviewState } from "../data/preview-state";
import type { PreviewSurface } from "../media/use-preview";
import { ConsoleButton } from "./console-button";
import { PreviewPicture } from "./preview-picture";
import styles from "./preview-panel.module.scss";
import { StatusMark } from "./status-mark";

interface PreviewPanelProps {
  mode: ConsoleMode;
  previewOn: boolean;
  previewSurface: PreviewSurface;
  previewState: PreviewState;
  frozenSince: string | null;
  onShowPreviewAgain: () => void;
}

export function PreviewPanel({
  mode,
  previewOn,
  previewSurface,
  previewState,
  frozenSince,
  onShowPreviewAgain,
}: PreviewPanelProps) {
  const cameraOff = mode === "camera_off";
  const previewStopped = previewOn && previewState === "stopped";
  return (
    <div className={styles.frame} data-mode={mode}>
      {previewOn && !previewStopped && <PreviewPicture surface={previewSurface} hidden={cameraOff} />}
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
        </div>
      )}
      {mode === "frozen" && (
        <div className={styles.notice}>
          <p className={styles.noticeText}>
            <StatusMark shape="square" tone="still" />
            {frozenSince ? t("console.frozen_since", { time: frozenSince }) : t("state.frozen")}
          </p>
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
