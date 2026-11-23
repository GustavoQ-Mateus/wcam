import type { Badge } from "../data/console-view";
import { stateBadge } from "../data/console-view";
import { t } from "../data/language";
import { useConsole } from "../data/use-console";
import { StatusMark } from "../console/status-mark";
import { useOverlayChannel } from "../media/use-overlay-channel";
import { CameraGlyph } from "./camera-glyph";
import styles from "./overlay-icon.module.scss";

const NO_PHONE_BADGE: Badge = { key: "state.waiting", tone: "neutral", shape: "ring" };

export default function OverlayIcon() {
  const { status } = useConsole();
  const { post } = useOverlayChannel();
  const badge = status ? stateBadge(status) : NO_PHONE_BADGE;
  return (
    <button
      type="button"
      className={styles.icon}
      aria-label={`${t("overlay.icon")}: ${t(badge.key)}`}
      title={t("overlay.drag_hint")}
      onPointerDown={(event) => {
        if (event.ctrlKey) {
          post({ type: "window.drag" });
        }
      }}
      onClick={(event) => {
        if (!event.ctrlKey) {
          post({ type: "panel.open" });
        }
      }}
    >
      <CameraGlyph />
      <span className={styles.mark}>
        <StatusMark shape={badge.shape} tone={badge.tone} />
      </span>
    </button>
  );
}
