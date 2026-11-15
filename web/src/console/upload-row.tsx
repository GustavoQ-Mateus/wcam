import { X } from "lucide-react";
import { useId } from "react";
import { errorMessageKey } from "../data/i18n";
import { t } from "../data/language";
import type { UploadItem } from "../media/upload-queue";
import styles from "./video-library.module.scss";

const PERCENT = 100;

interface UploadRowProps {
  item: UploadItem;
  onDismiss: () => void;
}

export function UploadRow({ item, onDismiss }: UploadRowProps) {
  const labelId = useId();
  const percent = Math.round(item.fraction * PERCENT);
  if (item.state === "failed") {
    return (
      <li className={styles.row}>
        <div className={styles.rowText}>
          <p className={styles.name} title={item.name}>
            {item.name}
          </p>
          <p className={styles.error} role="alert">
            {t(errorMessageKey(item.errorCode ?? "unknown"))}
          </p>
        </div>
        <button type="button" className={styles.iconButton} aria-label={t("console.video_dismiss")} onClick={onDismiss}>
          <X className={styles.icon} aria-hidden="true" />
        </button>
      </li>
    );
  }
  return (
    <li className={styles.upload}>
      <div className={styles.uploadText}>
        <p className={styles.name} title={item.name}>
          {item.name}
        </p>
        <p id={labelId} className={styles.note}>
          {item.state === "queued"
            ? t("console.video_queued")
            : t("console.video_uploading", { percent: String(percent) })}
        </p>
      </div>
      <div
        className={styles.progress}
        role="progressbar"
        aria-labelledby={labelId}
        aria-valuemin={0}
        aria-valuemax={PERCENT}
        aria-valuenow={percent}
      >
        <div className={styles.fill} style={{ transform: `scaleX(${String(item.fraction)})` }} />
      </div>
    </li>
  );
}
