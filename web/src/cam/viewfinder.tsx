import type { RefObject } from "react";
import styles from "./viewfinder.module.scss";

interface ViewfinderProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  mirrored: boolean;
  visible: boolean;
}

export function Viewfinder({ videoRef, mirrored, visible }: ViewfinderProps) {
  return (
    <video
      ref={videoRef}
      className={styles.video}
      data-mirrored={mirrored}
      data-visible={visible}
      autoPlay
      muted
      playsInline
      aria-hidden="true"
    />
  );
}
