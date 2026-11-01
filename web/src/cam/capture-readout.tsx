import type { CaptureFormat } from "../data/cam-state";
import { t } from "../data/language";
import styles from "./capture-readout.module.scss";

interface CaptureReadoutProps {
  capture: CaptureFormat;
  dimmed: boolean;
}

export function CaptureReadout({ capture, dimmed }: CaptureReadoutProps) {
  return (
    <p className={styles.readout} data-dimmed={dimmed}>
      {t("cam.capture_format", {
        width: String(capture.width),
        height: String(capture.height),
        fps: String(capture.frameRate),
      })}
    </p>
  );
}
