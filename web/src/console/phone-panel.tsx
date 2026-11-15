import { Smartphone } from "lucide-react";
import type { Facing } from "../data/cam-state";
import type { Session } from "../data/contract";
import { t } from "../data/language";
import styles from "./side-panel.module.scss";

interface PhonePanelProps {
  session: Session;
  facing: Facing | null;
  onChooseFacing: (facing: Facing) => void;
}

const FACINGS: readonly Facing[] = ["user", "environment"];
const CAMERA_KEYS = { user: "camera.front", environment: "camera.back" } as const;
const ORIENTATION_KEYS = {
  landscape: "console.orientation_landscape",
  portrait: "console.orientation_portrait",
} as const;

export function PhonePanel({ session, facing, onChooseFacing }: PhonePanelProps) {
  const orientation = session.video?.orientation;
  const line = [facing && t(CAMERA_KEYS[facing]), orientation && t(ORIENTATION_KEYS[orientation])].filter(Boolean);
  return (
    <section className={styles.panel}>
      <h2 className={styles.title}>{t("console.phone_title")}</h2>
      <div className={styles.device}>
        <Smartphone className={styles.phoneIcon} aria-hidden="true" />
        <div>
          <p className={styles.deviceName}>{session.deviceName ?? t("console.device_unknown")}</p>
          {line.length > 0 && <p className={styles.note}>{line.join(" · ")}</p>}
        </div>
      </div>
      <div className={styles.segments}>
        {FACINGS.map((option) => (
          <button
            key={option}
            type="button"
            className={styles.segment}
            aria-pressed={facing === option}
            onClick={() => {
              onChooseFacing(option);
            }}
          >
            {t(CAMERA_KEYS[option])}
          </button>
        ))}
      </div>
    </section>
  );
}
