import { t } from "../data/language";
import type { ResizeEdge } from "../data/overlay";
import { PreviewPicture } from "../console/preview-picture";
import { useAppPreview } from "../media/use-app-preview";
import { useOverlayChannel } from "../media/use-overlay-channel";
import styles from "./overlay-preview.module.scss";

const RESIZE_EDGES: readonly ResizeEdge[] = [
  "top",
  "right",
  "bottom",
  "left",
  "topLeft",
  "topRight",
  "bottomLeft",
  "bottomRight",
];

export default function OverlayPreview() {
  const preview = useAppPreview(true);
  const { post } = useOverlayChannel();
  return (
    <div
      className={styles.preview}
      role="img"
      aria-label={t("overlay.preview")}
      onPointerDown={() => {
        post({ type: "window.drag" });
      }}
    >
      <PreviewPicture surface={preview.surface} hidden={preview.state === "waiting"} />
      {preview.state === "waiting" && <p className={styles.waiting}>{t("console.preview_waiting")}</p>}
      {RESIZE_EDGES.map((edge) => (
        <span
          key={edge}
          className={styles.edge}
          data-edge={edge}
          onPointerDown={(event) => {
            event.stopPropagation();
            post({ type: "window.resize", edge });
          }}
        />
      ))}
      <button
        type="button"
        className={styles.close}
        aria-label={t("overlay.preview_close")}
        onPointerDown={(event) => {
          event.stopPropagation();
        }}
        onClick={() => {
          post({ type: "floatingPreview.toggle" });
        }}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 6l12 12M18 6 6 18" />
        </svg>
      </button>
    </div>
  );
}
