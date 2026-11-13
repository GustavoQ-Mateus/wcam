import type { ConsoleMode } from "../data/console-view";
import { t } from "../data/language";
import { ConsoleButton } from "./console-button";
import styles from "./preview-panel.module.scss";
import { StatusMark } from "./status-mark";

interface PreviewPanelProps {
  mode: ConsoleMode;
  previewOn: boolean;
  attachPreview: (video: HTMLVideoElement | null) => void;
  previewShowing: boolean;
  frozenSince: string | null;
  onUnfreeze: () => void;
  onCameraOn: () => void;
}

export function PreviewPanel({
  mode,
  previewOn,
  attachPreview,
  previewShowing,
  frozenSince,
  onUnfreeze,
  onCameraOn,
}: PreviewPanelProps) {
  const cameraOff = mode === "camera_off";
  const showVideo = previewOn && !cameraOff;
  return (
    <div className={styles.frame} data-mode={mode}>
      {showVideo && (
        <>
          <video ref={attachPreview} className={styles.video} autoPlay muted playsInline />
          {previewShowing && <span className={styles.label}>{t("console.preview_label")}</span>}
        </>
      )}
      {!previewOn && !cameraOff && <p className={styles.center}>{t("console.preview_hidden")}</p>}
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
