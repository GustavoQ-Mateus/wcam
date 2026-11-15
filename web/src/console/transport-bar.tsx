import { t } from "../data/language";
import controls from "./control-bar.module.scss";
import { PlaybackClock } from "./playback-clock";
import styles from "./transport-bar.module.scss";

interface TransportBarProps {
  active: boolean;
  frozen: boolean;
  mirror: boolean;
  duration: number;
  positionAt: (now: number) => number;
  canUse: boolean;
  canSplit: boolean;
  canDelete: boolean;
  canZoomIn: boolean;
  canZoomOut: boolean;
  previewOn: boolean;
  previewStopped: boolean;
  onTogglePause: () => void;
  onSplit: () => void;
  onDelete: () => void;
  onZoom: (direction: 1 | -1) => void;
  onMirror: () => void;
  onTogglePreview: () => void;
  onUse: () => void;
  onBackToCamera: () => void;
}

export function TransportBar({
  active,
  frozen,
  mirror,
  duration,
  positionAt,
  canUse,
  canSplit,
  canDelete,
  canZoomIn,
  canZoomOut,
  previewOn,
  previewStopped,
  onTogglePause,
  onSplit,
  onDelete,
  onZoom,
  onMirror,
  onTogglePreview,
  onUse,
  onBackToCamera,
}: TransportBarProps) {
  return (
    <div className={styles.bar}>
      <div className={styles.group}>
        {active && (
          <button type="button" className={controls.control} aria-pressed={frozen} onClick={onTogglePause}>
            {t(frozen ? "console.timeline_play" : "console.timeline_pause")}
          </button>
        )}
        <PlaybackClock duration={duration} positionAt={positionAt} />
      </div>
      <div className={styles.group}>
        <button type="button" className={controls.control} disabled={!canSplit} onClick={onSplit}>
          {t("console.timeline_split")}
        </button>
        <button type="button" className={controls.control} disabled={!canDelete} onClick={onDelete}>
          {t("console.timeline_delete")}
        </button>
        <button
          type="button"
          className={controls.control}
          disabled={!canZoomOut}
          onClick={() => {
            onZoom(-1);
          }}
        >
          {t("console.timeline_zoom_out")}
        </button>
        <button
          type="button"
          className={controls.control}
          disabled={!canZoomIn}
          onClick={() => {
            onZoom(1);
          }}
        >
          {t("console.timeline_zoom_in")}
        </button>
      </div>
      <div className={styles.end}>
        <button type="button" className={controls.control} aria-pressed={mirror} onClick={onMirror}>
          {t("controls.mirror")}
        </button>
        {!previewStopped && (
          <button type="button" className={controls.control} onClick={onTogglePreview}>
            {t(previewOn ? "controls.preview_off" : "controls.preview_on")}
          </button>
        )}
        {active ? (
          <button type="button" className={styles.primary} onClick={onBackToCamera}>
            {t("controls.back_to_phone")}
          </button>
        ) : (
          <>
            <button type="button" className={controls.control} onClick={onBackToCamera}>
              {t("controls.back_to_phone")}
            </button>
            <button type="button" className={styles.primary} disabled={!canUse} onClick={onUse}>
              {t("controls.use_video")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
