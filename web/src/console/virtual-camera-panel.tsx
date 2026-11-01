import { cpuPercentValue } from "../data/console-format";
import type { VirtualCamera, VirtualCameraUnavailableReason } from "../data/contract";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import styles from "./virtual-camera-panel.module.scss";

interface VirtualCameraPanelProps {
  virtualCamera: VirtualCamera;
  process: { cpuPercent: number };
}

const REASON_KEYS: Readonly<Record<VirtualCameraUnavailableReason, MessageKey>> = {
  driver_missing: "console.virtual_camera_driver_missing",
  device_in_use: "console.virtual_camera_device_in_use",
  error: "console.virtual_camera_error",
};
const SOURCE_KEYS: Readonly<Record<VirtualCamera["source"], MessageKey>> = {
  phone: "console.source_phone",
  placeholder: "console.source_placeholder",
};

export function VirtualCameraPanel({ virtualCamera, process }: VirtualCameraPanelProps) {
  const active = virtualCamera.state === "active";
  return (
    <section className={styles.panel} data-state={virtualCamera.state}>
      <h2 className={styles.title}>
        <span className={styles.indicator} aria-hidden="true" />
        {t(active ? "console.virtual_camera_active" : "console.virtual_camera_unavailable")}
      </h2>
      <p className={styles.detail}>
        {active || virtualCamera.reason === null
          ? t(SOURCE_KEYS[virtualCamera.source])
          : t(REASON_KEYS[virtualCamera.reason])}
      </p>
      <p className={styles.cpu}>{t("console.cpu", { percent: cpuPercentValue(process.cpuPercent) })}</p>
    </section>
  );
}
