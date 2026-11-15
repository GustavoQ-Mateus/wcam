import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { LibraryVideo } from "../data/contract";
import { t } from "../data/language";
import { LIBRARY_VIDEO_TYPE } from "../data/timeline";
import { formatClock } from "../data/video-position";
import { LibraryThumb } from "./library-thumb";
import styles from "./video-library.module.scss";

interface LibraryRowProps {
  video: LibraryVideo;
  inUse: boolean;
  onAdd: () => void;
  onRemove: () => void;
}

export function LibraryRow({ video, inUse, onAdd, onRemove }: LibraryRowProps) {
  const [confirming, setConfirming] = useState(false);
  if (confirming) {
    return (
      <li className={styles.confirm}>
        <p className={styles.note}>{t("console.video_remove_in_use")}</p>
        <div className={styles.confirmActions}>
          <button type="button" className={styles.danger} onClick={onRemove}>
            {t("console.video_remove")}
          </button>
          <button
            type="button"
            className={styles.link}
            onClick={() => {
              setConfirming(false);
            }}
          >
            {t("console.video_keep")}
          </button>
        </div>
      </li>
    );
  }
  return (
    <li
      className={styles.row}
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData(LIBRARY_VIDEO_TYPE, video.id);
        event.dataTransfer.effectAllowed = "copy";
      }}
    >
      <LibraryThumb video={video} />
      <div className={styles.rowText}>
        <p className={styles.name} title={video.name}>
          {video.name}
        </p>
        <p className={styles.note}>{formatClock(video.durationSeconds)}</p>
      </div>
      <button type="button" className={styles.iconButton} aria-label={t("console.video_add")} onClick={onAdd}>
        <Plus className={styles.icon} aria-hidden="true" />
      </button>
      <button
        type="button"
        className={styles.iconButton}
        aria-label={t("console.video_remove")}
        onClick={() => {
          if (inUse) {
            setConfirming(true);
            return;
          }
          onRemove();
        }}
      >
        <Trash2 className={styles.icon} aria-hidden="true" />
      </button>
    </li>
  );
}
