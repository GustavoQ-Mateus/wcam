import { useId, useRef, useState, type DragEvent } from "react";
import type { LibraryVideo, TimelineClip } from "../data/contract";
import { t } from "../data/language";
import { MAX_VIDEOS, videoInUse } from "../data/timeline";
import type { UploadItem } from "../media/upload-queue";
import { ConsoleButton } from "./console-button";
import { LibraryRow } from "./library-row";
import { UploadRow } from "./upload-row";
import styles from "./video-library.module.scss";

const VIDEO_TYPES = "video/*,.mov,.mkv";

interface VideoLibraryProps {
  videos: readonly LibraryVideo[];
  clips: readonly TimelineClip[];
  uploads: readonly UploadItem[];
  canSend: boolean;
  onAddFiles: (files: File[]) => void;
  onDismissUpload: (id: string) => void;
  onAddToTimeline: (videoId: string) => void;
  onRemove: (videoId: string) => void;
}

export function VideoLibrary({
  videos,
  clips,
  uploads,
  canSend,
  onAddFiles,
  onDismissUpload,
  onAddToTimeline,
  onRemove,
}: VideoLibraryProps) {
  const titleId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const full = videos.length >= MAX_VIDEOS;
  const acceptsFiles = canSend && !full;
  const dropFiles = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const files = [...event.dataTransfer.files];
    if (acceptsFiles && files.length > 0) {
      onAddFiles(files);
    }
  };
  return (
    <section
      className={styles.panel}
      aria-labelledby={titleId}
      data-dragging={dragging}
      onDragOver={(event) => {
        if (acceptsFiles && event.dataTransfer.types.includes("Files")) {
          event.preventDefault();
          setDragging(true);
        }
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setDragging(false);
        }
      }}
      onDrop={dropFiles}
    >
      <div className={styles.header}>
        <h2 id={titleId} className={styles.title}>
          {t("console.video_library")}
        </h2>
        <ConsoleButton
          variant="secondary"
          disabled={!acceptsFiles}
          onClick={() => {
            inputRef.current?.click();
          }}
        >
          {t("console.video_choose")}
        </ConsoleButton>
      </div>
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept={VIDEO_TYPES}
        multiple
        tabIndex={-1}
        aria-hidden="true"
        onChange={(event) => {
          const files = [...(event.currentTarget.files ?? [])];
          event.currentTarget.value = "";
          if (files.length > 0) {
            onAddFiles(files);
          }
        }}
      />
      {!canSend && <p className={styles.note}>{t("console.video_needs_phone")}</p>}
      {full && <p className={styles.note}>{t("errors.video_library_full")}</p>}
      {canSend && !full && videos.length === 0 && uploads.length === 0 && (
        <p className={styles.note}>{t("console.video_drop")}</p>
      )}
      {(videos.length > 0 || uploads.length > 0) && (
        <ul className={styles.list}>
          {videos.map((video) => (
            <LibraryRow
              key={video.id}
              video={video}
              inUse={videoInUse(clips, video.id)}
              onAdd={() => {
                onAddToTimeline(video.id);
              }}
              onRemove={() => {
                onRemove(video.id);
              }}
            />
          ))}
          {uploads.map((item) => (
            <UploadRow
              key={item.id}
              item={item}
              onDismiss={() => {
                onDismissUpload(item.id);
              }}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
