import type { PreviewSurface } from "../media/use-preview";
import styles from "./preview-panel.module.scss";

interface PreviewPictureProps {
  surface: PreviewSurface;
  hidden: boolean;
}

export function PreviewPicture({ surface, hidden }: PreviewPictureProps) {
  if (surface.kind === "canvas") {
    const { attach } = surface;
    return <canvas ref={attach} className={styles.video} hidden={hidden} />;
  }
  const { attach } = surface;
  return <video ref={attach} className={styles.video} hidden={hidden} autoPlay muted playsInline />;
}
