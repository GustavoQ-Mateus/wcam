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
const LENS_Y = { user: 19, environment: 5 } as const;

export function PhonePanel({ session, facing, onChooseFacing }: PhonePanelProps) {
  const orientation = session.video?.orientation;
  const line = [facing && t(CAMERA_KEYS[facing]), orientation && t(ORIENTATION_KEYS[orientation])].filter(Boolean);
  return (
    <section className={styles.panel}>
      <h2 className={styles.title}>{t("console.phone_title")}</h2>
      <div className={styles.device}>
        <svg className={styles.phoneIcon} viewBox="0 0 24 24" aria-hidden="true">
          <rect x="6" y="2" width="12" height="20" rx="2" />
          {facing && <circle cx="12" cy={LENS_Y[facing]} r="1.6" />}
        </svg>
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
