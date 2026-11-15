import { useId, useRef, useState, type DragEvent } from "react";
import type { VideoSource } from "../data/contract";
import { errorMessageKey } from "../data/i18n";
import { t } from "../data/language";
import type { VideoSourceActions } from "../data/use-video-source";
import { formatClock } from "../data/video-position";
import { ConsoleButton } from "./console-button";
import styles from "./video-panel.module.scss";

interface VideoPanelProps {
  videoSource: VideoSource;
  actions: VideoSourceActions;
}

const PERCENT = 100;
const VIDEO_TYPES = "video/*,.mov,.mkv";

export function VideoPanel({ videoSource, actions }: VideoPanelProps) {
  const titleId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const { file, active } = videoSource;
  const uploading = actions.uploadFraction !== null;
  const chooseFile = () => {
    inputRef.current?.click();
  };
  const dropFile = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) {
      actions.choose(dropped);
    }
  };
  return (
    <section
      className={styles.panel}
      aria-labelledby={titleId}
      data-dragging={dragging}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setDragging(false);
        }
      }}
      onDrop={dropFile}
    >
      <h2 id={titleId} className={styles.title}>
        {t("console.video_title")}
      </h2>
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept={VIDEO_TYPES}
        tabIndex={-1}
        aria-hidden="true"
        onChange={(event) => {
          const chosen = event.currentTarget.files?.[0];
          event.currentTarget.value = "";
          if (chosen) {
            actions.choose(chosen);
          }
        }}
      />
      {file && !uploading && (
        <div className={styles.file}>
          <p className={styles.name} title={file.name}>
            {file.name}
          </p>
          <p className={styles.note}>{t("console.video_duration", { duration: formatClock(file.durationSeconds) })}</p>
        </div>
      )}
      {active && <p className={styles.note}>{t("console.video_not_live")}</p>}
      {uploading && <UploadProgress fraction={actions.uploadFraction ?? 0} />}
      {!file && !uploading && (
        <div className={styles.empty}>
          <ConsoleButton variant="secondary" onClick={chooseFile}>
            {t("console.video_choose")}
          </ConsoleButton>
          <p className={styles.note}>{t("console.video_drop")}</p>
        </div>
      )}
      {file && !uploading && (
        <div className={styles.actions}>
          {!active && (
            <ConsoleButton variant="primary" onClick={actions.use}>
              {t("controls.use_video")}
            </ConsoleButton>
          )}
          <button type="button" className={styles.link} onClick={chooseFile}>
            {t("console.video_replace")}
          </button>
          <button type="button" className={styles.link} onClick={actions.remove}>
            {t("console.video_remove")}
          </button>
        </div>
      )}
      {actions.errorCode && (
        <p className={styles.error} role="alert">
          {t(errorMessageKey(actions.errorCode))}
        </p>
      )}
    </section>
  );
}

function UploadProgress({ fraction }: { fraction: number }) {
  const labelId = useId();
  const percent = Math.round(fraction * PERCENT);
  return (
    <div className={styles.progress}>
      <p id={labelId} className={styles.note}>
        {t("console.video_uploading", { percent: String(percent) })}
      </p>
      <div
        className={styles.track}
        role="progressbar"
        aria-labelledby={labelId}
        aria-valuemin={0}
        aria-valuemax={PERCENT}
        aria-valuenow={percent}
      >
        <div className={styles.fill} style={{ transform: `scaleX(${String(fraction)})` }} />
      </div>
    </div>
  );
}
